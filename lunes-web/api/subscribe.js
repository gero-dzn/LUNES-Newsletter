'use strict';

const crypto = require('crypto');
const { Resend } = require('resend');
const fs = require('fs');
const path = require('path');

const TOKEN_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 días

const resend = new Resend(process.env.RESEND_API_KEY);

function makeToken(email, contactId) {
  const payload = Buffer.from(
    JSON.stringify({ email, id: contactId, exp: Date.now() + TOKEN_TTL_MS })
  ).toString('base64url');
  const sig = crypto
    .createHmac('sha256', process.env.HMAC_SECRET)
    .update(payload)
    .digest('hex');
  return `${payload}.${sig}`;
}

function renderHtml(filename, vars) {
  let html = fs.readFileSync(path.join(__dirname, '..', 'emails', filename), 'utf-8');
  for (const [k, v] of Object.entries(vars)) {
    html = html.replace(new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'g'), v);
  }
  return html;
}

module.exports = async function handler(req, res) {
  // CORS — public subscription form, double opt-in keeps it safe
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST')   return res.status(405).json({ error: 'Method not allowed' });

  // Parse body (Vercel auto-parsea JSON, pero cubrimos el caso string por las dudas)
  let body = req.body ?? {};
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }

  const email = String(body.email ?? '').trim().toLowerCase();
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return res.status(400).json({ error: 'Email inválido.' });
  }

  // Agregar contacto como UNSUBSCRIBED (pendiente de confirmación)
  // Si ya existe, lo tratamos como re-suscripción: volvemos a enviar el mail de confirmación
  let contact;
  const { data: createData, error: createErr } = await resend.contacts.create({
    audienceId:   process.env.RESEND_AUDIENCE_ID,
    email,
    unsubscribed: true,
  });

  if (createErr) {
    // Si el contacto ya existe en Resend el error tiene name/type de conflicto;
    // buscamos el contacto existente para re-enviar la confirmación
    if (createErr.name === 'validation_error' || createErr.statusCode === 409 ||
        (createErr.message && createErr.message.toLowerCase().includes('already exists'))) {
      console.log('[subscribe] contact already exists, listing to find id');
      const { data: listData, error: listErr } = await resend.contacts.list({
        audienceId: process.env.RESEND_AUDIENCE_ID,
      });
      if (listErr || !listData?.data) {
        console.error('[subscribe] contacts.list failed:', listErr);
        return res.status(500).json({ error: 'Error al registrar. Intentá de nuevo.' });
      }
      const existing = listData.data.find(c => c.email === email);
      if (!existing) {
        console.error('[subscribe] existing contact not found after conflict');
        return res.status(500).json({ error: 'Error al registrar. Intentá de nuevo.' });
      }
      contact = existing;
      console.log('[subscribe] re-using existing contact:', contact.id);
    } else {
      console.error('contacts.create:', JSON.stringify(createErr));
      return res.status(500).json({ error: 'Error al registrar. Intentá de nuevo.' });
    }
  } else {
    contact = createData;
  }

  // Token firmado con email + contactId + expiración
  const token = makeToken(email, contact.id);
  // || en vez de ?? para que string vacío también active el fallback
  const apiBase = (process.env.API_BASE_URL || '').trim()
    || (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'https://lunes-newsletter.vercel.app');
  const confirmUrl = `${apiBase}/api/confirm?token=${encodeURIComponent(token)}`;
  console.log('[subscribe] apiBase:', apiBase);
  console.log('[subscribe] confirmUrl:', confirmUrl.slice(0, 80) + '...');

  // Renderizar y enviar mail de confirmación
  const html = renderHtml('confirm.html', { confirm_url: confirmUrl });

  const { error: emailErr } = await resend.emails.send({
    from:    process.env.FROM_EMAIL,
    to:      email,
    subject: 'Confirmá tu suscripción a LUNES',
    html,
    ...(process.env.REPLY_TO ? { replyTo: process.env.REPLY_TO } : {}),
  });

  if (emailErr) {
    console.error('emails.send:', emailErr);
    return res.status(500).json({ error: 'Error al enviar la confirmación.' });
  }

  return res.status(200).json({ ok: true });
};

'use strict';

const crypto = require('crypto');
const { Resend } = require('resend');
const fs = require('fs');
const path = require('path');

const ALLOWED_ORIGIN = 'https://geronimogentili.com';
const TOKEN_TTL_MS   = 24 * 60 * 60 * 1000; // 24 h

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
  // CORS — solo geronimogentili.com
  if (req.headers.origin === ALLOWED_ORIGIN) {
    res.setHeader('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  }
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Vary', 'Origin');

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
  const { data: contact, error: contactErr } = await resend.contacts.create({
    audienceId:   process.env.RESEND_AUDIENCE_ID,
    email,
    unsubscribed: true,
  });

  if (contactErr) {
    console.error('contacts.create:', contactErr);
    return res.status(500).json({ error: 'Error al registrar. Intentá de nuevo.' });
  }

  // Token firmado con email + contactId + expiración
  const token = makeToken(email, contact.id);
  const apiBase = process.env.API_BASE_URL
    ?? (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000');
  const confirmUrl = `${apiBase}/api/confirm?token=${encodeURIComponent(token)}`;

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

'use strict';

const crypto = require('crypto');
const { Resend } = require('resend');
const fs = require('fs');
const path = require('path');

const REDIRECT_OK  = 'https://geronimogentili.com/lunes/confirmado';
const REDIRECT_ERR = 'https://geronimogentili.com/lunes/confirmado?error=1';

const resend = new Resend(process.env.RESEND_API_KEY);

function verifyToken(raw) {
  const dot = raw.lastIndexOf('.');
  if (dot === -1) return null;

  const payload = raw.slice(0, dot);
  const sig     = raw.slice(dot + 1);

  const expected = crypto
    .createHmac('sha256', process.env.HMAC_SECRET)
    .update(payload)
    .digest('hex');

  // timingSafeEqual requiere buffers del mismo tamaño
  if (sig.length !== expected.length) return null;
  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null;

  const data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8'));
  if (Date.now() > data.exp) return null; // expirado
  return data;
}

function renderHtml(filename, vars) {
  let html = fs.readFileSync(path.join(__dirname, '..', 'emails', filename), 'utf-8');
  for (const [k, v] of Object.entries(vars)) {
    html = html.replace(new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'g'), v);
  }
  return html;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();

  const raw = String(req.query?.token ?? '');
  if (!raw) return res.redirect(302, REDIRECT_ERR);

  let data;
  try {
    data = verifyToken(raw);
  } catch {
    return res.redirect(302, REDIRECT_ERR);
  }

  if (!data) {
    // Token inválido o expirado — redirigir con flag de error para mostrar mensaje
    return res.redirect(302, REDIRECT_ERR);
  }

  const { email, id: contactId } = data;

  // Flipear contacto a SUBSCRIBED
  const { error: updateErr } = await resend.contacts.update({
    audienceId:   process.env.RESEND_AUDIENCE_ID,
    id:           contactId,
    unsubscribed: false,
  });

  if (updateErr) {
    console.error('contacts.update:', updateErr);
    return res.redirect(302, REDIRECT_ERR);
  }

  // Enviar bienvenida (fire-and-forget: si falla no bloquea la confirmación)
  const html = renderHtml('welcome.html', {
    unsubscribe_url: 'https://geronimogentili.com/lunes/baja', // Fase 5
  });
  resend.emails.send({
    from:    process.env.FROM_EMAIL,
    to:      email,
    subject: 'Bienvenido a LUNES',
    html,
    ...(process.env.REPLY_TO ? { replyTo: process.env.REPLY_TO } : {}),
  }).catch(err => console.error('welcome email:', err));

  return res.redirect(302, REDIRECT_OK);
};

'use strict';

const crypto = require('crypto');
const { Resend } = require('resend');
const fs = require('fs');
const path = require('path');

const REDIRECT_OK  = 'https://geronimogentili.com/lunes/confirmado';
const REDIRECT_ERR = 'https://geronimogentili.com/lunes/confirmado?error=1';

const resend = new Resend(process.env.RESEND_API_KEY);

function verifyToken(raw) {
  if (!process.env.HMAC_SECRET) {
    console.error('[confirm] HMAC_SECRET is not set');
    return null;
  }

  const dot = raw.lastIndexOf('.');
  if (dot === -1) {
    console.error('[confirm] token has no dot separator');
    return null;
  }

  const payload = raw.slice(0, dot);
  const sig     = raw.slice(dot + 1);

  const expected = crypto
    .createHmac('sha256', process.env.HMAC_SECRET)
    .update(payload)
    .digest('hex');

  if (sig.length !== expected.length) {
    console.error('[confirm] sig length mismatch: got', sig.length, 'expected', expected.length);
    return null;
  }

  if (!crypto.timingSafeEqual(Buffer.from(sig, 'utf8'), Buffer.from(expected, 'utf8'))) {
    console.error('[confirm] HMAC signature mismatch');
    return null;
  }

  let data;
  try {
    data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8'));
  } catch (e) {
    console.error('[confirm] payload parse error:', e.message);
    return null;
  }

  if (Date.now() > data.exp) {
    console.error('[confirm] token expired at', new Date(data.exp).toISOString());
    return null;
  }

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

  console.log('[confirm] req.url:', req.url);
  console.log('[confirm] req.query:', JSON.stringify(req.query));
  const raw = String(req.query?.token ?? '');
  console.log('[confirm] token length:', raw.length, '| RESEND_AUDIENCE_ID set:', !!process.env.RESEND_AUDIENCE_ID);

  if (!raw) return res.redirect(302, REDIRECT_ERR);

  let data;
  try {
    data = verifyToken(raw);
  } catch (e) {
    console.error('[confirm] verifyToken threw:', e.message);
    return res.redirect(302, REDIRECT_ERR);
  }

  if (!data) {
    console.error('[confirm] token invalid — redirecting to error');
    return res.redirect(302, REDIRECT_ERR);
  }

  const { email, id: contactId } = data;
  console.log('[confirm] token OK — email:', email, '| contactId:', contactId);

  // Flipear contacto a SUBSCRIBED
  const { data: updateData, error: updateErr } = await resend.contacts.update({
    audienceId:   process.env.RESEND_AUDIENCE_ID,
    id:           contactId,
    unsubscribed: false,
  });

  console.log('[confirm] contacts.update →', JSON.stringify({ data: updateData, error: updateErr }));

  if (updateErr) {
    console.error('[confirm] contacts.update failed:', JSON.stringify(updateErr));
    return res.redirect(302, REDIRECT_ERR);
  }

  // Enviar bienvenida (fire-and-forget)
  const html = renderHtml('welcome.html', {
    unsubscribe_url: 'https://geronimogentili.com/lunes/baja',
  });
  resend.emails.send({
    from:    process.env.FROM_EMAIL,
    to:      email,
    subject: 'Bienvenido/a a LUNES',
    html,
    ...(process.env.REPLY_TO ? { replyTo: process.env.REPLY_TO } : {}),
  }).catch(err => console.error('[confirm] welcome email error:', err.message));

  console.log('[confirm] success — redirecting to OK');
  return res.redirect(302, REDIRECT_OK);
};

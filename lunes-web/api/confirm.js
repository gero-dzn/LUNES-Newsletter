'use strict';

const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');

const REDIRECT_OK  = 'https://geronimogentili.com/lunes/confirmado';
const REDIRECT_ERR = 'https://geronimogentili.com/lunes/confirmado?error=1';

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
  let raw = String(req.query?.token ?? '');

  if (!raw && req.url) {
    try {
      const u = new URL(req.url, 'https://placeholder.invalid');
      raw = u.searchParams.get('token') ?? '';
      if (raw) console.log('[confirm] token recovered from req.url fallback');
    } catch (e) {
      console.error('[confirm] URL parse fallback error:', e.message);
    }
  }

  console.log('[confirm] token length:', raw.length);
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

  // Flipear contacto a SUBSCRIBED usando fetch directo (evita incompatibilidades del SDK)
  const updateResp = await fetch(
    `https://api.resend.com/audiences/${process.env.RESEND_AUDIENCE_ID}/contacts/${contactId}`,
    {
      method:  'PATCH',
      headers: {
        'Authorization': `Bearer ${process.env.RESEND_API_KEY}`,
        'Content-Type':  'application/json',
      },
      body: JSON.stringify({ unsubscribed: false }),
    }
  );

  if (!updateResp.ok) {
    const errBody = await updateResp.text();
    console.error('[confirm] contacts.update failed:', updateResp.status, errBody.slice(0, 300));
    return res.redirect(302, REDIRECT_ERR);
  }

  console.log('[confirm] contact updated → subscribed  (email:', email, ')');

  // Enviar bienvenida (fire-and-forget)
  const html = renderHtml('welcome.html', {
    unsubscribe_url: 'https://geronimogentili.com/lunes/baja',
  });
  fetch('https://api.resend.com/emails', {
    method:  'POST',
    headers: {
      'Authorization': `Bearer ${process.env.RESEND_API_KEY}`,
      'Content-Type':  'application/json',
    },
    body: JSON.stringify({
      from:    process.env.FROM_EMAIL,
      to:      [email],
      subject: 'Bienvenido/a a LUNES',
      html,
      ...(process.env.REPLY_TO ? { reply_to: process.env.REPLY_TO } : {}),
    }),
  }).catch(err => console.error('[confirm] welcome email error:', err.message));

  console.log('[confirm] success — redirecting to OK');
  return res.redirect(302, REDIRECT_OK);
};

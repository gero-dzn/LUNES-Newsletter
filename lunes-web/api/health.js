'use strict';

module.exports = function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();

  const vars = [
    'RESEND_API_KEY',
    'RESEND_AUDIENCE_ID',
    'FROM_EMAIL',
    'REPLY_TO',
    'HMAC_SECRET',
    'API_BASE_URL',
    'VERCEL_URL',
  ];

  const status = {};
  for (const v of vars) {
    const val = process.env[v];
    status[v] = val ? `set (${val.length} chars)` : 'MISSING';
  }

  return res.status(200).json({ ok: true, env: status });
};

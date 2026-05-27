'use strict';

const GITHUB_RAW = 'https://raw.githubusercontent.com/gero-dzn/LUNES-Newsletter/main/archive';

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();

  const slug = String(req.query?.slug ?? '').trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(slug)) {
    return res.status(400).send('slug inválido. Formato esperado: YYYY-MM-DD');
  }

  const url = `${GITHUB_RAW}/${slug}.html`;
  const upstream = await fetch(url, { headers: { 'User-Agent': 'lunes-newsletter/1.0' } });

  if (upstream.status === 404) {
    return res.status(404).send('Edición no encontrada.');
  }
  if (!upstream.ok) {
    return res.status(502).send(`GitHub respondió ${upstream.status}`);
  }

  const html = await upstream.text();

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 's-maxage=86400, stale-while-revalidate=3600');
  return res.status(200).send(html);
};

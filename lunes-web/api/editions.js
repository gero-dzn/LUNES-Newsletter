'use strict';

const GITHUB_API   = 'https://api.github.com/repos/gero-dzn/LUNES-Newsletter/contents/archive';
const GITHUB_RAW   = 'https://raw.githubusercontent.com/gero-dzn/LUNES-Newsletter/main/archive';
const MAX_EDITIONS = 6;

const SECTION_TAGS = {
  lead:      ':: Lo de la semana',
  tldr:      ':: TL;DR',
  radar:     ':: Radar',
  ai:        ':: IA Aplicada',
  try_this:  ':: Para probar',
  type_pick: ':: Tipografía',
  craft:     ':: Craft',
};

const MONTHS = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
const ACCENTS = ['#FF4D12', '#211B17', '#5C534C'];

function formatDate(dateStr) {
  const [y, m, d] = dateStr.split('-');
  return `${parseInt(d)} ${MONTHS[parseInt(m) - 1]} ${y}`;
}

function truncate(str, len) {
  if (!str || typeof str !== 'string') return '';
  str = str.trim();
  return str.length > len ? str.slice(0, len).trimEnd() + '…' : str;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();

  res.setHeader('Access-Control-Allow-Origin', '*');
  // Cache 1 hour on Vercel edge, serve stale while revalidating
  res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate=600');

  try {
    const listRes = await fetch(GITHUB_API, {
      headers: { 'User-Agent': 'lunes-newsletter/1.0' },
    });
    if (!listRes.ok) throw new Error(`GitHub API responded ${listRes.status}`);

    const files = await listRes.json();
    const jsonFiles = files
      .filter(f => f.type === 'file' && /^\d{4}-\d{2}-\d{2}\.json$/.test(f.name))
      .sort((a, b) => b.name.localeCompare(a.name)); // newest first

    const total   = jsonFiles.length;
    const toFetch = jsonFiles.slice(0, MAX_EDITIONS);

    const editions = await Promise.all(toFetch.map(async (f, i) => {
      try {
        const rawRes = await fetch(`${GITHUB_RAW}/${f.name}`);
        if (!rawRes.ok) return null;
        const data = await rawRes.json();
        const c    = data.curation || {};

        const tags = Object.keys(SECTION_TAGS)
          .filter(k => {
            const v = c[k];
            return v && (Array.isArray(v) ? v.length > 0 : Object.keys(v).length > 0);
          })
          .slice(0, 3)
          .map(k => SECTION_TAGS[k]);

        return {
          num:    `#${String(total - i).padStart(2, '0')}`,
          date:   formatDate(f.name.replace('.json', '')),
          accent: ACCENTS[i % 3],
          title:  truncate(c.lead?.title || c.subject || 'Edición LUNES', 65),
          sub:    truncate(
            Array.isArray(c.tldr) ? c.tldr[0]
              : typeof c.tldr === 'string' ? c.tldr
              : c.lead?.summary || '',
            110
          ),
          tags,
        };
      } catch {
        return null;
      }
    }));

    return res.status(200).json({ editions: editions.filter(Boolean) });
  } catch (err) {
    console.error('[editions]', err.message);
    return res.status(500).json({ error: 'No se pudieron cargar las ediciones.' });
  }
};

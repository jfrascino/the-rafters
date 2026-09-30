// Shared helpers: escaping, formatting, data loading, small UI atoms.
export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => [...r.querySelectorAll(s)];
export const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const cache = new Map();
export function load(path) {
  if (!cache.has(path)) {
    // core.json is always revalidated; its timestamp versions every other file so updates after a game show up at once
    const req = path === 'core.json'
      ? fetch('data/core.json', { cache: 'no-cache' })
      : load('core.json').then((c) => fetch(`data/${path}?v=${encodeURIComponent(c.updated || '0')}`));
    cache.set(path, req.then((r) => {
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    }).catch((e) => { cache.delete(path); throw e; }));
  }
  return cache.get(path);
}
export const tryLoad = (p) => load(p).catch(() => null);

// Numbers
export const n1 = (v) => (v == null || isNaN(v) ? '–' : (+v).toFixed(1));
export const n0 = (v) => (v == null || isNaN(v) ? '–' : Math.round(+v).toLocaleString());
export const pct = (v) => (v == null || isNaN(v) ? '–' : (v >= 1 && v <= 100 ? (+v).toFixed(1) : (v * 100).toFixed(1)));
export const pct3 = (v) => (v == null || isNaN(v) ? '–' : (+v).toFixed(3).replace(/^0/, ''));
export const sign = (v) => (v > 0 ? `+${v}` : `${v}`);
export const ord = (n) => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };

// Dates
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export function parseDate(d) { if (!d) return null; const x = new Date(d.length === 10 ? d + 'T12:00:00' : d); return isNaN(x) ? null : x; }
export function fmtDate(d, o = {}) {
  const x = parseDate(d); if (!x) return '';
  const s = `${MON[x.getMonth()]} ${x.getDate()}`;
  return o.year ? `${s}, ${x.getFullYear()}` : s;
}
export function fmtDay(d) { const x = parseDate(d); return x ? x.toLocaleDateString('en-US', { weekday: 'short' }) : ''; }
export function fmtTime(d) {
  const x = parseDate(d); if (!x || d.length === 10) return '';
  // ESPN stores "time TBA" games at 05:00Z / 04:00Z (midnight Eastern)
  const et = x.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' });
  return et === '12:00 AM' ? 'TBA' : `${et} ET`;
}
export const seasonLabel = (y) => `${y - 1}–${String(y).slice(2)}`;

// Finish ladder (deepest postseason result)
export const FINISH = {
  champ: { label: 'National Champions', short: 'Champs', rank: 7, color: 'var(--gold)' },
  runner: { label: 'National Runner-up', short: 'Runner-up', rank: 6.5, color: '#cfa85a' },
  final4: { label: 'Final Four', short: 'Final Four', rank: 6, color: '#b99a5e' },
  elite8: { label: 'Elite Eight', short: 'Elite 8', rank: 5, color: '#8fc1ff' },
  sweet16: { label: 'Sweet 16', short: 'Sweet 16', rank: 4, color: '#5f97db' },
  r32: { label: 'NCAA Round of 32', short: 'Rd of 32', rank: 3, color: '#3e6fb0' },
  r64: { label: 'NCAA First Round', short: 'Rd of 64', rank: 2, color: '#2f5388' },
  nit: { label: 'NIT', short: 'NIT', rank: 1, color: '#6b7489' },
  none: { label: 'No postseason', short: '—', rank: 0, color: '#3a4458' },
};
export function finishPill(f, extra = '') {
  const F = FINISH[f] || FINISH.none;
  const cls = f === 'champ' ? 'champ' : f === 'final4' || f === 'runner' ? 'ff' : f === 'none' ? '' : 'ice';
  return `<span class="pill ${cls}">${f === 'champ' ? '★ ' : ''}${esc(F.label)}${extra}</span>`;
}

// Logos & photos
export function logo(team, cls = '') {
  if (!team) return '';
  const src = team.logo;
  const ab = esc((team.abbr || team.name || '?').slice(0, 4));
  if (!src) return `<span class="logo logo-fallback ${cls}" aria-hidden="true">${ab}</span>`;
  return `<img class="logo ${cls}" src="${esc(src)}" alt="" loading="lazy" onerror="this.outerHTML='<span class=&quot;logo logo-fallback ${cls}&quot;>${ab}</span>'">`;
}
export const UCONN = { name: 'UConn', abbr: 'CONN', logo: 'https://a.espncdn.com/i/teamlogos/ncaa/500/41.png', color: '#0c2340' };
export const initials = (name) => (name || '?').split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
export function headshot(p, cls = '') {
  if (p?.photo) return `<img class="${cls}" src="${esc(p.photo)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ph',textContent:'${esc(initials(p.name))}'}))">`;
  return `<span class="ph ${cls}">${esc(initials(p?.name))}</span>`;
}

// Tooltip singleton
let tipEl;
export function tip(html, e) {
  if (!tipEl) { tipEl = document.createElement('div'); tipEl.className = 'tip'; document.body.appendChild(tipEl); }
  if (!html) { tipEl.classList.remove('on'); return; }
  tipEl.innerHTML = html;
  tipEl.classList.add('on');
  const r = tipEl.getBoundingClientRect();
  let x = e.clientX + 14, y = e.clientY + 14;
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
  tipEl.style.left = `${Math.max(8, x)}px`; tipEl.style.top = `${Math.max(8, y)}px`;
}
export function bindTips(root, attr = 'data-tip') {
  root.addEventListener('pointermove', (e) => { const t = e.target.closest(`[${attr}]`); tip(t ? t.getAttribute(attr) : null, e); });
  root.addEventListener('pointerleave', () => tip(null));
}

// Lightbox for videos & photos
export function openVideo(v) {
  const lb = $('#lightbox');
  lb.innerHTML = `<button class="lb-x" aria-label="Close">×</button><div class="lb-in">
    <iframe src="https://www.youtube-nocookie.com/embed/${esc(v.id)}?autoplay=1&rel=0" title="${esc(v.title)}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>
    <div class="lb-cap"><span><b>${esc(v.title)}</b>${v.channel ? ` · ${esc(v.channel)}` : ''}</span><a class="muted" href="https://www.youtube.com/watch?v=${esc(v.id)}" target="_blank" rel="noopener">Open on YouTube ↗</a></div></div>`;
  showLb(lb);
}
export function openMp4(v) {
  const lb = $('#lightbox');
  lb.innerHTML = `<button class="lb-x" aria-label="Close">×</button><div class="lb-in">
    <video class="lb-media" src="${esc(v.src)}" poster="${esc(v.thumb || '')}" controls autoplay playsinline></video>
    <div class="lb-cap"><span><b>${esc(v.title)}</b></span>${v.web ? `<a class="muted" href="${esc(v.web)}" target="_blank" rel="noopener">Source ↗</a>` : ''}</div></div>`;
  showLb(lb);
}
export function openPhoto(p) {
  const lb = $('#lightbox');
  lb.innerHTML = `<button class="lb-x" aria-label="Close">×</button><div class="lb-in">
    <img class="lb-media" src="${esc(p.full || p.url)}" alt="${esc(p.caption || '')}">
    <div class="lb-cap"><span>${esc(p.caption || '')}</span><span class="muted">${p.credit ? esc(p.credit) : ''}${p.license ? ` · ${esc(p.license)}` : ''}${p.page ? ` · <a href="${esc(p.page)}" target="_blank" rel="noopener">source ↗</a>` : ''}</span></div></div>`;
  showLb(lb);
}
function showLb(lb) {
  lb.hidden = false;
  document.body.style.overflow = 'hidden';
  const close = () => { lb.hidden = true; lb.innerHTML = ''; document.body.style.overflow = ''; removeEventListener('keydown', k); };
  const k = (e) => { if (e.key === 'Escape') close(); };
  addEventListener('keydown', k);
  lb.onclick = (e) => { if (e.target === lb || e.target.closest('.lb-x')) close(); };
  lb.querySelector('.lb-x')?.focus();
}

// Video thumbnails grid
export function videoCard(v) {
  const kind = { full_game: 'Full game', highlights: 'Highlights', moment: 'Moment', documentary: 'Documentary', interview: 'Interview', espn: 'ESPN clip' }[v.kind] || 'Video';
  const th = v.thumb || `https://i.ytimg.com/vi/${v.id}/hqdefault.jpg`;
  return `<button class="vid" data-vid="${esc(v.id)}"${v.src ? ` data-mp4="${esc(v.src)}"` : ''}>
    <div class="th"><img src="${esc(th)}" alt="" loading="lazy"><span class="pill k">${esc(kind)}</span></div>
    <b>${esc(v.title)}</b>${v.sub || v.channel ? `<small>${esc(v.sub || v.channel)}</small>` : ''}</button>`;
}
export function bindVideos(root, list) {
  const byId = new Map(list.map((v) => [v.id, v]));
  root.addEventListener('click', (e) => {
    const b = e.target.closest('[data-vid]'); if (!b) return;
    const v = byId.get(b.dataset.vid); if (!v) return;
    v.src ? openMp4(v) : openVideo(v);
  });
}
export function photoFig(p, i) {
  return `<button class="photo-it" data-ph="${i}"><img src="${esc(p.thumb || p.url)}" alt="${esc(p.caption || '')}" loading="lazy"${p.w ? ` width="${p.w}" height="${p.h}"` : ''}><figcaption>${esc(p.caption || '')}</figcaption></button>`;
}
export function bindPhotos(root, list) {
  root.addEventListener('click', (e) => { const b = e.target.closest('[data-ph]'); if (b) openPhoto(list[+b.dataset.ph]); });
}

// Sortable stats table.
// cols: [{k, label, l(eft), fmt, title, heat}] rows: objects. opts: {sort, desc, total, rowAttr}
export function statTable(cols, rows, opts = {}) {
  const id = 't' + Math.random().toString(36).slice(2, 8);
  const maxes = {};
  cols.forEach((c) => { if (c.heat) maxes[c.k] = Math.max(...rows.map((r) => +c.get?.(r) || +r[c.k] || 0), 0.0001); });
  const val = (c, r) => (c.get ? c.get(r) : r[c.k]);
  const cell = (c, r) => {
    const v = val(c, r);
    const txt = c.html ? c.html(r) : c.fmt ? c.fmt(v, r) : esc(v ?? '–');
    const heat = c.heat && v != null ? ` class="heat${c.l ? ' l' : ''}" style="--h:${(0.28 * (+v / maxes[c.k])).toFixed(3)}"` : c.l ? ' class="l"' : '';
    return `<td${heat}>${txt}</td>`;
  };
  const body = (rs) => rs.map((r) => `<tr${opts.rowAttr ? opts.rowAttr(r) : ''}>${cols.map((c) => cell(c, r)).join('')}</tr>`).join('');
  const html = `<div class="tbl-wrap"><table class="stats" id="${id}"><thead><tr>${cols.map((c, i) => `<th data-i="${i}" class="${c.l ? 'l' : ''}${opts.sort === c.k ? ' sorted' : ''}" ${c.title ? `title="${esc(c.title)}"` : ''}>${esc(c.label)}</th>`).join('')}</tr></thead>
    <tbody>${body(rows)}</tbody>${opts.total ? `<tfoot><tr class="tot">${cols.map((c) => cell(c, opts.total)).join('')}</tr></tfoot>` : ''}</table></div>`;
  const bind = (root) => {
    const t = root.querySelector('#' + id); if (!t) return;
    let cur = opts.sort, desc = opts.desc !== false;
    t.querySelector('thead').addEventListener('click', (e) => {
      const th = e.target.closest('th'); if (!th) return;
      const c = cols[+th.dataset.i];
      desc = cur === c.k ? !desc : !c.l; cur = c.k;
      const sorted = [...rows].sort((a, b) => {
        const x = val(c, a), y = val(c, b);
        if (x == null) return 1; if (y == null) return -1;
        const r = typeof x === 'string' ? x.localeCompare(y) : x - y;
        return desc ? -r : r;
      });
      t.tBodies[0].innerHTML = body(sorted);
      t.querySelectorAll('th').forEach((h) => h.classList.remove('sorted', 'asc'));
      th.classList.add('sorted'); if (!desc) th.classList.add('asc');
    });
  };
  return { html, bind };
}

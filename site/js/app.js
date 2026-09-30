// Router, search, and app shell.
import { $, $$, esc, load, headshot, seasonLabel, FINISH } from './ui.js';

const views = {
  '': () => import('./views/home.js'),
  now: () => import('./views/now.js'),
  seasons: () => import('./views/seasons.js'),
  season: () => import('./views/season.js'),
  game: () => import('./views/game.js'),
  player: () => import('./views/player.js'),
  players: () => import('./views/players.js'),
  march: () => import('./views/march.js'),
  numbers: () => import('./views/numbers.js'),
  vault: () => import('./views/vault.js'),
  legends: () => import('./views/legends.js'),
};
const navKey = { season: 'seasons', game: 'seasons', player: 'players' };

let current = null; // { destroy }
let seq = 0;
async function route() {
  const my = ++seq;
  const [name = '', ...args] = location.hash.replace(/^#\/?/, '').split('/').map(decodeURIComponent);
  const loader = views[name] || views[''];
  $$('#nav a').forEach((a) => a.classList.toggle('on', a.dataset.nav === (navKey[name] || name)));
  const main = $('#main');
  try { current?.destroy?.(); } catch (e) { console.warn(e); }
  current = null;
  main.innerHTML = '<div class="loading">Loading</div>';
  try {
    const [mod, core] = await Promise.all([loader(), load('core.json')]);
    if (my !== seq) return;
    main.innerHTML = '';
    current = (await mod.default(main, args, core)) || null;
    if (my !== seq) { current?.destroy?.(); return; }
    const t = main.querySelector('[data-title]')?.dataset.title;
    document.title = t ? `${t} · The Rafters` : 'The Rafters';
  } catch (e) {
    console.error(e);
    if (my === seq) main.innerHTML = `<div class="wrap section"><div class="empty">That page didn't load: ${esc(e.message)}. <a class="btn" href="#/">Back to the rafters</a></div></div>`;
  }
  if (!location.hash.includes('#top')) scrollTo({ top: 0, behavior: 'instant' });
  main.focus({ preventScroll: true });
}
addEventListener('hashchange', route);

// ── Search ──
let index = null;
async function buildIndex() {
  if (index) return index;
  const core = await load('core.json');
  index = [];
  core.players.forEach((p) => index.push({ k: 'Player', t: p.name, s: `${p.span}${p.pos ? ' · ' + p.pos : ''}${p.ppg != null ? ` · ${p.ppg.toFixed(1)} ppg` : ''}`, h: `#/player/${p.id}`, p, q: p.name.toLowerCase() }));
  core.seasons.forEach((s) => index.push({ k: 'Season', t: `${s.label} ${s.w}-${s.l}`, s: `${s.coach} · ${FINISH[s.finish]?.label || ''}`, h: `#/season/${s.y}`, q: `${s.y} ${s.label} ${s.y - 1} ${s.coach}`.toLowerCase(), yr: s.y }));
  Object.values(core.opponents || {}).forEach((o) => index.push({ k: 'Opponent', t: o.name, s: `${o.w}-${o.l} vs. since 1986–87`, h: `#/numbers/opp/${o.key}`, q: o.name.toLowerCase(), logo: o.logo }));
  return index;
}
function openSearch() {
  const box = $('#search'); box.hidden = false;
  const inp = $('#searchInput'); inp.value = ''; inp.focus();
  renderResults('');
}
function closeSearch() { $('#search').hidden = true; }
let sel = 0, results = [];
async function renderResults(q) {
  const idx = await buildIndex();
  q = q.trim().toLowerCase();
  results = !q ? idx.filter((r) => r.k === 'Season').slice(-6).reverse()
    : idx.filter((r) => r.q.includes(q) || r.q.split(' ').some((w) => w.startsWith(q))).sort((a, b) => (b.q.startsWith(q) - a.q.startsWith(q))).slice(0, 30);
  sel = 0;
  $('#searchResults').innerHTML = results.map((r, i) => `<a class="sr-item${i === 0 ? ' on' : ''}" href="${r.h}">${r.p ? headshot(r.p) : r.logo ? `<img src="${esc(r.logo)}" alt="" style="object-fit:contain;border-radius:0;background:none">` : `<span class="ph">${r.yr ? String(r.yr).slice(2) : '•'}</span>`}<span><b>${esc(r.t)}</b><small>${esc(r.s)}</small></span><span class="k">${r.k}</span></a>`).join('') || '<div class="empty" style="margin:16px">No matches</div>';
}
$('#searchBtn').addEventListener('click', openSearch);
$('#search').addEventListener('click', (e) => { if (e.target.id === 'search' || e.target.closest('.sr-item')) closeSearch(); });
$('#searchInput').addEventListener('input', (e) => renderResults(e.target.value));
$('#searchInput').addEventListener('keydown', (e) => {
  const items = $$('.sr-item');
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault(); sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
    items.forEach((it, i) => it.classList.toggle('on', i === sel)); items[sel]?.scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'Enter' && items[sel]) { location.hash = items[sel].getAttribute('href'); closeSearch(); }
  else if (e.key === 'Escape') closeSearch();
});
addEventListener('keydown', (e) => {
  if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); openSearch(); }
});

load('core.json').then((core) => {
  if (core.updated) $('#footUpdated').textContent = `Data updated ${new Date(core.updated).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })}.`;
}).catch(() => {});
route();

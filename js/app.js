// Router, search, and app shell.
import { $, $$, esc, load, tryLoad, headshot, seasonLabel, FINISH, setLogos } from './ui.js';

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
  moments: () => import('./views/moments.js'),
  moment: () => import('./views/moments.js'),
  venues: () => import('./views/venues.js'),
};
const navKey = { season: 'seasons', game: 'seasons', player: 'players', moment: 'moments', venues: 'legends' };

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
    setLogos(core.logos);
    if (my !== seq) return;
    main.innerHTML = '';
    current = (await mod.default(main, args, core)) || null;
    if (my !== seq) { current?.destroy?.(); return; }
    const t = main.querySelector('[data-title]')?.dataset.title;
    document.title = t ? `${t} · Storrs Lore` : 'Storrs Lore';
  } catch (e) {
    console.error(e);
    if (my === seq) main.innerHTML = `<div class="wrap section"><div class="empty">That page didn't load: ${esc(e.message)}. <a class="btn" href="#/">Back home</a></div></div>`;
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
  ((await tryLoad('moments.json'))?.moments || []).forEach((m) => index.push({ k: 'Moment', t: m.title, s: `${m.date.slice(0, 4)}${m.opp ? ` · vs. ${m.opp.name}` : ''}${m.res ? ` · ${m.res} ${m.pts}–${m.opp_pts}` : ''}`, h: `#/moment/${m.slug}`, q: `${m.title} ${m.nickname || ''} ${m.opp?.name || ''} ${m.date.slice(0, 4)} moment`.toLowerCase(), logo: m.opp?.logo }));
  Object.values(core.opponents || {}).forEach((o) => index.push({ k: 'Opponent', t: o.name, s: `${o.w}-${o.l} vs. since ${core.seasons[0].y - 1}–${String(core.seasons[0].y).slice(2)}`, h: `#/numbers/opp/${o.key}`, q: o.name.toLowerCase(), logo: o.logo }));
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

// the Moments section appears once fact-checked moments exist
tryLoad('moments.json').then((m) => { const a = $('#nav [data-nav="moments"]'); if (a) a.hidden = !m?.moments?.length; });
load('core.json').then((core) => {
  if (core.updated) $('#footUpdated').textContent = `Data updated ${new Date(core.updated).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })}.`;
}).catch(() => {});
route();

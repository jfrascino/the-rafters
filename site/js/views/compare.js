// Head to head: any two Huskies' UConn careers side by side. #/compare/<pidA>/<pidB>
import { esc, load, headshot, seasonLabel, n1, n0, bindTips, tip } from '../ui.js';
import { onResize } from '../charts.js';

const C = ['var(--ice)', 'var(--gold)'];   // player A, player B (fixed order, never by rank)
const ROWS = [
  ['Seasons', (p) => p.uc.length, n0],
  ['Games', (p) => p.c.g, n0],
  ['Points', (p) => p.c.pts, n0, 'pts'],
  ['Points per game', (p) => p.c.pts_pg, n1, 'pts'],
  ['Rebounds', (p) => p.c.trb, n0, 'trb'],
  ['Rebounds per game', (p) => p.c.trb_pg, n1, 'trb'],
  ['Assists', (p) => p.c.ast, n0, 'ast'],
  ['Assists per game', (p) => p.c.ast_pg, n1, 'ast'],
  ['Steals', (p) => p.c.stl, n0, 'stl'],
  ['Blocks', (p) => p.c.blk, n0, 'blk'],
  ['3-pointers', (p) => p.c.fg3, n0, 'fg3'],
  ['FG%', (p) => (p.c.fg_pct != null ? p.c.fg_pct * 100 : null), n1],
  ['3P%', (p) => (p.c.fg3_pct != null && p.c.fg3 ? p.c.fg3_pct * 100 : null), n1],
  ['FT%', (p) => (p.c.ft_pct != null ? p.c.ft_pct * 100 : null), n1],
  ['NCAA Tournaments', (p) => p.uc.filter((s) => s.finish && !['none', 'nit'].includes(s.finish)).length, n0],
  ['Final Fours', (p) => p.uc.filter((s) => ['champ', 'runner', 'final4'].includes(s.finish)).length, n0],
  ['National titles', (p) => p.uc.filter((s) => s.finish === 'champ').length, n0],
];

export default async function compare(main, args, core) {
  const ids = [args[0], args[1]].filter(Boolean);
  const players = await Promise.all(ids.map((id) => load(`players/${id}.json`).then((p) => ({ ...p, c: p.career || {}, uc: (p.seasons || []).filter((s) => s.uconn) })).catch(() => null)));
  const [A, B] = players;
  main.innerHTML = `<div data-title="${A && B ? `${esc(A.name)} vs. ${esc(B.name)}` : 'Compare Huskies'}"></div>
  <section class="march-hero"><div class="wrap grid" style="gap:18px">
    <span class="eyebrow gold">Head to head</span>
    <h1 class="h-display" style="font-size:clamp(44px,7vw,100px)">Compare Huskies</h1>
    <div class="cmp-pick">${[0, 1].map((i) => `<label class="cmp-in" style="--c:${C[i]}"><span class="eyebrow">Player ${i ? 'B' : 'A'}</span>
      <input type="search" data-i="${i}" placeholder="Search a Husky…" value="${esc(players[i]?.name || '')}" autocomplete="off" spellcheck="false"><div class="cmp-list" hidden></div></label>`).join('<span class="cmp-vs">vs.</span>')}</div>
  </div></section>
  ${A && B ? body(A, B, core) : `<section class="section"><div class="wrap"><div class="empty">Pick two players to put their UConn careers side by side.${A || B ? '' : ` Try <a href="#/compare/ray-allen-1/richard-hamilton-1" style="text-decoration:underline">Ray Allen vs. Rip Hamilton</a> or <a href="#/compare/kemba-walker-1/shabazz-napier-1" style="text-decoration:underline">Kemba vs. Shabazz</a>.`}</div></div></section>`}`;

  // pickers
  const all = core.players;
  main.querySelectorAll('.cmp-in input').forEach((inp) => {
    const list = inp.parentElement.querySelector('.cmp-list');
    const show = () => {
      const q = inp.value.trim().toLowerCase();
      const hits = (q ? all.filter((p) => p.name.toLowerCase().includes(q)) : all.slice().sort((a, b) => b.pts - a.pts)).slice(0, 8);
      list.innerHTML = hits.map((p) => `<button data-id="${esc(p.id)}">${headshot(p)}<span><b>${esc(p.name)}</b><small>${esc(p.span)}${p.ppg != null ? ` · ${n1(p.ppg)} ppg` : ''}</small></span></button>`).join('');
      list.hidden = !hits.length;
    };
    inp.addEventListener('focus', show);
    inp.addEventListener('input', show);
    inp.addEventListener('blur', () => setTimeout(() => { list.hidden = true; }, 150));
    list.addEventListener('mousedown', (e) => {
      const b = e.target.closest('[data-id]'); if (!b) return;
      const next = [...ids]; next[+inp.dataset.i] = b.dataset.id;
      location.hash = `#/compare/${next[0] || ''}${next[1] ? '/' + next[1] : ''}`.replace(/\/$/, '');
    });
  });
  if (!(A && B)) return null;
  const offs = [];
  const draw = () => main.querySelectorAll('[data-chart]').forEach((el) => seasonChart(el, [A, B], el.dataset.chart));
  draw(); bindTips(main);
  const first = main.querySelector('[data-chart]');
  if (first) offs.push(onResize(first, draw));
  return { destroy() { offs.forEach((f) => f()); tip(null); } };
}

function body(A, B, core) {
  const ps = [A, B];
  const partialFor = (k) => ps.filter((p) => p.c.partial?.[k]).map((p) => p.name);
  return `<section class="section" style="padding-top:20px"><div class="wrap">
    <div class="cmp-heads">${ps.map((p, i) => `<a class="cmp-head" href="#/player/${esc(p.id)}" style="--c:${C[i]}">
      <span class="ph">${headshot({ ...p, years: p.uc.map((s) => s.y) })}</span>
      <span><span class="eyebrow">${esc(p.span || '')} · ${esc(p.pos || '')}${p.num ? ` · #${esc(p.num)}` : ''}</span><b>${esc(p.name)}</b><small>${esc([p.ht, p.home].filter(Boolean).join(' · '))}</small></span></a>`).join('<span class="cmp-vs big">vs.</span>')}</div>
    <div class="panel cmp-rows">${ROWS.map(([label, get, fmt, pk]) => {
      const v = ps.map(get);
      if (v.every((x) => x == null)) return '';
      const max = Math.max(...v.map((x) => +x || 0), 0.0001);
      const lead = v[0] == null || v[1] == null || v[0] === v[1] ? -1 : v[0] > v[1] ? 0 : 1;
      const part = pk ? partialFor(pk) : [];
      return `<div class="cmp-row"><span class="cmp-v${lead === 0 ? ' lead' : ''}">${v[0] == null ? '–' : fmt(v[0])}</span>
        <span class="cmp-bar l"><i style="width:${((+v[0] || 0) / max) * 100}%;background:${C[0]}"></i></span>
        <span class="cmp-l">${esc(label)}${part.length ? `<sup data-tip="${esc(esc(`Not kept every season; ${part.join(' and ')}'s total covers only the seasons it was recorded`))}">*</sup>` : ''}</span>
        <span class="cmp-bar r"><i style="width:${((+v[1] || 0) / max) * 100}%;background:${C[1]}"></i></span>
        <span class="cmp-v${lead === 1 ? ' lead' : ''}">${v[1] == null ? '–' : fmt(v[1])}</span></div>`;
    }).join('')}</div>
    <p class="note" style="margin-top:8px">UConn games only. Leader in each row is bolded; bars are scaled to the larger value.</p>
  </div></section>
  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Year by year at UConn</span><h2 class="h2">Season by season</h2></div>
      <div class="legend">${ps.map((p, i) => `<span><i style="background:${C[i]}"></i>${esc(p.name)}</span>`).join('')}</div></div>
    <div class="cmp-charts">${[['pts', 'Points per game'], ['trb', 'Rebounds per game'], ['ast', 'Assists per game']].map(([k, t]) => `<figure class="panel chart-card"><figcaption class="eyebrow">${t}</figcaption><div data-chart="${k}"></div></figure>`).join('')}</div>
  </div></section>
  <section class="section"><div class="wrap cmp-honors">${ps.map((p, i) => `<div class="panel" style="--c:${C[i]}"><span class="eyebrow">${esc(p.name)}</span>
    ${p.draft ? `<p style="margin:8px 0"><b>NBA draft:</b> ${esc(p.draft)}</p>` : ''}
    ${(p.honors || []).length ? `<ul>${p.honors.map((h) => `<li>${esc(h)}</li>`).join('')}</ul>` : '<p class="muted">No major honors on file.</p>'}</div>`).join('')}</div></section>`;
}

// one small chart per stat: each player's per-game average by year of his UConn career
function seasonChart(el, ps, k) {
  const w = Math.max(260, el.clientWidth || 360), h = 170, l = 30, r = 12, t = 14, b = 26;
  const n = Math.max(...ps.map((p) => p.uc.length), 1);
  const vals = ps.flatMap((p) => p.uc.map((s) => s[k] ?? 0));
  const max = Math.max(4, ...vals) * 1.1;
  const x = (i) => (n === 1 ? (l + w - r) / 2 : l + (i / (n - 1)) * (w - l - r)), y = (v) => h - b - (v / max) * (h - t - b);
  let svg = `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">`;
  const step = max > 20 ? 10 : max > 8 ? 4 : 2;
  for (let v = 0; v <= max; v += step) svg += `<line x1="${l}" x2="${w - r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" ${v ? 'stroke-dasharray="2 5"' : ''}/><text x="${l - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
  for (let i = 0; i < n; i++) svg += `<text x="${x(i)}" y="${h - 6}" text-anchor="middle">${['1st', '2nd', '3rd', '4th', '5th', '6th'][i] || i + 1} yr</text>`;
  ps.forEach((p, j) => {
    const pts = p.uc.map((s, i) => [x(i), y(s[k] ?? 0), s]);
    svg += `<path d="${pts.map(([a, c], i) => `${i ? 'L' : 'M'}${a.toFixed(1)},${c.toFixed(1)}`).join('')}" fill="none" stroke="${C[j]}" stroke-width="2"/>`;
    pts.forEach(([a, c, s]) => { svg += `<circle cx="${a}" cy="${c}" r="5" fill="${C[j]}" stroke="var(--ink)" stroke-width="2" data-tip="${esc(`<b>${esc(p.name)}</b>${esc(s.label)} · ${n1(s[k])}`)}"/>`; });
  });
  el.innerHTML = svg + '</svg>';
}

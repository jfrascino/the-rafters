// Hand-built SVG charts, drawn to the container's real width so type stays readable.
import { esc, FINISH, fmtDate, sign, n1 } from './ui.js';

const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);
const W = (el, min = 320) => Math.max(min, Math.round(el.clientWidth || 800));

// Every season in one view. Top: games played, wins solid and losses as a pale cap (one hue; gold only for titles).
// Bottom: the March ladder, one square per NCAA round reached, so depth reads as height, not color.
const LADDER = [['NCAA', 'NCAA'], ['2nd rd', 'R32'], ['Sweet 16', 'S16'], ['Elite 8', 'E8'], ['Final 4', 'F4'], ['Title game', 'TG'], ['Champion', '★']];
const DEPTH = { none: 0, nit: 0, r64: 1, r32: 2, sweet16: 3, elite8: 4, final4: 5, runner: 6, champ: 7 };
export function skyline(el, seasons, eras) {
  const w = W(el), narrow = w < 700;
  const left = narrow ? 34 : 78, right = 6;
  const n = seasons.length, step = (w - left - right) / n, bw = Math.max(3, step - (narrow ? 2 : 4));
  const eraH = 26, barTop = eraH + 18, barH = narrow ? 150 : 190, gap = 26;
  const sq = Math.max(3, Math.min(bw, 12)), sqGap = 3, ladTop = barTop + barH + gap, ladH = LADDER.length * (sq + sqGap);
  const axisY = ladTop + ladH + 8, h = axisY + 20;
  const maxG = Math.max(...seasons.map((s) => s.w + s.l));
  const y = lin(0, maxG, barTop + barH, barTop);
  const x = (i) => left + i * step + (step - bw) / 2;
  let svg = `<svg class="skyline" viewBox="0 0 ${w} ${h}" role="img" aria-label="Wins, losses and NCAA Tournament depth for every season">`;
  // eras: a labelled bracket above the bars
  eras.forEach((e) => {
    const i0 = seasons.findIndex((s) => s.y >= e.from), i1 = seasons.findLastIndex((s) => s.y <= e.to);
    if (i0 < 0 || i1 < 0) return;
    const x0 = left + i0 * step + 2, x1 = left + (i1 + 1) * step - 2;
    svg += `<path d="M${x0},${eraH} V${eraH - 6} H${x1} V${eraH}" fill="none" stroke="var(--line-2)"/>`;
    svg += `<text class="era-label" x="${(x0 + x1) / 2}" y="${eraH - 11}" text-anchor="middle">${esc(narrow ? e.short : e.name)}</text>`;
  });
  // win gridlines (recessive)
  [10, 20, 30, 40].filter((v) => v < maxG).forEach((v) => {
    svg += `<line x1="${left}" x2="${w - right}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-dasharray="2 5"/><text x="${left - 8}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
  });
  svg += `<text x="${left - 8}" y="${barTop - 6}" text-anchor="end" style="fill:var(--fg-2)">${narrow ? 'G' : 'GAMES'}</text>`;
  // ladder row labels + faint empty cells
  LADDER.forEach(([long, short], r) => {
    const yy = ladTop + (LADDER.length - 1 - r) * (sq + sqGap);
    svg += `<text x="${left - 8}" y="${yy + sq - 1}" text-anchor="end" style="${r === 6 ? 'fill:var(--gold)' : ''}">${esc(narrow ? short : long)}</text>`;
  });
  seasons.forEach((s, i) => {
    const xi = x(i), champ = s.finish === 'champ', depth = DEPTH[s.finish] || 0;
    const barFill = champ ? 'var(--gold)' : 'var(--ice)';
    const F = FINISH[s.finish] || FINISH.none;
    const tipHtml = `<b>${esc(s.label)} · ${s.w}–${s.l}</b>${esc(s.coach)}<br>${esc(F.label)}${s.seed ? ` · No. ${s.seed} seed` : ''}${s.apFinal ? `<br>Final AP No. ${s.apFinal}` : ''}`;
    svg += `<a href="#/season/${s.y}" class="bar" data-tip="${esc(tipHtml)}" aria-label="${esc(s.label)}: ${s.w} wins, ${s.l} losses, ${esc(F.label)}">`;
    svg += `<rect x="${left + i * step}" y="${barTop - 4}" width="${step}" height="${axisY - barTop + 4}" fill="transparent"/>`;
    // losses cap, then wins (2px surface gap between them)
    svg += `<rect x="${xi}" y="${y(s.w + s.l)}" width="${bw}" height="${Math.max(0, y(s.w) - y(s.w + s.l) - 2)}" rx="2" fill="${barFill}" opacity=".22"/>`;
    svg += `<rect x="${xi}" y="${y(s.w)}" width="${bw}" height="${barTop + barH - y(s.w)}" rx="2" fill="${barFill}"/>`;
    // ladder cells
    const cx = xi + (bw - sq) / 2;
    for (let r = 0; r < LADDER.length; r++) {
      const yy = ladTop + (LADDER.length - 1 - r) * (sq + sqGap);
      const on = r < depth;
      svg += `<rect x="${cx}" y="${yy}" width="${sq}" height="${sq}" rx="1.5" fill="${on ? (r === 6 ? 'var(--gold)' : 'var(--fg-2)') : 'var(--line)'}" opacity="${on ? 1 : .55}"/>`;
    }
    if (s.finish === 'nit') svg += `<text x="${xi + bw / 2}" y="${ladTop + ladH - 2}" text-anchor="middle" style="font-size:9px;fill:var(--muted)">NIT</text>`;
    svg += '</a>';
    const every = narrow ? 5 : 2;
    if (champ || (s.y % every === 0 && !seasons.slice(Math.max(0, i - 1), i + 2).some((t) => t !== s && t.finish === 'champ'))) {
      svg += `<text x="${xi + bw / 2}" y="${axisY + 12}" text-anchor="middle" style="${champ ? 'fill:var(--gold);font-weight:700' : ''}">'${String(s.y).slice(2)}</text>`;
    }
  });
  svg += `<line x1="${left}" x2="${w - right}" y1="${barTop + barH + .5}" y2="${barTop + barH + .5}" stroke="var(--line-2)"/>`;
  el.innerHTML = svg + '</svg>';
}

// Game-by-game margin: the heartbeat of a season.
export function heartbeat(el, games, opts = {}) {
  const w = W(el), h = w < 640 ? 200 : 240, mid = h / 2 - 6;
  const gs = games.filter((g) => g.res);
  if (!gs.length) { el.innerHTML = '<div class="empty">No games played yet.</div>'; return; }
  const m = Math.max(20, ...gs.map((g) => Math.abs(g.pts - g.opp_pts)));
  const y = lin(0, m, 0, mid - 18);
  const bw = w / gs.length;
  let svg = `<svg class="heartbeat" viewBox="0 0 ${w} ${h}" role="img" aria-label="Scoring margin, game by game">`;
  let postStart = gs.findIndex((g) => g.type === 'NCAA' || g.type === 'NIT');
  const ctStart = gs.findIndex((g) => g.type === 'CTOURN');
  // band labels: the longest wording that fits inside the band (and clear of the +10/+20 scale at the right edge)
  const fit = (x0, x1, words) => { const room = x1 - x0 - 8 - (x1 >= w - 1 ? 28 : 0); return words.find((t) => t.length * 6.4 <= room) || ''; };
  if (ctStart >= 0) {
    const x1 = (postStart >= 0 ? postStart : gs.length) * bw;
    const lab = fit(ctStart * bw, x1, opts.ctLabels || ['CONF. TOURNEY', 'CONF.']);
    svg += `<rect x="${ctStart * bw}" y="0" width="${x1 - ctStart * bw}" height="${h - 12}" fill="rgba(143,193,255,.05)"/>${lab ? `<text x="${ctStart * bw + 4}" y="12">${lab}</text>` : ''}`;
  }
  if (postStart >= 0) {
    const lab = fit(postStart * bw, gs.length * bw, gs[postStart].type === 'NIT' ? ['NIT'] : ['NCAA TOURNAMENT', 'NCAA']);
    svg += `<rect x="${postStart * bw}" y="0" width="${(gs.length - postStart) * bw}" height="${h - 12}" fill="rgba(227,189,110,.08)"/>${lab ? `<text x="${postStart * bw + 4}" y="12" style="fill:var(--gold)">${lab}</text>` : ''}`;
  }
  [10, 20, 30, 40].filter((v) => v < m).forEach((v) => {
    svg += `<line x1="0" x2="${w}" y1="${mid - y(v)}" y2="${mid - y(v)}" stroke="var(--line)" stroke-dasharray="2 5"/><line x1="0" x2="${w}" y1="${mid + y(v)}" y2="${mid + y(v)}" stroke="var(--line)" stroke-dasharray="2 5"/>`;
    svg += `<text x="${w - 2}" y="${mid - y(v) - 3}" text-anchor="end">+${v}</text>`;
  });
  svg += `<line x1="0" x2="${w}" y1="${mid}" y2="${mid}" stroke="var(--line-2)"/>`;
  gs.forEach((g, i) => {
    const d = g.pts - g.opp_pts, x = i * bw + bw * .15, bwi = Math.max(1.5, bw * .7);
    const hh = Math.max(2, y(Math.abs(d)));
    const t = `<b>${g.res} ${g.pts}-${g.opp_pts}${g.ot ? ' ' + esc(g.ot) : ''}</b>${g.ha === 'A' ? '@ ' : g.ha === 'N' ? 'vs. ' : ''}${g.opp.rank ? `No. ${g.opp.rank} ` : ''}${esc(g.opp.name)}<br>${fmtDate(g.date, { year: true })}${g.round ? '<br>' + esc(g.round) : ''}`;
    const fill = g.res === 'W' ? (g.type === 'NCAA' ? 'var(--gold)' : 'var(--ice)') : 'var(--red)';
    svg += `<a class="g" href="#/game/${g.id}" data-tip="${esc(t)}"><rect x="${i * bw}" y="0" width="${bw}" height="${h}" fill="transparent"/><rect x="${x}" y="${d > 0 ? mid - hh : mid}" width="${bwi}" height="${hh}" rx="1" fill="${fill}"/></a>`;
  });
  svg += `<text x="2" y="${h - 1}">GAME 1</text><text x="${w - 2}" y="${h - 1}" text-anchor="end">GAME ${gs.length}</text>`;
  el.innerHTML = svg + '</svg>';
}

// AP poll ride, No. 1 at the top.
export function pollLine(el, polls) {
  const w = W(el), h = 190, l = 30, r = 12, t = 14, b = 26;
  const pts = polls.filter((p) => p.rank || p.rank === null);
  if (pts.length < 2) { el.innerHTML = '<div class="empty">No weekly poll data for this season.</div>'; return; }
  const x = lin(0, pts.length - 1, l, w - r), y = lin(1, 26, t, h - b);
  let svg = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="AP poll ranking by week">`;
  [1, 5, 10, 15, 20, 25].forEach((v) => { svg += `<line x1="${l}" x2="${w - r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-dasharray="2 5"/><text x="${l - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`; });
  svg += `<text x="${l - 6}" y="${y(26) + 4}" text-anchor="end">NR</text>`;
  let d = '', area = '';
  pts.forEach((p, i) => { const yy = y(p.rank || 26); d += `${i ? 'L' : 'M'}${x(i)},${yy}`; });
  area = `${d}L${x(pts.length - 1)},${h - b}L${x(0)},${h - b}Z`;
  svg += `<defs><linearGradient id="pg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--ice)" stop-opacity=".35"/><stop offset="1" stop-color="var(--ice)" stop-opacity="0"/></linearGradient></defs>`;
  svg += `<path d="${area}" fill="url(#pg)"/><path d="${d}" fill="none" stroke="var(--ice)" stroke-width="2.5" stroke-linejoin="round"/>`;
  pts.forEach((p, i) => {
    const yy = y(p.rank || 26);
    svg += `<circle cx="${x(i)}" cy="${yy}" r="${p.rank === 1 ? 5 : 3}" fill="${p.rank === 1 ? 'var(--gold)' : 'var(--ice)'}" data-tip="${esc(`<b>${p.rank ? 'No. ' + p.rank : 'Unranked'}</b>${esc(p.label || 'Week ' + (p.wk ?? i))}${p.date ? ' · ' + fmtDate(p.date) : ''}`)}"/>`;
  });
  const every = Math.ceil(pts.length / (w / 60));
  pts.forEach((p, i) => { if (i % every === 0) svg += `<text x="${x(i)}" y="${h - 6}" text-anchor="middle">${esc(p.short || (p.wk === 0 || p.wk === 'Pre' ? 'PRE' : p.wk === 'Final' ? 'FINAL' : 'W' + (p.wk ?? i)))}</text>`; });
  el.innerHTML = svg + '</svg>';
}

// Win probability (UConn's view) with scoring runs underneath.
export function winProb(el, wp, periods, uconnHome, marks = []) {
  const w = W(el), h = w < 600 ? 220 : 260, l = 36, r = 10, t = 12, b = 24;
  const n = wp.length;
  const x = lin(0, n - 1, l, w - r), y = lin(0, 1, h - b, t);
  const p = (v) => (uconnHome ? v : 1 - v);
  let line = '';
  wp.forEach((v, i) => { line += `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p(v[1])).toFixed(1)}`; });
  const above = `${line}L${x(n - 1)},${y(.5)}L${x(0)},${y(.5)}Z`;
  let svg = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="UConn win probability through the game">
    <defs><clipPath id="wpa"><rect x="0" y="0" width="${w}" height="${y(.5)}"/></clipPath><clipPath id="wpb"><rect x="0" y="${y(.5)}" width="${w}" height="${h}"/></clipPath></defs>`;
  [0, .25, .5, .75, 1].forEach((v) => { svg += `<line x1="${l}" x2="${w - r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" ${v === .5 ? '' : 'stroke-dasharray="2 5"'}/><text x="${l - 6}" y="${y(v) + 4}" text-anchor="end">${v * 100}%</text>`; });
  (periods || []).forEach((pi, k) => { if (!pi) return; svg += `<line x1="${x(pi)}" x2="${x(pi)}" y1="${t}" y2="${h - b}" stroke="var(--line-2)" stroke-dasharray="3 3"/><text x="${x(pi) + 4}" y="${h - 8}">${k === 0 ? '2ND HALF' : 'OT' + (k > 1 ? k : '')}</text>`; });
  svg += `<path d="${above}" fill="var(--ice)" opacity=".22" clip-path="url(#wpa)"/><path d="${above}" fill="var(--red)" opacity=".25" clip-path="url(#wpb)"/>`;
  svg += `<path d="${line}" fill="none" stroke="var(--fg)" stroke-width="2" stroke-linejoin="round"/>`;
  marks.forEach((m) => { svg += `<circle cx="${x(m.i)}" cy="${y(p(wp[m.i]?.[1] ?? .5))}" r="4.5" fill="var(--gold)" stroke="var(--ink)" stroke-width="2" data-tip="${esc(m.tip)}"/>`; });
  svg += `<text x="${l + 4}" y="${t + 12}" style="fill:var(--ice)">UCONN</text><text x="${l + 4}" y="${h - b - 6}" style="fill:var(--red-soft)">OPPONENT</text>`;
  el.innerHTML = svg + '</svg>';
}

// Score margin over the course of a game from play-by-play (UConn perspective).
export function flow(el, series, periods, marks = []) {
  const w = W(el), h = w < 600 ? 200 : 230, l = 36, r = 10, t = 12, b = 24;
  const n = series.length; if (n < 2) { el.innerHTML = ''; return; }
  const m = Math.max(8, ...series.map(Math.abs));
  const x = lin(0, n - 1, l, w - r), y = lin(-m, m, h - b, t);
  let d = '';
  series.forEach((v, i) => { d += `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`; });
  const area = `${d}L${x(n - 1)},${y(0)}L${x(0)},${y(0)}Z`;
  let svg = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Scoring margin through the game"><defs><clipPath id="fa"><rect x="0" y="0" width="${w}" height="${y(0)}"/></clipPath><clipPath id="fb"><rect x="0" y="${y(0)}" width="${w}" height="${h}"/></clipPath></defs>`;
  const step = m > 24 ? 10 : 5;
  for (let v = -Math.floor(m / step) * step; v <= m; v += step) svg += `<line x1="${l}" x2="${w - r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" ${v ? 'stroke-dasharray="2 5"' : ''}/><text x="${l - 6}" y="${y(v) + 4}" text-anchor="end">${v > 0 ? '+' + v : v}</text>`;
  (periods || []).forEach((pi) => { if (pi) svg += `<line x1="${x(pi)}" x2="${x(pi)}" y1="${t}" y2="${h - b}" stroke="var(--line-2)" stroke-dasharray="3 3"/>`; });
  svg += `<path d="${area}" fill="var(--ice)" opacity=".3" clip-path="url(#fa)"/><path d="${area}" fill="var(--red)" opacity=".32" clip-path="url(#fb)"/><path d="${d}" fill="none" stroke="var(--fg)" stroke-width="1.6"/>`;
  const big = series.reduce((a, v, i) => (v > series[a] ? i : a), 0), low = series.reduce((a, v, i) => (v < series[a] ? i : a), 0);
  if (series[big] > 0) svg += `<text x="${x(big)}" y="${y(series[big]) - 6}" text-anchor="middle" style="fill:var(--ice)">+${series[big]}</text>`;
  if (series[low] < 0) svg += `<text x="${x(low)}" y="${y(series[low]) + 14}" text-anchor="middle" style="fill:var(--red-soft)">${series[low]}</text>`;
  marks.forEach((k) => { if (series[k.i] != null) svg += `<circle cx="${x(k.i)}" cy="${y(series[k.i])}" r="4.5" fill="var(--gold)" stroke="var(--ink)" stroke-width="2" data-tip="${esc(k.tip)}"/>`; });
  el.innerHTML = svg + '</svg>';
}

// Half-court shot chart. shots: [{x, y, made, uconn, tip}] in ESPN coords (x 0–50 ft sideline to sideline, y ft from baseline).
export function shotChart(el, shots, filter) {
  const w = Math.min(W(el), 620), s = w / 50, h = 47 * s;
  const X = (v) => v * s, Y = (v) => h - v * s; // basket at bottom
  const ln = 'stroke="var(--maple-2)" stroke-opacity=".55" fill="none" stroke-width="1.4"';
  let svg = `<svg class="court" viewBox="0 0 ${w} ${h}" role="img" aria-label="Shot chart">
    <defs><linearGradient id="wood" x1="0" x2="1"><stop offset="0" stop-color="#2a1a0e"/><stop offset=".5" stop-color="#3a2513"/><stop offset="1" stop-color="#2a1a0e"/></linearGradient>
    <pattern id="planks" width="${s * 2}" height="${h}" patternUnits="userSpaceOnUse"><rect width="${s * 2}" height="${h}" fill="url(#wood)"/><line x1="0" x2="0" y1="0" y2="${h}" stroke="#000" stroke-opacity=".25"/></pattern></defs>
    <rect width="${w}" height="${h}" fill="url(#planks)" rx="4"/>
    <rect x="${X(19)}" y="${Y(19)}" width="${12 * s}" height="${19 * s}" fill="rgba(0,14,47,.55)" stroke="var(--maple-2)" stroke-opacity=".55"/>
    <circle cx="${X(25)}" cy="${Y(19)}" r="${6 * s}" ${ln}/>
    <path d="M${X(3.34)},${Y(0)} V${Y(9.9)} A${22.15 * s},${22.15 * s} 0 0 1 ${X(46.66)},${Y(9.9)} V${Y(0)}" ${ln}/>
    <line x1="${X(22)}" x2="${X(28)}" y1="${Y(4)}" y2="${Y(4)}" stroke="#fff" stroke-width="2"/>
    <circle cx="${X(25)}" cy="${Y(5.25)}" r="${.75 * s}" stroke="var(--red)" stroke-width="2" fill="none"/>
    <path d="M${X(21)},${Y(47)} A${4 * s},${4 * s} 0 0 1 ${X(29)},${Y(47)}" ${ln} transform="scale(1,1)"/>`;
  shots.filter(filter || (() => true)).forEach((p) => {
    const cx = X(p.x), cy = Y(Math.min(46.5, p.y));
    const c = p.uconn ? 'var(--ice)' : 'var(--red-soft)';
    svg += p.made
      ? `<circle cx="${cx}" cy="${cy}" r="${Math.max(3.5, s * .42)}" fill="${c}" fill-opacity=".85" stroke="var(--ink)" stroke-width="1" data-tip="${esc(p.tip)}"/>`
      : `<g data-tip="${esc(p.tip)}" stroke="${c}" stroke-width="1.8" stroke-opacity=".7"><line x1="${cx - 3.5}" y1="${cy - 3.5}" x2="${cx + 3.5}" y2="${cy + 3.5}"/><line x1="${cx - 3.5}" y1="${cy + 3.5}" x2="${cx + 3.5}" y2="${cy - 3.5}"/><circle cx="${cx}" cy="${cy}" r="6" fill="transparent" stroke="none"/></g>`;
  });
  el.innerHTML = svg + '</svg>';
}

// Career arc: small multiples of a stat by season.
export function arc(el, rows, stats) {
  const w = W(el), cols = w < 560 ? 1 : Math.min(stats.length, 3);
  const cw = (w - (cols - 1) * 18) / cols, h = 150, l = 8, r = 8, t = 30, b = 26;
  el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(${cols},minmax(0,1fr));gap:18px">${stats.map((st) => {
    const vals = rows.map((r0) => r0[st.k]);
    const max = Math.max(...vals.filter((v) => v != null), 1);
    const n = rows.length, bw = (cw - l - r) / n;
    const y = lin(0, max * 1.15, h - b, t);
    let s = `<svg viewBox="0 0 ${cw} ${h}"><text x="${l}" y="14" style="fill:var(--fg-2);font-size:12px;letter-spacing:.14em">${esc(st.label)}</text>`;
    rows.forEach((r0, i) => {
      const v = r0[st.k]; if (v == null) return;
      const x = l + i * bw + bw * .18, bwi = bw * .64;
      s += `<rect x="${x}" y="${y(v)}" width="${bwi}" height="${h - b - y(v)}" rx="2" fill="${r0.champ ? 'var(--gold)' : 'var(--ice)'}" opacity="${r0.uconn === false ? .35 : .9}"/>`;
      s += `<text x="${x + bwi / 2}" y="${y(v) - 6}" text-anchor="middle" style="fill:var(--fg);font-size:13px;font-weight:700">${n1(v)}</text>`;
      s += `<text x="${x + bwi / 2}" y="${h - 8}" text-anchor="middle">${esc(r0.tag)}</text>`;
    });
    return s + '</svg>';
  }).join('')}</div>`;
}

// Scatter of all seasons (e.g., offense vs defense efficiency).
export function scatter(el, pts, o) {
  const w = W(el), h = Math.min(520, Math.max(340, w * .6)), l = 44, r = 16, t = 16, b = 40;
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const pad = (a) => { const mn = Math.min(...a), mx = Math.max(...a), d = (mx - mn) * .08 || 1; return [mn - d, mx + d]; };
  const [x0, x1] = pad(xs), [y0, y1] = pad(ys);
  const x = lin(x0, x1, l, w - r), y = o.invertY ? lin(y0, y1, t, h - b) : lin(y0, y1, h - b, t);
  let svg = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(o.label)}">`;
  const ticks = (a0, a1) => { const st = (a1 - a0) > 20 ? 5 : 2; const out = []; for (let v = Math.ceil(a0 / st) * st; v <= a1; v += st) out.push(v); return out; };
  ticks(x0, x1).forEach((v) => { svg += `<line x1="${x(v)}" x2="${x(v)}" y1="${t}" y2="${h - b}" stroke="var(--line)" stroke-dasharray="2 5"/><text x="${x(v)}" y="${h - b + 16}" text-anchor="middle">${v}</text>`; });
  ticks(y0, y1).forEach((v) => { svg += `<line x1="${l}" x2="${w - r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-dasharray="2 5"/><text x="${l - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`; });
  svg += `<text x="${(l + w - r) / 2}" y="${h - 4}" text-anchor="middle" style="fill:var(--fg-2);letter-spacing:.14em">${esc(o.xLabel)}</text>`;
  svg += `<text x="12" y="${(t + h - b) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(t + h - b) / 2})" style="fill:var(--fg-2);letter-spacing:.14em">${esc(o.yLabel)}</text>`;
  if (o.corner) svg += `<text x="${w - r - 6}" y="${t + 14}" text-anchor="end" style="fill:var(--gold)">${esc(o.corner)} ↗</text>`;
  [...pts].sort((a, b) => (FINISH[a.finish]?.rank || 0) - (FINISH[b.finish]?.rank || 0)).forEach((p) => {
    const F = FINISH[p.finish] || FINISH.none, champ = p.finish === 'champ';
    svg += `<a href="#/season/${p.season}" data-tip="${esc(p.tip)}"><circle cx="${x(p.x)}" cy="${y(p.y)}" r="${champ ? 9 : 6}" fill="${F.color}" stroke="var(--ink)" stroke-width="1.5"/>`;
    if (champ || p.label) svg += `<text x="${x(p.x) + 11}" y="${y(p.y) + 4}" style="fill:${champ ? 'var(--gold)' : 'var(--fg-2)'};font-weight:700">'${String(p.season).slice(2)}</text>`;
    svg += '</a>';
  });
  el.innerHTML = svg + '</svg>';
}

// Mini sparkline path for covers (margins).
export function sparkPath(vals, w = 200, h = 34) {
  if (!vals?.length) return '';
  const m = Math.max(15, ...vals.map(Math.abs)), bw = w / vals.length;
  return vals.map((v, i) => `<rect x="${(i * bw).toFixed(1)}" y="${v > 0 ? h / 2 - (v / m) * h / 2 : h / 2}" width="${Math.max(1, bw - 1).toFixed(1)}" height="${Math.max(1, (Math.abs(v) / m) * h / 2).toFixed(1)}" fill="${v > 0 ? 'var(--ice)' : 'var(--red)'}"/>`).join('');
}

export function onResize(el, fn) {
  let w = el.clientWidth, t;
  const ro = new ResizeObserver(() => { if (Math.abs(el.clientWidth - w) > 20) { w = el.clientWidth; clearTimeout(t); t = setTimeout(fn, 120); } });
  ro.observe(el);
  return () => ro.disconnect();
}
export { sign };

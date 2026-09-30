import { esc, load, tryLoad, logo, UCONN, fmtDate, fmtTime, fmtDay, n1, statTable, bindTips, tip, videoCard, bindVideos, headshot, openMp4 } from '../ui.js';
import { winProb, flow, shotChart, onResize } from '../charts.js';
import { watch, nearTip } from '../live.js';

export default async function game(main, args, core) {
  const id = args[0] || '';
  const y = +id.split('-')[0];
  const [season, bundle] = await Promise.all([load(`seasons/${y}.json`), tryLoad(`games/${y}.json`)]);
  const gi = season.games.findIndex((g) => g.id === id);
  const g = season.games[gi];
  if (!g) throw new Error(`No game ${id}`);
  const d = bundle?.[id] || null;
  const prev = season.games[gi - 1], next = season.games[gi + 1];
  const U = d?.teams?.[0] || { ...UCONN, score: g.pts };
  const O = d?.teams?.[1] || { ...g.opp, score: g.opp_pts };
  const home = g.ha === 'H';
  const left = home ? O : U, right = home ? U : O; // scoreboard convention: away on the left
  const final = !!g.res;
  const nPer = Math.max(U.line?.length || 0, O.line?.length || 0);
  const title = `${g.res ? (g.res === 'W' ? 'UConn beats' : 'UConn falls to') : 'UConn vs.'} ${g.opp.name}`;

  main.innerHTML = `<div data-title="${esc(`${title}, ${fmtDate(g.day || g.date, { year: true })}`)}"></div>
  <section class="g-hero"><div class="wrap">
    <div class="s-hero-top"><a class="eyebrow" href="#/season/${y}">← ${esc(season.label)} · Game ${gi + 1} of ${season.games.length}</a>
      <nav class="s-nav">${prev ? `<a href="#/game/${prev.id}">← ${esc(prev.opp.abbr || prev.opp.name)}</a>` : ''}${next ? `<a href="#/game/${next.id}">${esc(next.opp.abbr || next.opp.name)} →</a>` : ''}</nav></div>
    <div class="board">
      ${g.round ? `<div class="board-label" style="text-align:center;margin-bottom:14px;color:${g.type === 'NCAA' ? 'var(--gold)' : ''}">${esc(g.round)}</div>` : ''}
      <div class="g-board">
        ${teamBlock(left, g, left === U)}
        <div class="g-mid">
          <span class="fin">${final ? `FINAL${g.ot ? ' / ' + esc(g.ot) : ''}` : esc(fmtTime(g.date) || 'UPCOMING')}</span>
          ${nPer ? `<table class="linescore"><thead><tr><th></th>${Array.from({ length: nPer }, (_, i) => `<th>${i < 2 ? i + 1 : 'OT' + (i > 2 ? i - 1 : '')}</th>`).join('')}<th>T</th></tr></thead><tbody>
            ${[left, right].map((t) => `<tr><td>${esc(t.abbr || t.name)}</td>${Array.from({ length: nPer }, (_, i) => `<td>${t.line?.[i] ?? ''}</td>`).join('')}<td>${t.score ?? ''}</td></tr>`).join('')}</tbody></table>` : ''}
        </div>
        ${teamBlock(right, g, right === U)}
      </div>
      <div class="board-foot"><span>${esc(fmtDay(g.day || g.date))} ${esc(fmtDate(g.day || g.date, { year: true }))}</span>${d?.venue?.name || g.arena ? `<span>${esc(d?.venue?.name || g.arena)}${d?.venue?.city || g.city ? ', ' + esc(d?.venue?.city || g.city) : ''}</span>` : ''}${d?.att || g.att ? `<span>Att. ${(+(d?.att || g.att)).toLocaleString()}</span>` : ''}${d?.tv || g.tv ? `<span>${esc(d?.tv || g.tv)}</span>` : ''}${g.rec ? `<span>UConn ${esc(g.rec)}</span>` : ''}</div>
    </div>
  </div></section>
  <div id="gbody"></div>`;

  const moments = (season.story?.moments || []).filter((m) => m.date && m.date.slice(0, 10) === g.date.slice(0, 10));
  if (moments.length) main.querySelector('#gbody').insertAdjacentHTML('beforebegin', `<section class="section" style="padding-bottom:0"><div class="wrap grid" style="gap:14px">${moments.map((m) => `
    <div class="panel otd" style="border-color:rgba(227,189,110,.4);background:linear-gradient(170deg,#2a2210,#10172b 70%)"><span class="eyebrow gold">The moment</span><h2 class="h2" style="font-size:clamp(26px,3vw,40px)">${esc(m.title)}</h2>${m.text ? `<p class="lede" style="font-size:17px">${esc(m.text)}</p>` : ''}</div>`).join('')}</div></section>`);
  const body = main.querySelector('#gbody');
  const offs = [];
  const vids = [...(g.videos || []), ...(d?.videos || [])];

  if (!d) {
    body.innerHTML = `<section class="section"><div class="wrap grid" style="gap:20px">
      <div class="empty">${final ? `No box score exists online for this game. Detailed box scores start in 2002–03, plus NCAA Tournament games from earlier years.${g.top ? `<br><br><b>${esc(g.top)}</b>` : ''}` : 'This game has not been played yet. The box score, win probability and play-by-play appear here after the final horn.'}</div>
      ${vids.length ? `<div class="vids" id="vids">${vids.map(videoCard).join('')}</div>` : ''}
    </div></section>`;
    if (vids.length) bindVideos(body.querySelector('#vids'), vids);
    let stop = () => {};
    if (!final && g.eid && nearTip(g.date)) {
      body.querySelector('.empty').insertAdjacentHTML('beforebegin', `<div class="panel otd" id="live"><span class="eyebrow red">Checking ESPN for a live score…</span></div>`);
      const liveEl = body.querySelector('#live');
      const leds = main.querySelectorAll('.g-team .led');
      stop = watch(g.eid, (L) => {
        if (L.state === 'pre') { liveEl.innerHTML = `<span class="eyebrow">Pregame · ${esc(L.detail || '')}</span>`; return; }
        const [ls, rs] = home ? [L.os, L.us] : [L.us, L.os];
        if (leds[0]) leds[0].textContent = ls; if (leds[1]) leds[1].textContent = rs;
        main.querySelector('.g-mid .fin').innerHTML = L.state === 'in' ? `<span class="pill live">Live</span> ${esc(L.detail || '')}` : `FINAL · ${esc(L.detail || '')}`;
        liveEl.innerHTML = `<span class="eyebrow ${L.state === 'in' ? 'red' : ''}">${L.state === 'in' ? 'Live from ESPN · updates every 20 seconds' : 'Final. The full box score appears here after the next data refresh.'}${L.uWin != null ? ` · UConn win probability ${(L.uWin * 100).toFixed(0)}%` : ''}</span>
          ${L.plays.map((p) => `<div class="pbp-row${p.scoring ? ' sc' : ''}${p.team === 'o' ? ' opp' : ''}"><span class="clk">${esc(p.clock || '')}</span><span></span><span>${esc(p.text || '')}</span><span class="scr">${p.us ?? ''}–${p.os ?? ''}</span></div>`).join('')}`;
      });
    }
    return { destroy() { stop(); } };
  }

  const plays = d.hasPlays ? await tryLoad(`plays/${id}.json`) : null;
  const tops = topPerformers(U, O);
  const shots = plays?.plays?.filter((p) => p[8] != null && p[9] != null && /shot|jumper|layup|dunk|three|tip/i.test(p[7] || '') && !/free throw/i.test(p[7] || '')) || [];

  body.innerHTML = `
  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Game score leaders</span><h2 class="h2">Who won it</h2></div></div>
    <div class="feature-row">${tops.map((p) => `
      <a class="panel otd" href="${p.pid ? `#/player/${esc(p.pid)}` : '#'}" style="grid-template-columns:auto 1fr;align-items:center;gap:16px">
        <span style="width:84px;height:84px;border-radius:50%;overflow:hidden;background:var(--panel-2);display:grid;place-items:center">${headshot(p, '')}</span>
        <span style="display:grid;gap:6px"><span class="eyebrow ${p.uconn ? '' : 'red'}">${p.uconn ? 'UConn' : esc(O.name)}</span><b style="font:800 22px/1 var(--f-display);text-transform:uppercase">${esc(p.name)}</b>
        <span style="font:700 16px/1.2 var(--f-cond);letter-spacing:.04em"><b style="font-size:26px">${p.pts}</b> PTS · ${p.reb} REB · ${p.ast} AST${p.stl ? ` · ${p.stl} STL` : ''}${p.blk ? ` · ${p.blk} BLK` : ''}</span>
        <span class="note">${p.fgm}-${p.fga} FG · ${p.tpm}-${p.tpa} 3PT · ${p.ftm}-${p.fta} FT${p.min ? ` · ${p.min} min` : ''}</span></span>
      </a>`).join('')}</div>
  </div></section>

  ${plays?.wp?.length || plays?.plays?.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Play by play</span><h2 class="h2">How it happened</h2></div>
      <div class="chips" id="flowTabs">${plays.wp?.length ? '<button class="chip on" data-c="wp">Win probability</button>' : ''}<button class="chip${plays.wp?.length ? '' : ' on'}" data-c="flow">Score margin</button></div></div>
    <div class="panel chart-card" id="flowChart"></div>
    ${runsHtml(plays, O)}
  </div></section>` : ''}

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Box score</span><h2 class="h2">The box</h2></div>
      <div class="chips" id="boxTabs"><button class="chip on" data-b="0">UConn</button><button class="chip" data-b="1">${esc(O.name)}</button></div></div>
    <div id="box"></div>
  </div></section>

  <section class="section"><div class="wrap g-grid">
    <div class="panel compare">${compareRows(U, O)}</div>
    ${shots.length > 10 ? `<div class="panel chart-card"><div class="sec-head" style="margin:0"><div><span class="eyebrow">${shots.length} charted shots</span><h3 class="h3">Shot chart</h3></div>
      <div class="chips" id="shotTabs"><button class="chip on" data-s="u">UConn</button><button class="chip" data-s="o">${esc(O.abbr || 'Opp')}</button><button class="chip" data-s="all">Both</button></div></div>
      <div id="shots"></div><div class="legend"><span><i style="background:var(--ice);border-radius:50%"></i>Made</span><span>✕ Missed</span></div></div>` : ''}
  </div></section>

  ${d.article?.story ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Game story${d.article.byline ? ' · ' + esc(d.article.byline) : ''}</span><h2 class="h2" style="max-width:26ch">${esc(d.article.headline || 'Recap')}</h2></div></div>
    <div class="story"><div class="recap">${sanitize(d.article.story)}</div>
      <div class="grid">${(d.article.images || []).slice(0, 3).map((im) => `<figure style="margin:0;display:grid;gap:6px"><img src="${esc(im.url)}" alt="${esc(im.caption || '')}" loading="lazy" style="border-radius:5px"><figcaption class="note">${esc(im.caption || '')}${im.credit ? ` (${esc(im.credit)})` : ''}</figcaption></figure>`).join('')}</div></div>
  </div></section>` : ''}

  ${vids.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${vids.length} videos</span><h2 class="h2">Watch</h2></div></div>
    <div class="vids" id="vids">${vids.map(videoCard).join('')}</div>
  </div></section>` : ''}

  ${plays?.plays?.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${plays.plays.length} plays</span><h2 class="h2">Every possession</h2></div>
      <div class="chips" id="pbpTabs"><button class="chip on" data-p="all">All</button><button class="chip" data-p="sc">Scoring</button><button class="chip" data-p="u">UConn</button><button class="chip" data-p="close">Last 5 min</button></div></div>
    <div class="panel pbp" id="pbp"></div>
  </div></section>` : ''}

  ${d.officials?.length ? `<section class="section"><div class="wrap"><p class="note">Officials: ${d.officials.map(esc).join(', ')}</p></div></section>` : ''}`;

  // Box score tables
  const box = body.querySelector('#box');
  const showBox = (i) => { const t = boxTable(i ? O : U, !i); box.innerHTML = t.html; t.bind(box); };
  showBox(0);
  body.querySelector('#boxTabs').addEventListener('click', (e) => { const b = e.target.closest('[data-b]'); if (!b) return; body.querySelectorAll('#boxTabs .chip').forEach((c) => c.classList.toggle('on', c === b)); showBox(+b.dataset.b); });

  // Flow chart
  const fc = body.querySelector('#flowChart');
  if (fc) {
    const periodsIdx = [];
    plays.plays.forEach((p, i) => { if (i && p[0] !== plays.plays[i - 1][0]) periodsIdx.push(i); });
    const margins = plays.plays.map((p) => p[3] - p[4]);
    let mode = plays.wp?.length ? 'wp' : 'flow';
    const draw = () => {
      if (mode === 'wp') {
        // wp holds [playIndex, uconnWinPct]; map to plays index space for period lines
        const wpPer = periodsIdx.map((pi) => plays.wp.findIndex((w) => w[0] >= pi));
        const marks = keyMoments(plays).map((m) => ({ i: plays.wp.findIndex((w) => w[0] >= m.i), tip: m.tip })).filter((m) => m.i >= 0);
        winProb(fc, plays.wp, wpPer, true, marks);
      } else flow(fc, margins, periodsIdx);
    };
    draw(); bindTips(fc); offs.push(onResize(fc, draw));
    body.querySelector('#flowTabs').addEventListener('click', (e) => { const b = e.target.closest('[data-c]'); if (!b) return; mode = b.dataset.c; body.querySelectorAll('#flowTabs .chip').forEach((c) => c.classList.toggle('on', c === b)); draw(); });
  }

  // Shot chart
  const sh = body.querySelector('#shots');
  if (sh) {
    const pts = shots.map((p) => ({ x: p[8], y: p[9], made: !!p[5], uconn: p[2] === 'u', tip: `<b>${p[5] ? 'Made' : 'Missed'}</b>${esc(p[7])}<br>${p[0] > 2 ? 'OT' : p[0] === 1 ? '1st half' : '2nd half'} · ${esc(p[1])}` }));
    let side = 'u';
    const draw = () => shotChart(sh, pts, (p) => side === 'all' || (side === 'u') === p.uconn);
    draw(); bindTips(sh); offs.push(onResize(sh, draw));
    body.querySelector('#shotTabs').addEventListener('click', (e) => { const b = e.target.closest('[data-s]'); if (!b) return; side = b.dataset.s; body.querySelectorAll('#shotTabs .chip').forEach((c) => c.classList.toggle('on', c === b)); draw(); });
  }

  // Play by play
  const pbp = body.querySelector('#pbp');
  if (pbp) {
    const ulogo = logo(U), ologo = logo(O);
    const lastPer = plays.plays.at(-1)?.[0];
    const clips = plays.clips || {};
    const nClips = Object.keys(clips).length;
    const render = (f) => {
      const rows = plays.plays.map((p, i) => [p, i]).filter(([p, i]) => f === 'all' || (f === 'sc' && p[5]) || (f === 'u' && p[2] === 'u') || (f === 'vid' && clips[i]) || (f === 'close' && (p[0] > 2 || (p[0] === lastPer && clockSec(p[1]) <= 300))));
      let per = 0;
      pbp.innerHTML = rows.map(([p, i]) => {
        const hdr = p[0] !== per ? `<div class="month-h">${(per = p[0]) === 1 ? '1st half' : per === 2 ? '2nd half' : 'Overtime ' + (per - 2)}</div>` : '';
        const c = clips[i];
        return `${hdr}<div class="pbp-row${p[5] ? ' sc' : ''}${p[2] === 'o' ? ' opp' : ''}"><span class="clk">${esc(p[1])}</span><span>${p[2] === 'u' ? ulogo : p[2] === 'o' ? ologo : ''}</span><span>${esc(p[7])}${c ? ` <button class="clip" data-clip="${i}" aria-label="Watch this play">▶ Watch</button>` : ''}</span><span class="scr">${p[3]}–${p[4]}</span></div>`;
      }).join('') || '<div class="empty" style="margin:16px">No plays match.</div>';
    };
    if (nClips) body.querySelector('#pbpTabs').insertAdjacentHTML('beforeend', `<button class="chip" data-p="vid">▶ ${nClips} clips</button>`);
    pbp.addEventListener('click', (e) => { const b = e.target.closest('[data-clip]'); if (!b) return; const c = clips[b.dataset.clip]; openMp4({ src: c.src, thumb: c.thumb, title: c.title || plays.plays[b.dataset.clip][7] }); });
    render('all');
    body.querySelector('#pbpTabs').addEventListener('click', (e) => { const b = e.target.closest('[data-p]'); if (!b) return; body.querySelectorAll('#pbpTabs .chip').forEach((c) => c.classList.toggle('on', c === b)); render(b.dataset.p); });
  }
  if (vids.length) bindVideos(body.querySelector('#vids'), vids);
  return { destroy() { offs.forEach((f) => f()); tip(null); } };
}

function teamBlock(t, g, isU) {
  const won = g.res && ((isU && g.res === 'W') || (!isU && g.res === 'L'));
  return `<div class="g-team">${logo(t, 'lg')}<span class="nm">${t.rank ? `<span class="rk">#${t.rank}</span> ` : ''}${t.seed ? `<span class="rk">(${t.seed})</span> ` : ''}${esc(isU ? 'UConn' : t.name)}</span>
    <span class="led ${won ? '' : 'white'}">${t.score ?? (isU ? g.pts : g.opp_pts) ?? '—'}</span>${t.record ? `<span class="rk">${esc(t.record)}</span>` : ''}</div>`;
}

function gameScore(p) {
  return p.pts + 0.4 * p.fgm - 0.7 * p.fga - 0.4 * (p.fta - p.ftm) + 0.7 * p.oreb + 0.3 * (p.reb - p.oreb) + p.stl + 0.7 * p.ast + 0.7 * p.blk - 0.4 * p.pf - p.to;
}
function topPerformers(U, O) {
  const norm = (p, uconn) => ({ ...p, uconn, pts: p.pts || 0, reb: p.reb || 0, ast: p.ast || 0, stl: p.stl || 0, blk: p.blk || 0, fgm: p.fgm || 0, fga: p.fga || 0, tpm: p.tpm || 0, tpa: p.tpa || 0, ftm: p.ftm || 0, fta: p.fta || 0, oreb: p.oreb || 0, to: p.to || 0, pf: p.pf || 0 });
  const us = (U.players || []).map((p) => norm(p, true)).sort((a, b) => gameScore(b) - gameScore(a));
  const them = (O.players || []).map((p) => norm(p, false)).sort((a, b) => gameScore(b) - gameScore(a));
  return [...us.slice(0, 2), ...them.slice(0, 1)].filter(Boolean);
}

function boxTable(t, isU) {
  const ps = (t.players || []).filter((p) => !p.dnp);
  const who = { k: 'name', label: 'Player', l: true, html: (r) => r.pid && isU ? `<a class="who" href="#/player/${esc(r.pid)}">${headshot(r)}<span>${esc(r.name)}${r.starter ? '' : ''}</span></a>` : `<span class="who">${esc(r.name)}${r.pos ? ` <span class="muted">${esc(r.pos)}</span>` : ''}</span>` };
  const sh = (m, a) => ({ k: m, label: m === 'fgm' ? 'FG' : m === 'tpm' ? '3PT' : 'FT', html: (r) => (r[a] != null ? `${r[m] ?? 0}-${r[a]}` : '–'), get: (r) => r[m] });
  const tot = {};
  ['min', 'pts', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'oreb', 'reb', 'ast', 'stl', 'blk', 'to', 'pf'].forEach((k) => { tot[k] = ps.reduce((a, p) => a + (+p[k] || 0), 0); });
  tot.name = 'Team'; tot.min = tot.min ? Math.round(tot.min) : '';
  const cols = [who, { k: 'st', label: 'GS', get: (r) => (r.starter ? '•' : ''), html: (r) => (r.starter ? '<span style="color:var(--gold)">●</span>' : '') }, { k: 'min', label: 'MIN' }, { k: 'pts', label: 'PTS', heat: 1 },
    sh('fgm', 'fga'), sh('tpm', 'tpa'), sh('ftm', 'fta'), { k: 'oreb', label: 'OREB' }, { k: 'reb', label: 'REB', heat: 1 }, { k: 'ast', label: 'AST', heat: 1 },
    { k: 'stl', label: 'STL' }, { k: 'blk', label: 'BLK' }, { k: 'to', label: 'TO' }, { k: 'pf', label: 'PF' }];
  return statTable(cols, ps, { total: { ...tot, name: 'Totals' } });
}

function compareRows(U, O) {
  const s = (t, k) => t.stats?.[k];
  const rows = [['Field goal %', 'fg_pct', 1], ['3-point %', 'tp_pct', 1], ['Free throw %', 'ft_pct', 1], ['Rebounds', 'reb'], ['Offensive rebounds', 'oreb'], ['Assists', 'ast'], ['Steals', 'stl'], ['Blocks', 'blk'], ['Turnovers', 'to', 0, true], ['Points in the paint', 'paint'], ['Fast break points', 'fast'], ['Points off turnovers', 'pot'], ['Largest lead', 'lead'], ['Bench points', 'bench']];
  const out = rows.map(([lab, k, isPct, lowGood]) => {
    const a = +s(U, k), b = +s(O, k);
    if (isNaN(a) || isNaN(b) || (a === 0 && b === 0)) return '';
    const tot = a + b || 1;
    const good = lowGood ? a < b : a > b;
    return `<div class="cmp-row"><span class="lab">${lab}</span><span style="color:${good ? 'var(--ice)' : 'var(--fg-2)'}">${isPct ? a.toFixed(1) : a}</span>
      <div class="cmp-bar"><i style="width:${(a / tot) * 100}%;background:var(--ice)"></i><i style="width:${(b / tot) * 100}%;background:var(--red);opacity:.7"></i></div><span class="v2" style="color:${!good && a !== b ? 'var(--red-soft)' : 'var(--fg-2)'}">${isPct ? b.toFixed(1) : b}</span></div>`;
  }).join('');
  return `<div class="sec-head" style="margin:0 0 4px"><div><span class="eyebrow">Team stats</span><h3 class="h3">UConn vs. ${esc(O.abbr || O.name)}</h3></div></div>${out || '<div class="empty">Team stats unavailable.</div>'}`;
}

const clockSec = (c) => { const [m, s] = String(c).split(':').map(Number); return (m || 0) * 60 + (s || 0); };

// Biggest scoring runs + go-ahead moments from the play log.
function runsHtml(plays, O) {
  const ps = plays.plays; if (!ps?.length) return '';
  const runs = []; let cur = null;
  ps.forEach((p, i) => {
    if (!p[5] || !p[2]) return;
    if (cur && cur.side === p[2]) { cur.pts += p[6] || 0; cur.end = i; }
    else { if (cur) runs.push(cur); cur = { side: p[2], pts: p[6] || 0, start: i, end: i }; }
  });
  if (cur) runs.push(cur);
  const best = runs.filter((r) => r.pts >= 8).sort((a, b) => b.pts - a.pts).slice(0, 4);
  const leadChanges = ps.reduce((a, p, i) => { if (!i) return a; const d0 = Math.sign(ps[i - 1][3] - ps[i - 1][4]), d1 = Math.sign(p[3] - p[4]); return a + (d0 && d1 && d0 !== d1 ? 1 : 0); }, 0);
  const ties = ps.reduce((a, p, i) => a + (i && p[5] && p[3] === p[4] ? 1 : 0), 0);
  const big = Math.max(0, ...ps.map((p) => p[3] - p[4])), bigO = Math.max(0, ...ps.map((p) => p[4] - p[3]));
  return `<div class="feature-row" style="margin-top:16px">
    <div class="panel otd"><span class="eyebrow">Lead changes · ties</span><span class="score">${leadChanges} · ${ties}</span></div>
    <div class="panel otd"><span class="eyebrow">Biggest leads</span><span class="score"><span style="color:var(--ice)">UConn +${big}</span> · <span style="color:var(--red-soft)">${esc(O.abbr || 'Opp')} +${bigO}</span></span></div>
    ${best.map((r) => `<div class="panel otd"><span class="eyebrow ${r.side === 'u' ? '' : 'red'}">${r.side === 'u' ? 'UConn' : esc(O.abbr || O.name)} run</span><span class="score">${r.pts}–0</span><span class="note">${esc(ps[r.start][1])} ${ps[r.start][0] > 2 ? 'OT' : ps[r.start][0] === 1 ? '1st half' : '2nd half'} to ${esc(ps[r.end][1])}</span></div>`).join('')}
  </div>`;
}
function keyMoments(plays) {
  const ps = plays.plays, out = [];
  // last go-ahead score by the winner
  const fin = ps.at(-1); if (!fin) return out;
  const uWon = fin[3] > fin[4];
  for (let i = ps.length - 1; i > 0; i--) {
    const p = ps[i], q = ps[i - 1];
    const was = uWon ? q[3] <= q[4] : q[4] <= q[3], now = uWon ? p[3] > p[4] : p[4] > p[3];
    if (p[5] && was && now) { out.push({ i, tip: `<b>Go-ahead for good</b>${esc(p[7])}<br>${esc(p[1])} · ${p[3]}–${p[4]}` }); break; }
  }
  return out;
}

// ESPN recap HTML → only safe tags.
function sanitize(html) {
  const doc = new DOMParser().parseFromString(`<div>${html}</div>`, 'text/html');
  const ok = new Set(['P', 'B', 'STRONG', 'I', 'EM', 'H2', 'H3', 'UL', 'OL', 'LI', 'BR', 'A', 'BLOCKQUOTE']);
  const walk = (n) => {
    [...n.childNodes].forEach((c) => {
      if (c.nodeType === 1) {
        if (!ok.has(c.tagName)) { walk(c); c.replaceWith(...c.childNodes); return; }
        [...c.attributes].forEach((a) => { if (!(c.tagName === 'A' && a.name === 'href' && /^https?:/.test(a.value))) c.removeAttribute(a.name); });
        if (c.tagName === 'A') { c.target = '_blank'; c.rel = 'noopener'; }
        walk(c);
      } else if (c.nodeType !== 3) c.remove();
    });
  };
  const root = doc.body.firstChild; walk(root);
  return root.innerHTML;
}

import { esc, load, tryLoad, logo, UCONN, fmtDate, fmtTime, fmtDay, bindTips, tip, videoCard, bindVideos, headshot, FINISH, n1 } from '../ui.js';
import { skyline, onResize } from '../charts.js';
import { watch, nearTip } from '../live.js';

export default async function home(main, _args, core) {
  const titles = core.seasons.filter((s) => s.finish === 'champ');
  const cur = core.current || {};
  const eras = core.eras || [];
  const firstY = core.seasons[0].y;
  const totW = core.seasons.reduce((a, s) => a + s.w, 0), totL = core.seasons.reduce((a, s) => a + s.l, 0);
  const ncaaW = core.seasons.reduce((a, s) => a + (s.ncaaW || 0), 0), ncaaL = core.seasons.reduce((a, s) => a + (s.ncaaL || 0), 0);
  const featured = (core.videos || []).filter((v) => v.featured).slice(0, 12);

  main.innerHTML = `
  <section class="rafters" id="rafters" data-title="">
    <div class="rafters-hint" aria-hidden="true">Tap a banner</div>
    <div class="rafters-copy"><div class="wrap">
      <span class="eyebrow red">UConn men's basketball · ${firstY - 1} to now</span>
      <h1 class="h-display"><span>${titles.length} banners.</span><span class="thin">${core.seasons.filter((s) => !s.future).length} seasons.</span></h1>
      <p class="lede">Every team since Jim Calhoun walked into Storrs in 1986. Every game, every box score we could find, every Husky, and every March that ended with a ladder and a pair of scissors.</p>
      <div class="chips" style="margin-top:6px"><a class="btn solid" href="#/now">The ${esc(cur.label || '2026–27')} Huskies</a><a class="btn" href="#/season/${firstY}">Start in ${firstY - 1}–${String(firstY).slice(2)}</a><a class="btn" href="#/march">March</a></div>
    </div></div>
    <div class="banner-tip" id="bannerTip"></div>
  </section>

  <section class="section"><div class="wrap grid" style="gap:28px">
    ${nextGameBlock(cur)}
  </div></section>

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${totW}–${totL} since ${firstY - 1} · ${ncaaW}–${ncaaL} in the NCAA Tournament</span><h2 class="h2">Every season, one skyline</h2></div></div>
    <div class="skyline-wrap" id="sky"></div>
      <div class="legend sky-legend">${['champ', 'runner', 'final4', 'elite8', 'sweet16', 'r32', 'r64', 'nit', 'none'].map((k) => `<span><i style="background:${FINISH[k].color}"></i>${FINISH[k].short === '—' ? 'No postseason' : FINISH[k].short}</span>`).join('')}<span><i style="background:var(--red);opacity:.5"></i>Losses</span></div>
  </div></section>

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Three coaches</span><h2 class="h2">The eras</h2></div></div>
    <div class="feature-row">${eras.map(eraCard).join('')}</div>
  </div></section>

  <section class="section" id="otdSec"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow" id="otdEyebrow">On this day</span><h2 class="h2">This date in Husky history</h2></div><span class="aside">Games played on today's date in any season since ${firstY - 1}.</span></div>
    <div class="feature-row" id="otd"><div class="empty">Loading…</div></div>
  </div></section>

  ${featured.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">From the vault</span><h2 class="h2">Moments you can still hear</h2></div><a class="btn" href="#/vault">All video</a></div>
    <div class="hscroll" id="featVids">${featured.map((v) => `<div style="width:min(320px,80vw)">${videoCard(v)}</div>`).join('')}</div>
  </div></section>` : ''}

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Since ${firstY - 1}</span><h2 class="h2">Most points in a UConn uniform</h2></div><a class="btn" href="#/numbers">All the numbers</a></div>
    <div class="panel lead-list">${[...core.players].filter((p) => p.pts).sort((a, b) => b.pts - a.pts).slice(0, 10).map((p, i) => `
      <a class="lead-row" href="#/player/${p.id}"><span class="i">${i + 1}</span>${headshot(p)}<span><b>${esc(p.name)}</b><small>${esc(p.span)} · ${n1(p.ppg)} ppg</small></span><span class="v">${p.pts.toLocaleString()}</span></a>`).join('')}</div>
  </div></section>`;

  // Skyline
  const sky = main.querySelector('#sky');
  const drawSky = () => skyline(sky, core.seasons.filter((s) => !s.future), eras);
  drawSky(); bindTips(sky);
  const offSky = onResize(sky, drawSky);

  // Rafters 3D
  let scene = null;
  const host = main.querySelector('#rafters');
  const tipEl = main.querySelector('#bannerTip');
  const secondary = (core.banners?.secondary || []);
  import('../rafters.js').then(({ mount }) => {
    if (!host.isConnected) return;
    scene = mount(host, {
      titles: titles.map((s) => ({ y: s.y, rec: `${s.w}–${s.l}`, coach: s.coach, mop: s.mop })),
      secondary,
      onPick: (b) => { location.hash = `#/season/${b.y}`; },
      onHover: (b, e) => {
        if (!b || !e) { tipEl.classList.remove('on'); return; }
        const r = host.getBoundingClientRect();
        tipEl.style.left = `${e.clientX - r.left}px`; tipEl.style.top = `${e.clientY - r.top}px`;
        tipEl.textContent = b.kind === 'title' ? `${b.y} national champions · ${b.rec}` : `${(b.label || '').replace('\n', ' ')} ${b.y}`;
        tipEl.classList.add('on');
      },
    });
    if (!scene) host.insertAdjacentHTML('afterbegin', `<div class="fallback-banners">${titles.map((s) => `<a class="pill champ" href="#/season/${s.y}">${s.y}</a>`).join('')}</div>`);
  });

  // Countdown
  let timer = 0;
  const cd = main.querySelector('#countdown');
  if (cd && cur.next?.date) {
    const target = new Date(cur.next.date).getTime();
    const tick = () => {
      let s = Math.max(0, Math.floor((target - Date.now()) / 1000));
      const d = Math.floor(s / 86400); s -= d * 86400; const h = Math.floor(s / 3600); s -= h * 3600; const m = Math.floor(s / 60); s -= m * 60;
      cd.innerHTML = [[d, 'Days'], [h, 'Hrs'], [m, 'Min'], [s, 'Sec']].map(([v, l]) => `<div><span class="led">${String(v).padStart(2, '0')}</span><span class="board-label">${l}</span></div>`).join('');
    };
    tick(); timer = setInterval(tick, 1000);
  }

  // On this day
  tryLoad('games_index.json').then((gi) => {
    const el = main.querySelector('#otd'); if (!el) return;
    if (!gi) { main.querySelector('#otdSec').hidden = true; return; }
    const now = new Date();
    let md = `${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    let hits = gi.filter((g) => g.date.slice(5, 10) === md && g.res);
    let label = 'On this day';
    if (!hits.length) {
      // nearest upcoming date that has a game
      const all = [...new Set(gi.filter((g) => g.res).map((g) => g.date.slice(5, 10)))].sort();
      const next = all.find((d) => d > md) || all[0];
      hits = gi.filter((g) => g.date.slice(5, 10) === next && g.res); md = next;
      const [mm, dd] = next.split('-');
      label = `No games on today's date. Next up: ${new Date(2000, mm - 1, dd).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}`;
    }
    main.querySelector('#otdEyebrow').textContent = label;
    hits.sort((a, b) => (b.big || 0) - (a.big || 0) || b.date.localeCompare(a.date));
    el.innerHTML = hits.slice(0, 6).map((g) => `
      <a class="panel otd" href="#/game/${g.id}">
        <span class="eyebrow ${g.type === 'NCAA' ? 'gold' : ''}">${fmtDate(g.date, { year: true })}${g.round ? ' · ' + esc(g.round) : ''}</span>
        <div class="game-line">${logo(g.opp)}<b style="font:700 18px/1.1 var(--f-cond);text-transform:uppercase">${g.ha === 'A' ? 'at ' : g.ha === 'N' ? 'vs. ' : 'vs. '}${esc(g.opp.name)}</b></div>
        <div class="game-line"><span class="score" style="color:${g.res === 'W' ? 'var(--ice)' : 'var(--red-soft)'}">${g.res} ${g.pts}–${g.opp_pts}</span>${g.ot ? `<span class="pill">${esc(g.ot)}</span>` : ''}</div>
        ${g.top ? `<span class="note">${esc(g.top)}</span>` : ''}
      </a>`).join('');
  });

  if (featured.length) bindVideos(main.querySelector('#featVids'), featured);

  // Game night: swap the countdown for the live score
  let stopLive = () => {};
  if (cur.next?.eid && nearTip(cur.next.date) && cd) {
    stopLive = watch(cur.next.eid, (L) => {
      if (L.state === 'pre') return;
      clearInterval(timer);
      cd.innerHTML = `<div><span class="led">${L.us}</span><span class="board-label">UConn</span></div><div><span class="led white">${L.os}</span><span class="board-label">${esc(cur.next.opp.abbr || 'Opp')}</span></div>`;
      cd.insertAdjacentHTML('beforebegin', '');
      const lab = cd.previousElementSibling; if (lab) lab.innerHTML = L.state === 'in' ? `<span class="pill live">Live</span> ${esc(L.detail || '')}` : `Final · ${esc(L.detail || '')}`;
    });
  }

  return { destroy() { scene?.destroy(); clearInterval(timer); offSky(); tip(null); stopLive(); } };
}

function eraCard(e) {
  return `<a class="panel otd" href="#/seasons" style="gap:14px">
    <div style="display:flex;gap:16px;align-items:center">
      ${e.photo ? `<img src="${esc(e.photo)}" alt="" style="width:84px;height:84px;border-radius:50%;object-fit:cover;object-position:50% 20%;border:2px solid var(--line-2)" loading="lazy">` : ''}
      <div style="display:grid;gap:6px"><span class="eyebrow">${e.from - 1}–${e.to === 9999 ? 'now' : e.to}</span><h3 class="h2" style="font-size:34px">${esc(e.name)}</h3></div>
    </div>
    <div class="era-stats">
      <div><b>${e.w}–${e.l}</b><span>Record</span></div>
      <div><b>${e.titles?.length || 0}</b><span>Titles</span></div>
      <div><b>${e.ff || 0}</b><span>Final Fours</span></div>
      <div><b>${e.ncaa || 0}</b><span>NCAA trips</span></div>
    </div>
    ${e.blurb ? `<p class="muted" style="font-size:15px">${esc(e.blurb)}</p>` : ''}
  </a>`;
}

function nextGameBlock(cur) {
  const g = cur.next;
  if (!g) return cur.last ? lastGameBlock(cur) : '';
  const opp = g.opp || {};
  const home = g.ha === 'H';
  const left = home ? opp : UCONN, right = home ? UCONN : opp;
  return `<div class="sec-head" style="margin-bottom:0"><div><span class="eyebrow red">${esc(cur.label || '')} · ${esc(cur.record || 'Season opener')}${cur.rank ? ` · AP No. ${cur.rank}` : ''}</span><h2 class="h2">Next tip</h2></div><a class="btn" href="#/now">Full schedule</a></div>
  <a class="board" href="#/game/${g.id}">
    <div class="nextgame">
      <div class="team">${logo(left, 'xl')}<b>${left.rank ? `<span class="led" style="font-size:.9em">${left.rank}</span> ` : ''}${esc(left.name)}</b><span class="board-label">${left === UCONN ? (home ? 'Home' : 'Away') : (home ? 'Away' : 'Home')}</span></div>
      <div class="mid"><span class="board-label">${esc(fmtDay(g.date))} ${esc(fmtDate(g.date, { year: true }))} · ${esc(fmtTime(g.date))}</span><div class="countdown" id="countdown"></div><span class="board-label">${g.ha === 'N' ? 'Neutral site' : home ? 'Home' : 'Road'}</span></div>
      <div class="team">${logo(right, 'xl')}<b>${right.rank ? `<span class="led" style="font-size:.9em">${right.rank}</span> ` : ''}${esc(right.name)}</b><span class="board-label">${right === UCONN ? 'Home' : 'Home'}</span></div>
    </div>
    <div class="board-foot">${g.venue ? `<span>${esc(g.venue)}</span>` : ''}${g.tv ? `<span>TV: ${esc(g.tv)}</span>` : ''}${g.note ? `<span>${esc(g.note)}</span>` : ''}</div>
  </a>
  ${cur.last ? lastGameBlock(cur, true) : ''}`;
}
function lastGameBlock(cur, small) {
  const g = cur.last;
  return `<a class="panel otd" href="#/game/${g.id}" style="${small ? '' : ''}">
    <span class="eyebrow">Last time out · ${fmtDate(g.date, { year: true })}</span>
    <div class="game-line">${logo(g.opp)}<b style="font:700 18px/1.1 var(--f-cond);text-transform:uppercase">${g.ha === 'A' ? 'at ' : 'vs. '}${esc(g.opp.name)}</b><span class="score" style="margin-left:auto;color:${g.res === 'W' ? 'var(--ice)' : 'var(--red-soft)'}">${g.res} ${g.pts}–${g.opp_pts}</span></div>
    ${g.top ? `<span class="note">${esc(g.top)}</span>` : ''}</a>`;
}

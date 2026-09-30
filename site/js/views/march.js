import { esc, logo, fmtDate, bindTips, tip, videoCard, bindVideos } from '../ui.js';

const ROUNDS = ['First Round', 'Second Round', 'Sweet 16', 'Elite Eight', 'Final Four', 'Title Game'];

export default async function march(main, _args, core) {
  const M = core.march || { years: [] };
  const yrs = M.years;
  const games = yrs.flatMap((y) => y.games);
  const W = games.filter((g) => g.res === 'W').length, L = games.filter((g) => g.res === 'L').length;
  const reached = (r) => yrs.filter((y) => y.games.some((g) => g.r >= r)).length;
  const bySeed = {};
  yrs.forEach((y) => { const k = y.seed || '?'; bySeed[k] ||= { n: 0, w: 0, l: 0 }; bySeed[k].n++; y.games.forEach((g) => { bySeed[k][g.res === 'W' ? 'w' : 'l']++; }); });
  const titleVids = (core.videos || []).filter((v) => v.round && /final|championship|title/i.test(v.round) && v.kind !== 'interview').slice(0, 12);

  main.innerHTML = `<div data-title="March"></div>
  <section class="march-hero"><div class="wrap grid" style="gap:18px">
    <span class="eyebrow gold">The NCAA Tournament since ${core.seasons[0].y - 1}</span>
    <h1 class="h-display">March<br>belongs<br>to us.</h1>
    <p class="lede">${yrs.length} tournaments, ${W} wins, ${L} losses. In national championship games: ${games.filter((g) => g.r === 5 && g.res === 'W').length}–${games.filter((g) => g.r === 5 && g.res === 'L').length}${games.some((g) => g.r === 5 && g.res === 'L') ? '' : ', never beaten on the final Monday'}.</p>
    <div class="round-table" style="margin-top:12px">
      ${[['Appearances', yrs.length], ['Record', `${W}–${L}`], ['Sweet 16s', reached(2)], ['Elite Eights', reached(3)], ['Final Fours', reached(4)], ['Titles', M.titles?.length || 0]].map(([l, v]) => `<div class="panel"><b>${v}</b><span>${l}</span></div>`).join('')}
    </div>
  </div></section>

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow gold">${M.titles?.length || 0} national championships</span><h2 class="h2">The title runs</h2></div></div>
    <div class="title-cards">${(M.titles || []).map((t) => `
      <div class="tcard"><div style="display:flex;justify-content:space-between;align-items:start;gap:10px"><a class="yr" href="#/season/${t.y}">${t.y}</a><span style="text-align:right;display:grid;gap:4px"><span class="pill champ">${t.rec}</span><span class="note">No. ${t.seed} seed · ${esc(t.coach)}</span></span></div>
        ${t.mop ? `<span class="eyebrow">Most Outstanding Player · <span style="color:var(--fg)">${esc(t.mop)}</span></span>` : ''}
        <ol>${t.games.map((g) => `<li><span class="rd">${esc(ROUNDS[g.r] || g.round)}</span><a href="#/game/${g.id}">${g.opp.seed ? `<span class="muted">${g.opp.seed}</span> ` : ''}${esc(g.opp.name)}</a><span>${g.pts}–${g.opp_pts}</span></li>`).join('')}</ol>
        <span class="note">Average margin +${(t.games.reduce((a, g) => a + g.pts - g.opp_pts, 0) / t.games.length).toFixed(1)}</span>
      </div>`).join('')}</div>
  </div></section>

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Every bracket, every round</span><h2 class="h2">The path, year by year</h2></div>
      <div class="legend"><span><i style="background:rgba(143,193,255,.5)"></i>Win</span><span><i style="background:rgba(228,0,43,.6)"></i>Loss</span><span><i style="background:var(--gold)"></i>Title</span></div></div>
    ${yrs.some((y) => y.y === 1996) ? '<p class="note" style="margin-bottom:12px">The NCAA later vacated UConn\'s three 1996 tournament games; they are shown as played.</p>' : ''}
    <div class="bracket-scroll"><div class="bracket-years" id="by">
      <div class="byear head"><div>Year</div><div>Seed</div>${ROUNDS.map((r) => `<div>${r}</div>`).join('')}</div>
      ${[...yrs].reverse().map((y) => `<div class="byear"><a class="y" href="#/season/${y.y}">${y.y}</a><span class="sd">${y.seed || ''}</span>${ROUNDS.map((_, r) => {
        const g = y.games.find((x) => x.r === r);
        if (!g) return '<span class="cell none"></span>';
        const cls = g.res === 'L' ? 'L' : r === 5 ? 'T' : 'W';
        return `<a class="cell ${cls}" href="#/game/${g.id}" data-tip="${esc(`<b>${g.res} ${g.pts}–${g.opp_pts}${g.ot ? ' ' + esc(g.ot) : ''}</b>${ROUNDS[r]} · ${g.opp.seed ? '(' + g.opp.seed + ') ' : ''}${esc(g.opp.name)}<br>${fmtDate(g.date, { year: true })}${g.arena ? ' · ' + esc(g.arena) : ''}`)}">${logo(g.opp)}<span>${esc(g.opp.abbr || g.opp.name)} ${g.pts}–${g.opp_pts}</span></a>`;
      }).join('')}</div>`).join('')}
    </div></div>
  </div></section>

  <section class="section"><div class="wrap num-grid">
    <div><div class="sec-head"><div><span class="eyebrow">By seed line</span><h3 class="h2" style="font-size:32px">Seeds</h3></div></div>
      <div class="panel lead-list">${Object.entries(bySeed).sort((a, b) => a[0] - b[0]).map(([s, v]) => `<div class="lead-row" style="grid-template-columns:60px 1fr auto"><b>No. ${s}</b><span class="muted">${v.n} time${v.n > 1 ? 's' : ''}</span><span class="v">${v.w}–${v.l}</span></div>`).join('')}</div></div>
    <div><div class="sec-head"><div><span class="eyebrow">Heartbreak ledger</span><h3 class="h2" style="font-size:32px">Who ended it</h3></div></div>
      <div class="panel lead-list">${yrs.filter((y) => y.games.at(-1)?.res === 'L').reverse().map((y) => { const g = y.games.at(-1); return `<a class="lead-row" href="#/game/${g.id}" style="grid-template-columns:52px 36px 1fr auto"><b>${y.y}</b>${logo(g.opp)}<span><b>${esc(g.opp.name)}</b><small>${ROUNDS[g.r]}${g.arena ? ' · ' + esc(g.arena) : ''}</small></span><span class="v" style="font-size:20px;color:var(--red-soft)">${g.pts}–${g.opp_pts}</span></a>`; }).join('')}</div></div>
  </div></section>

  ${titleVids.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow gold">One shining moment, six times</span><h2 class="h2">Title nights</h2></div></div>
    <div class="vids" id="tv">${titleVids.map(videoCard).join('')}</div>
  </div></section>` : ''}

  ${M.nit?.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">The other tournament</span><h2 class="h2">NIT runs</h2></div></div>
    <div class="chips">${M.nit.map((n) => `<a class="chip" href="#/season/${n.y}">${n.y} · ${n.w}–${n.l}${n.champ ? ' · NIT champions' : ''}</a>`).join('')}</div>
  </div></section>` : ''}`;
  bindTips(main.querySelector('#by'));
  if (titleVids.length) bindVideos(main.querySelector('#tv'), titleVids);
  return { destroy() { tip(null); } };
}

import { esc, load, tryLoad, logo, headshot, fmtDate, n1, n0, pct, statTable, bindTips, tip, FINISH, finishPill } from '../ui.js';
import { scatter, onResize } from '../charts.js';

export default async function numbers(main, args, core) {
  if (args[0] === 'opp' && args[1]) return opponent(main, args[1], core);
  const L = core.leaders || {};
  const board = (title, list, unit, fmt = n0) => `<div class="panel lead-list"><div style="padding:14px 14px 6px"><span class="eyebrow">${esc(title)}</span></div>${(list || []).slice(0, 10).map((r, i) => `
    <a class="lead-row" href="${r.gid ? `#/game/${r.gid}` : `#/player/${r.pid}`}"><span class="i">${i + 1}</span>${headshot(r)}<span><b>${esc(r.name)}</b><small>${esc(r.sub || '')}</small></span><span class="v">${fmt(r.v)}${unit ? `<small style="display:inline;font:600 12px var(--f-cond);color:var(--muted)"> ${unit}</small>` : ''}</span></a>`).join('')}</div>`;

  const withEff = core.seasons.filter((s) => s.ortg && s.drtg && !s.future);
  main.innerHTML = `<div data-title="Numbers"></div>
  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Since ${core.seasons[0].y - 1}</span><h1 class="h1">The numbers</h1></div></div>
    <div class="tabs" id="ntabs">${['Records', 'Season vs. season', 'Efficiency map', 'Opponents'].map((t, i) => `<button class="${i ? '' : 'on'}" data-t="${i}">${t}</button>`).join('')}</div>
    <div id="npane"></div>
  </div></section>`;
  const pane = main.querySelector('#npane');
  let off = () => {};
  const panes = [
    () => {
      pane.innerHTML = `<div class="grid" style="gap:36px">
        <div><h2 class="h2" style="margin-bottom:16px">Career</h2><div class="num-grid">${board('Points', L.career?.pts)}${board('Rebounds', L.career?.trb)}${board('Assists', L.career?.ast)}${board('Blocks', L.career?.blk)}${board('Steals', L.career?.stl)}${board('3-pointers made', L.career?.fg3)}</div></div>
        <div><h2 class="h2" style="margin-bottom:16px">Single season</h2><div class="num-grid">${board('Points', L.season?.pts)}${board('Points per game (min. 20 G)', L.season?.ppg, 'PPG', n1)}${board('Rebounds', L.season?.trb)}${board('Assists', L.season?.ast)}${board('Blocks', L.season?.blk)}${board('3-pointers made', L.season?.fg3)}</div></div>
        ${L.game ? `<div><h2 class="h2" style="margin-bottom:6px">Single game</h2><p class="note" style="margin-bottom:16px">${esc(L.gameNote || 'From box scores on file.')}</p><div class="num-grid">${board('Points', L.game.pts)}${board('Rebounds', L.game.reb)}${board('Assists', L.game.ast)}${board('Blocks', L.game.blk)}${board('3-pointers made', L.game.tpm)}${board('Steals', L.game.stl)}</div></div>` : ''}
      </div>`;
    },
    () => {
      const rows = core.seasons.map((s) => ({ ...s, pctv: s.w / (s.w + s.l), marg: s.ppg && s.oppg ? s.ppg - s.oppg : null, fr: FINISH[s.finish]?.rank || 0 }));
      const t = statTable([
        { k: 'y', label: 'Season', l: true, html: (r) => `<a href="#/season/${r.y}">${esc(r.label)}</a>` }, { k: 'coach', label: 'Coach', l: true },
        { k: 'w', label: 'W', heat: 1 }, { k: 'l', label: 'L' }, { k: 'pctv', label: 'Win%', fmt: (v) => (v * 100).toFixed(1) }, { k: 'cw', label: 'Conf', html: (r) => (r.cw != null ? `${r.cw}–${r.cl}` : '–'), get: (r) => r.cw },
        { k: 'ppg', label: 'PPG', fmt: n1 }, { k: 'oppg', label: 'OPP', fmt: n1 }, { k: 'marg', label: 'Margin', fmt: (v) => (v == null ? '–' : (v > 0 ? '+' : '') + v.toFixed(1)), heat: 1 },
        { k: 'srs', label: 'SRS', fmt: n1, title: 'Simple Rating System' }, { k: 'sos', label: 'SOS', fmt: n1, title: 'Strength of schedule' }, { k: 'ortg', label: 'ORtg', fmt: n1 }, { k: 'drtg', label: 'DRtg', fmt: n1 }, { k: 'pace', label: 'Pace', fmt: n1 },
        { k: 'apPre', label: 'AP Pre' }, { k: 'apFinal', label: 'AP Final' }, { k: 'seed', label: 'Seed' }, { k: 'fr', label: 'Finish', l: true, html: (r) => finishPill(r.finish) },
      ], rows.reverse(), { sort: 'y' });
      pane.innerHTML = t.html; t.bind(pane);
    },
    () => {
      pane.innerHTML = `<div class="panel chart-card"><div class="sec-head" style="margin:0"><div><span class="eyebrow">Points scored vs. allowed per 100 possessions</span><h3 class="h3">Every season on one map</h3></div>
        <div class="legend">${['champ', 'runner', 'final4', 'elite8', 'sweet16', 'r32', 'r64', 'nit', 'none'].map((k) => `<span><i style="background:${FINISH[k].color};border-radius:50%"></i>${FINISH[k].short === '—' ? 'None' : FINISH[k].short}</span>`).join('')}</div></div><div id="sc"></div>
        <p class="note">Up and to the right is better: more efficient offense, stingier defense. Ratings from Sports-Reference where published; earlier seasons are estimated from team box-score totals (possessions = FGA − OREB + TO + 0.475 × FTA).</p></div>`;
      const el = pane.querySelector('#sc');
      const pts = withEff.map((s) => ({ season: s.y, label: s.finish === 'runner' || s.finish === 'final4', y: s.drtg, x: s.ortg, finish: s.finish, tip: `<b>${esc(s.label)} · ${s.w}-${s.l}</b>ORtg ${n1(s.ortg)} · DRtg ${n1(s.drtg)}<br>${esc(FINISH[s.finish]?.label || '')}` }));
      const draw = () => scatter(el, pts, { xLabel: 'OFFENSIVE RATING', yLabel: 'DEFENSIVE RATING (BETTER ↑)', corner: 'Elite both ways', label: 'Efficiency map', invertY: true });
      draw(); bindTips(el); off = onResize(el, draw);
    },
    () => {
      const opps = Object.values(core.opponents || {}).sort((a, b) => b.w + b.l - (a.w + a.l));
      const t = statTable([
        { k: 'name', label: 'Opponent', l: true, html: (r) => `<a class="who" href="#/numbers/opp/${esc(r.key)}">${logo(r)}${esc(r.name)}</a>` },
        { k: 'g', label: 'G', get: (r) => r.w + r.l, heat: 1 }, { k: 'w', label: 'W' }, { k: 'l', label: 'L' }, { k: 'pct', label: 'Win%', get: (r) => r.w / (r.w + r.l), fmt: (v) => (v * 100).toFixed(0) },
        { k: 'all', label: 'All-time', title: 'Official all-time series record (UConn record book, every era)', html: (r) => (r.allW != null ? `${r.allW}–${r.allL}` : ''), get: (r) => (r.allW != null ? r.allW + r.allL : -1) },
        { k: 'ncaa', label: 'NCAA', title: 'Meetings in the NCAA Tournament', html: (r) => (r.ncaa ? `${r.ncaaW}–${r.ncaa - r.ncaaW}` : '') , get: (r) => r.ncaa },
        { k: 'last', label: 'Last met', html: (r) => fmtDate(r.last, { year: true }), get: (r) => r.last },
      ], opps, { sort: 'g' });
      pane.innerHTML = `<p class="note" style="margin-bottom:12px">${opps.length} opponents since ${core.seasons[0].y - 1}–${String(core.seasons[0].y).slice(2)}. Tap one for every meeting.</p>${t.html}`; t.bind(pane);
    },
  ];
  const show = (i) => { off(); off = () => {}; panes[i](); };
  show(+(args[0] === 'tab' ? args[1] : 0) || 0);
  main.querySelector('#ntabs').addEventListener('click', (e) => { const b = e.target.closest('[data-t]'); if (!b) return; main.querySelectorAll('#ntabs button').forEach((x) => x.classList.toggle('on', x === b)); show(+b.dataset.t); });
  return { destroy() { off(); tip(null); } };
}

async function opponent(main, key, core) {
  const o = core.opponents?.[key];
  const gi = await load('games_index.json');
  const gs = gi.filter((g) => g.opp.key === key && g.res);
  if (!o) throw new Error('Unknown opponent');
  const pts = gs.reduce((a, g) => a + g.pts, 0), opp = gs.reduce((a, g) => a + g.opp_pts, 0);
  const streak = (() => { let n = 0; const r = gs.at(-1)?.res; for (let i = gs.length - 1; i >= 0 && gs[i].res === r; i--) n++; return r ? `${r}${n}` : '–'; })();
  main.innerHTML = `<div data-title="UConn vs. ${esc(o.name)}"></div>
  <section class="s-hero"><div class="wrap">
    <a class="eyebrow" href="#/numbers/tab/3">← All opponents</a>
    <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap">${logo(o, 'xl')}<h1 class="h-display" style="font-size:clamp(40px,7vw,96px)">vs. ${esc(o.name)}</h1></div>
    <div class="statline">${o.allW != null ? `<div><b>${o.allW}–${o.allL}</b><span>All-time (official)</span></div>` : ''}<div><b>${o.w}–${o.l}</b><span>Since ${core.seasons[0].y - 1}–${String(core.seasons[0].y).slice(2)}</span></div><div><b>${gs.length ? n1(pts / gs.length) : '–'}–${gs.length ? n1(opp / gs.length) : '–'}</b><span>Avg score</span></div><div><b>${streak}</b><span>Current streak</span></div>${o.ncaa ? `<div><b>${o.ncaaW}–${o.ncaa - o.ncaaW}</b><span>In the NCAAs</span></div>` : ''}</div>
  </div></section>
  <section class="section"><div class="wrap"><div class="panel sched">${gs.slice().reverse().map((g) => `
    <a class="srow${g.type === 'NCAA' ? ' post' : ''}" href="#/game/${g.id}"><span class="d">${fmtDate(g.date, { year: true }).replace(', ', '<br>')}</span>${logo(g.opp)}
      <span class="o"><b><span class="muted" style="font-weight:600">${g.ha === 'A' ? 'at' : 'vs.'}</span> ${esc(g.opp.name)}</b><small>${esc([g.round, g.top].filter(Boolean).join(' · '))}</small></span>
      <span class="r ${g.res}">${g.res}${g.forfeit ? '<em>FF</em>' : ''} ${g.pts}–${g.opp_pts}${g.ot ? `<em>${esc(g.ot)}</em>` : ''}</span><span class="x">›</span></a>`).join('')}</div></div></section>`;
}

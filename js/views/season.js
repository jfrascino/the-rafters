import { esc, load, logo, fmtDate, fmtTime, finishPill, FINISH, n1, n0, pct, statTable, bindTips, tip, videoCard, bindVideos, photoFig, bindPhotos, initials, ord } from '../ui.js';
import { heartbeat, pollLine, onResize } from '../charts.js';

export default async function season(main, args, core) {
  const y = +args[0] || core.seasons.at(-1).y;
  const s = await load(`seasons/${y}.json`);
  const idx = core.seasons.findIndex((x) => x.y === y);
  const prev = core.seasons[idx - 1], next = core.seasons[idx + 1];
  const sum = core.seasons[idx] || {};
  const champ = s.finish === 'champ';
  const played = s.games.filter((g) => g.res);
  const ncaa = s.games.filter((g) => g.type === 'NCAA');
  const ctourn = s.games.filter((g) => g.type === 'CTOURN');
  const nit = s.games.filter((g) => g.type === 'NIT');
  const story = s.story || {};
  const paras = (story.text || '').split(/\n\s*\n/).filter(Boolean);
  const roster = [...(s.roster || [])].sort((a, b) => (b.pg?.pts ?? -1) - (a.pg?.pts ?? -1));

  main.innerHTML = `<div data-title="${esc(s.label)}"></div>
  <section class="s-hero">
    <div class="bgyear" aria-hidden="true">${String(y - 1).slice(2)}–${String(y).slice(2)}</div>
    <div class="wrap">
      <div class="s-hero-top"><span class="eyebrow">${esc(s.label)} · ${esc(s.coach)} · ${esc(s.conf || '')}</span>
        <nav class="s-nav" aria-label="Season navigation">${prev ? `<a href="#/season/${prev.y}">← ${esc(prev.label)}</a>` : ''}${next ? `<a href="#/season/${next.y}">${esc(next.label)} →</a>` : ''}</nav></div>
      <h1 class="h-display" style="font-size:clamp(40px,7vw,104px);max-width:14ch">${esc(story.headline || s.label)}</h1>
      <div class="chips">${finishPill(s.finish)}${s.seed ? `<span class="pill">No. ${s.seed} seed${s.region ? ' · ' + esc(s.region) : ''}</span>` : ''}${s.confFinish ? `<span class="pill">${esc(s.confFinish)}</span>` : ''}${(story.honors || []).filter((h) => /champion/i.test(h)).slice(0, 3).map((h) => `<span class="pill ff">${esc(h)}</span>`).join('')}</div>
      <div class="statline">
        <div><b>${s.w}–${s.l}</b><span>Overall</span></div>
        ${s.cw != null ? `<div><b>${s.cw}–${s.cl}</b><span>${esc(s.confShort || 'Conf')}</span></div>` : ''}
        <div><b>${s.apFinal ? '#' + s.apFinal : s.apHigh ? '#' + s.apHigh : 'NR'}</b><span>${s.apFinal ? 'Final AP' : s.apHigh ? 'AP peak' : 'Final AP'}</span></div>
        ${s.apHigh && s.apFinal ? `<div><b>#${s.apHigh}</b><span>AP peak</span></div>` : ''}
        ${s.ppg ? `<div><b>${n1(s.ppg)}</b><span>Points/G</span></div><div><b>${n1(s.oppg)}</b><span>Allowed/G</span></div>` : ''}
        ${s.srs != null ? `<div><b>${n1(s.srs)}</b><span title="Simple Rating System: points better than an average team">SRS</span></div>` : ''}
      </div>
    </div>
  </section>

  ${paras.length || story.honors?.length ? `<section class="section"><div class="wrap story">
    <div class="prose">${paras.map((p) => `<p>${esc(p)}</p>`).join('') || '<p class="muted">Season story coming soon.</p>'}
      ${story.sources?.length ? `<p class="note">Sources: ${story.sources.slice(0, 4).map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener" style="text-decoration:underline">${esc(new URL(u).hostname.replace('www.', ''))}</a>`).join(', ')}</p>` : ''}</div>
    <div class="grid" style="gap:28px">
      ${story.honors?.length ? `<div class="honors"><span class="eyebrow gold">Honors</span><ul>${story.honors.map((h) => `<li>${esc(h)}</li>`).join('')}</ul></div>` : ''}
      ${story.moments?.length ? `<div class="honors"><span class="eyebrow">Key moments</span><ul>${story.moments.map((m) => `<li style="display:grid;gap:4px"><b style="font:700 16px/1.2 var(--f-cond);text-transform:uppercase;letter-spacing:.03em">${m.date ? `<span class="muted">${fmtDate(m.date)} · </span>` : ''}${esc(m.title)}</b><span class="muted" style="font-size:14px">${esc(m.text || '')}</span></li>`).join('')}</ul></div>` : ''}
    </div>
  </div></section>` : ''}

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Game by game · ${played.length} games</span><h2 class="h2">The heartbeat</h2></div><span class="aside">Bar height is the final margin. Wins rise, losses fall. Tap any game for its box score.</span></div>
    <div id="hb"></div>
  </div></section>

  ${ncaa.length || nit.length ? runSection(ncaa.length ? ncaa : nit, ncaa.length ? 'NCAA Tournament' : 'NIT', champ) : ''}
  ${ctourn.length ? runSection(ctourn, `${s.confShort || 'Conference'} Tournament`, false, true) : ''}

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${roster.length} players</span><h2 class="h2">The roster</h2></div><span class="aside">Tap a card to flip it for the full stat line.</span></div>
    <div class="cards" id="cards">${roster.map((p) => playerCard(p, champ, y)).join('')}</div>
  </div></section>

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Sortable · tap a column</span><h2 class="h2">Stats</h2></div></div>
    <div class="tabs" role="tablist" id="stabs">${['Per game', 'Totals', 'Advanced', 'Team vs. opponents'].map((t, i) => `<button role="tab" class="${i ? '' : 'on'}" data-t="${i}">${t}</button>`).join('')}</div>
    <div id="stbl"></div>
  </div></section>

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${s.games.length} games</span><h2 class="h2">Schedule &amp; results</h2></div></div>
    <div class="panel sched" id="sched">${schedule(s.games)}</div>
  </div></section>

  ${(s.polls || []).length > 1 ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">AP Top 25, week by week</span><h2 class="h2">The poll ride</h2></div></div>
    <div class="panel chart-card" id="poll"></div>
  </div></section>` : ''}

  ${(s.videos || []).length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${s.videos.length} videos</span><h2 class="h2">Watch ${esc(s.label)}</h2></div></div>
    <div class="vids" id="vids">${s.videos.map(videoCard).join('')}</div>
  </div></section>` : ''}

  ${(s.photos || []).length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${s.photos.length} photos</span><h2 class="h2">Photos</h2></div></div>
    <div class="photos" id="photos">${s.photos.map(photoFig).join('')}</div>
  </div></section>` : ''}`;

  // Heartbeat + poll
  const hb = main.querySelector('#hb');
  const drawHb = () => heartbeat(hb, s.games);
  drawHb(); bindTips(hb);
  const offs = [onResize(hb, drawHb)];
  const pollEl = main.querySelector('#poll');
  if (pollEl) { const d = () => pollLine(pollEl, s.polls); d(); bindTips(pollEl); offs.push(onResize(pollEl, d)); }

  // Card flips
  main.querySelector('#cards').addEventListener('click', (e) => {
    if (e.target.closest('a')) return;
    const c = e.target.closest('.pcard'); if (c) c.classList.toggle('flip');
  });
  main.querySelector('#cards').addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.classList.contains('pcard')) { e.preventDefault(); e.target.classList.toggle('flip'); }
  });

  // Stat tables
  const tables = statTables(s, roster);
  const stbl = main.querySelector('#stbl');
  const showT = (i) => { const t = tables[i](); stbl.innerHTML = t.html; t.bind(stbl); };
  showT(0);
  main.querySelector('#stabs').addEventListener('click', (e) => {
    const b = e.target.closest('[data-t]'); if (!b) return;
    main.querySelectorAll('#stabs button').forEach((x) => x.classList.toggle('on', x === b));
    showT(+b.dataset.t);
  });

  if (s.videos?.length) bindVideos(main.querySelector('#vids'), s.videos);
  if (s.photos?.length) bindPhotos(main.querySelector('#photos'), s.photos);
  return { destroy() { offs.forEach((f) => f()); tip(null); } };
}

function runSection(games, title, champ, conf) {
  const last = games.at(-1);
  const won = last?.res === 'W';
  return `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow ${conf ? '' : 'gold'}">${esc(title)}</span><h2 class="h2">${champ && !conf ? 'The run to the title' : conf ? (won ? 'Tournament champions' : 'Conference tournament') : 'The tournament run'}</h2></div></div>
    <div class="panel run">${games.map((g, i) => {
      const cls = g.res === 'L' ? 'l' : (i === games.length - 1 && won && (champ || conf)) ? 'title' : '';
      return `<a class="run-step ${cls}" href="#/game/${g.id}">
        <span class="round">${esc(g.round || fmtDate(g.date))}</span>
        <span class="opp">${logo(g.opp)}<span>${g.opp.seed ? `<span class="muted">${g.opp.seed}</span> ` : ''}${esc(g.opp.name)}</span></span>
        <span class="sc">${g.res ? `${g.res} ${g.pts}–${g.opp_pts}` : 'TBD'}</span>
        <span class="where">${fmtDate(g.date, { year: true })}${g.arena ? ' · ' + esc(g.arena) : ''}${g.ot ? ' · ' + esc(g.ot) : ''}</span>
        ${g.top ? `<span class="where" style="color:var(--fg-2)">${esc(g.top)}</span>` : ''}
      </a>`;
    }).join('')}</div>
  </div></section>`;
}

export function playerCard(p, champ, y) {
  const pg = p.pg || {};
  const photo = p.photo ? `<img src="${esc(p.photo)}" alt="" loading="lazy" class="${p.photoWide ? 'wide' : ''}" onerror="this.remove()">` : '';
  return `<div class="pcard${champ ? ' champ' : ''}" tabindex="0" aria-label="${esc(p.name)} card">
    <div class="pcard-in">
      <div class="pcard-face pcard-front">
        <div class="photo"><span class="initials" aria-hidden="true">${esc(initials(p.name))}</span>${photo}</div>
        ${p.num != null && p.num !== '' ? `<span class="jnum">${esc(p.num)}</span>` : ''}
        ${p.pos ? `<span class="pill pos">${esc(p.pos)}</span>` : ''}
        <div class="plate"><span class="nm">${esc(p.name)}<small>${[p.cls, p.ht, p.home].filter(Boolean).map(esc).join(' · ')}</small></span>
          <span class="mini"><span><b>${n1(pg.pts)}</b>PTS</span><span><b>${n1(pg.trb)}</b>REB</span><span><b>${n1(pg.ast)}</b>AST</span></span></div>
      </div>
      <div class="pcard-face pcard-back">
        <span class="bk-nm">${esc(p.name)}</span>
        <span class="bk-bio">${[p.pos, p.cls, p.ht, p.wt ? p.wt + ' lb' : '', p.home, p.hs].filter(Boolean).map(esc).join(' · ')}</span>
        <table><thead><tr><th>${y ? `'${String(y).slice(2)}` : ''}</th><th>G</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th></tr></thead>
          <tbody><tr><td>Per G</td><td>${pg.g ?? '–'}</td><td>${n1(pg.mp)}</td><td>${n1(pg.pts)}</td><td>${n1(pg.trb)}</td><td>${n1(pg.ast)}</td></tr>
          <tr><td>Shoot</td><td colspan="5" style="text-align:right">FG ${pct(pg.fg_pct)} · 3P ${pct(pg.fg3_pct)} · FT ${pct(pg.ft_pct)}</td></tr>
          <tr><td>D</td><td colspan="5" style="text-align:right">${n1(pg.stl)} STL · ${n1(pg.blk)} BLK</td></tr>
          ${p.adv?.per != null ? `<tr><td>Adv</td><td colspan="5" style="text-align:right">PER ${n1(p.adv.per)} · WS ${n1(p.adv.ws)}${p.adv.bpm != null ? ' · BPM ' + n1(p.adv.bpm) : ''}</td></tr>` : ''}</tbody></table>
        <a class="go" href="#/player/${esc(p.pid)}">Career →</a>
      </div>
    </div>
    <button class="flipbtn" aria-label="Flip card" tabindex="-1">⟲</button>
  </div>`;
}

function statTables(s, roster) {
  const who = { k: 'name', label: 'Player', l: true, html: (r) => `<a class="who" href="#/player/${esc(r.pid)}">${esc(r.name)}</a>` };
  const G = (k) => (r) => r.pg?.[k], T = (k) => (r) => r.tot?.[k], A = (k) => (r) => r.adv?.[k];
  const withStats = roster.filter((r) => r.pg && r.pg.g);
  return [
    () => statTable([who, { k: 'cls', label: 'Cl', l: true, get: (r) => r.cls }, { k: 'g', label: 'G', get: G('g') }, { k: 'gs', label: 'GS', get: G('gs') }, { k: 'mp', label: 'MIN', get: G('mp'), fmt: n1 },
      { k: 'pts', label: 'PTS', get: G('pts'), fmt: n1, heat: 1 }, { k: 'trb', label: 'REB', get: G('trb'), fmt: n1, heat: 1 }, { k: 'ast', label: 'AST', get: G('ast'), fmt: n1, heat: 1 },
      { k: 'stl', label: 'STL', get: G('stl'), fmt: n1 }, { k: 'blk', label: 'BLK', get: G('blk'), fmt: n1 }, { k: 'tov', label: 'TO', get: G('tov'), fmt: n1 },
      { k: 'fg_pct', label: 'FG%', get: G('fg_pct'), fmt: pct }, { k: 'fg3_pct', label: '3P%', get: G('fg3_pct'), fmt: pct }, { k: 'ft_pct', label: 'FT%', get: G('ft_pct'), fmt: pct },
      { k: 'orb', label: 'OREB', get: G('orb'), fmt: n1 }, { k: 'pf', label: 'PF', get: G('pf'), fmt: n1 }], withStats, { sort: 'pts' }),
    () => statTable([who, { k: 'g', label: 'G', get: T('g') }, { k: 'mp', label: 'MIN', get: T('mp'), fmt: n0 }, { k: 'pts', label: 'PTS', get: T('pts'), fmt: n0, heat: 1 },
      { k: 'fg', label: 'FGM', get: T('fg') }, { k: 'fga', label: 'FGA', get: T('fga') }, { k: 'fg3', label: '3PM', get: T('fg3') }, { k: 'fg3a', label: '3PA', get: T('fg3a') },
      { k: 'ft', label: 'FTM', get: T('ft') }, { k: 'fta', label: 'FTA', get: T('fta') }, { k: 'orb', label: 'OREB', get: T('orb') }, { k: 'trb', label: 'REB', get: T('trb'), heat: 1 },
      { k: 'ast', label: 'AST', get: T('ast'), heat: 1 }, { k: 'stl', label: 'STL', get: T('stl') }, { k: 'blk', label: 'BLK', get: T('blk') }, { k: 'tov', label: 'TO', get: T('tov') }, { k: 'pf', label: 'PF', get: T('pf') }],
      withStats.filter((r) => r.tot), { sort: 'pts' }),
    () => {
      const cols = [who, { k: 'per', label: 'PER', get: A('per'), fmt: n1, heat: 1, title: 'Player Efficiency Rating' }, { k: 'ts_pct', label: 'TS%', get: A('ts_pct'), fmt: pct, title: 'True shooting %' },
        { k: 'efg_pct', label: 'eFG%', get: A('efg_pct'), fmt: pct }, { k: 'usg_pct', label: 'USG%', get: A('usg_pct'), fmt: n1, title: 'Usage rate' }, { k: 'ast_pct', label: 'AST%', get: A('ast_pct'), fmt: n1 },
        { k: 'trb_pct', label: 'REB%', get: A('trb_pct'), fmt: n1 }, { k: 'stl_pct', label: 'STL%', get: A('stl_pct'), fmt: n1 }, { k: 'blk_pct', label: 'BLK%', get: A('blk_pct'), fmt: n1 },
        { k: 'ortg', label: 'ORtg', get: A('off_rtg'), fmt: n1 }, { k: 'drtg', label: 'DRtg', get: A('def_rtg'), fmt: n1 }, { k: 'ws', label: 'WS', get: A('ws'), fmt: n1, heat: 1, title: 'Win shares' },
        { k: 'bpm', label: 'BPM', get: A('bpm'), fmt: n1, title: 'Box plus/minus' }];
      const rows = withStats.filter((r) => r.adv);
      return rows.length ? statTable(cols, rows, { sort: 'ws' }) : { html: '<div class="empty">Advanced stats are not available for this season.</div>', bind() {} };
    },
    () => {
      const t = s.team?.pg || {}, o = s.team?.opp || {};
      const rows = [['Points', 'pts'], ['Field goal %', 'fg_pct', pct], ['3-point %', 'fg3_pct', pct], ['3-pointers made', 'fg3'], ['Free throw %', 'ft_pct', pct], ['Free throws made', 'ft'], ['Rebounds', 'trb'], ['Offensive rebounds', 'orb'], ['Assists', 'ast'], ['Steals', 'stl'], ['Blocks', 'blk'], ['Turnovers', 'tov'], ['Fouls', 'pf']]
        .filter(([, k]) => t[k] != null).map(([label, k, f]) => ({ label, u: t[k], o: o[k], f: f || n1 }));
      if (!rows.length) return { html: '<div class="empty">Team totals are not available for this season.</div>', bind() {} };
      return statTable([{ k: 'label', label: 'Per game', l: true }, { k: 'u', label: 'UConn', html: (r) => `<b>${r.f(r.u)}</b>` }, { k: 'o', label: 'Opponents', html: (r) => r.f(r.o) },
        { k: 'd', label: 'Edge', html: (r) => { const d = r.u - r.o; if (isNaN(d)) return '–'; const v = r.f === pct ? (d * (Math.abs(r.u) <= 1 ? 100 : 1)).toFixed(1) : d.toFixed(1); return `<span style="color:${(r.label === 'Turnovers' || r.label === 'Fouls' ? -d : d) > 0 ? 'var(--ice)' : 'var(--red-soft)'}">${d > 0 ? '+' : ''}${v}</span>`; } }], rows, {});
    },
  ];
}

export function schedule(games, opts = {}) {
  let month = '';
  return games.map((g) => {
    const m = new Date(g.date.slice(0, 10) + 'T12:00:00').toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    const head = m !== month ? `<div class="month-h">${(month = m)}</div>` : '';
    const post = g.type === 'NCAA' || g.type === 'NIT';
    const ha = g.ha === 'A' ? 'at' : g.ha === 'N' ? 'vs.' : 'vs.';
    const sub = [g.round, g.arena, g.tv && !g.res ? g.tv : ''].filter(Boolean).join(' · ');
    return `${head}<a class="srow${post ? ' post' : ''}" href="#/game/${g.id}">
      <span class="d">${fmtDate(g.date)}<br><span style="font-size:11px">${new Date(g.date.slice(0, 10) + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short' })}</span></span>
      ${logo(g.opp)}
      <span class="o"><b><span class="muted" style="font-weight:600">${ha}</span> ${g.opp.rank ? `<span class="rk">${g.opp.rank}</span>` : ''}${esc(g.opp.name)}</b>${sub ? `<small>${esc(sub)}</small>` : ''}</span>
      <span class="r ${g.res || ''}">${g.res ? `${g.res} ${g.pts}–${g.opp_pts}${g.ot ? `<em>${esc(g.ot)}</em>` : ''}` : `<span class="muted" style="font-size:14px">${esc(fmtTime(g.date) || 'TBA')}</span>`}</span>
      <span class="x" aria-hidden="true">${g.box ? '›' : ''}</span>
    </a>`;
  }).join('');
}

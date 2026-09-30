import { esc, load, logo, fmtDate, n1, n0, pct, statTable, bindTips, tip, videoCard, bindVideos, photoFig, bindPhotos, ord, FINISH } from '../ui.js';
import { arc, onResize } from '../charts.js';
import { playerCard } from './season.js';

export default async function player(main, args, core) {
  const p = await load(`players/${args[0]}.json`);
  const uc = p.seasons.filter((s) => s.uconn !== false);
  const last = uc.at(-1) || {};
  const champYears = uc.filter((s) => s.finish === 'champ').map((s) => s.y);
  const c = p.career || {};
  const logs = p.gamelog || [];
  const card = { ...last, name: p.name, pid: p.id, photo: p.photo, photoWide: p.photoWide, num: p.num ?? last.num, pos: p.pos, cls: p.span, ht: p.ht, home: p.home, hs: p.hs, wt: p.wt,
    pg: { g: c.g, mp: c.mp_pg, pts: c.pts_pg, trb: c.trb_pg, ast: c.ast_pg, stl: c.stl_pg, blk: c.blk_pg, fg_pct: c.fg_pct, fg3_pct: c.fg3_pct, ft_pct: c.ft_pct } };
  const best = [...logs].filter((g) => g.pts != null).sort((a, b) => b.pts - a.pts || b.reb - a.reb).slice(0, 10);
  const tourney = logs.filter((g) => g.type === 'NCAA');

  main.innerHTML = `<div data-title="${esc(p.name)}"></div>
  <section class="p-hero">
    <div class="bgnum" aria-hidden="true">${esc(p.num ?? '')}</div>
    <div class="wrap">
      <div>${playerCard(card, champYears.length > 0)}</div>
      <div class="p-info">
        <span class="eyebrow ${champYears.length ? 'gold' : ''}">${esc(p.span)} · ${esc(p.pos || '')}${champYears.length ? ` · ${champYears.length > 1 ? champYears.length + '× ' : ''}national champion` : ''}</span>
        <h1 class="h-display" style="font-size:clamp(46px,7.5vw,112px)">${esc(p.name)}</h1>
        <div class="p-bio">${[['HT', p.ht], ['WT', p.wt ? p.wt + ' lb' : ''], ['Home', p.home], ['HS', p.hs], ['Born', p.born]].filter(([, v]) => v).map(([k, v]) => `<span><b>${k}</b>${esc(v)}</span>`).join('')}</div>
        ${p.honors?.length ? `<div class="honor-list">${p.honors.map((h) => `<span class="pill ${/champion|all-america|\bAA\b|POY|MOP|player of the year|most outstanding/i.test(h) ? 'ff' : ''}">${esc(h)}</span>`).join('')}</div>` : ''}
        ${p.draft ? `<p style="font:600 16px/1.4 var(--f-cond);letter-spacing:.04em;text-transform:uppercase"><span class="muted">NBA draft · </span>${esc(p.draft)}</p>` : ''}
        <div class="statline">
          <div><b>${n0(c.pts)}</b><span>Points${p.ranks?.pts ? ` · ${ord(p.ranks.pts)} since '87` : ''}</span></div>
          <div><b>${n0(c.trb)}</b><span>Rebounds${p.ranks?.trb && p.ranks.trb <= 25 ? ` · ${ord(p.ranks.trb)}` : ''}</span></div>
          <div><b>${n0(c.ast)}</b><span>Assists${p.ranks?.ast && p.ranks.ast <= 25 ? ` · ${ord(p.ranks.ast)}` : ''}</span></div>
          <div><b>${c.g ?? '–'}</b><span>Games</span></div>
          ${c.blk ? `<div><b>${n0(c.blk)}</b><span>Blocks${p.ranks?.blk && p.ranks.blk <= 25 ? ` · ${ord(p.ranks.blk)}` : ''}</span></div>` : ''}
        </div>
        ${p.bio ? `<p class="lede" style="font-size:16px">${esc(p.bio)}</p>` : ''}
        <div class="chips">${uc.map((s) => `<a class="chip" href="#/season/${s.y}">${esc(s.label)}${s.finish === 'champ' ? ' ★' : ''}</a>`).join('')}${p.nba_url ? `<a class="chip" href="${esc(p.nba_url)}" target="_blank" rel="noopener">NBA stats ↗</a>` : ''}</div>
      </div>
    </div>
  </section>

  ${uc.length > 1 ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Per game, season by season</span><h2 class="h2">The career arc</h2></div></div>
    <div class="panel chart-card" id="arc"></div>
  </div></section>` : ''}

  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">College career${p.seasons.some((s) => s.uconn === false) ? ' · other schools dimmed' : ''}</span><h2 class="h2">Season by season</h2></div></div>
    <div id="seasTbl"></div>
  </div></section>

  ${best.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">From ${logs.length} box scores on file</span><h2 class="h2">Biggest games</h2></div></div>
    <div class="feature-row">${best.slice(0, 6).map((g) => `
      <a class="panel otd" href="#/game/${g.id}"><span class="eyebrow ${g.type === 'NCAA' ? 'gold' : ''}">${fmtDate(g.date, { year: true })}${g.round ? ' · ' + esc(g.round) : ''}</span>
        <div class="game-line">${logo(g.opp)}<b style="font:700 17px/1.1 var(--f-cond);text-transform:uppercase">${g.ha === 'A' ? 'at' : 'vs.'} ${esc(g.opp.name)}</b><span class="pill ${g.res === 'W' ? 'ice' : 'red'}" style="margin-left:auto">${g.res} ${esc(g.score)}</span></div>
        <span class="score">${g.pts} <span style="font-size:16px" class="muted">PTS</span> ${g.reb} <span style="font-size:16px" class="muted">REB</span> ${g.ast} <span style="font-size:16px" class="muted">AST</span></span>
        <span class="note">${g.fgm}-${g.fga} FG · ${g.tpm}-${g.tpa} 3PT · ${g.ftm}-${g.fta} FT${g.min ? ` · ${g.min} min` : ''}</span></a>`).join('')}</div>
  </div></section>` : ''}

  ${tourney.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow gold">NCAA Tournament · ${tourney.filter((g) => g.res === 'W').length}–${tourney.filter((g) => g.res === 'L').length}</span><h2 class="h2">In March</h2></div>
      <span class="aside">${n1(tourney.reduce((a, g) => a + (g.pts || 0), 0) / tourney.length)} points per game across ${tourney.length} tournament games.</span></div>
    <div id="tourTbl"></div>
  </div></section>` : ''}

  ${logs.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${logs.length} games</span><h2 class="h2">Game log</h2></div>
      <div class="chips" id="logYears">${[...new Set(logs.map((g) => g.y))].map((yy, i, a) => `<button class="chip${i === a.length - 1 ? ' on' : ''}" data-y="${yy}">${yy - 1}–${String(yy).slice(2)}</button>`).join('')}</div></div>
    <div id="logTbl"></div>
  </div></section>` : ''}

  ${p.videos?.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${p.videos.length} videos</span><h2 class="h2">Watch ${esc(p.name.split(' ').at(-1))}</h2></div></div>
    <div class="vids" id="vids">${p.videos.map(videoCard).join('')}</div>
  </div></section>` : ''}
  ${p.photos?.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Photos</span><h2 class="h2">Gallery</h2></div></div>
    <div class="photos" id="photos">${p.photos.map(photoFig).join('')}</div>
  </div></section>` : ''}`;

  const offs = [];
  main.querySelector('.pcard')?.addEventListener('click', (e) => { if (!e.target.closest('a')) e.currentTarget.classList.toggle('flip'); });

  const arcEl = main.querySelector('#arc');
  if (arcEl) {
    const rows = uc.map((s) => ({ tag: `'${String(s.y).slice(2)}`, pts: s.pts, trb: s.trb, ast: s.ast, champ: s.finish === 'champ' }));
    const d = () => arc(arcEl, rows, [{ k: 'pts', label: 'POINTS' }, { k: 'trb', label: 'REBOUNDS' }, { k: 'ast', label: 'ASSISTS' }]);
    d(); offs.push(onResize(arcEl, d));
  }

  const st = statTable([
    { k: 'label', label: 'Season', l: true, html: (r) => (r.uconn === false ? `<span class="dim">${esc(r.label)}</span>` : `<a href="#/season/${r.y}">${esc(r.label)}</a>${r.finish === 'champ' ? ' <span style="color:var(--gold)">★</span>' : ''}`) },
    { k: 'school', label: 'School', l: true, html: (r) => `<span class="${r.uconn === false ? 'dim' : ''}">${esc(r.school || 'UConn')}</span>` },
    { k: 'cls', label: 'Cl', l: true }, { k: 'g', label: 'G' }, { k: 'gs', label: 'GS' }, { k: 'mp', label: 'MIN', fmt: n1 },
    { k: 'pts', label: 'PTS', fmt: n1, heat: 1 }, { k: 'trb', label: 'REB', fmt: n1, heat: 1 }, { k: 'ast', label: 'AST', fmt: n1, heat: 1 },
    { k: 'stl', label: 'STL', fmt: n1 }, { k: 'blk', label: 'BLK', fmt: n1 }, { k: 'fg_pct', label: 'FG%', fmt: pct }, { k: 'fg3_pct', label: '3P%', fmt: pct }, { k: 'ft_pct', label: 'FT%', fmt: pct },
    { k: 'per', label: 'PER', fmt: n1, get: (r) => r.adv?.per }, { k: 'ws', label: 'WS', fmt: n1, get: (r) => r.adv?.ws },
  ], p.seasons, { total: { label: 'UConn career', school: '', g: c.g, gs: c.gs, mp: c.mp_pg, pts: c.pts_pg, trb: c.trb_pg, ast: c.ast_pg, stl: c.stl_pg, blk: c.blk_pg, fg_pct: c.fg_pct, fg3_pct: c.fg3_pct, ft_pct: c.ft_pct, adv: { ws: c.ws } } });
  const stEl = main.querySelector('#seasTbl'); stEl.innerHTML = st.html; st.bind(stEl);

  const logCols = [
    { k: 'date', label: 'Date', l: true, html: (r) => `<a href="#/game/${r.id}">${fmtDate(r.date)}</a>` },
    { k: 'opp', label: 'Opponent', l: true, get: (r) => r.opp.name, html: (r) => `<span class="who">${logo(r.opp)}${r.ha === 'A' ? '@ ' : ''}${esc(r.opp.name)}</span>` },
    { k: 'res', label: 'Result', l: true, html: (r) => `<span style="color:${r.res === 'W' ? 'var(--ice)' : 'var(--red-soft)'}">${r.res} ${esc(r.score)}</span>` },
    { k: 'min', label: 'MIN' }, { k: 'pts', label: 'PTS', heat: 1 }, { k: 'fgm', label: 'FG', html: (r) => `${r.fgm ?? 0}-${r.fga ?? 0}` }, { k: 'tpm', label: '3PT', html: (r) => `${r.tpm ?? 0}-${r.tpa ?? 0}` },
    { k: 'ftm', label: 'FT', html: (r) => `${r.ftm ?? 0}-${r.fta ?? 0}` }, { k: 'reb', label: 'REB', heat: 1 }, { k: 'ast', label: 'AST', heat: 1 }, { k: 'stl', label: 'STL' }, { k: 'blk', label: 'BLK' }, { k: 'to', label: 'TO' },
  ];
  const tEl = main.querySelector('#tourTbl');
  if (tEl) { const t = statTable([{ k: 'round', label: 'Round', l: true, html: (r) => `<a href="#/game/${r.id}">${esc(r.round || fmtDate(r.date))}</a>` }, ...logCols.slice(1)], tourney, {}); tEl.innerHTML = t.html; t.bind(tEl); }
  const lEl = main.querySelector('#logTbl');
  if (lEl) {
    const show = (yy) => { const t = statTable(logCols, logs.filter((g) => g.y === yy), {}); lEl.innerHTML = t.html; t.bind(lEl); };
    show(logs.at(-1).y);
    main.querySelector('#logYears').addEventListener('click', (e) => { const b = e.target.closest('[data-y]'); if (!b) return; main.querySelectorAll('#logYears .chip').forEach((x) => x.classList.toggle('on', x === b)); show(+b.dataset.y); });
  }
  if (p.videos?.length) bindVideos(main.querySelector('#vids'), p.videos);
  if (p.photos?.length) bindPhotos(main.querySelector('#photos'), p.photos);
  return { destroy() { offs.forEach((f) => f()); tip(null); } };
}

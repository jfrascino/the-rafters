import { esc, FINISH, finishPill, tryLoad, seasonLabel } from '../ui.js';
import { sparkPath } from '../charts.js';

export default async function seasons(main, args, core) {
  const eras = core.eras || [{ name: 'All seasons', from: 0, to: 9999 }];
  const byEra = eras.map((e) => ({ e, list: core.seasons.filter((s) => s.y >= e.from && s.y <= e.to).reverse() })).reverse();
  main.innerHTML = `<div data-title="Seasons"></div>
  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${core.seasons.length} seasons since ${core.seasons[0].y - 1}</span><h1 class="h1">Every team</h1></div>
      <div class="chips" id="fchips">${[['all', 'All'], ['champ', 'Champions'], ['final4', 'Final Fours'], ['ncaa', 'NCAA teams'], ['big', '30-win seasons']].map(([k, l], i) => `<button class="chip${i ? '' : ' on'}" data-f="${k}">${l}</button>`).join('')}</div></div>
    <div id="eras">${byEra.map(({ e, list }) => `
      <div class="era-block">
        <div class="era-title"><h2 class="h2">${esc(e.name)}</h2><span class="muted">${e.from - 1}–${e.to === 9999 ? 'now' : e.to} · ${e.w}–${e.l}${e.titles?.length ? ` · ${e.titles.length} title${e.titles.length > 1 ? 's' : ''}` : ''}</span></div>
        ${e.recordNote ? `<p class="note stat-note" style="margin:-6px 0 16px">${e.w}–${e.l} is his official record; the team went ${e.courtW}–${e.courtL} on the court. ${esc(e.recordNote)}</p>` : ''}
        <div class="covers">${list.map(cover).join('')}</div>
      </div>`).join('')}</div>
  </div></section>`;
  const test = {
    all: () => true, champ: (s) => s.finish === 'champ',
    final4: (s) => ['champ', 'runner', 'final4'].includes(s.finish),
    ncaa: (s) => (FINISH[s.finish]?.rank || 0) >= 2, big: (s) => s.w >= 30,
  };
  main.querySelector('#fchips').addEventListener('click', (e) => {
    const b = e.target.closest('[data-f]'); if (!b) return;
    main.querySelectorAll('#fchips .chip').forEach((c) => c.classList.toggle('on', c === b));
    const f = test[b.dataset.f];
    main.querySelectorAll('.cover').forEach((c) => { c.hidden = !f(core.seasons.find((s) => s.y === +c.dataset.y)); });
    main.querySelectorAll('.era-block').forEach((blk) => { blk.hidden = !blk.querySelector('.cover:not([hidden])'); });
  });
  // the early years (1900-01 to 1976-77), from the record book
  const H = await tryLoad('history.json');
  if (H?.seasons?.length && main.isConnected) {
    main.insertAdjacentHTML('beforeend', earlyYears(H));
    if (args[0] === 'early') setTimeout(() => main.querySelector('#early')?.scrollIntoView({ block: 'start' }), 60);   // after the router's scroll-to-top
  }
}

function earlyYears(H) {
  const S = H.seasons, w = S.reduce((a, s) => a + (s.w || 0), 0), l = S.reduce((a, s) => a + (s.l || 0), 0);
  const eras = (H.coaches || []).filter((c) => !/interim/i.test(c.name)).map((c) => ({ ...c, list: S.filter((s) => s.y >= (c.from || 0) && s.y <= Math.min(c.to || 9999, 1977)) }))
    .filter((e) => e.list.length).reverse();
  const tile = (s) => {
    const nc = s.titles.some((t) => /NCAA/.test(t)), nit = s.titles.some((t) => /NIT|Invitation/.test(t));
    const crowns = s.titles.filter((t) => /Champion/i.test(t) && !/NCAA|NIT/.test(t)).map((t) => t.replace(/Conference/, 'Conf.').replace(/Co-Champions?/i, 'co-champs').replace(/Champions?/i, 'champs'));
    return `<a class="cover early${nc ? ' ncaa' : ''}" href="#/season/${s.y}"><span class="yr">${s.y - 1}<small>–${String(s.y).slice(2)}</small></span>
      <div style="display:grid;gap:6px;align-content:start"><span class="rec">${s.none ? '<span class="muted" style="font-size:15px">No team</span>' : `${s.w}–${s.l}`}</span></div>
      <div class="meta">${nc ? '<span class="pill ice">NCAA</span>' : ''}${nit ? '<span class="pill">NIT</span>' : ''}${crowns.map((c) => `<span class="pill ff">${esc(c)}</span>`).join('')}</div></a>`;
  };
  return `<section class="section" id="early"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow gold">From UConn's record book · ${S.length} seasons</span><h2 class="h1">The early years</h2></div>
      <span class="aside">1900–01 to 1976–77: ${w}–${l}. Every season's record and results as UConn's record book prints them; where the book disagrees with itself, the season page says so.</span></div>
    ${eras.map((e) => `<div class="era-block"><div class="era-title"><h3 class="h2">${esc(e.name === 'No Coach' ? 'Before the first coach' : e.name)}</h3><span class="muted">${esc(e.name === 'No Coach' ? '1900–1915' : e.years)} · ${e.w}–${e.l}</span></div>
      <div class="covers">${e.list.slice().reverse().map(tile).join('')}</div></div>`).join('')}
  </div></section>`;
}

function cover(s) {
  const champ = s.finish === 'champ';
  return `<a class="cover${champ ? ' champ' : ''}" href="#/season/${s.y}" data-y="${s.y}">
    <span class="yr">${s.y - 1}<small>–${String(s.y).slice(2)}</small></span>
    <div style="display:grid;gap:6px;align-content:start"><span class="rec">${s.future ? 'Upcoming' : `${s.w}–${s.l}`}${s.cw != null ? ` <span class="muted" style="font-size:14px">(${s.cw}–${s.cl} ${esc(s.confShort || '')})</span>` : ''}</span>
    ${s.headline ? `<span class="muted" style="font-size:13px;line-height:1.3">${esc(s.headline)}</span>` : ''}</div>
    <div class="meta">${s.future ? '<span class="pill live">Coming soon</span>' : finishPill(s.finish)}${s.seed ? `<span class="pill">No. ${s.seed} seed</span>` : ''}${s.apFinal ? `<span class="pill">AP ${s.apFinal}</span>` : ''}${s.officialRec ? `<span class="pill red" title="Official NCAA record ${esc(s.officialRec)}">Vacated</span>` : ''}</div>
    <svg class="spark" viewBox="0 0 200 34" preserveAspectRatio="none" aria-hidden="true">${sparkPath(s.spark)}</svg>
  </a>`;
}

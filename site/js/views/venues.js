// Home floors: every building UConn has called home, with the record book's numbers and the site's own game-by-game count.
import { esc, load, logo, fmtDate, seasonLabel, bindTips, tip } from '../ui.js';

const yr = (d) => (d ? String(d).slice(0, 4) : '');
const span = (n) => `${yr(n.from)}–${n.to ? yr(n.to) : ''}`;

export default async function venues(main, args) {
  const V = await load('venues.json');
  const B = V.buildings || [];
  main.innerHTML = `<div data-title="Home floors"></div>
  <section class="march-hero"><div class="wrap grid" style="gap:16px">
    <a class="eyebrow" href="#/legends">← Legends</a>
    <span class="eyebrow gold">Every building UConn has called home</span>
    <h1 class="h-display">Home floors</h1>
    <p class="lede">From the Field House to Gampel to Hartford: UConn's official record in each building from the record book, plus every game since 1986–87 counted in the building it was actually played in.</p>
    <div class="chips">${B.map((b) => `<button class="chip" data-go="${esc(b.key)}">${esc(b.short)}</button>`).join('')}</div>
  </div></section>
  ${B.map(building).join('')}
  ${V.homeStreaks?.length ? `<section class="section"><div class="wrap"><div class="panel ven-streaks"><span class="eyebrow">Longest home winning streaks, any building (record book)</span>
    <div>${V.homeStreaks.map((s) => `<span><b>${s.games}</b> games · ${esc(s.when)}</span>`).join('')}</div></div></div></section>` : ''}
  <section class="section"><div class="wrap"><p class="note">${esc(V.source || '')} for the official lines; the game-by-game counts use UConn's record-book site codes for every game since 1986–87. Building histories are researched and sourced in the site's data.</p></div></section>`;
  main.querySelector('.chips').addEventListener('click', (e) => {
    const b = e.target.closest('[data-go]'); if (b) main.querySelector('#v-' + b.dataset.go)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  if (args[0]) setTimeout(() => main.querySelector('#v-' + args[0])?.scrollIntoView({ block: 'start' }), 50);
  bindTips(main);
  return { destroy() { tip(null); } };
}

function building(b) {
  const o = b.official, s = b.since;
  const main = o?.lines?.[0];
  const pct = main ? Math.round((1000 * main.w) / (main.w + main.l)) / 10 : null;
  return `<section class="section ven" id="v-${esc(b.key)}"><div class="wrap">
    <div class="ven-head">
      <div class="ven-id">
        <span class="eyebrow">${esc(b.city || '')}${b.demolished ? ` · demolished ${esc(yr(b.demolished))}` : ''}</span>
        <h2 class="h1">${esc(b.short)}</h2>
        <div class="ven-names">${(b.names || []).map((n) => `<span><b>${esc(n.name)}</b>${esc(span(n))}</span>`).join('<i>→</i>')}</div>
        ${b.blurb ? `<p class="lede" style="font-size:17px">${esc(b.blurb)}</p>` : ''}
        ${b.moments?.length ? `<div class="chips">${b.moments.map((m) => `<a class="pill ff" href="#/moment/${esc(m.slug)}">Moment: ${esc(m.title)} →</a>`).join('')}</div>` : ''}
      </div>
      ${main ? `<div class="panel ven-rec">
        <span class="eyebrow gold">UConn's record here</span>
        <b class="ven-wl">${main.w}–${main.l}</b>
        <span class="ven-bar"><i style="width:${pct}%"></i></span>
        <span class="note">${pct}% · ${main.misprint ? `${main.w + main.l} games` : `${main.games} games`}${main.what ? ` (${esc(main.what)})` : ''}</span>
        ${o.lines.slice(1).map((l) => `<span class="note">${l.w}–${l.l} in ${l.games} games${l.what ? ` (${esc(l.what)})` : ''}</span>`).join('')}
        ${main.misprint ? `<span class="note ven-flag">The record book prints ${main.games} games here, but ${main.w} + ${main.l} = ${main.w + main.l}${o.lines[1] ? `, which also squares with its overall line (${o.lines[1].games} games, ${o.lines[1].w}–${o.lines[1].l})` : ''}.</span>` : ''}
        ${(o.streaks || []).map((st) => streakLine(st, s)).join('')}
        <span class="note">Source: UConn record book</span>
      </div>` : ''}
    </div>
    ${s ? `<div class="ven-since">
      <div class="sec-head" style="margin:28px 0 12px"><div><span class="eyebrow">Game by game since ${esc(seasonLabel(s.from))}</span><h3 class="h2" style="font-size:30px">${s.w}–${s.l} in ${s.g} games</h3></div>
        ${s.home[0] + s.home[1] !== s.g ? `<span class="aside">${s.home[0]}–${s.home[1]} as the home team; the rest were neutral-site games (conference or NCAA tournament).</span>` : ''}</div>
      ${s.seasons.length > 2 ? `<div class="ven-strip" aria-label="Record here by season">${s.seasons.map((x) => `<span data-tip="${esc(`<b>${seasonLabel(x.y)}</b>${x.w}–${x.l} here`)}"><i class="w" style="height:${x.w * 7}px"></i><i class="l" style="height:${x.l * 7}px"></i><small>${String(x.y).slice(2)}</small></span>`).join('')}</div>` : ''}
      <div class="ven-games">
        ${gameCard(b.full ? 'First game here' : 'Earliest game in our records', s.first)}${gameCard(b.current ? 'Most recent' : 'Last game here', s.last)}
        ${s.streak ? `<div class="panel ven-g"><span class="eyebrow">Longest winning streak here</span><b>${s.streak.n} straight</b><small>${esc(fmtDate(s.streak.from.date, { year: true }))} to ${esc(fmtDate(s.streak.to.date, { year: true }))}</small></div>` : ''}
        ${s.bigWins.slice(0, 2).map((g, i) => gameCard(i ? 'Next-biggest win' : 'Biggest win', g)).join('')}
      </div>
    </div>` : ''}
  </div></section>`;
}

function streakLine(st, s) {
  // the record book's season label vs the game-by-game run, when we can see the whole run
  const ours = s?.streak && s.streak.n === st.games ? s.streak : null;
  const span = ours ? `${seasonLabel(+ours.from.date.slice(0, 4) + (+ours.from.date.slice(5, 7) >= 8 ? 1 : 0))} to ${seasonLabel(+ours.to.date.slice(0, 4) + (+ours.to.date.slice(5, 7) >= 8 ? 1 : 0))}` : null;
  const differs = span && span.replace(/–/g, '-') !== st.when.replace(' through ', ' to ');
  return `<span class="note"><b style="color:var(--fg)">${st.games} straight wins</b>, ${esc(st.when)}${differs ? ` <span class="ven-flag">(game by game, the run went from ${esc(fmtDate(ours.from.date, { year: true }))} to ${esc(fmtDate(ours.to.date, { year: true }))})</span>` : ''}</span>`;
}

function gameCard(label, g) {
  if (!g) return '';
  return `<a class="panel ven-g" href="#/game/${esc(g.gid)}"><span class="eyebrow">${esc(label)}</span>
    <span class="ven-gl">${logo({ logo: g.logo, name: g.opp })}<b class="${g.res === 'W' ? 'w' : 'l'}">${g.res} ${g.pts}–${g.opp_pts}${g.ot ? ` (${esc(g.ot)})` : ''}</b></span>
    <small>vs. ${esc(g.opp)} · ${esc(fmtDate(g.date, { year: true }))}${g.name ? ` · ${esc(g.name)}` : ''}</small></a>`;
}

// The early years (1900-01 to 1976-77): one season from UConn's record book, its game list exactly as printed.
import { esc, load, fmtDate, seasonLabel } from '../ui.js';

const wl = (r) => (r ? `${r[0]}–${r[1]}` : '');

export default async function historySeason(main, y, core) {
  const H = await load('history.json');
  const list = H.seasons;
  const i = list.findIndex((s) => s.y === y);
  const s = list[i];
  if (!s) throw new Error(`No ${seasonLabel(y)} season in the record book`);
  const prev = list[i - 1], next = list[i + 1] || (core.seasons[0] ? { y: core.seasons[0].y } : null);
  const n = s.games.length;
  const ncaa = s.titles.find((t) => /NCAA/.test(t)), nit = s.titles.find((t) => /NIT|National Invitation/.test(t));
  const confTitles = s.titles.filter((t) => /Champion/i.test(t) && !/NCAA|NIT/.test(t));
  main.innerHTML = `<div data-title="${esc(seasonLabel(y))}"></div>
  <section class="s-hero">
    <div class="bgyear" aria-hidden="true">${String(y - 1).slice(2)}–${String(y).slice(2)}</div>
    <div class="wrap">
      <div class="s-hero-top"><span class="eyebrow"><a href="#/seasons/early">The early years</a> · ${esc(seasonLabel(y))}${s.coach && s.coach !== 'No Coach' ? ` · ${esc(s.coachLine || s.coach)}` : ' · no head coach'}</span>
        <nav class="s-nav" aria-label="Season navigation">${prev ? `<a href="#/season/${prev.y}">← ${esc(seasonLabel(prev.y))}</a>` : ''}${next ? `<a href="#/season/${next.y}">${esc(seasonLabel(next.y))} →</a>` : ''}</nav></div>
      <h1 class="h-display" style="font-size:clamp(40px,7vw,104px)">${esc(seasonLabel(y))}</h1>
      <div class="chips">${ncaa ? `<span class="pill ice">${esc(ncaa)}</span>` : ''}${nit ? `<span class="pill">${esc(nit)}</span>` : ''}${confTitles.map((t) => `<span class="pill ff">${esc(t)}</span>`).join('')}</div>
      ${s.none ? '<p class="lede">No team: UConn did not play a schedule this season.</p>' : `<div class="statline">
        <div><b>${s.w}–${s.l}</b><span>Overall</span></div>
        ${s.home ? `<div><b>${wl(s.home)}</b><span>Home</span></div>` : ''}${s.away ? `<div><b>${wl(s.away)}</b><span>Away</span></div>` : ''}${s.neutral ? `<div><b>${wl(s.neutral)}</b><span>Neutral</span></div>` : ''}
        ${s.pts != null && n ? `<div><b>${(s.pts / (s.w + s.l)).toFixed(1)}</b><span>Points/G</span></div><div><b>${(s.opp / (s.w + s.l)).toFixed(1)}</b><span>Allowed/G</span></div>` : ''}
      </div>`}
    </div>
  </section>
  ${n ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${n} games${s.pts != null ? ` · ${s.pts.toLocaleString()} points scored, ${s.opp.toLocaleString()} allowed` : ''}</span><h2 class="h2">The schedule</h2></div>
      <span class="aside">${s.games.some((g) => g.site) ? `${s.games.some((g) => g.date) ? '' : 'The record book lists these games in order, without dates. '}"at" = away, "vs." = neutral site.` : 'The record book lists these games in order, without dates or sites.'}</span></div>
    <div class="panel hist-games${s.games.some((g) => g.date) ? '' : ' nodate'}">${s.games.map((g) => `<div class="hist-g ${g.res === 'W' ? 'w' : 'l'}">
      <span class="d">${g.date ? esc(fmtDate(g.date)) : ''}</span>
      <span class="o">${g.site === 'A' ? '<i>at</i> ' : g.site === 'N' ? '<i>vs.</i> ' : g.site === 'H' && !s.games.some((x) => x.site === 'A' || x.site === 'N') ? '<i>home ·</i> ' : ''}${esc(g.opp)}${g.event ? `<small>${esc(g.event)}</small>` : ''}</span>
      <b>${g.res} ${g.pts}–${g.opp_pts}${g.ot ? ` <small>${esc(g.ot)}</small>` : ''}</b></div>`).join('')}</div>
    ${s.notes.length || s.coachNote ? `<div class="grid" style="gap:6px;margin-top:14px">${[...s.notes, ...(s.coachNote ? [s.coachNote] : [])].map((t) => `<p class="note"><span class="pill ff" style="margin-right:8px">Record book</span>${esc(t)}</p>`).join('')}</div>` : ''}
  </div></section>` : ''}
  <section class="section"><div class="wrap"><p class="note">Source: ${esc(H.source)}. Rosters and player stats for the early years are a work in progress.</p></div></section>`;
}

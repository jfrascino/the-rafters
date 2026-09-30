import { esc, load, logo, fmtDate, headshot } from '../ui.js';

const norm = (s) => String(s || '').toLowerCase().normalize('NFKD').replace(/[^\w ]/g, '').replace(/\b(jr|sr|ii|iii)\b/g, '').replace(/\s+/g, ' ').trim();

export default async function legends(main, _args, core) {
  const L = await load('legends.json');
  const byName = new Map(core.players.map((p) => [norm(p.name), p]));
  const who = (name) => { const p = byName.get(norm(name)); return p ? `<a href="#/player/${esc(p.id)}" style="text-decoration:underline;text-decoration-color:var(--line-2);text-underline-offset:3px">${esc(name)}</a>` : esc(name); };
  const oppByName = new Map(Object.values(core.opponents || {}).map((o) => [norm(o.name), o]));
  const T = L.program_totals || {};
  const hoh = L.huskies_of_honor?.members || [];
  const aa = L.all_americans?.list || [];
  const poy = L.players_of_the_year?.list || [];
  const draft = L.nba_draft?.first_round_since_1987 || [];

  main.innerHTML = `<div data-title="Legends"></div>
  <section class="march-hero"><div class="wrap grid" style="gap:18px">
    <span class="eyebrow gold">The program, all time</span>
    <h1 class="h-display">Legends</h1>
    <div class="round-table">${[['National titles', T.national_titles], ['Final Fours', T.final_fours], ['NCAA trips', T.ncaa_appearances], ['Big East tourney titles', T.big_east_tournament_titles], ['Big East reg. season', T.big_east_regular_season_titles], ['NIT titles', T.nit_titles]]
      .filter(([, v]) => v != null).map(([l, v]) => `<div class="panel"><b>${esc(v)}</b><span>${l}</span></div>`).join('')}</div>
    ${T.most_consecutive_wins_sweet16_or_later ? `<p class="lede">Consecutive NCAA Tournament wins from the Sweet 16 on: <b style="color:var(--gold)">${esc(T.most_consecutive_wins_sweet16_or_later)}</b>.</p>` : ''}
  </div></section>

  ${(L.retired_numbers || []).length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Never worn again</span><h2 class="h2">Retired numbers</h2></div></div>
    <div class="jerseys">${L.retired_numbers.map((r) => `<div class="jersey"><svg viewBox="0 0 200 220" aria-hidden="true"><path d="M60 10 L80 4 Q100 22 120 4 L140 10 L190 40 L172 86 L150 76 L150 214 L50 214 L50 76 L28 86 L10 40 Z" fill="var(--navy)" stroke="var(--fg)" stroke-width="3"/><path d="M80 4 Q100 22 120 4" fill="none" stroke="var(--red)" stroke-width="6"/><text x="100" y="72" text-anchor="middle" font-family="Graduate, serif" font-size="20" fill="var(--fg)">UCONN</text><text x="100" y="170" text-anchor="middle" font-family="'Big Shoulders Display', Impact, sans-serif" font-weight="900" font-size="96" fill="var(--fg)" stroke="var(--red)" stroke-width="2">${esc(r.number)}</text></svg>
      <b>${who(r.player)}</b><span class="note">${esc(r.tenure || '')}${r.ceremony ? ` · retired ${fmtDate(r.ceremony, { year: true })}` : ''}</span></div>`).join('')}</div>
  </div></section>` : ''}

  ${hoh.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">The wall at Gampel</span><h2 class="h2">Huskies of Honor</h2></div><span class="aside">${hoh.length} members</span></div>
    ${L.huskies_of_honor.notes ? `<p class="lede" style="font-size:16px;margin-bottom:18px">${esc([].concat(L.huskies_of_honor.notes).join(' '))}</p>` : ''}
    <div class="hoh">${hoh.map((m) => `<div class="hoh-it"><span class="hn">${esc(m.number ?? '')}</span><span><b>${who(m.name)}</b><small>${esc([m.role, m.seasons].filter(Boolean).join(' · '))}</small></span></div>`).join('')}</div>
  </div></section>` : ''}

  ${(L.coaches || []).length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">On the sideline</span><h2 class="h2">The coaches</h2></div></div>
    <div class="grid" style="gap:18px">${L.coaches.map((c) => `<div class="panel otd" style="grid-template-columns:minmax(0,1fr);gap:14px">
      <div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">${c.image ? `<img src="${esc(c.image.thumb_url || c.image.url || c.image)}" alt="" style="width:96px;height:96px;border-radius:50%;object-fit:cover;object-position:50% 20%" loading="lazy">` : ''}
        <div style="display:grid;gap:6px"><span class="eyebrow">${esc(c.tenure || '')} · ${esc(c.uconn_record || '')}</span><h3 class="h2" style="font-size:36px">${esc(c.name)}</h3>
        <div class="chips">${(c.national_titles || []).map((y) => `<a class="pill champ" href="#/season/${y}">★ ${y}</a>`).join('')}${(c.honors || []).slice(0, 4).map((h) => `<span class="pill">${esc(typeof h === 'string' ? h : h.text || h.award || '')}</span>`).join('')}</div></div></div>
      <div class="recap" style="font-size:16px">${(Array.isArray(c.bio) ? c.bio : String(c.bio || '').split(/\n\s*\n/)).map((p) => `<p>${esc(p)}</p>`).join('')}</div></div>`).join('')}</div>
  </div></section>` : ''}

  <section class="section"><div class="wrap num-grid">
    ${aa.length ? `<div><div class="sec-head"><div><span class="eyebrow">By year</span><h3 class="h2" style="font-size:32px">All-Americans</h3></div></div>
      <div class="panel lead-list">${aa.slice().reverse().map((a) => `<div class="lead-row" style="grid-template-columns:52px minmax(0,1fr) auto"><b>${a.year}</b><span><b>${who(a.player)}</b></span><small class="muted" style="text-align:right">${esc(a.team || '')}</small></div>`).join('')}</div></div>` : ''}
    ${poy.length ? `<div><div class="sec-head"><div><span class="eyebrow">Hardware</span><h3 class="h2" style="font-size:32px">Players of the year</h3></div></div>
      <div class="panel lead-list">${poy.slice().reverse().map((a) => `<div class="lead-row" style="grid-template-columns:52px minmax(0,1fr)"><b>${a.year}</b><span><b>${who(a.player)}</b><small>${esc(a.award || '')}</small></span></div>`).join('')}</div></div>` : ''}
  </div></section>

  ${draft.length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">First-round picks since 1987 · ${draft.length}</span><h2 class="h2">Draft night</h2></div></div>
    <div class="tbl-wrap"><table class="stats"><thead><tr><th class="l">Year</th><th class="l">Player</th><th>Pick</th><th class="l">Team</th></tr></thead><tbody>
      ${draft.slice().sort((a, b) => b.year - a.year || a.pick - b.pick).map((d) => `<tr><td class="l">${d.year}</td><td class="l">${(() => { const p = byName.get(norm(d.player)); return p ? `<a class="who" href="#/player/${esc(p.id)}">${headshot(p)}${esc(d.player)}</a>` : esc(d.player); })()}</td><td>${d.pick}${d.lottery ? ' <span class="pill ff" style="margin-left:6px">Lottery</span>' : ''}</td><td class="l">${esc(d.team || '')}</td></tr>`).join('')}</tbody></table></div>
  </div></section>` : ''}

  ${(L.rivalries || []).length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Bad blood</span><h2 class="h2">Rivalries</h2></div></div>
    <div class="feature-row">${L.rivalries.map((r) => { const o = oppByName.get(norm(r.opponent)); return `<div class="panel otd">
      <div class="game-line">${o ? logo(o, 'lg') : ''}<div style="display:grid;gap:4px"><h3 class="h3">${o ? `<a href="#/numbers/opp/${esc(o.key)}">${esc(r.opponent)}</a>` : esc(r.opponent)}</h3>${o ? `<span class="score">${o.w}–${o.l}</span>` : ''}</div></div>
      <p class="muted" style="font-size:15px">${esc(r.summary || '')}</p>
      ${(r.notable_games || []).length ? `<ul style="margin:0;padding-left:18px;display:grid;gap:4px;font-size:14px;color:var(--fg-2)">${r.notable_games.slice(0, 5).map((g) => `<li>${g.gid ? `<a href="#/game/${esc(g.gid)}" style="text-decoration:underline;text-underline-offset:3px">` : ''}${fmtDate(g.date, { year: true })}: ${esc(g.result)} ${esc(g.score)}${g.gid ? '</a>' : ''}${g.event ? ` <span class="muted">· ${esc(g.event)}</span>` : ''}</li>`).join('')}</ul>` : ''}</div>`; }).join('')}</div>
  </div></section>` : ''}

  ${(L.nicknames_and_quotes || []).length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Said and named</span><h2 class="h2">Words that stuck</h2></div></div>
    <div class="feature-row">${L.nicknames_and_quotes.map((q) => `<figure class="panel otd" style="margin:0"><blockquote style="margin:0;font:800 clamp(22px,2.4vw,30px)/1.1 var(--f-display);text-transform:uppercase">“${esc(q.text)}”</blockquote>
      <figcaption class="note">${q.who ? `<b style="color:var(--fg-2)">${who(q.who)}</b>` : ''}${q.when ? ` · ${fmtDate(q.when, { year: true })}` : ''}${q.context ? `<br>${esc(q.context)}` : ''}</figcaption></figure>`).join('')}</div>
  </div></section>` : ''}

  ${(L.arenas || []).length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">Home floors</span><h2 class="h2">The buildings</h2></div></div>
    <div class="feature-row">${L.arenas.map((a) => `<div class="panel otd"><span class="eyebrow">${esc(a.years || '')}${a.capacity ? ` · capacity ${esc(a.capacity)}` : ''}</span><h3 class="h3">${esc(a.name)}</h3><span class="note">${esc(a.location || '')}</span>${a.notes ? `<p class="muted" style="font-size:15px">${esc(a.notes)}</p>` : ''}</div>`).join('')}</div>
  </div></section>` : ''}

  ${(L.ncaa_records?.list || []).length ? `<section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">In the NCAA record book</span><h2 class="h2">Records</h2></div></div>
    <div class="honors"><ul>${L.ncaa_records.list.map((r) => `<li>${esc(r)}</li>`).join('')}</ul></div>
  </div></section>` : ''}

  <section class="section"><div class="wrap"><p class="note">Researched from Wikipedia and UConn Athletics sources; every entry in the underlying data carries its source link.</p></div></section>`;
}

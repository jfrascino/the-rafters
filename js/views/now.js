import { esc, logo, UCONN, fmtDate, fmtTime, fmtDay, ord } from '../ui.js';
import season from './season.js';

// The current team: a live scoreboard strip, then the full season page for the current year.
export default async function now(main, _args, core) {
  const cur = core.current || {};
  const y = cur.season || core.seasons.at(-1).y;
  const top = document.createElement('section');
  top.className = 'section';
  top.style.paddingBottom = '0';
  const g = cur.next;
  top.innerHTML = g ? `<div class="wrap"><a class="board" href="#/game/${g.id}" style="display:grid;grid-template-columns:auto 1fr auto;gap:18px;align-items:center">
      <span class="board-label" style="color:var(--led)">Next</span>
      <span style="display:flex;align-items:center;gap:14px;min-width:0">${logo(g.opp, 'lg')}<span style="display:grid;gap:6px;min-width:0"><b style="font:800 clamp(18px,2.4vw,28px)/1 var(--f-cond);text-transform:uppercase;letter-spacing:.04em">${g.ha === 'A' ? 'at' : 'vs.'} ${g.opp.rank ? `<span class="led">${g.opp.rank}</span> ` : ''}${esc(g.opp.name)}</b>
        <span class="board-label">${esc(fmtDay(g.day || g.date))} ${esc(fmtDate(g.day || g.date, { year: true }))} · ${esc(fmtTime(g.date))}${g.tv ? ' · ' + esc(g.tv) : ''}${g.venue ? ' · ' + esc(g.venue) : ''}</span></span></span>
      <span class="led" id="nowCd" style="font-size:clamp(22px,3.4vw,40px)"></span></a></div>` : '';
  const hubEl = document.createElement('section');
  hubEl.className = 'section hub';
  hubEl.innerHTML = hubHtml(core);
  const sub = document.createElement('div');
  main.append(top, hubEl, sub);
  let t = 0;
  const cd = top.querySelector('#nowCd');
  if (cd) {
    const target = new Date(g.date).getTime();
    const tick = () => { const s = Math.max(0, (target - Date.now()) / 1000); const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60); cd.textContent = d ? `${d}D ${String(h).padStart(2, '0')}H` : `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`; };
    tick(); t = setInterval(tick, 1000);
  }
  const inner = await season(sub, [String(y)], core);
  return { destroy() { clearInterval(t); inner?.destroy?.(); } };
}

// The live season hub: where UConn stands right now. Off-season numbers are labeled with the season they belong to.
function hubHtml(core) {
  const h = core.hub || {};
  const prevLbl = `${h.season - 2}–${String(h.season - 1).slice(2)}`;
  const tag = (o, lbl) => (o?.final ? `<span class="hub-final">${esc(lbl || prevLbl)} final</span>` : '');
  const cur = core.current || {};
  const sum = core.seasons.find((s) => s.y === h.season) || {};
  const ap = h.polls?.ap, co = h.polls?.coaches, net = h.net, br = h.bracket;
  const rankTxt = (p) => (p?.rank ? `No. ${p.rank}` : p?.votes ? 'RV' : 'NR');
  const tiles = [
    `<div class="hub-tile"><span class="eyebrow">Record</span><b>${cur.record || '0–0'}</b><span>${sum.cw != null && (sum.cw + sum.cl) ? `${sum.cw}–${sum.cl} Big East` : 'Big East play starts later'}</span></div>`,
    ap ? `<div class="hub-tile"><span class="eyebrow">AP poll</span><b>${rankTxt(ap)}</b><span>${ap.votes && !ap.rank ? `${ap.votes} points · ` : ''}${esc(fmtDate(ap.date))}</span>${tag(ap, ap.label)}</div>` : '',
    co ? `<div class="hub-tile"><span class="eyebrow">Coaches poll</span><b>${rankTxt(co)}</b><span>${esc(fmtDate(co.date))}</span>${tag(co, co.label)}</div>` : '',
    net ? `<div class="hub-tile"><span class="eyebrow">NCAA NET</span><b>No. ${net.rank}</b><span>Quad 1: ${esc(net.quads?.[0] || '–')}</span>${tag(net)}</div>` : '',
    br ? `<div class="hub-tile"><span class="eyebrow">Projected seed</span><b>${br.seed ? `No. ${br.seed}` : '—'}</b><span>${br.avg ? `avg. ${br.avg.toFixed(2)} in ${br.brackets} brackets` : 'not projected yet'}</span>${tag(br)}</div>` : '',
  ].join('');
  const pv = h.preview;
  const preview = pv ? `<div class="panel hub-card">
      <span class="eyebrow">Next opponent</span>
      <div class="hub-opp">${logo(pv.opp, 'lg')}<div><h3 class="h3">${esc(pv.opp.name)}</h3><span class="note">${pv.record ? [pv.record, pv.standing].filter(Boolean).map(esc).join(' · ') : 'Their season hasn’t started'}</span></div></div>
      <ul class="hub-list">
        ${pv.series.allW != null ? `<li><span>All-time series</span><b>UConn ${pv.series.allW}–${pv.series.allL}</b></li>` : `<li><span>Series since ${core.seasons[0].y - 1}–${String(core.seasons[0].y).slice(2)}</span><b>${pv.series.w + pv.series.l ? `UConn ${pv.series.w}–${pv.series.l}` : 'First meeting'}</b></li>`}
        ${pv.last ? `<li><span>Last meeting</span><b><a href="#/game/${esc(pv.last.id)}">${esc(pv.last.res)} ${pv.last.pts}–${pv.last.opp_pts}${pv.last.ot ? ' ' + esc(pv.last.ot) : ''}</a> · ${esc(fmtDate(pv.last.date, { year: true }))}</b></li>` : ''}
        ${(pv.leaders || []).map((l) => `<li><span>${esc(l.stat)}</span><b>${esc(l.name)} · ${esc(l.value)}</b></li>`).join('')}
      </ul></div>` : '';
  const rc = h.recap;
  const recap = rc ? `<div class="panel hub-card">
      <span class="eyebrow">Last game</span>
      <a class="hub-opp" href="#/game/${esc(rc.id)}">${logo(rc.opp, 'lg')}<div><h3 class="h3">${rc.res === 'W' ? 'Beat' : 'Lost to'} ${esc(rc.opp.name)}, ${rc.pts}–${rc.opp_pts}${rc.ot ? ' (' + esc(rc.ot) + ')' : ''}</h3><span class="note">${esc(fmtDate(rc.date, { year: true }))}${rc.record ? ` · UConn ${esc(rc.record)}` : ''}</span></div></a>
      <ul class="hub-list">${rc.tops.map((t) => `<li><span>${t.pid ? `<a href="#/player/${esc(t.pid)}">${esc(t.name)}</a>` : esc(t.name)}</span><b>${esc(t.line)}${t.seasonHigh ? ' <span class="pill ice">season high</span>' : ''}</b></li>`).join('')}</ul></div>` : '';
  const ms = (h.milestones || []).slice().sort((a, b) => a.left - b.left);
  const miles = ms.length ? `<div class="panel hub-card"><span class="eyebrow">Milestone watch</span><ul class="hub-list">${ms.map((m) => `<li><span>${m.pid ? `<a href="#/player/${esc(m.pid)}">${esc(m.who)}</a>` : esc(m.who)}</span><b>${esc(m.text)}</b></li>`).join('')}</ul></div>` : '';
  const st = h.standings;
  const table = st ? `<div class="panel hub-card"><span class="eyebrow">Big East standings ${tag(st, st.label)}</span>
      <table class="hub-table"><thead><tr><th></th><th class="l">Team</th><th>Conf</th><th>Overall</th><th>Streak</th></tr></thead><tbody>
      ${st.rows.map((r) => `<tr class="${r.id === '41' ? 'me' : ''}"><td>${esc(r.seed || '')}</td><td class="l"><span class="tm">${logo(r, 'sm')} ${esc(r.name)}</span></td><td>${esc(r.conf || '')}</td><td>${esc(r.overall || '')}</td><td>${esc(r.streak || '')}</td></tr>`).join('')}
      </tbody></table></div>` : '';
  const top10 = ap?.top?.length ? `<div class="panel hub-card"><span class="eyebrow">AP top 10 ${tag(ap, ap.label)}</span>
      <table class="hub-table"><tbody>${ap.top.map((r) => `<tr class="${r.id === '41' ? 'me' : ''}"><td>${r.rank}</td><td class="l"><span class="tm">${logo(r, 'sm')} ${esc(r.name)}</span></td><td>${esc(r.record || '')}</td></tr>`).join('')}</tbody></table></div>` : '';
  return `<div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${esc(h.label || '')} · updated after every game</span><h2 class="h2">Where UConn stands</h2></div></div>
    <div class="hub-tiles">${tiles}</div>
    <div class="hub-grid">${preview}${recap}${miles}${table}${top10}</div>
  </div>`;
}

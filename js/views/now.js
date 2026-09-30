import { esc, logo, UCONN, fmtDate, fmtTime, fmtDay } from '../ui.js';
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
  const sub = document.createElement('div');
  main.append(top, sub);
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

import { esc } from '../ui.js';
import { playerCard } from './season.js';

export default async function players(main, _args, core) {
  const eras = core.eras || [];
  const all = core.players;
  main.innerHTML = `<div data-title="Huskies"></div>
  <section class="section"><div class="wrap">
    <div class="sec-head"><div><span class="eyebrow">${all.length} players since ${core.seasons[0].y - 1}</span><h1 class="h1">Every Husky</h1></div></div>
    <div class="filters">
      <input type="search" id="pq" placeholder="Find a player" autocomplete="off" aria-label="Find a player">
      <select id="pera" aria-label="Era"><option value="">All eras</option>${eras.map((e, i) => `<option value="${i}">${esc(e.name)}</option>`).join('')}</select>
      <select id="ppos" aria-label="Position"><option value="">All positions</option><option value="G">Guards</option><option value="F">Forwards</option><option value="C">Centers</option></select>
      <select id="psort" aria-label="Sort"><option value="pts">Career points</option><option value="ppg">Points per game</option><option value="trb">Rebounds</option><option value="ast">Assists</option><option value="blk">Blocks</option><option value="g">Games</option><option value="first">First season</option><option value="name">Name</option></select>
    </div>
    <div class="chips" id="pchips" style="margin-bottom:22px">${[['', 'Everyone'], ['champ', 'National champions'], ['k', '1,000-point club'], ['nba', 'NBA draft picks'], ['aa', 'All-Americans'], ['now', 'Current roster']].map(([k, l], i) => `<button class="chip${i ? '' : ' on'}" data-c="${k}">${l}</button>`).join('')}</div>
    <p class="note" id="pcount" style="margin-bottom:14px"></p>
    <div class="cards" id="pcards"></div>
    <div style="display:flex;justify-content:center;margin-top:24px"><button class="btn" id="pmore" hidden>Show more</button></div>
  </div></section>`;

  const $ = (s) => main.querySelector(s);
  let chip = '', shown = 48;
  const curY = core.current?.season;
  const test = {
    '': () => true, champ: (p) => p.champ, k: (p) => p.pts >= 1000, nba: (p) => !!p.draft, aa: (p) => (p.honors || []).some((h) => /all-america/i.test(h)), now: (p) => p.years.includes(curY),
  };
  const render = () => {
    const q = $('#pq').value.trim().toLowerCase();
    const era = eras[$('#pera').value];
    const pos = $('#ppos').value;
    const sort = $('#psort').value;
    let list = all.filter((p) => test[chip](p) && (!q || p.name.toLowerCase().includes(q)) && (!era || p.years.some((y) => y >= era.from && y <= era.to)) && (!pos || (p.pos || '').includes(pos)));
    const key = { pts: (p) => p.pts || 0, ppg: (p) => (p.g >= 20 ? p.ppg : 0) || 0, trb: (p) => p.trb || 0, ast: (p) => p.ast || 0, blk: (p) => p.blk || 0, g: (p) => p.g || 0, first: (p) => -p.years[0] };
    list.sort(sort === 'name' ? (a, b) => a.last.localeCompare(b.last) : (a, b) => key[sort](b) - key[sort](a));
    $('#pcount').textContent = `${list.length} player${list.length === 1 ? '' : 's'}`;
    $('#pcards').innerHTML = list.slice(0, shown).map((p) => playerCard({ ...p, pid: p.id, cls: p.span, pg: { g: p.g, mp: p.mpg, pts: p.ppg, trb: p.rpg, ast: p.apg, fg_pct: p.fg_pct, fg3_pct: p.fg3_pct, ft_pct: p.ft_pct, stl: p.spg, blk: p.bpg } }, p.champ)).join('') || '<div class="empty">No players match.</div>';
    $('#pmore').hidden = list.length <= shown;
  };
  ['#pq', '#pera', '#ppos', '#psort'].forEach((s) => $(s).addEventListener('input', () => { shown = 48; render(); }));
  $('#pchips').addEventListener('click', (e) => { const b = e.target.closest('[data-c]'); if (!b) return; chip = b.dataset.c; main.querySelectorAll('#pchips .chip').forEach((c) => c.classList.toggle('on', c === b)); shown = 48; render(); });
  $('#pmore').addEventListener('click', () => { shown += 48; render(); });
  $('#pcards').addEventListener('click', (e) => { if (e.target.closest('a')) return; const c = e.target.closest('.pcard'); if (c) c.classList.toggle('flip'); });
  render();
}

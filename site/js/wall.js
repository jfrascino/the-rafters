// The "Every Husky" wall: slowly drifting columns of Jason's restored player photos behind the home headline.
// One Husky at a time steps into full color with his name; hover lights any tile; click opens the player.
import { esc } from './ui.js';

export function mountWall(host, players, avoidEl) {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // day-seeded shuffle: the wall changes daily but holds still within a visit
  let seed = Math.floor(Date.now() / 864e5) % 233280;
  const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
  const pool = players.map((p) => ({ p, r: rnd() })).sort((a, b) => a.r - b.r).map((x) => x.p);
  const ver = (p) => ((p.photo || '').match(/\?v=\w+/) || [''])[0];
  const tile = (p) => `<a class="wall-tile" href="#/player/${esc(p.id)}" tabindex="-1" aria-hidden="true"><img src="assets/wall/${esc(p.id)}.jpg${ver(p)}" alt="" decoding="async"><span class="wall-nm"><b>${esc(p.name)}</b>${esc(p.span)}</span></a>`;

  let lastW = 0;
  const build = () => {
    const w = host.clientWidth;
    if (!w || Math.abs(w - lastW) < 40) return;
    lastW = w;
    const tileW = w < 700 ? 96 : w < 1200 ? 124 : 144, gap = w < 700 ? 6 : 8;
    const cols = Math.ceil(w / (tileW + gap)) + 1;
    const perCol = Math.max(8, Math.ceil(pool.length / cols)); // each half of a column must outrun the visible height
    let k = 0, html = '';
    for (let c = 0; c < cols; c++) {
      const items = Array.from({ length: perCol }, () => pool[k++ % pool.length]).map(tile).join('');
      const dur = Math.round(perCol * 11 + (c % 3) * 9); // seconds per full loop: a slow drift
      html += `<div class="wall-col${c % 2 ? ' down' : ''}" style="--dur:${dur}s;margin-top:${-((c * 53) % 120)}px">${items}${items}</div>`;
    }
    host.style.setProperty('--tile-w', `${tileW}px`);
    host.style.setProperty('--gap', `${gap}px`);
    host.innerHTML = html;
  };
  build();

  // Spotlight one visible tile at a time, never behind the headline
  let visible = true, timer = 0, lit = null;
  const spotlight = () => {
    if (!visible || document.hidden) return;
    lit?.classList.remove('lit');
    const hr = host.parentElement.getBoundingClientRect(), ar = avoidEl?.getBoundingClientRect();
    const cand = [...host.querySelectorAll('.wall-tile')].filter((t) => {
      const r = t.getBoundingClientRect();
      if (r.top < hr.top + 20 || r.bottom > hr.bottom - 20 || r.left < hr.left + 10 || r.right > hr.right - 10) return false;
      return !ar || r.right < ar.left - 24 || r.left > ar.right + 24 || r.bottom < ar.top - 24 || r.top > ar.bottom + 24;
    });
    lit = cand[Math.floor(Math.random() * cand.length)] || null;
    lit?.classList.add('lit');
  };
  if (!reduce) { timer = setInterval(spotlight, 2600); setTimeout(spotlight, 900); }

  const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; host.classList.toggle('paused', !visible); }, { threshold: 0 });
  io.observe(host.parentElement);
  let rt = 0;
  const ro = new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(build, 200); });
  ro.observe(host);
  return () => { clearInterval(timer); io.disconnect(); ro.disconnect(); };
}

// Moments: UConn's greatest nights told in full. #/moments (index) and #/moment/<slug> (one long-form page).
// Every paragraph carries numbered sources; scores, clocks, box lines and charts come from the site's own game data.
import { esc, load, tryLoad, logo, UCONN, fmtDate, headshot, openVideo, openMp4, openPhoto, bindTips, tip } from '../ui.js';
import { winProb, flow, onResize } from '../charts.js';

const FILTERS = ['All', 'Championships', 'Buzzer-beaters', 'Marathons', 'Comebacks', 'Conference titles', 'Milestones', 'Heartbreak'];
const longDate = (d) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
const scoreLine = (m) => (m.res ? `${m.res === 'W' ? 'UConn' : esc(m.opp?.name || '')} ${m.res === 'W' ? m.pts : m.opp_pts}, ${m.res === 'W' ? esc(m.opp?.name || '') : 'UConn'} ${m.res === 'W' ? m.opp_pts : m.pts}${m.ot ? ` (${esc(m.ot)})` : ''}` : '');
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

export default async function moments(main, args, core) {
  return location.hash.startsWith('#/moment/') ? page(main, args[0], core) : index(main, core);
}

// ───────────────────────── Index ─────────────────────────
async function index(main, core) {
  const { moments: all } = await load('moments.json');
  const y0 = 1978, y1 = Math.max(core.seasons.at(-1).y, ...all.map((m) => +m.date.slice(0, 4)));
  const pos = (m) => {
    const d = new Date(m.date + 'T12:00:00');
    return ((d.getFullYear() + d.getMonth() / 12 - y0) / (y1 - y0 + 1)) * 100;
  };
  main.innerHTML = `<div data-title="Moments"></div>
  <section class="mo-ihero"><div class="wrap">
    <span class="eyebrow red">Storrs Lore · Moments</span>
    <h1 class="h-display">The nights<br><span class="thin">that made</span> UConn</h1>
    <p class="lede">${all.length === 1 ? 'One moment' : `${all.length} moments`}, told in full: the stakes, the final seconds beat by beat, the video, the voices and what came next. Every fact is sourced.</p>
  </div>
  <div class="wrap"><div class="mo-time" id="moTime" aria-label="Timeline of moments">
    <div class="mo-time-axis">${[1980, 1990, 2000, 2010, 2020].map((y) => `<span style="left:${((y - y0) / (y1 - y0 + 1)) * 100}%">${y}</span>`).join('')}</div>
    ${all.map((m) => `<a class="mo-dot${m.tags.includes('Championships') ? ' gold' : ''}" href="#/moment/${esc(m.slug)}" style="left:${pos(m).toFixed(2)}%" data-tip="${esc(`<b>${esc(m.title)}</b>${esc(fmtDate(m.date, { year: true }))}${m.res ? ' · ' + scoreLine(m) : ''}`)}" aria-label="${esc(m.title)}"></a>`).join('')}
  </div></div></section>
  <section class="section" style="padding-top:28px"><div class="wrap">
    <div class="chips" id="moFilter" style="margin-bottom:22px">${FILTERS.filter((f) => f === 'All' || all.some((m) => m.tags.includes(f))).map((f, i) => `<button class="chip${i ? '' : ' on'}" data-f="${esc(f)}">${esc(f)}</button>`).join('')}</div>
    <div class="mo-grid" id="moGrid"></div>
  </div></section>`;
  const grid = main.querySelector('#moGrid');
  const render = (f) => {
    grid.innerHTML = all.filter((m) => f === 'All' || m.tags.includes(f)).map(card).join('') || '<div class="empty">None yet.</div>';
  };
  render('All');
  main.querySelector('#moFilter').addEventListener('click', (e) => {
    const b = e.target.closest('[data-f]'); if (!b) return;
    main.querySelectorAll('#moFilter .chip').forEach((c) => c.classList.toggle('on', c === b));
    render(b.dataset.f);
  });
  bindTips(main.querySelector('#moTime'));
  return { destroy() { tip(null); } };
}

export function card(m, opts = {}) {
  const wide = !opts.noWide && m.tags.includes('Championships');
  return `<a class="mo-card${wide ? ' wide' : ''}" href="#/moment/${esc(m.slug)}">
    <div class="mo-card-img">${m.hero ? `<img src="${esc(m.hero.url)}" alt="" loading="lazy">` : ''}</div>
    <div class="mo-card-body">
      <span class="mo-card-date">${esc(fmtDate(m.date, { year: true }))}${m.venue ? ` · ${esc(m.venue)}` : ''}</span>
      ${m.nickname ? `<span class="mo-card-nick">“${esc(m.nickname)}”</span>` : ''}
      <h3>${esc(m.title)}</h3>
      ${m.dek ? `<p>${esc(m.dek)}</p>` : ''}
      ${m.res ? `<span class="mo-card-score">${logo(m.opp)}<b class="${m.res === 'W' ? 'w' : 'l'}">${m.res}</b> ${esc(scoreLine(m))}</span>` : ''}
    </div></a>`;
}

// ───────────────────────── One moment ─────────────────────────
async function page(main, slug, core) {
  const [m, list] = await Promise.all([load(`moments/${slug}.json`), tryLoad('moments.json')]);
  const all = list?.moments || [];
  const k = all.findIndex((x) => x.slug === slug);
  const prev = all[k - 1], next = all[k + 1];
  const g = m.game;
  const U = { ...UCONN }, O = g ? { ...g.opp } : null;
  const S = new Map(m.sources.map((s) => [s.n, s]));
  const cast = m.cast || [];

  // link the first mention of each Husky in a block to his page
  const linker = () => {
    const done = new Set();
    return (html) => cast.reduce((h, c) => {
      if (done.has(c.pid)) return h;
      const re = new RegExp(`\\b${c.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`);
      if (!re.test(h)) return h;
      done.add(c.pid);
      return h.replace(re, `<a class="mo-name" href="#/player/${esc(c.pid)}">${esc(c.name)}</a>`);
    }, html);
  };
  const sn = (src) => (src?.length ? `<span class="mo-sns">${src.map((n) => `<button class="mo-sn" data-src="${n}" aria-label="Source ${n}" data-tip="${esc(esc(S.get(n)?.what || S.get(n)?.label || ''))}">${n}</button>`).join('')}</span>` : '');
  const prose = (items, cls = '') => { const L = linker(); return items.map((p) => `<p class="${cls}">${L(esc(p.text))}${sn(p.src)}</p>`).join(''); };

  const ch = [
    m.setup.length && ['setup', 'The setup'],
    (m.story.length || m.chart) && ['game', 'The game'],
    m.sequence.length && ['finish', 'The finish'],
    (m.numbers.length || m.pbp) && ['numbers', 'By the numbers'],
    m.videos.length && ['watch', 'Watch'],
    m.quotes.length && ['voices', 'Voices'],
    (m.aftermath.length || m.next?.length || m.legacy.length) && ['after', 'What came next'],
    (m.leaders?.u?.length) && ['box', 'The box'],
    ['sources', 'Sources'],
  ].filter(Boolean);

  const f = m.facts || {};
  const per = (p) => ({ '1H': '1st half', '2H': '2nd half', OT: 'OT', OT1: 'OT', OT2: '2OT', OT3: '3OT', OT4: '4OT', OT5: '5OT', OT6: '6OT' }[String(p || '').toUpperCase()] || String(p || ''));
  const heroVid = m.hero?.kind === 'video' ? m.videos.find((v) => v.id === m.hero.video) : null;

  main.innerHTML = `<div data-title="${esc(m.title)}"></div>
  <div class="mo-progress" aria-hidden="true"><i id="moProg"></i></div>
  <header class="mo-hero${m.hero ? '' : ' plain'}">
    ${m.hero ? `<div class="mo-hero-bg"><img src="${esc(m.hero.url)}" alt="" class="${reduced() ? '' : 'kb'}"${m.hero.pos ? ` style="object-position:${esc(m.hero.pos)}"` : ''}></div>` : ''}
    <div class="wrap mo-hero-in">
      <a class="eyebrow mo-back" href="#/moments">← All moments</a>
      <span class="mo-kicker">${esc(longDate(m.date))}${f.venue ? ` · ${esc(f.venue)}` : ''}${f.event ? ` · ${esc(f.event)}` : ''}</span>
      ${m.nickname ? `<span class="mo-nick">“${esc(m.nickname)}”</span>` : ''}
      <h1 class="mo-title">${esc(m.title)}</h1>
      ${m.dek ? `<p class="mo-dek">${esc(m.dek)}</p>` : ''}
      ${g ? `<div class="mo-final">
        <span class="mo-ft">${logo(U, 'lg')}<b class="led ${g.res === 'W' ? 'white' : ''}" data-count="${g.pts}">${g.pts}</b></span>
        <span class="mo-fmid"><span class="board-label">Final${g.ot ? ' / ' + esc(g.ot) : ''}</span>${g.forfeit ? '<span class="board-label" style="color:var(--gold)">Forfeit win</span>' : ''}</span>
        <span class="mo-ft"><b class="led ${g.res === 'L' ? 'white' : 'dim'}" data-count="${g.opp_pts}">${g.opp_pts}</b>${logo(O, 'lg')}</span>
      </div>` : ''}
      ${heroVid ? `<button class="btn solid mo-heroplay" data-vid="${esc(heroVid.id)}">▶ Watch it</button>` : ''}
    </div>
    ${m.hero?.credit ? `<span class="mo-credit">${esc(m.hero.credit)}</span>` : ''}
  </header>

  <div class="mo-body">
    <nav class="mo-rail" aria-label="Chapters">${ch.map(([id, t]) => `<button data-go="${id}">${esc(t)}</button>`).join('')}</nav>
    <div class="mo-main">
      <section class="mo-facts"><div class="mo-facts-in">
        <div><span>Date</span><b>${esc(longDate(m.date))}</b></div>
        ${f.tip ? `<div><span>Tip-off</span><b>${esc(f.tip)}</b></div>` : ''}
        ${f.venue ? `<div><span>Venue</span><b>${esc(f.venue)}${f.city ? `<small>${esc(f.city)}</small>` : ''}</b></div>` : ''}
        ${f.att ? `<div><span>Attendance</span><b>${(+f.att).toLocaleString()}${sn(f.attSrc)}</b></div>` : ''}
        ${f.event ? `<div><span>Stage</span><b>${esc(f.event)}</b></div>` : ''}
        ${f.tv ? `<div><span>On the air</span><b>${esc(f.tv)}${f.announcers?.length ? `<small>${esc(f.announcers.join(', '))}</small>` : ''}</b></div>` : ''}
        ${m.entering?.u ? `<div><span>Coming in</span><b>${enterLine('UConn', m.entering.u)}${O ? `<small>${enterLine(O.name, m.entering.o)}</small>` : ''}${sn(m.entering.src)}</b></div>` : ''}
      </div></section>

      ${m.setup.length ? `<section class="mo-ch reveal" id="ch-setup"><h2 class="mo-h"><span>01</span>The setup</h2>
        <div class="mo-prose dropcap">${prose(m.setup)}</div>
        ${cast.length ? `<div class="mo-cast">${cast.slice(0, 6).map((c) => `<a href="#/player/${esc(c.pid)}" class="mo-castp"><span class="ph">${headshot({ ...c, y: m.y }, '')}</span><span><b>${esc(c.name)}</b><small>${[c.num ? '#' + c.num : '', c.pos, c.cls].filter(Boolean).map(esc).join(' · ')}</small></span></a>`).join('')}</div>` : ''}
      </section>` : ''}

      ${m.story.length || m.chart ? `<section class="mo-ch reveal" id="ch-game"><h2 class="mo-h"><span>02</span>The game</h2>
        ${m.story.length ? `<div class="mo-prose">${prose(m.story)}</div>` : ''}
        ${m.chart ? `<figure class="panel chart-card mo-chart"><figcaption><span class="eyebrow">${m.chart.wp ? 'UConn win probability' : 'Score margin'}, every play</span>${m.chart.marks.length ? '<span class="note">Gold dots: the finish, below</span>' : ''}</figcaption><div id="moChart"></div></figure>` : ''}
      </section>` : ''}

      ${m.sequence.length ? `<section class="mo-ch mo-finish" id="ch-finish"><h2 class="mo-h"><span>03</span>The finish</h2>
        <div class="mo-fin">
          <div class="mo-stick"><div class="board mo-sb">
            <div class="mo-sb-row"><span class="mo-sb-t">${logo(U)}<b>UConn</b></span><b class="led white" id="sbU">${m.sequence[0].u ?? ''}</b></div>
            <div class="mo-sb-mid"><span class="led red" id="sbClock">${esc(m.sequence[0].clock || '')}</span><span class="board-label" id="sbPer">${esc(per(m.sequence[0].period))}</span></div>
            <div class="mo-sb-row"><span class="mo-sb-t">${logo(O)}<b>${esc(O?.name || '')}</b></span><b class="led" id="sbO">${m.sequence[0].o ?? ''}</b></div>
          </div></div>
          <ol class="mo-beats">${m.sequence.map((b, i) => `<li class="mo-beat" data-i="${i}">
            <span class="mo-beat-clk">${esc(b.clock || '')}<small>${esc(per(b.period))}</small></span>
            <div><p>${linker()(esc(b.text))}${sn(b.src)}</p>
              <span class="mo-beat-sc">${b.u != null ? `UConn ${b.u}, ${esc(O?.abbr || O?.name || '')} ${b.o}` : ''}</span>
              ${b.clip ? `<button class="mo-clip" data-clip="${i}"><img src="${esc(b.clip.thumb || '')}" alt="" loading="lazy"><span>▶ Watch this play</span></button>` : ''}</div>
          </li>`).join('')}</ol>
        </div>
        ${m.shot ? `<figure class="panel mo-court"><figcaption><span class="eyebrow gold">The shot</span><b>${esc(m.shot.text)}</b><span class="note">${esc(m.shot.clock)} · ${esc(m.shot.period)}${m.shot.ft ? ` · ${m.shot.ft} feet from the rim, per ESPN's shot chart` : ''}</span></figcaption><div id="moCourt"></div></figure>` : ''}
      </section>` : ''}

      ${m.numbers.length || m.pbp ? `<section class="mo-ch reveal" id="ch-numbers"><h2 class="mo-h"><span>04</span>By the numbers</h2>
        ${m.numbers.length ? `<div class="mo-nums">${m.numbers.map((n) => `<div class="mo-num"><b>${esc(n.value)}</b><span>${esc(n.label)}${sn(n.src)}</span></div>`).join('')}</div>` : ''}
        ${m.pbp ? `<div class="mo-nums small">
          <div class="mo-num"><b>${m.pbp.leadChanges}</b><span>lead changes</span></div>
          <div class="mo-num"><b>${m.pbp.ties}</b><span>ties</span></div>
          <div class="mo-num"><b>+${m.pbp.bigU}</b><span>UConn's biggest lead</span></div>
          <div class="mo-num"><b>+${m.pbp.bigO}</b><span>${esc(O?.name || 'Opponent')}'s biggest lead</span></div>
          ${m.pbp.runU && m.pbp.runU.pts >= 6 ? `<div class="mo-num"><b>${m.pbp.runU.pts}–0</b><span>UConn's best run (${esc(m.pbp.runU.from)} to ${esc(m.pbp.runU.to)})</span></div>` : ''}
        </div><p class="note" style="margin-top:10px">Counted from ESPN's play-by-play.</p>` : ''}
      </section>` : ''}

      ${m.videos.length ? `<section class="mo-ch reveal" id="ch-watch"><h2 class="mo-h"><span>05</span>Watch</h2>
        <div class="mo-vids">${m.videos.map((v, i) => `<button class="mo-vid${i ? '' : ' big'}" data-vid="${esc(v.id)}">
          <span class="th"><img src="${esc(v.thumb || `https://i.ytimg.com/vi/${v.id}/${i ? 'hqdefault' : 'maxresdefault'}.jpg`)}" alt="" loading="lazy" ${i || v.thumb ? '' : `onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/${esc(v.id)}/hqdefault.jpg'"`}><i>▶</i></span>
          <span class="mo-vid-t"><span class="pill">${esc(KIND[v.kind] || 'Video')}${v.start ? ` · starts at ${hms(v.start)}` : ''}</span><b>${esc(v.title)}</b><small>${esc(v.channel || '')}</small></span></button>`).join('')}</div>
      </section>` : ''}

      ${m.quotes.length ? `<section class="mo-ch reveal" id="ch-voices"><h2 class="mo-h"><span>06</span>Voices</h2>
        <div class="mo-quotes">${m.quotes.map((q) => `<blockquote class="mo-q"><p>“${esc(q.text)}”</p><footer><b>${esc(q.who || '')}</b>${q.role ? `, ${esc(q.role)}` : ''}${q.when ? ` · ${esc(q.when)}` : ''}${sn(q.src)}</footer></blockquote>`).join('')}</div>
      </section>` : ''}

      ${m.papers?.length ? `<section class="mo-ch reveal" id="ch-papers"><h2 class="mo-h"><span>—</span>The morning after</h2>
        <div class="mo-papers">${m.papers.map((p, i) => `<figure class="mo-paper">${p.url ? `<button data-paper="${i}"><img src="${esc(p.url)}" alt="${esc(p.headline || '')}" loading="lazy"></button>` : ''}<figcaption><b>${esc(p.paper || '')}</b>${p.date ? ` · ${esc(fmtDate(p.date, { year: true }))}` : ''}${p.headline ? `<span>“${esc(p.headline)}”</span>` : ''}${p.page ? `<a href="${esc(p.page)}" target="_blank" rel="noopener">Read the page ↗</a>` : ''}</figcaption></figure>`).join('')}</div>
      </section>` : ''}

      ${m.aftermath.length || m.next?.length || m.legacy.length ? `<section class="mo-ch reveal" id="ch-after"><h2 class="mo-h"><span>07</span>What came next</h2>
        ${m.aftermath.length ? `<div class="mo-prose">${prose(m.aftermath)}</div>` : ''}
        ${m.next?.length ? `<div class="mo-next-games">${m.next.map((x) => `<a href="#/game/${esc(x.gid)}" class="mo-ng ${x.res === 'W' ? 'w' : 'l'}"><span class="note">${esc(fmtDate(x.date))} · ${esc((x.round || '').replace(/^NCAA /, ''))}</span>${logo({ logo: x.logo, name: x.opp })}<b>${x.res} ${x.pts}–${x.opp_pts}${x.ot ? ` (${esc(x.ot)})` : ''}</b><small>vs. ${esc(x.opp)}</small></a>`).join('')}</div>` : ''}
        ${m.legacy.length ? `<div class="mo-prose mo-legacy">${prose(m.legacy)}</div>` : ''}
      </section>` : ''}

      ${m.leaders?.u?.length ? `<section class="mo-ch reveal" id="ch-box"><h2 class="mo-h"><span>08</span>The box</h2>
        <div class="mo-leaders">${[...m.leaders.u.map((p) => ({ ...p, u: true })), ...m.leaders.o].map((p) => `<a class="mo-ld${p.u ? '' : ' opp'}" ${p.u && p.pid ? `href="#/player/${esc(p.pid)}"` : ''}>
          <span class="ph">${p.u ? headshot({ ...p, y: m.y }, '') : (p.photo ? `<img src="${esc(p.photo)}" alt="" loading="lazy">` : logo(O))}</span>
          <span><span class="eyebrow ${p.u ? '' : 'red'}">${p.u ? 'UConn' : esc(m.leaders.oName || '')}</span><b>${esc(p.name)}</b><span class="mo-ld-l">${esc(p.line)}</span><small>${esc(p.shoot || '')}${p.min ? ` · ${p.min} min` : ''}</small></span></a>`).join('')}</div>
        ${m.gid ? `<a class="btn" href="#/game/${esc(m.gid)}" style="margin-top:18px">Full box score${m.chart ? ' & play-by-play' : ''} →</a>` : ''}
        ${m.boxNote ? `<p class="note">${esc(m.boxNote)}</p>` : ''}
      </section>` : ''}

      <section class="mo-ch" id="ch-sources"><h2 class="mo-h"><span>✓</span>Sources</h2>
        <p class="note" style="margin-bottom:12px">Every fact on this page was checked against these. Numbers in the text point here.</p>
        <ol class="mo-srcs">${m.sources.map((s) => `<li id="mo-src-${s.n}"><span>${s.n}</span><div>${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)} ↗</a>` : `<b>${esc(s.label)}</b>`}${s.what ? `<small>${esc(s.what)}</small>` : ''}</div></li>`).join('')}</ol>
      </section>
    </div>
  </div>

  <nav class="wrap mo-pn">${prev ? `<a href="#/moment/${esc(prev.slug)}" class="prev"><span class="eyebrow">← Earlier</span><b>${esc(prev.title)}</b><small>${esc(fmtDate(prev.date, { year: true }))}</small></a>` : '<span></span>'}${next ? `<a href="#/moment/${esc(next.slug)}" class="next"><span class="eyebrow">Later →</span><b>${esc(next.title)}</b><small>${esc(fmtDate(next.date, { year: true }))}</small></a>` : '<span></span>'}</nav>`;

  const offs = [];
  bindTips(main);
  // the sticky scoreboard sits right under the top bar, whose height changes when the nav wraps on phones
  const tb = () => main.style.setProperty('--tb', `${document.getElementById('topbar')?.offsetHeight || 58}px`);
  tb(); addEventListener('resize', tb); offs.push(() => removeEventListener('resize', tb));

  // count the final score up when the hero loads
  if (!reduced()) main.querySelectorAll('.mo-final [data-count]').forEach((el) => {
    const to = +el.dataset.count, t0 = performance.now(), dur = 1400;
    const step = (t) => { const k = Math.min(1, (t - t0) / dur); el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(step); };
    el.textContent = '0'; requestAnimationFrame(step);
  });

  // reading progress + chapter rail
  const prog = main.querySelector('#moProg');
  const rail = [...main.querySelectorAll('.mo-rail [data-go]')];
  const onScroll = () => {
    const h = document.documentElement;
    prog.style.transform = `scaleX(${Math.min(1, h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight))})`;
    let cur = null;
    rail.forEach((b) => { const s = main.querySelector('#ch-' + b.dataset.go); if (s && s.getBoundingClientRect().top < innerHeight * 0.4) cur = b; });
    rail.forEach((b) => b.classList.toggle('on', b === cur));
  };
  addEventListener('scroll', onScroll, { passive: true }); onScroll();
  offs.push(() => removeEventListener('scroll', onScroll));
  main.querySelector('.mo-rail').addEventListener('click', (e) => {
    const b = e.target.closest('[data-go]'); if (b) main.querySelector('#ch-' + b.dataset.go)?.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
  });

  // sources: jump + flash (hash links would fight the router)
  main.addEventListener('click', (e) => {
    const s = e.target.closest('.mo-sn');
    if (s) {
      const li = main.querySelector('#mo-src-' + s.dataset.src);
      li?.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'center' });
      li?.classList.remove('flash'); void li?.offsetWidth; li?.classList.add('flash');
      return;
    }
    const v = e.target.closest('[data-vid]');
    if (v) { const vid = m.videos.find((x) => x.id === v.dataset.vid); if (vid) (vid.src ? openMp4(vid) : openVideo({ ...vid })); return; }
    const c = e.target.closest('[data-clip]');
    if (c) { const b = m.sequence[+c.dataset.clip]; openMp4({ src: b.clip.src, thumb: b.clip.thumb, title: b.clip.title }); return; }
    const pp = e.target.closest('[data-paper]');
    if (pp) { const p = m.papers[+pp.dataset.paper]; openPhoto({ url: p.url, caption: `${p.paper || ''}${p.headline ? ' · ' + p.headline : ''}`, page: p.page }); }
  });

  // fade chapters in as they arrive
  const io = new IntersectionObserver((es) => es.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } }), { rootMargin: '0px 0px -10% 0px' });
  main.querySelectorAll('.reveal').forEach((el) => io.observe(el));
  offs.push(() => io.disconnect());

  // the finish: the scoreboard follows the beat in the middle of the screen
  const beats = [...main.querySelectorAll('.mo-beat')];
  if (beats.length) {
    const sbU = main.querySelector('#sbU'), sbO = main.querySelector('#sbO'), sbC = main.querySelector('#sbClock'), sbP = main.querySelector('#sbPer');
    let last = -1;
    const show = (i) => {
      if (i === last) return; last = i;
      const b = m.sequence[i];
      beats.forEach((el, j) => { el.classList.toggle('on', j === i); el.classList.toggle('past', j < i); });
      if (b.u != null) { bump(sbU, b.u); bump(sbO, b.o); }
      sbC.textContent = b.clock || ''; sbP.textContent = per(b.period);
    };
    // the active beat is the last one whose top has crossed the middle of the screen (robust to fast flicks)
    let raf = 0;
    const pick = () => { raf = 0; let i = 0; beats.forEach((el, j) => { if (el.getBoundingClientRect().top < innerHeight * 0.55) i = j; }); show(i); };
    const onS = () => { if (!raf) raf = requestAnimationFrame(pick); };
    addEventListener('scroll', onS, { passive: true });
    offs.push(() => { removeEventListener('scroll', onS); cancelAnimationFrame(raf); });
    pick();
  }

  // charts
  const cel = main.querySelector('#moChart');
  if (cel) {
    const C = m.chart;
    const draw = () => {
      if (C.wp) {
        const wpIdx = (pi) => C.wp.findIndex((w) => w[0] >= pi);
        winProb(cel, C.wp, C.periods.map(wpIdx), true, C.marks.map((k) => ({ i: wpIdx(k.play), tip: esc(k.label) })).filter((k) => k.i >= 0));
      } else flow(cel, C.margin, C.periods, C.marks.map((k) => ({ i: k.play, tip: esc(k.label) })));
    };
    draw(); offs.push(onResize(cel, draw));
  }
  const court = main.querySelector('#moCourt');
  if (court) { const draw = () => fullCourt(court, m.shot); draw(); offs.push(onResize(court, draw)); }

  return { destroy() { offs.forEach((f) => f()); tip(null); } };
}

const KIND = { full_game: 'Full game', highlights: 'Highlights', final_play: 'The final play', moment: 'The moment', documentary: 'Documentary', interview: 'Interview', radio: 'Radio call', espn: 'ESPN' };
const hms = (s) => { s = +s; const h = Math.floor(s / 3600), mm = Math.floor((s % 3600) / 60), ss = s % 60; return `${h ? h + ':' + String(mm).padStart(2, '0') : mm}:${String(ss).padStart(2, '0')}`; };
function enterLine(name, e) {
  if (!e) return '';
  return esc([e.rank ? `#${String(e.rank).replace(/^#/, '')}` : '', name, e.record ? `(${e.record})` : '', e.seed ? `· ${e.seed} seed` : ''].filter(Boolean).join(' '));
}
function bump(el, v) {
  if (!el || el.textContent === String(v)) return;
  el.textContent = v;
  el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump');
}

// Full court, UConn's basket on the left: where the shot came from and its flight to the rim.
// ESPN coordinates: x = 0–50 ft sideline to sideline, y = feet from the baseline of the shooting team's basket.
function fullCourt(el, s) {
  const w = Math.min(el.clientWidth || 800, 980), k = w / 94, h = 50 * k;
  const X = (ft) => ft * k, Y = (ft) => ft * k;
  const ln = 'stroke="var(--maple-2)" stroke-opacity=".5" fill="none" stroke-width="1.3"';
  const end = (flip) => {
    const fx = (v) => (flip ? X(94 - v) : X(v));
    const sweep = flip ? 0 : 1;
    return `<rect x="${Math.min(fx(0), fx(19))}" y="${Y(19)}" width="${19 * k}" height="${12 * k}" fill="rgba(0,14,47,.5)" stroke="var(--maple-2)" stroke-opacity=".5"/>
      <path d="M${fx(19)},${Y(19)} A${6 * k},${6 * k} 0 0 ${sweep} ${fx(19)},${Y(31)}" ${ln}/>
      <path d="M${fx(0)},${Y(3.34)} H${fx(9.9)} A${22.15 * k},${22.15 * k} 0 0 ${sweep} ${fx(9.9)},${Y(46.66)} H${fx(0)}" ${ln}/>
      <line x1="${fx(4)}" x2="${fx(4)}" y1="${Y(22)}" y2="${Y(28)}" stroke="#fff" stroke-width="2"/>
      <circle cx="${fx(5.25)}" cy="${Y(25)}" r="${0.75 * k}" stroke="var(--red)" stroke-width="2" fill="none"/>`;
  };
  // the shot: along the court = y, across = x
  const sx = X(s.y), sy = Y(s.x), rx = X(5.25), ry = Y(25);
  const mx = (sx + rx) / 2, my = Math.min(sy, ry) - Math.max(40, Math.abs(sx - rx) * 0.28);
  el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" class="mo-courtsvg" role="img" aria-label="${esc(s.text)}">
    <defs><linearGradient id="mowood" x1="0" x2="1"><stop offset="0" stop-color="#2a1a0e"/><stop offset=".5" stop-color="#3a2513"/><stop offset="1" stop-color="#2a1a0e"/></linearGradient>
      <radialGradient id="moglow"><stop offset="0" stop-color="var(--gold)" stop-opacity=".9"/><stop offset="1" stop-color="var(--gold)" stop-opacity="0"/></radialGradient></defs>
    <rect width="${w}" height="${h}" rx="4" fill="url(#mowood)"/>
    <line x1="${X(47)}" x2="${X(47)}" y1="0" y2="${h}" ${ln}/><circle cx="${X(47)}" cy="${Y(25)}" r="${6 * k}" ${ln}/>
    ${end(false)}${end(true)}
    <path d="M${sx},${sy} Q${mx},${my} ${rx},${ry}" fill="none" stroke="var(--gold)" stroke-width="2" stroke-dasharray="6 6" class="mo-flight"/>
    <circle cx="${sx}" cy="${sy}" r="${Math.max(18, 3 * k)}" fill="url(#moglow)"/>
    <circle cx="${sx}" cy="${sy}" r="7" fill="var(--gold)" stroke="var(--ink)" stroke-width="2"/>
    ${s.ft ? `<text x="${(sx + rx) / 2}" y="${Math.max(16, my + 4)}" text-anchor="middle" class="mo-ftlab">${s.ft} FT</text>` : ''}
  </svg>`;
}

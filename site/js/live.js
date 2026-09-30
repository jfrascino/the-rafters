// Live game night: poll ESPN's public summary feed straight from the browser (it allows cross-origin reads).
const URL_ = (id) => `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event=${id}`;

export async function fetchLive(eid) {
  const r = await fetch(URL_(eid), { cache: 'no-store' });
  if (!r.ok) throw new Error('live feed ' + r.status);
  const d = await r.json();
  const comp = d.header?.competitions?.[0];
  if (!comp) return null;
  const st = comp.status?.type || {};
  const teams = comp.competitors.map((c) => ({ id: c.team?.id || c.id, homeAway: c.homeAway, score: +c.score || 0, abbr: c.team?.abbreviation, name: c.team?.location }));
  const u = teams.find((t) => String(t.id) === '41'), o = teams.find((t) => String(t.id) !== '41');
  const plays = (d.plays || []).slice(-6).reverse().map((p) => ({ clock: p.clock?.displayValue, period: p.period?.number, text: p.text, scoring: p.scoringPlay, team: String(p.team?.id || '') === '41' ? 'u' : p.team ? 'o' : null, us: u?.homeAway === 'home' ? p.homeScore : p.awayScore, os: u?.homeAway === 'home' ? p.awayScore : p.homeScore }));
  const wpArr = d.winprobability || [];
  const wpLast = wpArr.at(-1);
  const uWin = wpLast ? (u?.homeAway === 'home' ? wpLast.homeWinPercentage : 1 - wpLast.homeWinPercentage) : null;
  return { state: st.state, detail: st.shortDetail || st.detail, clock: comp.status?.displayClock, period: comp.status?.period, us: u?.score, os: o?.score, plays, uWin };
}

// Poll while the tab is visible; stops itself after the final.
export function watch(eid, onData, { every = 20000 } = {}) {
  let t = 0, dead = false;
  const tick = async () => {
    if (dead) return;
    if (!document.hidden) {
      try {
        const L = await fetchLive(eid);
        if (L) { onData(L); if (L.state === 'post') { dead = true; return; } }
      } catch (e) { /* offline or feed hiccup: try again next tick */ }
    }
    t = setTimeout(tick, every);
  };
  tick();
  return () => { dead = true; clearTimeout(t); };
}

// Is this scheduled game close enough to tip-off to start polling?
export function nearTip(iso) {
  const d = new Date(iso).getTime();
  const now = Date.now();
  // ESPN parks "time TBA" games at midnight Eastern, so treat that whole day as a window
  return now > d - 3 * 3600e3 && now < d + 30 * 3600e3;
}

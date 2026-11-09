# Storrs Lore — season-start review (2026-11-08)

Jason (2026-11-08): the AP Top 10 on #/now shows no real records now that the season has begun; review the entire
site so it is issue-free for the 2026-27 season. Standing rules from Jason: data accuracy is the most important
thing; decide fixes and tell him after (no approval needed for bug fixes); keep the off-season "2025-26 final"
honesty (never pass old numbers off as current).

Context: UConn is 2-0 (W 86-46 Gardner-Webb Nov 2, W 85-77 vs No. 16 Michigan in Boston Nov 6). Next game is
Wagner, Mon Nov 9, 7 PM ET (game 2027-3). The launchd updater (dev/auto_update.sh) skips while code is uncommitted,
so all code fixes must be committed and deployed well before tip on Nov 9.

## Found so far (verified on the live #/now page)
1. **AP top 10 records all "0-0".** ESPN's rankings feed carries each team's record as of the poll (preseason,
   Oct 19). Fix: season_hub.py fetches each top-10 team's live record (ESPN `teams/{id}`), the table shows it.
2. **NET tile shows last season's NET as current** (No. 9, 34-6, Quad 1 11-4). build.py sets `final = not played_now`,
   but ncaa.com still lists the 2025-26 final. Fix: final when the NET row's W+L exceeds games UConn has played.
3. **Season header for the current season** says "NR · Final AP" (UConn is No. 4) and "No postseason".
4. **Stats table FT% "1.0"** for Junior County (100% shown as a fraction).
5. **Milestone watch lists Solo Ball** (out for the season, medical redshirt) twice.
6. **Key moments "APR 19 · Mullins returns"** but the story says April 18 (known unapplied fact-check fix).
7. **Exhibitions** (Oct 13 Syracuse, Oct 20 at Michigan State, Oct 27 Purdue) still show tip times like upcoming games.
8. **Next opponent "0-2 · 1st in NEC"**: a conference standing before conference play means nothing.
9. **"Season high" pill** on every top performer in game 2: noise this early.
10. Roster "Elmir Džafic" vs story "Džafić": check the official spelling.

## Settled by Kai (Opus) while the reviews ran
- #6 Mullins: April 18 is right (the ledger already fixed the story; sources WFSB 2026-04-18, Yahoo). Added a ledger
  item for `key_moments[1].date` in `pipeline/out/media/verify_seasons.json` (applied by build.py's apply_ledger).
- Solo Ball's redshirt was announced April 20, 2026 (uconnhuskies.com/news/2026/4/20): that key moment is right.
- #7 Exhibitions: official results added to `pipeline/out/media/verify_current.json` → `official_schedule[*].result`
  `{res, pts, opp_pts, box (official box score URL), source}`: W 72-52 Syracuse (Oct 13), W 78-70 at Michigan State
  (Oct 20), W 76-53 Purdue (Oct 27). Code still needs to pass them through (build.py ~line 1175) and render them.
- #10 Spelling: UConn's official roster says "Elmir Džafic"; ledger item makes the 2027 story match.
- #8 ESPN's team endpoint has only the overall record; the conference record is in the standings endpoint for the
  team's group (`team.groups.id`, e.g. NEC = 19): `/apis/v2/sports/basketball/mens-college-basketball/standings?group=<id>`.

## Review findings
### Page review (Sonnet, live site; Kai re-checked A1 and A6 in the data)
- A1 **All-time series omit this season**: `allW/allL` come from the record book (through 2025-26) and build.py
  ~L1926 sets them without adding later games. Michigan shows 2–3 all-time beside 3–2 since 1977–78 (truth 3–3);
  Gardner-Webb 2–0 beside 3–0 (truth 3–0). Same field feeds #/now's "All-time series" and #/numbers > Opponents.
- A2 **Home Floors (#/venues) skip this season**: the Hartford/PeoplesBank Arena panel's "Most recent" is still
  Feb 25, 2026 and its since-1987 block (363 g) misses the Nov 2 home win (364). Official building records from the
  record book (through 2025-26) also need this season's games added.
- A3 **#/numbers Season vs. Season, 2026–27 row**: AP PRE "–" (was preseason No. 4), finish "No postseason".
- A4 **#/seasons 2026–27 row**: "No postseason" pill; no AP tag (2025–26 shows "AP 2").
- A5 **Key moments written before the season** read as previews after the game: "Nov 6 · Michigan in Boston —
  Title-game rematch…" with no result; #/game/2027-2's "The moment" box repeats that preview sentence.
- A6 **AP game stories leak the footer** (2027-1, 2027-2): everything from the first "------" line on (editor's
  correction note, "Sign up for Top 25 poll alerts here…") shows as text; datelines render "BOSTON -- —".
- A7 **#/season/2027 stats tabs**: "Advanced stats are not available" and "Team totals are not available" although
  both box scores exist (`team` in seasons/2027.json is `{}`).
- A8 Transfers' earlier seasons are missing (Nik Khamenia's Duke year etc.); Demary's Georgia rows do show.
- A9 Solo Ball's page: 2026–27 row of dashes, no redshirt note, span "2023–27".
- A10 #/game/2027-2 TV "TNT" vs schedule "TNT, truTV and HBO Max"; box score has no "Team" row, so player REB/TO
  sums (31, 9) differ from team totals (33, 12) without explanation.
- A11 Schedule ranks are ESPN's current ranks (preseason poll for now): fine if the updater keeps refreshing them.
- A12 No game highlight videos on the two finished games.
- A13 Stale player files in site/data/players/ (n-*.json, espn-4895737 = an old Solo Ball duplicate).
- A14 Big East standings before conference play: seeds 1–11 are alphabetical among 0–0 teams (meaningless).
- Verified fine: home hero totals, Hurley 201–75, season record and per-game/totals tables vs box scores, Mullins
  career totals, box-score sums, series since 1977-78, no console errors, phone width OK.

### Pipeline review (Sonnet; Kai re-checked P1 and P4 in the code)
- P1 **Game night:** `site/js/views/game.js` only runs the live ESPN widget when the game has NO detail (`if (!d)`),
  but the updater writes a partial box score mid-game, so 20 min after tip the page shows a frozen partial box and
  never goes live. The schedule row also leaks a partial leader (`top`) onto the unplayed game.
- P2 **~20 min after every final** UConn's official stat sheet still has one game fewer; `official_stats.apply`
  mixes it in (Nov 6: Mullins g=1, 43.0 ppg, until the next run).
- P4 **`pct()` in site/js/ui.js** treats exactly 1.0 as an already-scaled percent: every 100% line shows "1.0"
  (also 55 historical player-seasons). Stored percentages are fractions.
- P5 Home Floors: `pipeline/out/official/venues.json` gives 2027 home games `building_key: None`; venues_build.py
  only counts games with a key.
- P6 bracketmatrix.com now shows "Bracket Matrix - 2027 … PRESEASON MATRIX" (UConn seed 2, avg 1.90, 52 brackets)
  with no d/m/y date, so `updated` is null and the tile wrongly says "2025-26 final".
- P7 ncaa.com writes "Through Games Apr. 06 2026" (no comma): the `through` regex never matches.
- P8 `cw/cl` (conference record) come only from Sports-Reference, so after Dec 23 the 2026-27 conference record
  never appears; espn_fetch already records `conferenceGame` per game.
- P9 auto_update.sh: a failed Cloudflare deploy (Nov 6 04:22, "Unknown internal error") is never retried; the next
  run sees "no changes".
- P10 next_opp: leaders always empty (ESPN statistics endpoint shape); it reads the next opponent from the previous
  build's core.json, so right after a final it fetches the old opponent.
- P12 standings(): no guard against an empty ESPN response overwriting the good file.
- P13 `finish_for` (build.py ~1109) treats a win like a loss: mid-tournament a team that won its R64 game reads "r64".
- P14 Season-level lists treat 2-0 like a finished season (numbers.js Win% etc.).
- P15 Box score shows ESPN's "Elmir Dzafic" (roster: "Džafic"); game page TV "TNT" vs schedule "TNT, truTV and HBO Max";
  11 orphan `site/data/players/n-*.json` + `espn-4895737` (old Solo Ball duplicate).
- Verified fine: both box scores match ESPN line by line, play-by-play ends at the finals, attendance/officials,
  season totals = box sums, career 3PM (Mullins 79 = 72 + 7), program record 1,895–1,031 (book 1,893–1,031 + 2–0),
  Hurley 201–75, live.js endpoints (CORS ok, pre/post states, home/away win prob), should_update game window.
- ESPN has no highlight videos for these games (A12 has no source; not fixing now).

## Fix list (two builders, disjoint files)
Rules for both: data accuracy first; never invent numbers; don't commit, push or deploy (Kai deploys); don't touch
the other builder's files. The launchd updater skips while code is uncommitted, so it won't interfere.

### Builder A — pipeline (`pipeline/*.py`, `dev/auto_update.sh`, new `pipeline/out_for_season.json`, `.gitignore`)
Only builder A runs `pipeline/build.py` / `season_hub.py`. No browser.
- A-1 Top-10 live records (`season_hub.py` polls): fetch each top-10 team's current overall record for both polls
  (ESPN `teams/{id}` → `record.items[type=total].summary`, deduped, fail-soft) and store it as `now` on the rank
  row. Keep `record` (record at poll time) for polls_history.
- A-2 NET: regex `,?\s+` for "Through Games Apr. 06 2026". build.py: `final` = the NET row's W+L is more than the
  games UConn has played this season (fallback: `not played_now`). Keep `record` in the hub.
- A-3 Bracket: read the season from the `<title>` ("Bracket Matrix - 2027") and the PRESEASON marker; save `season`
  and `preseason`; build.py `final` = `season != current_season` (old date rule only when `season` is missing).
  Make the date regex look only near the page's "updated" text, not the first d/m/y anywhere.
- A-4 next_opp: take the next game from the freshly fetched ESPN schedule (wherever espn_fetch writes it), not the
  previous build's core.json; leaders from the ESPN core API team leaders (`sports.core.api.espn.com/v2/sports/
  basketball/leagues/mens-college-basketball/seasons/<y>/types/2/teams/<id>/leaders`, athlete name via `$ref`),
  points/rebounds/assists; drop `standing` until the team has played a conference game (its group's standings
  `vsconf` summary, group id from `team.groups.id`).
- A-5 standings(): never overwrite a good file with empty rows.
- A-6 Series: `allW/allL` += this site's W/L for games in seasons after the record book's coverage (book is through
  2025-26: take it from series_records.json's `_source` if it says so, else a named constant). Feeds now/numbers.
- A-7 Home Floors: in venues_build.py, a home game (`ha == 'H'`) with `building_key: None` is mapped by its arena
  string (PeoplesBank Arena / XL Center / Hartford Civic Center → the Hartford building key; "Gampel" → gampel; use
  the keys the file already uses). Official building records (record book, through 2025-26) + this season's games.
- A-8 Out for the season: new `pipeline/out_for_season.json`
  `{"2027": {"solomon-ball-2": {"note": "Medical redshirt (wrist surgery)", "source": "https://uconnhuskies.com/news/2026/4/20/mens-basketball-solo-ball-to-medical-redshirt-in-2026-27"}}}`
  (check the pid). build.py: skip those players in the milestone watch; roster entry gets `out: {note, source}`;
  the player's season row for that year gets `out: {note}`.
- A-9 Exhibitions: pass `result` from verify_current.json through as `res`, `pts`, `opp_pts`, `box` on each
  `exhibitions[]` entry.
- A-10 Recap `seasonHigh` only when the player has played at least 5 games this season (this one included).
- A-11 `inProgress: true` on the current season's core.json `seasons` row and seasons/<y>.json while
  `y == current_season` and (an unplayed game remains or today < April 10 of year y).
- A-12 Current season summary: `apPre` present in the core.json `seasons` row (the season file already knows
  preseason No. 4); `cw/cl` from ESPN `conferenceGame` over played games when Sports-Reference meta has none.
- A-13 finish_for: a win in a round means the team reached the next round (R64 win → r32 … regional final win →
  Final Four, semifinal win → title game, title win → champ). Prove no completed season's finish changes (diff
  core.json `seasons[].finish` before/after).
- A-14 Team vs. opponents for a season without Sports-Reference `team` data whose played games all have box scores
  (the current season): sum team and opponent box totals into the same structure the SR seasons use (inspect
  seasons/2026.json `team`). No advanced/model stats.
- A-15 A game without a final result gets no box-score detail, `top` or leaders in the published data (ESPN's
  partial mid-game box stays out until the final).
- A-16 official_stats.py: don't apply the official sheet to the current season when its games count differs from
  the games UConn has played (the sheet lags a final by ~20 min).
- A-17 AP stories: drop everything from the first line that is only dashes ("------") on; fix the "BOSTON -- —"
  dateline (find where it comes from).
- A-18 Game detail TV = the official schedule's TV string when there is one; UConn players in box scores use the
  site's player name (roster spelling).
- A-19 After writing `site/data/players/`, remove player files this build didn't write (report the count).
- A-20 auto_update.sh: retry cf-pages-deploy up to 3 times; remember the last deployed commit
  (`dev/.deployed_commit`, gitignored) and deploy when HEAD differs even if the data didn't change. launchd may be
  running the script: write the new version to a temp file and `mv` it into place.
- A-21 `.gitignore`: add `.wrangler/` and `dev/.deployed_commit`.
- Then run `pipeline/season_hub.py` and `pipeline/build.py`, and check the outputs: hub (`now` records, NET final,
  bracket preseason), Michigan 3–3 / Gardner-Webb 3–0 all-time, Hartford building incl. Nov 2, Solo Ball out,
  exhibitions, `inProgress`, apPre 4, 2027 `team` totals = box sums, no historical finish changed, stats validation
  numbers unchanged for past seasons (`official check` line), orphan files gone.

### Builder B — pages (`site/js/**`, `site/css/**` only)
Don't run build.py or edit site/data. Code defensively: fields from builder A may not exist yet.
You may use the built-in browser (local preview: `preview_start` name `uconn-hoops`, port 8786; one tab only);
run `python3 pipeline/stamp.py` if the import map serves stale modules. Stop/close audio-free tabs when done.
- B-1 `pct()` in ui.js: stored percentages are fractions → always `(v*100).toFixed(1)`. Audit every use of `pct`
  (also passed as a function reference, e.g. table column formats) and fix any caller that passes 0–100 values.
- B-2 game.js: when the game is not final, show the pregame/live view (the `!d` branch with `watch()`) even if
  detail data exists.
- B-3 now.js: top-10 record `r.now || r.record`. NET tile: when `net.final` and UConn has played this season →
  "—" with "2026–27 NET not out yet · 2025–26 final No. 9" (labels from `hub.season`). Bracket tile: `br.preseason`
  → "Preseason projection" instead of a "final" tag. Standings: while every team's conference record is 0-0, hide
  the seed numbers and sort by overall record (win %, then wins), with "Conference play starts later".
- B-4 season.js: (a) header for `s.inProgress` (or `y === core.current.season` and a game remains): "Season in
  progress" pill instead of "No postseason" (a real finish pill once UConn reaches the postseason); AP stat = current
  AP rank from `core.hub.polls.ap` when it isn't `final` ("#4 · AP poll", "RV"/"NR" when unranked), "AP peak" only
  when different. (b) Exhibitions: result "W 72–52" (`res/pts/opp_pts`) in the result column, linking to `box`
  (official box score, new tab). (c) Roster cards with `out`: "Out for the season · medical redshirt" instead of
  "– PTS – REB – AST". (d) Key moments dated on a played game (`g.day || g.date`): add the result chip
  ("W 85–77", links to the game). (e) Stats tabs: no "Advanced" tab for an in-progress season without advanced
  data; "Team vs. opponents" renders once `team` is filled.
- B-5 seasons.js: in-progress row gets the in-progress pill and the current AP rank tag.
- B-6 numbers.js (Season vs. Season and other season lists): mark the in-progress season ("in progress"), finish
  not "No postseason"; AP PRE from data.
- B-7 player.js: a season row with `out` shows the note ("Medical redshirt · did not play") instead of dashes; the
  span counts only seasons with games (Solo Ball 2023–26).
- B-8 game.js: no "The moment" box for an in-progress season (those key moments were written before the games); box
  score gets a "Team" row for REB/TO when team totals exceed the player sums.

---

# Transfers' earlier college seasons (2026-11-09)

Jason chose to do this here (follow-up from the season-start review). Deadline: committed and deployed before the
updater's game window opens at 4 PM ET today (Wagner tips 7 PM ET); the updater skips while code is uncommitted.

## Findings (Kai)
- Other-school rows come from Sports-Reference player pages: build.py (~line 1826) reads
  `sr_players[pid].tables.players_per_game.rows` (files in `pipeline/out/sr/players/<sr-slug>.json`) and adds every
  non-UConn row as `{y, label, school, uconn: false, cls, g, gs, mp, pts, trb, ast, stl, blk, fg_pct, fg3_pct, ft_pct}`.
  Career totals, ranks and milestones use only UConn rows, so other-school rows never count (keep it that way).
- The 2026-27 newcomers have ESPN-based ids (`espn-<athleteId>`) and no SR page, so they show only their UConn row:
  Nik Khamenia `espn-5144124` (Duke), Jaye Nash `espn-5060718` (Jacksonville State), Na'jai Hines `espn-5292602`
  (Seton Hall), Oskar Giltay `espn-5312293` (Stanford), Nils Machowski `espn-5175080` (Wofford), Elmir Džafic
  `espn-5311500` (Arkansas), Isaiah Shaw `espn-4896885` (Northern Arizona). Freshmen (County, Landrew, Amosov) have
  no college seasons; Jacob Ross's SR page has no rows; Jayden Ross and Demary already work.
- Tools: `pipeline/sr_fetch.py` `fetch(url)` (cached in cache.nosync/sr, ≥3.5 s between requests, 429 back-off) and
  `pipeline/sr_parse.py` `parse_season(html, year)` (roster with `sr_id`) and `parse_player(html, sr_id)`.
  SR URLs: `/cbb/schools/connecticut/men/2027.html`, `/cbb/players/<sr_id>.html`.
- Second source: ESPN `https://site.web.api.espn.com/apis/common/v3/sports/basketball/mens-college-basketball/athletes/<id>/stats`
  → `categories[name=averages].statistics[]` (`season.displayName` "2025-26", `teamSlug`, stats per `labels`: GP GS MIN
  FG FG% 3PT 3P% FT FT% OR DR REB AST BLK STL PF TO PTS). Khamenia: Duke 2025-26 38 GP, 5 GS, 19.8 MIN, 5.7 PTS.

## Plan
1. New `pipeline/transfer_seasons.py` (run by hand, not by the updater: earlier seasons don't change): for each
   current-roster player without other-school rows, find his SR id on SR's UConn current-season roster (match names
   accent-insensitively: SR "Džafić" = official "Džafic"), fetch his SR page, take non-UConn per-game rows; fetch ESPN
   career stats; compare season by season. Write `pipeline/out/official/transfer_seasons.json`:
   `{pid: {name, sr_id, espn_id, seasons: [row as above + "checked": "sr+espn"], disagreements: [...]}}`.
   Agreement: GP and GS equal; MIN/PTS/REB/AST/STL/BLK per game within 0.1; FG%/3P%/FT% within 0.2 points.
   A stat the two sources disagree on is settled by a third source (that school's official season stats) when
   possible, otherwise left blank (None) and listed in `disagreements`. A season only one source has: include it with
   `"checked": "sr-only"`/`"espn-only"` and list it in the report.
2. build.py: when a player's SR page gives no other-school rows, take them from transfer_seasons.json (school
   name as SR prints it). Nothing else changes; career/ranks/milestones stay UConn-only.
3. Don't touch `pipeline/out/sr/players/`, don't run `sr_scrape.py` (its 2027 build would switch the current season
   onto SR data), don't commit or deploy (Kai does).

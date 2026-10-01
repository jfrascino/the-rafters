# Storrs Lore — "Moments" research brief

Storrs Lore (https://jfrascino.github.io/the-rafters/) is a UConn men's basketball fan encyclopedia. Its owner's
overriding rule: **the veracity of every fact is the most important thing on the site.** Nothing unverified ships.
We are building a "Moments" section: immersive, modern long-form pages for UConn's greatest moments — the date, venue,
storyline, the decisive sequence told beat by beat, video, archival media, voices, aftermath. Not a recap-by-numbers:
the story of the moment, told vividly — but every single fact must be sourced.

## Your job
Research each assigned moment thoroughly on the web and write ONE JSON file per moment to
`~/Projects/the-rafters/pipeline/out/moments/drafts/<slug>.json` (schema below). Do not modify any other file.

## Use the site's own data as a cross-check (read-only)
- `~/Projects/the-rafters/site/data/seasons/<springYear>.json` → `games[]` (id, date, opp, res, pts, opp_pts, ot, arena, city, round)
- `~/Projects/the-rafters/site/data/games/<springYear>.json` → keyed by game id: `venue`, `att`, `tv`, `officials`, `teams[]` (box score: players with stats), `videos[]` (already-verified YouTube videos for that game)
- `~/Projects/the-rafters/site/data/plays/<gameId>.json` → `plays[]` rows: [period, clock, team ('u'=UConn,'o'=opponent), uconnScore, oppScore, scoringPlay, points, text, x, y]; `wp` = win probability where present
If a source contradicts our data, say so in `conflicts` (don't silently pick one).

## Sources
Prefer contemporaneous and primary: NYT archive (nytimes.com/19xx/...), AP/UPI wire stories, Sports Illustrated Vault (vault.si.com),
Hartford Courant (courant.com), ESPN recaps/box scores, NCAA.com, uconnhuskies.com, opponents' athletics sites and media guides,
the UConn Record Book PDF (https://uconnhuskies.com/documents/download/2026/8/13/RECORD_BOOK_26-27_V2_.pdf),
The Daily Campus (UConn student paper) scans on archive.org (identifiers like `ct_daily_campus_1990-03-23`; search
https://archive.org/advancedsearch.php?q=ct_daily_campus+AND+date:1990-03*&fl[]=identifier&rows=50&output=json).
Wikipedia is a lead only — confirm anything you take from it in a primary/reliable source.

## Hard rules
1. Every sentence of narrative must be supported by the sources listed on it. No invented details, no "probably",
   no color you can't cite (crowd noise, what someone was thinking, etc. only if a source says it).
2. Write in your own words (no copied article text). Vivid, present-tense-friendly, but factual. Short paragraphs.
3. Quotes: verbatim from a cited source, ≤ 25 words each, max 4 per moment, attributed (who, role, when said).
4. Clock times and scores in the decisive sequence must be exact and sourced; if the site has play-by-play for the game,
   use it as the backbone and cite it as "site:plays/<gameId>".
5. Nicknames ("The Shot", etc.) only if widely used — cite where it's used. Otherwise a plain descriptive title.
6. Videos: YouTube only. Verify each ID with `curl -s "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<ID>&format=json"`
   and record the returned title + author_name. Only keep videos that clearly show THIS game (full game, highlights,
   the final play, a radio call, a documentary segment about it). Include the site's own `videos[]` IDs that fit too.
   Note the timestamp (seconds) where the key moment occurs in a full-game/long video if you can determine it.
7. Photos: only (a) Wikimedia Commons files with a stated license, or (b) archival newspaper scans on archive.org
   (Daily Campus, etc.) — give the item URL, page, and an IIIF crop URL if you can build one
   (format: https://iiif.archive.org/image/iiif/3/<identifier>%2F<file path url-encoded>/<x>,<y>,<w>,<h>/max/0/default.jpg),
   and say exactly what the photo shows and how you confirmed it is this game. No Getty/AP/press photos.
8. If the site lacks a box score for the game (teams[] empty) and you find a complete one in a reliable source,
   transcribe it into `box` with the source. Otherwise leave `box` null.
9. Anything you could not verify goes in `unsure` and NOT in the narrative.

## JSON schema (one file per moment)
{
  "slug": "<given>", "gameId": "<given>",
  "title": "headline, ≤ 7 words",
  "nickname": {"text": "...", "sources": ["url"]} | null,
  "dek": "one vivid sentence (≤ 30 words) — sourced facts only",
  "date": "YYYY-MM-DD", "tip": {"text": "e.g. 9:00 p.m. ET", "sources": []} | null,
  "venue": "building name on that date", "city": "City, ST", "attendance": {"n": 0, "sources": []} | null,
  "event": "e.g. Big East tournament final", "tv": {"network": "", "announcers": [], "sources": []} | null,
  "entering": {"uconn": {"record": "W-L", "rank": "AP #", "seed": ""}, "opp": {"record": "", "rank": "", "seed": ""}, "sources": []},
  "setup":    [{"text": "...", "sources": ["url", ...]}],      // 2–4 paragraphs: the stakes, the storylines, who mattered
  "game":     [{"text": "...", "sources": []}],                // 2–4 paragraphs: how the game unfolded before the decisive stretch
  "sequence": [{"period": "2H|OT1|...", "clock": "0:05", "uconn": 73, "opp": 74, "text": "...", "sources": []}],  // 5–12 beats, in order
  "numbers":  [{"value": "6", "label": "overtimes", "sources": []}],   // 3–6 striking, sourced facts (not simple box stats — we compute those)
  "quotes":   [{"text": "...", "who": "...", "role": "...", "when": "postgame|years later (year)", "source": "url"}],
  "aftermath":[{"text": "...", "sources": []}],                // what happened next (days / that season)
  "legacy":   [{"text": "...", "sources": []}],                // why it still matters (optional)
  "videos":   [{"youtube": "ID", "title": "<oEmbed title>", "channel": "<oEmbed author_name>", "kind": "full_game|highlights|final_play|radio|documentary", "start": null, "why": "how you know it is this game"}],
  "photos":   [{"url": "", "page": "", "credit": "", "license": "", "depicts": "", "verified": ""}],
  "newspaper":[{"paper": "", "date": "YYYY-MM-DD", "page_url": "", "iiif": "", "headline": "", "verified": ""}],
  "box": null,
  "conflicts": [{"field": "", "ours": "", "source_says": "", "sources": []}],
  "unsure": ["..."],
  "sources": [{"url": "", "what": ""}]
}
Return a short summary when done: slugs written, anything notable, open conflicts.

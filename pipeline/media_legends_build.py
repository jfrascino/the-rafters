"""Build out/media/legends.json — program lore with a source URL on every fact.

Inputs (all fetched & cached): lore_raw.json (program/coach/player/arena/rivalry articles), players_wikitext.json,
schedules_parsed.json (season articles), awards (program article), uconnhuskies.com pages.
"""
import json, os, re
from collections import defaultdict
from media_common import CACHE, save, wt2text, wiki_url
from media_awards import parse_awards

W = "https://en.wikipedia.org/wiki/"
PROGRAM = W + "UConn_Huskies_men%27s_basketball"
L = json.load(open(os.path.join(CACHE, "lore_raw.json")))
PW = json.load(open(os.path.join(CACHE, "players_wikitext.json")))
PR = json.load(open(os.path.join(CACHE, "players_raw.json")))
S = json.load(open(os.path.join(CACHE, "schedules_parsed.json")))
AW = parse_awards()
images = json.load(open(os.path.join(os.path.dirname(__file__), "out", "media", "images.json"))) if os.path.exists(os.path.join(os.path.dirname(__file__), "out", "media", "images.json")) else {"players": []}
IMG = {p["wiki_title"]: p for p in images.get("players", [])}

def url(title):
    return (L.get(title) or {}).get("url") or wiki_url(title)

def img_for(title):
    p = IMG.get(title)
    if not p: return None
    return {k: p.get(k) for k in ("image_url", "thumb_url", "file_page", "license", "author", "context", "caption_or_description")}

# ---------------- coaches ----------------
coaches = [
 {"name": "Jim Calhoun", "tenure": "1986–2012", "seasons": 26, "uconn_record": "629–245", "pct": ".720",
  "career_d1_wins": 873, "national_titles": [1999, 2004, 2011], "final_fours": [1999, 2004, 2009, 2011],
  "big_east_tournament_titles": [1990, 1996, 1998, 1999, 2002, 2004, 2011],
  "big_east_regular_season_titles": [1990, 1994, 1995, 1996, 1998, 1999, 2002, 2003, 2005, 2006],
  "other_titles": ["1988 NIT"],
  "honors": ["Naismith Memorial Basketball Hall of Fame (2005)", "AP National Coach of the Year (1990)",
             "Big East Coach of the Year (1990, 1994, 1996, 1998)", "John R. Wooden Legends of Coaching Award (2005)", "Huskies of Honor"],
  "bio": [
   "James A. Calhoun was born May 10, 1942, and raised in Braintree, Massachusetts. After his father died when Calhoun was 15, he "
   "left Lowell State after three months to support his family, working as a granite cutter, headstone engraver and gravedigger "
   "before returning to college at American International College, where he captained the team and graduated in 1968. He coached "
   "high school ball in Old Lyme, Westport and Dedham before Northeastern hired him in 1972; he moved Northeastern from Division II to "
   "Division I in 1979 and left as that school's all-time winningest coach (245–138).",
   "UConn named Calhoun head coach on May 14, 1986. After a 9–19 debut, his teams won the 1988 NIT, broke through with the 1990 "
   "\"Dream Season\" that made him the consensus national coach of the year, and then won national championships in 1999, 2004 and "
   "2011 — the last making him, at 68, the oldest coach to win a Division I men's title. He won 800 games by February 2009, "
   "survived prostate cancer (2003) and other health scares, and was enshrined in the Naismith Hall of Fame in 2005.",
   "Calhoun retired on September 13, 2012, handing the program to former point guard Kevin Ollie. His UConn record was 629–245, "
   "and he finished with 873 Division I victories. He later coached Division III University of Saint Joseph (2018–2021)."],
  "sources": [url("Jim Calhoun"), PROGRAM], "image": img_for("Jim Calhoun")},
 {"name": "Kevin Ollie", "tenure": "2012–2018", "seasons": 6, "uconn_record": "113–79", "pct": ".588",
  "national_titles": [2014], "final_fours": [2014], "other_titles": ["2016 AAC tournament"],
  "honors": ["Ben Jobe Award (2013)"],
  "bio": [
   "Kevin Ollie, born December 27, 1972, grew up in South Central Los Angeles and starred at Crenshaw High School before playing "
   "four seasons (1991–95) at UConn for Jim Calhoun. He graduated in 1995 and spent 13 NBA seasons (1997–2010) with 12 franchises, "
   "earning a reputation as a culture-setting veteran — Kevin Durant credited him with changing the culture in Oklahoma City.",
   "Ollie joined Calhoun's staff in 2010, helping guide the 2011 champions, and was promoted to head coach in September 2012. His "
   "first team was banned from the postseason because of a low Academic Progress Rate, but his second, led by Shabazz Napier, became "
   "the first No. 7 seed to win the national championship in 2014. He is one of only four African-American coaches to win the NCAA "
   "men's title.",
   "The program then slid, including its first losing season in 30 years in 2016–17. UConn fired Ollie with just cause on March 10, "
   "2018, amid an NCAA investigation that produced a show-cause order and vacated wins. He later coached in the NBA, most recently as "
   "the Brooklyn Nets' interim head coach."],
  "sources": [url("Kevin Ollie"), PROGRAM], "image": img_for("Kevin Ollie")},
 {"name": "Dan Hurley", "tenure": "2018–present", "seasons": 8, "uconn_record": "199–75 (through 2025–26)", "pct": ".726",
  "national_titles": [2023, 2024], "final_fours": [2023, 2024, 2026], "big_east_tournament_titles": [2024],
  "big_east_regular_season_titles": [2024],
  "honors": ["Naismith College Coach of the Year (2024)", "Sporting News Coach of the Year (2024)", "Big East Coach of the Year (2024)"],
  "bio": [
   "Daniel Hurley, born January 16, 1973, in Jersey City, New Jersey, is the son of Hall of Fame high school coach Bob Hurley Sr. "
   "and the brother of former Duke star Bobby Hurley. He played at St. Anthony High School and then at Seton Hall, where he stepped "
   "away from the game early in his junior year for mental-health reasons before returning to average 13.8 and 14.3 points in his "
   "final two seasons.",
   "Hurley built St. Benedict's Prep into a national power (223–21 in nine years), set Wagner's single-season wins record, and took "
   "Rhode Island to the 2017 and 2018 NCAA tournaments. UConn hired him on March 22, 2018, to rebuild a program at its low point; he "
   "steered the Huskies back to the Big East and to the NCAA tournament in 2021.",
   "Then came the most dominant stretch in modern college basketball: national titles in 2023 and 2024, the latter with a school-record "
   "37 wins, the program's first No. 1 overall seed and an NCAA-record +140 tournament margin. Hurley turned down Kentucky and the "
   "Los Angeles Lakers in 2024, and in 2026 led UConn to its third Final Four in four years and the national championship game."],
  "sources": [url("Dan Hurley"), PROGRAM], "image": img_for("Dan Hurley")},
]

# ---------------- championships ----------------
def ncaa_path(y):
    out = []
    for g in S[str(y)]["games"]:
        if "ncaa" in g["section"].lower() and "invitation" not in g["section"].lower():
            out.append({"round": re.sub(r"(?i)^ncaa\s*", "", g["gamename"]), "date": g["date"], "opponent": g["opponent"],
                        "opponent_seed": g["oppseed"] or None, "result": g["result"],
                        "score": f"{g['uconn']}–{g['opp_score']}" + (f" ({g['ot']})" if g["ot"] else ""), "site": g["site"]})
    return out

def seed(y):
    for g in S[str(y)]["games"]:
        if "ncaa" in g["section"].lower() and g["seed"]: return g["seed"]
    return None

MOP = {n_y[1]: n_y[0] for n_y in AW.get("NCAA Tournament MOP", [])}
TITLES = {
 1999: ("Tropicana Field, St. Petersburg, Florida", "UConn entered as the West's No. 1 seed, beat Gonzaga to reach its first Final Four, and as roughly nine-point underdogs upset top-ranked Duke 77–74. Richard Hamilton scored 27 in the final; Khalid El-Amin shouted \"We shocked the world!\" at the buzzer.", [W + "1999_NCAA_Division_I_men%27s_basketball_tournament"]),
 2004: ("Alamodome, San Antonio, Texas", "Preseason No. 1 UConn rallied from eight points down in the final three minutes to beat Duke 79–78 in the semifinals, then beat Georgia Tech 82–73. Emeka Okafor was MOP; the UConn women won the next night, the first men's-and-women's sweep.", [W + "2004_NCAA_Division_I_men%27s_basketball_tournament"]),
 2011: ("Reliant Stadium, Houston, Texas", "After winning five Big East tournament games in five days, UConn won six more, beating Kentucky 56–55 and Butler 53–41 — holding the Bulldogs to a title-game-record 18.8 percent shooting — for 11 straight postseason wins. Kemba Walker was MOP.", [W + "2011_NCAA_Division_I_men%27s_basketball_tournament"]),
 2014: ("AT&T Stadium, Arlington, Texas", "The first No. 7 seed ever to win it all, UConn beat Saint Joseph's in overtime, Villanova, Iowa State, Michigan State, No. 1 overall seed Florida and Kentucky. Shabazz Napier was MOP: \"You're looking at the hungry Huskies.\"", [W + "2014_NCAA_Division_I_men%27s_basketball_tournament"]),
 2023: ("NRG Stadium, Houston, Texas", "A No. 4 seed, UConn won all six games by at least 13 points (20.0 average), the first champion of the 64-team era to do so, and beat San Diego State 76–59. Adama Sanogo was MOP.", [W + "2023_NCAA_Division_I_men%27s_basketball_tournament"]),
 2024: ("State Farm Stadium, Glendale, Arizona", "The No. 1 overall seed won every game by at least 14 points, set an NCAA-record +140 margin (including a 30–0 run against Illinois), and beat Purdue 75–60 to become the first repeat champion since Florida in 2007. Tristen Newton was MOP.", [W + "2024_NCAA_Division_I_men%27s_basketball_tournament"]),
}
championships = []
for y, (site, story, extra) in TITLES.items():
    championships.append({"year": y, "season": f"{y-1}–{str(y)[2:]}", "coach": {1999: "Jim Calhoun", 2004: "Jim Calhoun", 2011: "Jim Calhoun", 2014: "Kevin Ollie"}.get(y, "Dan Hurley"),
                          "seed": seed(y), "final_site": site, "most_outstanding_player": MOP.get(y), "path": ncaa_path(y), "story": story,
                          "all_tournament_team": [n for n, yy in AW.get("NCAA All-Tournament Team", []) if yy == y],
                          "sources": [S[str(y)]["url"], PROGRAM] + extra})

final_fours = []
for y, res in [(1999, "Champion"), (2004, "Champion"), (2009, "National semifinalist"), (2011, "Champion"), (2014, "Champion"),
               (2023, "Champion"), (2024, "Champion"), (2026, "Runner-up")]:
    ff = [g for g in ncaa_path(y) if re.search(r"final four|national|championship", g["round"], re.I)]
    final_fours.append({"year": y, "result": res, "games": ff, "sources": [S[str(y)]["url"], PROGRAM]})

# ---------------- Huskies of Honor ----------------
hoh_wt = L["Huskies of Honor"]["wikitext"]
m = re.search(r"===\s*Men's basketball\s*===(.*?)===\s*Women's basketball", hoh_wt, re.S)
rows = [r for r in m.group(1).split("|-") if "||" in r or "\n|" in r]
hoh = []
for r in rows:
    cells = [wt2text(c).strip() for c in re.split(r"\|\||\n\|", r) if wt2text(c).strip()]
    cells = [re.sub(r'^style="[^"]*"\s*\|\s*', "", c) for c in cells]
    if len(cells) >= 4 and not cells[0].startswith("!"):
        num, name, pos, yrs = cells[0], cells[1], cells[2], cells[3]
        home = cells[4] if len(cells) > 4 else None
        hoh.append({"number": None if num.startswith("999") or num in ("—", "–") else num, "name": name, "role": pos, "seasons": yrs, "hometown": home if home not in ("—",) else None})
huskies_of_honor = {"members": hoh, "notes": [
    "Inaugural men's class (13 players, 3 coaches) announced December 26, 2006 and inducted February 5, 2007.",
    "Kemba Walker was added April 5, 2011 — the first men's player added after the inaugural class.",
    "Alex Karaban was inducted on Senior Day, February 28, 2026 — the first men's player honored while still active at UConn."],
    "sources": [url("Huskies of Honor"), PROGRAM, url("Alex Karaban")]}

retired = [
 {"number": 34, "player": "Ray Allen", "tenure": "1993–1996", "announced": "2018-12-07", "ceremony": "2019-03-03", "note": "First number ever retired by UConn men's basketball (announced alongside Rebecca Lobo's women's No. 50).", "sources": [PROGRAM, url("Ray Allen")]},
 {"number": 32, "player": "Richard Hamilton", "tenure": "1996–1999", "announced": "2024-01-30", "ceremony": "2024-02-24", "sources": [PROGRAM]},
 {"number": 50, "player": "Emeka Okafor", "tenure": "2001–2004", "announced": "2026-02-09", "ceremony": "2026-02-18", "note": "Retired at halftime of the Creighton game at Gampel Pavilion.", "sources": [PROGRAM, url("Emeka Okafor")]},
]

# ---------------- All-Americans, POY ----------------
aa = []
for key, team in [("Consensus First Team All-Americans", "Consensus first team"), ("Consensus Second Team All-Americans", "Consensus second team"),
                  ("AP All-American Honorable Mentions", "AP honorable mention")]:
    for n, y in AW.get(key, []):
        if y >= 1987: aa.append({"year": y, "player": n, "team": team})
aa.sort(key=lambda r: (r["year"], r["team"]))
poy = [{"year": y, "player": n, "award": k} for k in ("Big East Player of the Year", "AAC Player of the Year", "UPI College Basketball Player of the Year", "NABC National Player of the Year")
       for n, y in AW.get(k, []) if y >= 1987]
poy.sort(key=lambda r: r["year"])
other_awards = {k: [{"player": n, "year": y} for n, y in v if y >= 1987] for k, v in AW.items()
                if k not in ("All-New England First Team", "All-Yankee Conference First Team", "All-ECAC", "Yankee Conference Rookie of the Year",
                             "ECAC Player of the Year", "New England Player of the Year")}

# ---------------- NBA draft ----------------
wt = L["UConn Huskies men's basketball"]["wikitext"]
dm = re.search(r"UConn Players in the NBA Draft(.*?)\|\}", wt, re.S)
draft = []
for r in dm.group(1).split("|-")[1:]:
    cells = [wt2text(c).strip() for c in r.strip().split("\n|") if wt2text(c).strip()]
    cells = [c.lstrip("|").strip() for c in cells]
    if len(cells) >= 5 and cells[1].isdigit():
        draft.append({"player": cells[0].rstrip("#").strip(), "year": int(cells[1]), "round": int(cells[2]), "pick": int(cells[3]), "team": cells[4],
                      "lottery": cells[0].endswith("#")})
first_round = [d for d in draft if d["round"] == 1 and d["year"] >= 1987]

# ---------------- McDonald's All-Americans ----------------
mcd = []
for t, w in PW.items():
    p = PR.get(t) or {}
    if not p.get("is_player"): continue
    mm = re.search(r"McDonald.s All.American(?: Game)?\|McDonald.s All-American\]\]\s*\(\[\[(\d{4})", w) or re.search(r"McDonald.s All.American(?: Game)?[^\n]{0,40}?(\d{4}) McDonald", w)
    mm2 = re.search(r"\[\[(\d{4}) McDonald's All-American Boys Game", w)
    anym = re.search(r"McDonald.s All.American", w)
    if not anym or "nominee" in w[max(0, anym.start() - 40):anym.start() + 80]: continue
    mm3 = re.search(r"McDonald.s All.American(?: Game)?\|McDonald.s All-American\]\]\s*\((\d{4})\)", w)
    yr = int(mm.group(1)) if mm else (int(mm2.group(1)) if mm2 else (int(mm3.group(1)) if mm3 else None))
    col = re.search(r"\n\s*\|\s*college\s*=(.*?)(?=\n\s*\||\n\}\})", w, re.S)
    colt = wt2text(col.group(1)) if col else ""
    first_school = re.split(r"\(|;|\*|\n", colt.strip().lstrip("*").strip())[0].strip()
    transfer = bool(first_school) and not re.search(r"UConn|Connecticut", first_school)
    name = re.sub(r"\s*\(.*\)", "", t)
    uy = p.get("uconn_years")
    mcd.append({"player": name, "mcdonalds_year": yr, "uconn_years": f"{uy[0]}–{uy[1]}" if uy and uy[0] else None,
                "arrived_as": "transfer" + (f" from {first_school}" if first_school else "") if transfer else "high school signee",
                "source": p.get("url") or wiki_url(t)})
mcd.sort(key=lambda r: r["mcdonalds_year"] or 0)

# ---------------- arenas ----------------
arenas = [
 {"name": "Hugh S. Greer Field House", "location": "Storrs, CT", "years": "1954–1990", "capacity": "4,604",
  "notes": "UConn's on-campus home until Gampel opened; still stands northwest of the pavilion.", "sources": [PROGRAM, url("Harry A. Gampel Pavilion")]},
 {"name": "Harry A. Gampel Pavilion", "location": "Storrs, CT", "years": "1990–present", "opened": "1990-01-21",
  "first_game": "1990-01-27: No. 20 UConn 72, No. 15 St. John's 58", "capacity": "10,244 (8,241 originally; expanded after 1995–96 and 2001–02; lower bowl renovated 2025)",
  "record": "239–45 men's record through 2025–26",
  "notes": "Largest on-campus arena in New England; named for 1943 alumnus Harry A. Gampel, who donated $1 million. Home of the Huskies of Honor panels and retired numbers.",
  "sources": [url("Harry A. Gampel Pavilion")]},
 {"name": "Hartford Civic Center → XL Center → PeoplesBank Arena", "location": "Hartford, CT (about 25 miles from Storrs)", "years": "UConn men since 1976 (arena opened 1975)",
  "names": [{"name": "Hartford Civic Center", "from": 1975}, {"name": "XL Center", "from": "December 2007"}, {"name": "PeoplesBank Arena", "from": 2025}],
  "capacity": "15,495 for basketball (2025–present)",
  "notes": "UConn played most home games here until Gampel opened, then split home games roughly evenly between Storrs and Hartford — marquee games are not reserved for Hartford. Hosted NCAA first/second rounds in 1983, 1985, 1988, 1990, 1998 and 2019.",
  "sources": [url("PeoplesBank Arena"), PROGRAM]},
 {"name": "New Haven Coliseum", "location": "New Haven, CT", "years": "1986–87 (occasional home site)", "notes": "One of three home venues in Calhoun's first season.", "sources": [S["1987"]["url"]]},
 {"name": "Werth Family Champions Center", "location": "Storrs, CT", "years": "2014–present", "notes": "$40 million practice facility on the former Memorial Stadium site with identical men's and women's wings.", "sources": [PROGRAM]},
]

# ---------------- rivalries ----------------
def h2h(opp_pat):
    w = l = 0; games = []
    for y in sorted(S):
        for g in S[y]["games"]:
            if re.fullmatch(opp_pat, g["opponent"]) and g["result"] in ("W", "L") and "xhib" not in g["section"].lower():
                if g.get("vacated"): pass
                w += g["result"] == "W"; l += g["result"] == "L"
                games.append({"season": int(y), "date": g["date"], "result": g["result"], "score": f"{g['uconn']}–{g['opp_score']}" + (f" ({g['ot']})" if g["ot"] else ""),
                              "event": (g["section"] + (" " + g["gamename"] if g["gamename"] else "")).strip(), "site": g["site"]})
    return w, l, games

def notable(games):
    out = []
    for g in games:
        ev = g["event"].lower()
        if "ncaa" in ev or "championship" in ev or "final" in ev or "semifinal" in ev or "ot" in g["score"].lower() or "invitation" in ev:
            out.append(g)
    return out

RIV = [
 ("Syracuse", r"Syracuse", "Big East rivalry defined by Hall of Fame coaches Jim Boeheim and Jim Calhoun; its signature game was Syracuse's 127–117 six-overtime win in the 2009 Big East quarterfinals, which ended at 1:22 a.m.", [url("Syracuse–UConn rivalry")]),
 ("Georgetown", r"Georgetown", "The two schools each won a record seven original-Big East tournaments. Georgetown dominated the 1980s and early 1990s, UConn the mid-1990s to mid-2000s and the new-Big East era; UConn leads the all-time series 43–36 (through March 13, 2026). Ray Allen's winner beat the Hoyas for the 1996 Big East title.", [url("Georgetown–UConn men's basketball rivalry")]),
 ("Villanova", r"Villanova", "Big East rival in both the original and new conference; Villanova beat UConn in the 1995 Big East final, and UConn's 71–69 win over No. 8 Villanova in 2022 was its first top-10 win in eight years.", [PROGRAM]),
 ("Duke", r"Duke", "UConn's great non-conference foil: Christian Laettner's buzzer-beater ended the 1990 Dream Season, Duke won again in the 1991 Sweet Sixteen, and UConn beat Duke for the 1999 title, in the 2004 Final Four, and on Braylon Mullins' 35-footer in the 2026 Elite Eight.", [PROGRAM, S["1990"]["url"], S["2026"]["url"]]),
 ("Kentucky", r"Kentucky", "UConn beat Kentucky in the 2010 Maui final, the 2011 Final Four (56–55) and the 2014 national championship game (60–54), after an 87–83 win in the 2006 second round.", [PROGRAM, S["2011"]["url"], S["2014"]["url"]]),
 ("Pittsburgh", r"Pittsburgh", "A physical Big East rival: UConn beat Pitt in the 2002 (double overtime) and 2004 Big East finals, Pitt won the 2003 final, and Kemba Walker's step-back beat the No. 1-seeded Panthers in the 2011 quarterfinals.", [PROGRAM, url("Kemba Walker")]),
 ("Providence", r"Providence", "New England Big East rival; the Friars ended UConn's Big East tournament runs in 1993 and 1994, and the teams renewed the rivalry when UConn returned to the Big East in 2020.", [PROGRAM]),
 ("St. John's", r"St\. John's", "UConn christened Gampel Pavilion with a 72–58 win over St. John's in 1990 and beat the Red Storm for the 1999 Big East title; St. John's won the 2000 and 2026 Big East finals.", [PROGRAM, url("Harry A. Gampel Pavilion")]),
]
rivalries = []
for name, pat, summary, srcs in RIV:
    w, l, games = h2h(pat)
    rivalries.append({"opponent": name, "summary": summary, "record_1986_87_to_2025_26": f"{w}–{l}",
                      "record_note": "Computed from game results in the Wikipedia season articles (1986–87 through 2025–26); vacated games counted as played.",
                      "notable_games": notable(games), "sources": srcs + [S[str(y)]["url"] for y in sorted({g["season"] for g in notable(games)})][:12]})

# ---------------- nicknames & quotes ----------------
quotes = [
 {"text": "We shocked the world!", "who": "Khalid El-Amin", "when": "1999-03-29", "context": "Shouted into a courtside TV camera as UConn beat Duke for the 1999 national title.", "source": PROGRAM},
 {"text": "The Shot", "type": "nickname", "who": "Tate George", "when": "1990-03-22", "context": "Name for George's buzzer-beater (on Scott Burrell's full-court pass) that beat Clemson 71–70 in the 1990 Sweet Sixteen.", "source": PROGRAM},
 {"text": "The Dream Season", "type": "nickname", "when": "1989–90", "context": "The 31–6 team that won UConn's first Big East titles.", "source": PROGRAM},
 {"text": "Cardiac Kemba does it again!", "who": "Dave Pasch (ESPN)", "when": "2011-03-10", "context": "Call of Kemba Walker's step-back winner against Pittsburgh in the 2011 Big East quarterfinals.", "source": PROGRAM},
 {"text": "Five games in five days", "type": "nickname", "when": "2011-03-08 to 2011-03-12", "context": "UConn's unprecedented Big East tournament title run.", "source": PROGRAM},
 {"text": "You're looking at the hungry Huskies. This is what happens when you ban us.", "who": "Shabazz Napier", "when": "2014-04-07", "context": "After winning the 2014 title, a year after UConn's postseason ban.", "source": PROGRAM},
 {"text": "Better get us now. That's all, you better get us now. Because it's coming.", "who": "Dan Hurley", "when": "2020-01-18", "context": "After a 61–55 loss at No. 14 Villanova, foreshadowing UConn's return to power.", "source": PROGRAM},
 {"text": "Not a dime back!", "who": "Jim Calhoun", "when": "2009", "context": "Response to a question about his salary as Connecticut's highest-paid state employee; the fan blog \"A Dime Back\" took its name from it.", "source": url("Jim Calhoun")},
 {"text": "The dagger", "type": "nickname", "who": "Rashad Anderson", "context": "Jim Calhoun's nickname for Anderson because of his clutch shooting; Anderson retired as UConn's career three-point leader (276).", "source": url("Rashad Anderson")},
 {"text": "Rip", "type": "nickname", "who": "Richard Hamilton", "context": "Richard \"Rip\" Hamilton, 1999 Most Outstanding Player.", "source": PROGRAM},
 {"text": "Blue blood", "type": "nickname", "when": "2023", "context": "Status many analysts assigned UConn after its fifth national title.", "source": PROGRAM},
 {"text": "Back-to-Back", "type": "nickname", "when": "2024", "context": "UConn became the first repeat champion since Florida in 2007.", "source": PROGRAM},
 {"text": "Jonathan", "type": "mascot", "context": "Every UConn husky mascot is named Jonathan, after Jonathan Trumbull, Connecticut's last colonial and first state governor; the husky was chosen by a student poll in the 1930s.", "source": url("Jonathan (mascot)")},
 {"text": "One of the greatest shots in the history of the NCAA tournament.", "who": "Jeff Borzello (ESPN)", "when": "2026-03-29", "context": "On Braylon Mullins' game-winning three against Duke in the 2026 Elite Eight.", "source": url("Braylon Mullins")},
]

program_totals = {"ncaa_appearances": 39, "ncaa_record": "77–34 (excluding vacated 1996 games)", "final_fours": 8, "national_titles": 6,
                  "nit_titles": 1, "big_east_regular_season_titles": 11, "big_east_tournament_titles": 8, "aac_tournament_titles": 1,
                  "most_consecutive_wins_sweet16_or_later": "19 (2011–2026, NCAA record)", "source": PROGRAM}
ncaa_records = [
 "Best point differential in a single tournament: +140 (2024)", "Highest average margin of victory by a champion: 23.3 (2024)",
 "Most consecutive double-digit wins vs. non-conference opponents: 24 (2022–2024)", "Most games in a season since 1948: 41 (2011)",
 "Largest lead before opponent scores (D-I): 32–0 vs New Hampshire, Dec. 12, 1990",
 "Most different players with a three-pointer in one game: 10 vs Xavier, Jan. 28, 2024", "Most consecutive wins in the Sweet Sixteen or later: 19 (2011–2026)"]

save("legends.json", {"generated": "2026-09-30", "coaches": coaches, "national_championships": championships, "final_fours": final_fours,
      "huskies_of_honor": huskies_of_honor, "retired_numbers": retired,
      "all_americans": {"list": aa, "source": PROGRAM},
      "players_of_the_year": {"list": poy, "source": PROGRAM},
      "other_awards": {"by_award": other_awards, "source": PROGRAM},
      "nba_draft": {"first_round_since_1987": first_round, "all_picks": draft, "source": PROGRAM},
      "mcdonalds_all_americans": {"list": mcd, "note": "Players whose Wikipedia article lists McDonald's All-American selection; may be incomplete for players without that detail in their article.", "verify": True},
      "arenas": arenas, "rivalries": rivalries, "nicknames_and_quotes": quotes, "program_totals": program_totals,
      "ncaa_records": {"list": ncaa_records, "source": PROGRAM}})
print("coaches", len(coaches), "titles", len(championships), "HoH", len(hoh), "AA", len(aa), "POY", len(poy), "draft", len(draft), "1st rd", len(first_round), "mcd", len(mcd), "rivalries", [(r["opponent"], r["record_1986_87_to_2025_26"]) for r in rivalries])
print([ (h["name"],h["seasons"]) for h in hoh])
print([(m["player"], m["mcdonalds_year"], m["arrived_as"]) for m in mcd])

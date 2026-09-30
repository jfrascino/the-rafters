"""Fetch plaintext + wikitext of program-lore articles."""
import json, os
from media_common import wiki, CACHE, wiki_url

TITLES = ["UConn Huskies men's basketball", "Jim Calhoun", "Kevin Ollie", "Dan Hurley", "Harry A. Gampel Pavilion",
          "XL Center", "Syracuse–UConn rivalry", "Georgetown–UConn men's basketball rivalry", "Huskies of Honor",
          "UConn Huskies", "Tate George", "Ray Allen", "Kemba Walker", "Shabazz Napier", "Emeka Okafor", "Ben Gordon",
          "Richard Hamilton (basketball)", "Donyell Marshall", "Adama Sanogo", "Tristen Newton", "Donovan Clingan",
          "Khalid El-Amin", "Caron Butler", "Rudy Gay", "Hasheem Thabeet", "Chris Smith (basketball, born 1970)",
          "Clifford Robinson (basketball, born 1966)", "Scott Burrell", "Nadav Henefeld", "Jordan Hawkins", "Andre Jackson Jr.",
          "Alex Karaban", "Stephon Castle", "Cam Spencer", "Jeremy Lamb", "Alex Oriakhi", "Ryan Boatright", "A. J. Price",
          "Jerome Dyson", "Jeff Adrien", "Marcus Williams (basketball, born 1985)", "Josh Boone (basketball)", "Charlie Villanueva",
          "Hilton Armstrong", "Taliek Brown", "Rashad Anderson", "Denham Brown", "Travis Knight (basketball)", "Doron Sheffer",
          "Donny Marshall", "Kevin Freeman (basketball)", "Ricky Moore (basketball)", "Jake Voskuhl", "James Bouknight",
          "Andre Drummond", "Liam McNeeley", "Braylon Mullins", "Tarris Reed Jr.", "Solo Ball",
          "1999 NCAA Division I Men's Basketball Championship Game", "2004 NCAA Division I Men's Basketball Championship Game",
          "2011 NCAA Division I Men's Basketball Championship Game", "2014 NCAA Division I Men's Basketball Championship Game",
          "2023 NCAA Division I Men's Basketball Championship Game", "2024 NCAA Division I Men's Basketball Championship Game",
          "2026 NCAA Division I Men's Basketball Championship Game",
          "1999 NCAA Division I men's basketball tournament", "2004 NCAA Division I men's basketball tournament",
          "2011 NCAA Division I men's basketball tournament", "2014 NCAA Division I men's basketball tournament",
          "2023 NCAA Division I men's basketball tournament", "2024 NCAA Division I men's basketball tournament",
          "2026 NCAA Division I men's basketball tournament", "1990 NCAA Division I men's basketball tournament",
          "Big East Conference (1979–2013)", "Big East Conference", "American Athletic Conference", "Hartford Civic Center",
          "PeoplesBank Arena", "Kentucky–UConn rivalry", "Pittsburgh–UConn rivalry", "Duke–UConn rivalry", "Villanova–UConn rivalry",
          "Providence–UConn rivalry", "St. John's–UConn rivalry", "2009 Big East men's basketball tournament",
          "2011 Big East men's basketball tournament", "2008–09 Big East Conference men's basketball season",
          "Big East Conference Men's Basketball Player of the Year", "Big East Conference Men's Basketball Coach of the Year",
          "American Athletic Conference Men's Basketball Player of the Year", "NCAA basketball tournament Most Outstanding Player",
          "UConn Huskies men's basketball statistical leaders", "Kevin Ollie", "Karl Hobbs", "Howie Dickenman", "George Blaney",
          "Dom Perno", "Tom Moore (basketball coach)", "Luke Murray (basketball)", "Kimani Young", "Glen Miller (basketball)",
          "Dave Leitao", "Andre LaFleur", "Patrick Sellers", "Oregon Ducks men's basketball", "Rolling Thunder (UConn)",
          "Jonathan (mascot)", "UConn Huskies Marching Band", "Werth Family UConn Basketball Champions Center", "Freeman Williamson",
          ]
out = {}
titles = list(dict.fromkeys(TITLES))
for k in range(0, len(titles), 20):
    b = titles[k:k+20]
    d = wiki(action="query", titles="|".join(b), prop="revisions|info", rvprop="content", rvslots="main", redirects=1, inprop="url")
    red = {r["from"]: r["to"] for r in d["query"].get("redirects", [])}
    norm = {r["from"]: r["to"] for r in d["query"].get("normalized", [])}
    pages = {p["title"]: p for p in d["query"]["pages"]}
    for t in b:
        tt = red.get(norm.get(t, t), norm.get(t, t))
        p = pages.get(tt)
        if not p or p.get("missing"):
            print("MISSING", t); continue
        wt = p["revisions"][0]["slots"]["main"]["content"]
        out[t] = {"title": p["title"], "url": p.get("fullurl") or wiki_url(p["title"]), "wikitext": wt}
    print(k, flush=True)
json.dump(out, open(os.path.join(CACHE, "lore_raw.json"), "w"), ensure_ascii=False)
print("saved", len(out))

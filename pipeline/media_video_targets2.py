"""Second batch of video targets: iconic regular-season games, moments, documentaries, legend profiles,
plus retries for NCAA games that found nothing. -> cache.nosync/media/video_targets2.json"""
import json, os
from media_common import CACHE
sched = json.load(open(os.path.join(CACHE, "schedules_parsed.json")))
picks = json.load(open(os.path.join(CACHE, "video_picks.json")))

def game(y, date, note, extra_q=None, must=None):
    for g in sched[y]["games"]:
        if g["date"] == date:
            t = {"season": int(y), "date": date, "opponent": g["opponent"], "round": note, "result": g["result"],
                 "uconn": g["uconn"], "opp_score": g["opp_score"], "ot": g["ot"], "site": g["site"], "target_kind": "iconic",
                 "wiki": sched[y]["url"]}
            yr = date[:4]
            t["queries"] = [f"UConn vs {g['opponent']} {yr}", f"Connecticut {g['opponent']} {yr} basketball {note}"] + (extra_q or [])
            if must: t["must_any"] = must
            return t
    raise SystemExit(f"not found {y} {date}")

T = [
 game("1990", "1990-01-27", "First game at Gampel Pavilion", ["UConn St. John's 1990 Gampel Pavilion first game"]),
 game("1990", "1990-01-20", "Regular season", ["UConn Georgetown 1990 Hartford Civic Center"]),
 game("1990", "1990-01-15", "Regular season", ["UConn Syracuse 1990 Hartford"]),
 game("1995", "1994-11-29", "Regular season", ["UConn Duke 1994 Ray Allen"]),
 game("1999", "1999-02-06", "Regular season", ["UConn Stanford 1999 Hamilton"]),
 game("2000", "1999-12-07", "Regular season", ["UConn Arizona 1999 El-Amin"]),
 game("2000", "1999-11-12", "Coaches vs. Cancer Classic", ["UConn Duke 1999 Coaches vs Cancer"]),
 game("2002", "2002-01-26", "Regular season", ["UConn Arizona 2002 overtime Caron Butler"]),
 game("2004", "2004-01-11", "Regular season", ["UConn Oklahoma 2004 Gampel"]),
 game("2005", "2005-03-02", "Calhoun's 700th win", ["Jim Calhoun 700th win Georgetown 2005"]),
 game("2006", "2005-11-23", "Maui Invitational Final", ["UConn Gonzaga 2005 Maui Denham Brown"]),
 game("2009", "2008-12-20", "Battle in Seattle", ["UConn Gonzaga 2008 Seattle A.J. Price overtime"]),
 game("2009", "2009-02-25", "Calhoun's 800th win", ["Jim Calhoun 800th win Marquette 2009"]),
 game("2010", "2010-01-23", "Regular season vs No. 1", ["UConn upsets #1 Texas 2010"]),
 game("2011", "2010-11-23", "Maui Invitational Semifinal", ["UConn Michigan State Maui 2010 Kemba"]),
 game("2011", "2010-11-24", "Maui Invitational Final", ["UConn Kentucky Maui 2010 Kemba Walker"]),
 game("2011", "2011-01-08", "Regular season", ["Kemba Walker game winner Texas 2011"]),
 game("2013", "2012-11-09", "Armed Forces Classic (Ollie's first game)", ["UConn Michigan State Ramstein Germany 2012"]),
 game("2014", "2013-12-02", "Regular season", ["Shabazz Napier buzzer beater Florida 2013"]),
 game("2014", "2013-11-22", "2K Sports Classic Championship", ["UConn Indiana 2K Sports Classic 2013"]),
 game("2019", "2018-11-15", "2K Sports Classic Semifinal", ["UConn Syracuse 2018 2K Classic Hurley"]),
 game("2020", "2019-11-17", "Regular season", ["UConn Florida 2019 Gampel upset"]),
 game("2022", "2021-11-24", "Battle 4 Atlantis Quarterfinal", ["UConn Auburn double overtime Bahamas 2021"]),
 game("2022", "2022-02-22", "Regular season", ["UConn Villanova 2022 XL Center"]),
 game("2023", "2022-11-27", "Phil Knight Invitational Championship", ["UConn Iowa State Phil Knight Invitational 2022"]),
 game("2023", "2022-11-25", "Phil Knight Invitational Semifinal", ["UConn Alabama Phil Knight 2022"]),
 game("2024", "2023-11-20", "Empire Classic Championship", ["UConn Texas Empire Classic 2023"]),
 game("2024", "2023-12-05", "Jimmy V Classic", ["UConn North Carolina Jimmy V 2023"]),
 game("2024", "2023-12-15", "Regular season", ["UConn Gonzaga Madison Square Garden 2023"]),
 game("2024", "2024-02-17", "Regular season", ["UConn Marquette February 2024"]),
 game("2025", "2024-12-14", "Regular season", ["UConn Gonzaga 2024 McNeeley"]),
 game("2025", "2025-02-11", "Regular season", ["Liam McNeeley 38 points Creighton"]),
 game("2025", "2024-11-25", "Maui Invitational First Round", ["UConn Memphis Maui 2024 overtime"]),
 game("2026", "2025-11-15", "Hall of Fame Series Boston", ["UConn BYU TD Garden 2025"]),
 game("2026", "2025-12-02", "Regular season", ["UConn Kansas Allen Fieldhouse 2025"]),
 game("2026", "2025-12-09", "Jimmy V Classic", ["UConn Florida Jimmy V 2025"]),
 game("2026", "2026-02-18", "Emeka Okafor jersey retirement game", ["Emeka Okafor jersey retirement UConn"], None),
]
# retries for NCAA/BET games with no picks: alternate phrasing
for e in picks:
    if e["picks"]: continue
    t = dict(e["target"]); y = t["season"]; o = t["opponent"]
    t["queries"] = [f"{y} NCAA tournament {o} Connecticut", f"{o} vs Connecticut {y}", f"UConn {o} March {y}"]
    if "Big East" in t["round"]:
        t["queries"] = [f"{y} Big East championship Pittsburgh Connecticut", f"Pitt UConn Big East final {y}"]
    if t["round"] == "Regular Season":
        continue
    T.append(t)

def moment(season, title, queries, must, kind_hint="moment", date=None, players=None):
    return {"season": season, "date": date or "", "opponent": None, "round": title, "target_kind": kind_hint,
            "queries": queries, "must_any": must, "players": players or []}

T += [
 moment(1990, "Tate George 'The Shot' vs Clemson", ["Tate George The Shot Clemson 1990", "Tate George buzzer beater Clemson"], ["tate george", "the shot"], date="1990-03-22", players=["Tate George", "Scott Burrell"]),
 moment(1990, "Christian Laettner beats UConn 1990", ["Laettner buzzer beater UConn 1990 Elite Eight"], ["laettner"], date="1990-03-24"),
 moment(1996, "Ray Allen game-winner vs Georgetown, 1996 Big East final", ["Ray Allen game winner Georgetown 1996 Big East championship"], ["ray allen"], date="1996-03-09", players=["Ray Allen"]),
 moment(1998, "Rip Hamilton buzzer-beater vs Washington", ["Richard Hamilton buzzer beater Washington 1998", "Rip Hamilton game winner 1998 Sweet 16"], ["hamilton", "rip"], date="1998-03-19", players=["Richard Hamilton"]),
 moment(1999, "Khalid El-Amin: 'We shocked the world!'", ["We shocked the world El-Amin 1999", "Khalid El-Amin we shocked the world"], ["shock", "el-amin", "el amin"], date="1999-03-29", players=["Khalid El-Amin"]),
 moment(1999, "One Shining Moment 1999", ["One Shining Moment 1999 CBS"], ["one shining moment"], "highlights", date="1999-03-29"),
 moment(2004, "One Shining Moment 2004", ["One Shining Moment 2004"], ["one shining moment"], "highlights", date="2004-04-05"),
 moment(2011, "One Shining Moment 2011", ["One Shining Moment 2011"], ["one shining moment"], "highlights", date="2011-04-04"),
 moment(2014, "One Shining Moment 2014", ["One Shining Moment 2014"], ["one shining moment"], "highlights", date="2014-04-07"),
 moment(2023, "One Shining Moment 2023", ["One Shining Moment 2023"], ["one shining moment"], "highlights", date="2023-04-03"),
 moment(2024, "One Shining Moment 2024", ["One Shining Moment 2024"], ["one shining moment"], "highlights", date="2024-04-08"),
 moment(2026, "One Shining Moment 2026", ["One Shining Moment 2026"], ["one shining moment"], "highlights", date="2026-04-06"),
 moment(2011, "Kemba Walker step-back beats Pitt ('Cardiac Kemba')", ["Kemba Walker step back Pitt Big East tournament 2011", "Cardiac Kemba does it again"], ["kemba"], date="2011-03-10", players=["Kemba Walker"]),
 moment(2011, "Kemba Walker game-winner at Texas", ["Kemba Walker game winner at Texas 2011 overtime"], ["kemba"], date="2011-01-08", players=["Kemba Walker"]),
 moment(2014, "Shabazz Napier: 'Hungry Huskies' speech", ["Shabazz Napier hungry huskies this is what happens when you ban us"], ["napier", "hungry"], date="2014-04-07", players=["Shabazz Napier"]),
 moment(2014, "Shabazz Napier buzzer-beater vs Florida", ["Shabazz Napier game winner Florida buzzer 2013"], ["napier"], date="2013-12-02", players=["Shabazz Napier"]),
 moment(2016, "Jalen Adams three-quarter-court shot vs Cincinnati", ["Jalen Adams half court shot Cincinnati 4OT", "Jalen Adams buzzer beater Cincinnati AAC"], ["jalen adams", "adams"], date="2016-03-11", players=["Jalen Adams"]),
 moment(2009, "Six-overtime classic vs Syracuse", ["Syracuse UConn six overtime 2009 Big East", "6 OT Syracuse UConn"], ["overtime", "6 ot", "6ot", "six"], date="2009-03-12"),
 moment(2026, "Braylon Mullins' shot beats Duke", ["Braylon Mullins game winner Duke", "Braylon Mullins logo three Duke Elite Eight"], ["mullins"], date="2026-03-29", players=["Braylon Mullins", "Silas Demary Jr.", "Alex Karaban"]),
 moment(2024, "Illinois 30–0 run", ["UConn 30-0 run Illinois Elite Eight"], ["30-0", "30–0"], date="2024-03-30"),
 moment(2023, "UConn cuts down the nets in Houston", ["UConn celebration national championship 2023 nets"], ["2023"], "moment", date="2023-04-03"),
 moment(2024, "Hurley and UConn celebrate back-to-back", ["UConn back to back celebration 2024 Hurley"], ["back-to-back", "back to back", "repeat"], "moment", date="2024-04-08"),
 moment(1999, "1999 championship parade", ["UConn 1999 championship parade Hartford"], ["parade"], "moment"),
 moment(2004, "2004 championship parade", ["UConn 2004 championship parade Hartford"], ["parade"], "moment"),
 moment(2011, "2011 championship parade", ["UConn 2011 parade Hartford Kemba"], ["parade"], "moment"),
 moment(2014, "2014 championship parade", ["UConn 2014 championship parade Hartford"], ["parade"], "moment"),
 moment(2023, "2023 championship parade", ["UConn 2023 championship parade Hartford"], ["parade"], "moment"),
 moment(2024, "2024 championship parade", ["UConn 2024 championship parade Hartford"], ["parade"], "moment"),
 moment(2024, "White House visit, September 2024", ["UConn men's basketball White House 2024 Biden"], ["white house"], "moment", date="2024-09"),
 moment(2014, "White House visit 2014", ["UConn Huskies White House Obama 2014"], ["white house", "obama"], "moment"),
 moment(2019, "Ray Allen jersey retirement ceremony", ["Ray Allen jersey retirement UConn 2019"], ["ray allen"], "moment", date="2019-03-03", players=["Ray Allen"]),
 moment(2024, "Richard Hamilton jersey retirement", ["Rip Hamilton jersey retirement UConn 2024"], ["hamilton"], "moment", date="2024-02-24", players=["Richard Hamilton"]),
 moment(2026, "Emeka Okafor jersey retirement", ["Emeka Okafor number 50 retired UConn"], ["okafor"], "moment", date="2026-02-18", players=["Emeka Okafor"]),
 moment(2026, "Alex Karaban inducted into Huskies of Honor", ["Alex Karaban Huskies of Honor"], ["karaban"], "moment", date="2026-02-28", players=["Alex Karaban"]),
 moment(2007, "Huskies of Honor inaugural ceremony", ["UConn Huskies of Honor ceremony 2007"], ["huskies of honor"], "moment", date="2007-02-05"),
 moment(2013, "Jim Calhoun retirement press conference", ["Jim Calhoun retirement press conference 2012"], ["calhoun"], "interview", date="2012-09-13", players=[]),
 moment(2006, "Jim Calhoun Hall of Fame enshrinement", ["Jim Calhoun Hall of Fame speech 2005"], ["calhoun"], "interview", date="2005-09"),
 moment(2019, "Dan Hurley introduced as UConn coach", ["Dan Hurley introductory press conference UConn 2018"], ["hurley"], "interview", date="2018-03-23"),
 moment(2020, "Hurley: 'You better get us now'", ["Dan Hurley better get us now Villanova 2020"], ["hurley"], "interview", date="2020-01-18"),
 moment(2013, "Kevin Ollie named head coach", ["Kevin Ollie named UConn head coach 2012"], ["ollie"], "interview", date="2012-09-13"),
 # documentaries / features
 moment(0, "Jim Calhoun documentary / profile", ["Jim Calhoun documentary", "E:60 Calhoun Project", "Jim Calhoun career tribute UConn"], ["calhoun"], "documentary"),
 moment(0, "UConn basketball history documentary", ["UConn men's basketball history documentary", "how UConn became a basketball powerhouse"], ["uconn"], "documentary"),
 moment(1999, "1999 championship retrospective", ["1999 UConn national championship team documentary", "UConn 1999 title 25 years later"], ["1999"], "documentary"),
 moment(2004, "2004 championship retrospective", ["2004 UConn national championship documentary Okafor Gordon"], ["2004"], "documentary"),
 moment(2011, "2011 title run feature", ["Kemba Walker 2011 UConn run documentary", "UConn 11 straight 2011 documentary"], ["kemba", "2011"], "documentary"),
 moment(2014, "2014 title run feature", ["Shabazz Napier 2014 UConn documentary", "UConn 2014 hungry huskies documentary"], ["2014", "napier"], "documentary"),
 moment(2023, "2023 title run feature", ["UConn 2023 national championship documentary", "UConn 2023 season documentary"], ["2023"], "documentary"),
 moment(2024, "Back-to-back feature", ["UConn back to back documentary 2024", "UConn 2024 national champions documentary"], ["2024", "back"], "documentary"),
 moment(2024, "Dan Hurley profile", ["Dan Hurley documentary UConn", "Dan Hurley feature ESPN"], ["hurley"], "documentary"),
 moment(1990, "The Dream Season retrospective", ["UConn 1990 dream season", "UConn Dream Season documentary 1990"], ["dream season", "1990"], "documentary"),
]
LEGENDS = [("Ray Allen", 1996), ("Richard Hamilton", 1999), ("Emeka Okafor", 2004), ("Ben Gordon", 2004), ("Kemba Walker", 2011),
           ("Shabazz Napier", 2014), ("Donyell Marshall", 1994), ("Caron Butler", 2002), ("Rudy Gay", 2006), ("Hasheem Thabeet", 2009),
           ("Khalid El-Amin", 1999), ("Chris Smith", 1992), ("Cliff Robinson", 1989), ("Andre Drummond", 2012), ("Jeremy Lamb", 2012),
           ("Adama Sanogo", 2023), ("Jordan Hawkins", 2023), ("Tristen Newton", 2024), ("Donovan Clingan", 2024), ("Stephon Castle", 2024),
           ("Alex Karaban", 2026), ("Tarris Reed", 2026), ("James Bouknight", 2021), ("Charlie Villanueva", 2005), ("A.J. Price", 2009),
           ("Scott Burrell", 1993), ("Tate George", 1990), ("Nadav Henefeld", 1990), ("Cam Spencer", 2024), ("Liam McNeeley", 2025)]
for name, yr in LEGENDS:
    last = name.split()[-1].lower()
    T.append(moment(yr, f"{name} UConn career highlights", [f"{name} UConn highlights", f"{name} UConn career"], [last], "highlights", players=[name]))
json.dump(T, open(os.path.join(CACHE, "video_targets2.json"), "w"), indent=1, ensure_ascii=False)
print(len(T))

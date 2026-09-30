"""Hand-written season narratives for the UConn men's basketball super-fan app.

Every fact below was taken from pages fetched into pipeline/cache.nosync/media (Wikipedia season articles,
the "UConn Huskies men's basketball" program article, coach/player articles, uconnhuskies.com).
Each season lists the extra source URLs (beyond its own season article) that its story relies on.
"""

W = "https://en.wikipedia.org/wiki/"
PROGRAM = W + "UConn_Huskies_men%27s_basketball"
CALHOUN = W + "Jim_Calhoun"
OLLIE = W + "Kevin_Ollie"
HURLEY = W + "Dan_Hurley"
GAMPEL = W + "Harry_A._Gampel_Pavilion"

STORIES = {
1987: {
 "headline": "Calhoun Arrives, and the Rebuild Begins",
 "story": (
  "UConn hired Jim Calhoun away from Northeastern on May 14, 1986, after 14 seasons in Boston in which his Huskies reached the "
  "NCAA tournament five times in his last six years. The new coach inherited a program coming off four straight losing seasons "
  "and a roster built around future NBA big man Clifford Robinson. Then the floor dropped out: halfway through the year Robinson "
  "and fellow starter Phil Gamble were ruled academically ineligible. Playing home games at the Field House in Storrs, the "
  "Hartford Civic Center and the New Haven Coliseum, UConn scratched out wins such as a 96–94 overtime decision over Rhode Island "
  "and a 56–54 finale over Seton Hall, but finished 9–19 and 3–13 in the Big East. The year ended with a 61–59 loss to Boston "
  "College in the first round of the Big East tournament. It would be the only losing season of Calhoun's 26 years in Storrs."),
 "sources": [PROGRAM, CALHOUN],
},
1988: {
 "headline": "NIT Champions: The First Trophy",
 "story": (
  "With Clifford Robinson and Phil Gamble academically eligible again, Calhoun's second team showed what was coming. The Huskies "
  "stunned No. 9 Syracuse 51–50 inside the Carrier Dome in January and beat No. 14 Georgetown 66–59 in Hartford. A 75–62 win over "
  "Providence gave UConn its first Big East tournament victory since 1980, and an NIT bid followed. The Huskies won at West "
  "Virginia in overtime, beat Louisiana Tech in Hartford and VCU at the Field House, then took over Madison Square Garden: 73–67 "
  "over Boston College in the semifinals and 72–67 over Ohio State in the March 30 final. It was the school's first national "
  "basketball title, Robinson made the all-tournament team, and the 20–14 record was UConn's first winning season since 1981–82. "
  "The Huskies would post a winning record every year from here through 2015–16."),
 "sources": [PROGRAM, W + "Clifford_Robinson_(basketball,_born_1966)"],
},
1989: {
 "headline": "Knocking on the Door",
 "story": (
  "Calhoun's third team took another step, going 18–13 overall and 6–10 in a brutal Big East. The signature night came on January "
  "16, 1989, when UConn beat No. 11 Syracuse 68–62 at the Hartford Civic Center. Clifford Robinson, in his final season, earned "
  "second-team All-Big East honors. After a 74–66 loss to Seton Hall in the Big East quarterfinals, the Huskies returned to the NIT "
  "and won twice more — 67–62 at Charlotte and a 73–72 thriller over California in Hartford — before UAB ended the run 85–79 in the "
  "quarterfinals at the Field House. Robinson went to the Portland Trail Blazers with the 36th pick of the 1989 NBA draft. The "
  "foundation was set; the breakthrough was one season away."),
 "sources": [PROGRAM],
},
1990: {
 "headline": "The Dream Season",
 "story": (
  "Unranked in the preseason, the 1989–90 Huskies became the team that put UConn basketball on the national map. Led by Chris "
  "Smith, Israeli freshman Nadav Henefeld, Scott Burrell, Tate George and Rod Sellers, UConn beat No. 5 Syracuse and No. 2 "
  "Georgetown in back-to-back games at the Hartford Civic Center in January and cracked the AP poll for the first time. Days later "
  "the new Gampel Pavilion opened, and the Huskies christened it with a 72–58 win over No. 15 St. John's on January 27. UConn won "
  "a share of the Big East regular-season title, then beat Seton Hall, Georgetown and Syracuse (78–75) at Madison Square Garden for "
  "its first Big East tournament crown. As a No. 1 seed in the East, UConn routed Boston University and California before Burrell's "
  "full-court pass found George for a buzzer-beater that beat Clemson 71–70 — forever known in Connecticut as \"The Shot.\" Two "
  "days later, Duke ended the dream on a buzzer-beater of its own, 79–78 in overtime. UConn finished 31–6, and Calhoun was the "
  "consensus national coach of the year."),
 "sources": [PROGRAM, CALHOUN, W + "Tate_George", GAMPEL, W + "Nadav_Henefeld", W + "Scott_Burrell"],
},
1991: {
 "headline": "Back to the Sweet Sixteen",
 "story": (
  "The encore to the Dream Season was a 20–11 team that proved 1990 was no fluke. Chris Smith and Scott Burrell carried the "
  "Huskies to wins over No. 11 Pittsburgh, No. 20 Georgetown and No. 20 Seton Hall (in overtime), and UConn went 9–7 in the Big "
  "East. Georgetown ended the Huskies' conference tournament in the quarterfinals, 68–49, but UConn earned a second straight NCAA "
  "bid and made it count, beating LSU 79–62 and Xavier 66–50 to reach the Sweet Sixteen for the second year in a row. Once again "
  "Duke stood in the way, and this time the Blue Devils won comfortably, 81–67. Smith was second-team All-Big East and an AP "
  "honorable-mention All-American; Burrell made the third team. In their first full season in Gampel Pavilion, the "
  "Huskies went 7–2 on their new home floor."),
 "sources": [PROGRAM],
},
1992: {
 "headline": "Chris Smith Writes the Record Book",
 "story": (
  "Bridgeport's own Chris Smith closed his career as UConn's all-time leading scorer with 2,145 points, earning first-team "
  "All-Big East honors as a senior. The Huskies went 20–10 (10–8 Big East), beating No. 23 Wake Forest, No. 17 St. John's and No. "
  "21 Syracuse along the way, while freshman Donyell Marshall made the Big East All-Freshman team and Scott Burrell was second-team "
  "All-Big East. St. John's knocked UConn out of the Big East tournament in overtime, 64–59, but the Huskies returned to the NCAA "
  "tournament and crushed Nebraska 86–65 before Ohio State ended the season 78–55 in the second round. Smith, who also left as the "
  "school's career leader in three-pointers with 242, was drafted 34th overall by the Minnesota Timberwolves."),
 "sources": [PROGRAM, W + "Chris_Smith_(basketball,_born_1970)"],
},
1993: {
 "headline": "A Pause Before the Surge",
 "story": (
  "The 1992–93 Huskies slipped to 15–13 and 9–9 in the Big East, the lone non-NCAA season between 1990 and 1996. There were "
  "moments — an 81–80 win at No. 17 Pittsburgh in February chief among them — and Donyell Marshall blossomed into a first-team "
  "All-Big East forward. But Providence ended UConn's Big East tournament in the quarterfinals, 73–55, and the NIT trip lasted one "
  "night: a 90–88 overtime loss to Jackson State. Senior Scott Burrell, the first player in NCAA history to compile 1,500 points, "
  "750 rebounds, 275 assists and 300 steals, went 20th overall to the Charlotte Hornets in the 1993 NBA draft — "
  "a two-sport star who had also been drafted by baseball's Toronto Blue Jays and spent two summers in the minor leagues."),
 "sources": [PROGRAM, W + "Scott_Burrell"],
},
1994: {
 "headline": "Donyell Marshall's Big East",
 "story": (
  "With junior Donyell Marshall at the peak of his powers and freshmen Ray Allen and Doron Sheffer arriving, UConn went 29–5 and "
  "16–2 to win the Big East regular-season title. Marshall was the unanimous Big East Player of the Year, the league's Defensive "
  "Player of the Year and a consensus first-team All-American; Sheffer was Big East Rookie of the Year and Allen made the "
  "All-Freshman team, while Calhoun won Big East Coach of the Year. The Huskies rose as high as No. 2, highlighted by a 77–36 "
  "demolition at No. 12 Virginia. Providence edged UConn 69–67 in the Big East semifinals, but the Huskies beat Rider and George "
  "Washington to reach the Sweet Sixteen, where Florida won 69–60 in overtime. Marshall left for the NBA as the No. 4 overall pick."),
 "sources": [PROGRAM, W + "Donyell_Marshall", W + "Ray_Allen", W + "Doron_Sheffer"],
},
1995: {
 "headline": "Ray Allen Takes Flight",
 "story": (
  "Sophomore Ray Allen became a star — 21.1 points per game and first-team All-Big East — and UConn became a juggernaut. The "
  "Huskies opened with a 90–86 win over No. 8 Duke, reeled off a 15-game winning streak, climbed to No. 1, and went 16–2 to "
  "repeat as Big East regular-season champions, sweeping Syracuse along the way. In the Big East tournament UConn beat Pittsburgh "
  "and Georgetown before Villanova won the final 94–78. As a No. 2 seed in the West, the Huskies beat Chattanooga, Cincinnati and "
  "Maryland — senior Donny Marshall averaged more than 24 points in the tournament — before falling to top-seeded UCLA 102–96 in the "
  "Elite Eight. Guard Kevin Ollie, a future UConn head coach, made third-team All-Big East."),
 "sources": [PROGRAM, W + "Ray_Allen", W + "Donny_Marshall"],
},
1996: {
 "headline": "Ray Allen's Big East Masterpiece",
 "story": (
  "The 1995–96 Huskies won 23 straight games, went 17–1 in the Big East for a third consecutive regular-season title, and "
  "delivered one of the greatest finishes in Big East tournament history. Trailing Georgetown 74–63 with four minutes left in the "
  "championship game at Madison Square Garden, UConn closed on a 12–0 run capped by Ray Allen's off-balance winner with 14 seconds "
  "to go, 75–74. Allen was named Big East Player of the Year and a consensus first-team All-American, and Calhoun was Big East "
  "Coach of the Year. In the NCAA tournament UConn beat Colgate and Eastern Michigan before Mississippi State ended the season 60–55 "
  "in the Sweet Sixteen; the NCAA later vacated UConn's 1996 tournament games after two players were ruled ineligible. Allen went "
  "fifth overall in the 1996 draft, with Travis Knight (29th) and Sheffer (36th) also selected."),
 "sources": [PROGRAM, CALHOUN, W + "Ray_Allen"],
},
1997: {
 "headline": "Rip Hamilton's Rookie Year",
 "story": (
  "With Allen, Sheffer and Knight gone to the pros, UConn regrouped around freshman Richard \"Rip\" Hamilton, who made the Big "
  "East All-Freshman team. The Huskies went 18–15 and 7–11 in the league, and a 63–62 loss to Pittsburgh ended their Big East "
  "tournament in the first round. Earlier, the Huskies had beaten No. 20 Boston College 61–54. The NIT offered a stage to grow: UConn beat Iona, Bradley and "
  "Nebraska in three home games at Gampel Pavilion to reach Madison Square Garden, lost a 71–66 semifinal to Florida State, then beat Arkansas 74–64 to finish third. The young core — Hamilton, Ricky "
  "Moore, Kevin Freeman and Jake Voskuhl — would be back, and within two years it would be champion of the entire sport."),
 "sources": [PROGRAM],
},
1998: {
 "headline": "Rip's Buzzer-Beater, Elite Eight Again",
 "story": (
  "Freshman point guard Khalid El-Amin joined Rip Hamilton, and UConn roared to 32–5, won its Big East division and captured the "
  "Big East tournament, beating Syracuse 69–54 in the final. Hamilton was Big East Player of the Year and a consensus second-team "
  "All-American; El-Amin was Big East Rookie of the Year and tournament MVP; Calhoun won Big East Coach of the Year again. In the "
  "NCAA tournament UConn dispatched Fairleigh Dickinson and Indiana, then produced an unforgettable Sweet Sixteen finish: down 74–73 "
  "to Washington, the Huskies got three shots in the final 15 seconds, and Hamilton rebounded a Jake Voskuhl miss, then his own, "
  "before hitting the winner at the horn, 75–74. North Carolina ended the run in the Elite Eight, 75–64."),
 "sources": [PROGRAM, W + "Richard_Hamilton_(basketball)", W + "Khalid_El-Amin"],
},
1999: {
 "headline": "We Shocked the World",
 "story": (
  "Rip Hamilton passed on the NBA, the entire starting five returned, and UConn started 19–0, holding the No. 1 ranking for a "
  "program-record 10 weeks. The first loss came February 1 to Syracuse in Hartford with Hamilton and center Jake Voskuhl injured, "
  "and the Huskies answered by winning 70–59 at No. 4 Stanford. They won the Big East regular season and beat St. John's 82–63 for "
  "the conference tournament title, with Kevin Freeman named MVP. As the No. 1 seed in the West, UConn beat UTSA, New Mexico and "
  "Iowa, then Gonzaga 67–62 for the program's first Final Four. After a 64–58 semifinal win over Ohio State in St. Petersburg, "
  "roughly nine-point underdogs UConn beat top-ranked Duke 77–74 on March 29, 1999. Hamilton scored 27 and was named Most "
  "Outstanding Player, El-Amin scored UConn's final four points, Ricky Moore hounded Duke's guards — and as time expired El-Amin "
  "shouted into a TV camera: \"We shocked the world!\" The 34–2 record remains the best winning percentage in program history."),
 "sources": [PROGRAM, CALHOUN, W + "Richard_Hamilton_(basketball)", W + "Khalid_El-Amin", W + "Ricky_Moore_(basketball)", W + "Kevin_Freeman_(basketball)"],
},
2000: {
 "headline": "Defending Champs, Early No. 1",
 "story": (
  "The defending champions opened 1999–2000 ranked No. 1 and beat No. 10 Duke and No. 2 Arizona early. Khalid El-Amin, now the "
  "leader, averaged 16.0 points, earned first-team All-Big East honors, became a Naismith Award finalist and set a Big East record "
  "by making 93.4 percent of his free throws in league play; his career-high 34 points came in a 75–70 loss at Notre Dame that "
  "snapped a 10-game winning streak. UConn went 25–10 (10–6 Big East) and reached the Big East tournament final with wins over "
  "Boston College, Seton Hall and Georgetown before St. John's won the title game 80–70. In the NCAA tournament the Huskies beat "
  "Utah State 75–67, then fell to Tennessee 65–51 in the second round. El-Amin and Voskuhl went back-to-back to the Chicago Bulls "
  "in the 2000 draft."),
 "sources": [PROGRAM, W + "Khalid_El-Amin"],
},
2001: {
 "headline": "Enter Caron Butler",
 "story": (
  "A retooled roster leaned on freshman Caron Butler, who led the Huskies in scoring (15.3) and rebounding (7.6) and made the Big "
  "East All-Freshman team, and on freshman point guard Taliek Brown, who started every game. UConn beat No. 5 Arizona 71–69, No. "
  "9 Boston College 82–71 — Brown scored 21 that night — and No. 13 Notre Dame 75–59, but finished just 20–12 and 8–8 in the Big "
  "East. Syracuse ended the Huskies' Big East tournament in the first round, 86–75, sending UConn to the NIT, where it beat South "
  "Carolina 72–65 before losing to Detroit 67–61. Brown also dished a season-best 12 assists in an overtime win over St. John's, and the Huskies went 8–1 at Gampel. "
  "It was the program's only NIT trip between 1998 and 2009."),
 "sources": [PROGRAM, W + "Caron_Butler", W + "Taliek_Brown"],
},
2002: {
 "headline": "Caron Butler's Big East Crown",
 "story": (
  "Sophomore Caron Butler averaged 20.3 points and 7.5 rebounds and carried UConn to a 27–7 season, the Big East East Division "
  "title and the Big East tournament crown. Freshman Ben Gordon hit the game-winning three against Villanova in the quarterfinals, "
  "UConn beat Notre Dame in the semis, and the Huskies outlasted Pittsburgh 74–65 in double overtime in the final. Butler was "
  "tournament MVP and shared Big East Player of the Year with Pitt's Brandin Knight. Earlier the Huskies had won 100–98 in overtime "
  "at No. 10 Arizona. As a No. 2 seed, UConn beat Hampton, NC State and Southern Illinois before Butler's 32 points weren't enough "
  "in a 90–82 Elite Eight loss to eventual national champion Maryland. Butler went 10th overall to the Miami Heat, while freshmen "
  "Emeka Okafor and Ben Gordon made the All-Freshman team."),
 "sources": [PROGRAM, W + "Caron_Butler", W + "Ben_Gordon"],
},
2003: {
 "headline": "Calhoun's Courage, Okafor's Rise",
 "story": (
  "On February 3, 2003, Jim Calhoun announced he had prostate cancer; he had surgery three days later and was back on the sideline "
  "against St. John's at Gampel Pavilion only 16 days after the operation. Around him a future champion was taking shape. Sophomore "
  "Emeka Okafor was the national and Big East Defensive Player of the Year and first-team All-Big East, and Ben Gordon made the "
  "second team. UConn (23–10, 10–6) shared the Big East East Division title, won at No. 9 Notre Dame 87–79, and beat Seton Hall "
  "and Syracuse at the Garden before Pittsburgh won the Big East final 74–56. As a No. 5 seed the Huskies beat BYU and Stanford, "
  "then lost a Sweet Sixteen shootout to top-seeded Texas, 82–78. Every starter would return."),
 "sources": [PROGRAM, CALHOUN, W + "Emeka_Okafor", W + "Ben_Gordon"],
},
2004: {
 "headline": "Calhoun's Best Team Wins It All",
 "story": (
  "Preseason No. 1 with its whole starting lineup back, UConn stumbled against Georgia Tech in the Preseason NIT, then won 11 "
  "straight, including an 86–59 rout of No. 7 Oklahoma at Gampel. The Huskies finished second in the Big East, then won the "
  "tournament, beating top-seeded Pittsburgh 61–58 in the final as Ben Gordon set a scoring record and took MVP honors. As a No. 2 "
  "seed they beat Vermont, DePaul, Vanderbilt and Alabama — Rashad Anderson hit six threes and scored 28 in the regional final — "
  "then rallied from eight down with three minutes left to stun Duke 79–78 in the Final Four. On April 5 in San Antonio, UConn beat "
  "Georgia Tech 82–73 for its second national title. Emeka Okafor, battling back problems all season, was Most Outstanding Player, "
  "Big East Player of the Year and national defensive player of the year. A night later the UConn women also won, making UConn the "
  "first school to sweep both titles. Okafor and Gordon went No. 2 and No. 3 in the draft; Calhoun called it the best team he ever "
  "coached."),
 "sources": [PROGRAM, CALHOUN, W + "Emeka_Okafor", W + "Ben_Gordon", W + "Rashad_Anderson"],
},
2005: {
 "headline": "Calhoun's 700th, a Hall of Fame Year",
 "story": (
  "After losing two top-three draft picks, UConn reloaded around sophomore Charlie Villanueva (13.6 points, 8.3 rebounds), Big "
  "East Defensive Player of the Year Josh Boone, Big East Most Improved Player Marcus Williams and Big East Rookie of the Year Rudy "
  "Gay. The Huskies went 23–8 and 13–3 to share the Big East regular-season title, and on March 2, 2005, Jim Calhoun earned his "
  "700th career win against Georgetown at Gampel Pavilion. Syracuse edged UConn 67–63 in the Big East semifinals. As a No. 2 seed "
  "in Worcester, the Huskies beat Central Florida before NC State upset them 65–62 in the second round. Villanueva left for the NBA "
  "as the seventh overall pick — and later that year Calhoun was inducted into the Naismith Memorial Basketball Hall of Fame."),
 "sources": [PROGRAM, CALHOUN, W + "Charlie_Villanueva", W + "Josh_Boone_(basketball)"],
},
2006: {
 "headline": "So Close: George Mason Stuns No. 1 Seed",
 "story": (
  "Loaded with future pros, UConn won the Maui Invitational on Denham Brown's last-second jumper against Gonzaga, spent weeks at "
  "No. 1 and went 30–4, sharing the Big East regular-season title at 14–2. Marcus Williams, suspended for several months after a "
  "stolen-laptop case, returned to run the offense; Rudy Gay was first-team All-Big East and a consensus second-team All-American; "
  "Hilton Armstrong was Big East Defensive Player of the Year. Syracuse beat the Huskies 86–84 in overtime in the Big East "
  "quarterfinals, but UConn earned a No. 1 seed and beat Albany, Kentucky and Washington — Rashad Anderson's three forced overtime "
  "in a 98–92 Sweet Sixteen win in which Williams scored 26. In the regional final, 11th-seeded George Mason won 86–84 in overtime "
  "after Brown's layup had forced the extra period. Five Huskies were drafted in 2006, four in the first round — tying the record."),
 "sources": [PROGRAM, W + "Marcus_Williams_(basketball,_born_1985)", W + "Denham_Brown", W + "Rashad_Anderson", W + "Rudy_Gay", W + "Hilton_Armstrong"],
},
2007: {
 "headline": "Young Huskies Miss the Dance",
 "story": (
  "With the 2006 draft class gone, Calhoun started over with freshmen such as Hasheem Thabeet — who tied the school "
  "record with 10 blocks in a game on December 3, 2006 — and Jerome Dyson, both Big East All-Rookie picks, plus A.J. Price, back on "
  "the court after surviving a life-threatening brain bleed; Price played all 31 games, starting 23 at point guard. UConn won its first 11 games and climbed to No. 12, but the young team "
  "faded to 17–14 and 6–10 in the Big East, with Jeff Adrien earning second-team all-conference honors. Syracuse beat the Huskies "
  "78–65 in the first round of the Big East tournament, and for the first time since Calhoun's first season there was no postseason "
  "invitation of any kind."),
 "sources": [PROGRAM, W + "Hasheem_Thabeet", W + "A._J._Price", W + "Jerome_Dyson"],
},
2008: {
 "headline": "A.J. Price Goes Down, San Diego Stuns",
 "story": (
  "UConn bounced back to 24–9 and 13–5, finishing fourth in the Big East. A.J. Price and Jeff Adrien were first-team All-Big East, "
  "Hasheem Thabeet was the league's and the NABC's Defensive Player of the Year, and the Huskies won at No. 7 Indiana and beat "
  "ranked Marquette, Pittsburgh and Notre Dame. West Virginia ended their Big East tournament in the quarterfinals, 78–72. As a No. "
  "4 seed in Tampa, UConn lost Price to a torn ACL nine minutes into its first-round game against 13th-seeded San Diego and fell "
  "70–69 in overtime — the first opening-round loss of Calhoun's UConn career. It spoiled a season in which the Huskies went "
  "8–0 at Gampel Pavilion and Price was a USBWA All-American. That May, the coach began treatment for squamous cell "
  "carcinoma."),
 "sources": [PROGRAM, CALHOUN, W + "A._J._Price", W + "Jeff_Adrien", W + "Hasheem_Thabeet"],
},
2009: {
 "headline": "Six Overtimes and a Final Four",
 "story": (
  "Preseason No. 2 with its starting five back plus McDonald's All-American Kemba Walker, UConn won the Paradise Jam, beat No. 8 "
  "Gonzaga 88–83 in overtime in Seattle and rose to No. 1 in February. Jim Calhoun won his 800th game at Marquette on February 25, "
  "but the Huskies lost Jerome Dyson to a knee injury against Syracuse. Hasheem Thabeet shared Big East Player of the Year with "
  "Pitt's DeJuan Blair and was national defensive player of the year. In the Big East quarterfinals, UConn and Syracuse played an "
  "epic six-overtime game at Madison Square Garden that ended at 1:22 a.m. — Syracuse winning 127–117. The Huskies still earned a "
  "No. 1 seed, beat Chattanooga, Texas A&M and Purdue, then Missouri 82–75 behind 23 points from Walker for their third Final Four. "
  "Michigan State ended the run 82–73 in Detroit. Thabeet went No. 2 in the draft."),
 "sources": [PROGRAM, CALHOUN, W + "Hasheem_Thabeet", W + "Kemba_Walker", W + "A._J._Price", W + "Syracuse%E2%80%93UConn_rivalry"],
},
2010: {
 "headline": "Beating No. 1, Then Falling Short",
 "story": (
  "A season of turbulence. Jim Calhoun took a medical leave on January 19, 2010, and did not return to the bench until February "
  "13. In between, the Huskies produced their best moment of the year, beating No. 1 Texas 88–74 at Gampel Pavilion on January 23. "
  "Jerome Dyson returned from knee surgery to average 17.7 points and was named Sporting News Comeback Player of the Year, and "
  "sophomore Kemba Walker started every game, averaging 14.6 points. But UConn finished 18–16 and 7–11 in the Big East, lost to "
  "St. John's in the Big East tournament's opening round, and landed in the NIT, where it beat Northeastern 59–57 before a 65–63 "
  "loss at Virginia Tech, where Walker scored 18. Senior Stanley Robinson was drafted 59th overall by the Orlando Magic."),
 "sources": [PROGRAM, CALHOUN, W + "Jerome_Dyson", W + "Kemba_Walker"],
},
2011: {
 "headline": "Cardiac Kemba and Eleven Straight",
 "story": (
  "Picked 10th in the Big East, UConn won the Maui Invitational by beating No. 2 Michigan State and No. 8 Kentucky, and Kemba "
  "Walker became a national sensation. an 82–81 overtime win at No. 12 Texas added to the legend, but a 9–9 Big East record left "
  "UConn tied for ninth. Then came five games in five days at Madison Square Garden: DePaul, Georgetown, top-seeded Pittsburgh on "
  "Walker's step-back at the horn (\"Cardiac Kemba does it again!\"), Syracuse in overtime, and Louisville in the final. Walker scored "
  "a record 130 points. As a No. 3 seed the Huskies beat Bucknell, Cincinnati, San Diego State and Arizona, edged Kentucky 56–55 in "
  "the Final Four, and smothered Butler 53–41 in Houston, holding the Bulldogs to 18.8 percent shooting. Walker was Most "
  "Outstanding Player, freshman Jeremy Lamb starred alongside him, and at 68 Calhoun became the oldest coach to win a title. The "
  "Huskies played 41 games and won their last 11."),
 "sources": [PROGRAM, CALHOUN, W + "Kemba_Walker", W + "Jeremy_Lamb"],
},
2012: {
 "headline": "The Defending Champions Stumble",
 "story": (
  "Freshman phenom Andre Drummond joined Jeremy Lamb, Shabazz Napier and Alex Oriakhi, but the title defense never found its "
  "footing. Calhoun served an NCAA-imposed three-game suspension to open Big East play, then took a medical leave on February 3 for "
  "spinal stenosis, with associate head coach George Blaney running the team until Calhoun returned March 3 to beat Pittsburgh. "
  "UConn went 20–14 and 8–10 in the league; Lamb was first-team All-Big East. The Huskies won twice in the Big East tournament "
  "before Syracuse edged them 58–55, and as a No. 9 seed they lost to Iowa State 77–64 in the NCAA first round. Drummond and Lamb "
  "were lottery picks, and on September 13, 2012, Calhoun announced his retirement after 26 seasons."),
 "sources": [PROGRAM, CALHOUN, W + "Andre_Drummond", W + "Jeremy_Lamb"],
},
2013: {
 "headline": "Ollie's First Year: No Postseason, No Surrender",
 "story": (
  "Kevin Ollie, a Calhoun-era point guard and 13-year NBA journeyman, took over a team that was banned from the postseason because "
  "of a low Academic Progress Rate. His debut came on November 9, 2012, at Ramstein Air Base in Germany, where UConn beat No. 14 "
  "Michigan State 66–62 in the Armed Forces Classic. At the Paradise Jam in St. Thomas, UConn beat Wake Forest and in-state Quinnipiac in double overtime before New "
  "Mexico won the final 66–60. Shabazz Napier (first-team All-Big East) and Ryan Boatright (15.4 points) "
  "formed one of the best backcourts in the country, the Huskies won at No. 17 Notre Dame, and they finished 20–10 and 10–8 in "
  "what turned out to be the final season of the original Big East. Ollie received the Ben Jobe Award, and UConn stayed behind in "
  "the conference's successor, the American Athletic Conference."),
 "sources": [PROGRAM, OLLIE, W + "Shabazz_Napier", W + "Ryan_Boatright"],
},
2014: {
 "headline": "The Hungry Huskies",
 "story": (
  "Out of the postseason ban came a champion nobody predicted. UConn beat Indiana in the 2K Sports Classic final and Florida on a "
  "Shabazz Napier buzzer-beater, finished tied for third in the new American Athletic Conference, and lost the AAC final to "
  "Louisville. As a No. 7 seed, the Huskies survived Saint Joseph's in overtime after Amida Brimah's three-point play tied the game, "
  "then beat Villanova in Buffalo and Iowa State and Michigan State at Madison Square Garden — making Ollie the first UConn coach other than "
  "Calhoun to reach a Final Four. They knocked off No. 1 overall seed Florida 63–53 and beat Kentucky 60–54 in Arlington, Texas, "
  "for their fourth title, the first ever by a No. 7 seed. Napier, the AAC Player of the Year, was Most Outstanding Player and "
  "told the country: \"You're looking at the hungry Huskies. This is what happens when you ban us.\" The UConn women won again, too."),
 "sources": [PROGRAM, W + "Shabazz_Napier", W + "Amida_Brimah", W + "Ryan_Boatright"],
},
2015: {
 "headline": "Boatright's Last Run",
 "story": (
  "Without Napier and DeAndre Daniels, the defending champions leaned on senior Ryan Boatright, a unanimous first-team All-AAC "
  "pick who averaged 17.4 points. Amida Brimah, a hero of the 2014 title run, was the AAC Defensive Player of the Year and once scored 40 points on 13-of-13 "
  "shooting against Coppin State, and freshman Daniel Hamilton was the league's Rookie of the Year. UConn went 20–15 and 10–8, tied "
  "for fifth, then made a run in the AAC tournament — beating South Florida, Cincinnati and Tulsa — before SMU won the final 62–54. "
  "A late 81–73 win over No. 21 SMU had raised hopes, but left out of the NCAA field, the Huskies lost to Arizona "
  "State 68–61 in the first round of the NIT."),
 "sources": [PROGRAM, W + "Ryan_Boatright", W + "Amida_Brimah", W + "Daniel_Hamilton_(basketball)"],
},
2016: {
 "headline": "Jalen Adams and the Four-Overtime Miracle",
 "story": (
  "Ranked No. 20 in the preseason, UConn beat Michigan in the Bahamas before close losses to Syracuse (79–76) and Gonzaga "
  "(73–70) at the Battle 4 Atlantis, then bounced in and out of the polls and finished sixth in the AAC at 11–7, earning a No. 5 "
  "seed in the conference tournament. Then came one of the most memorable nights in program history: down three with 0.8 seconds "
  "left in the third overtime against Cincinnati, freshman Jalen Adams banked in a three-quarter-court shot to force a fourth "
  "overtime, and UConn won 104–97. The Huskies beat top-seeded Temple and Memphis to win the AAC tournament, with Daniel Hamilton — "
  "who averaged 12.5 points and a league-best 8.9 rebounds — named MVP. As a No. 9 seed they beat Colorado 74–67 before top overall seed Kansas won 73–61. UConn finished 25–11."),
 "sources": [PROGRAM, W + "Jalen_Adams", W + "Daniel_Hamilton_(basketball)"],
},
2017: {
 "headline": "The First Losing Season in 30 Years",
 "story": (
  "Ranked No. 18 in the preseason, UConn opened with home losses to Wagner and Northeastern, stood 3–4 by early December, and never fully recovered its footing. A 52–50 "
  "win over Syracuse at Madison Square Garden in December provided a spark, and sophomore Jalen Adams (14.4 points, 6.1 assists) "
  "made first-team All-AAC and freshman Christian Vital started 10 games and averaged 9.1 points, but the Huskies finished 9–9 in the conference and 16–17 overall — the program's first losing season "
  "since Calhoun's debut in 1986–87. As the No. 6 seed they upset No. 3 Houston in the AAC quarterfinals before Cincinnati won the "
  "semifinal 81–71. The 16–17 finish ended a streak of 29 straight winning seasons that began with the 1988 NIT champions."),
 "sources": [PROGRAM, W + "Jalen_Adams"],
},
2018: {
 "headline": "The Nadir",
 "story": (
  "The bottom. UConn was unranked all season and absorbed 11 double-digit losses. In January 2018 the school revealed the NCAA was "
  "investigating possible recruiting violations, and home attendance sank to its lowest level in nearly 30 years. The Huskies "
  "finished 7–11 in the AAC and lost to SMU 80–73 in the first round of the conference tournament on March 8; two days later, Kevin "
  "Ollie was fired for just cause. Jalen Adams (18.1 points, 4.7 assists) made second-team All-AAC, and sophomore Christian Vital scored a career-high "
  "30 in an 85–66 win over Boston University. In July 2019 the NCAA vacated the season's "
  "wins because of the recruiting violations, leaving an official record of 0–18 — and a program in need of a reset."),
 "sources": [PROGRAM, OLLIE, W + "Jalen_Adams"],
},
2019: {
 "headline": "Hurley Arrives to Rebuild",
 "story": (
  "UConn hired Rhode Island's Dan Hurley, son of Hall of Famer Bob Hurley Sr., and introduced him on March 23, 2018. His first big "
  "win came quickly — 83–76 over No. 15 Syracuse in the 2K Sports Classic at Madison Square Garden, the program's first top-15 "
  "victory since 2014 — but Iowa won the next night and the season turned into a grind. Senior Jalen Adams's year ended with a knee "
  "injury after he had climbed to 12th on UConn's career scoring list with 1,657 points, Christian Vital averaged 14.9 "
  "points, Josh Carlton was the AAC's Most Improved Player, and UConn went 6–12 in the AAC and 16–17 overall before Houston routed the Huskies "
  "84–45 in the conference quarterfinals. The good news came in June 2019: UConn would return to the Big East for 2020–21."),
 "sources": [PROGRAM, HURLEY, W + "Christian_Vital", W + "Jalen_Adams"],
},
2020: {
 "headline": "\"Better Get Us Now\"",
 "story": (
  "UConn's farewell season in the American brought freshman James Bouknight, a redshirt year for Howard transfer R.J. "
  "Cole, and signs of life: a win over No. 15 Florida at Gampel, "
  "a double-overtime loss to No. 18 Xavier in the Charleston Classic, Bouknight's 23 points in a 72–71 overtime win over Cincinnati, and a 77–71 senior-night win over No. 21 Houston. After a "
  "January loss at Villanova, Dan Hurley warned opponents that they had \"better get us now\" — because it was coming. Bouknight made "
  "third-team All-AAC, and UConn went 19–12 and 10–8, its first winning season since "
  "2015–16. The Huskies were set to face Tulane in the AAC tournament on March 12, 2020, when the COVID-19 pandemic canceled the "
  "event hours before tipoff."),
 "sources": [PROGRAM, W + "James_Bouknight", W + "Christian_Vital"],
},
2021: {
 "headline": "Big East Homecoming, Back in the Dance",
 "story": (
  "UConn's return to the Big East came in an empty Gampel Pavilion as COVID-19 canceled five games and forced four more to be "
  "rescheduled. James Bouknight scored a career-high 40 in an overtime loss to No. 9 Creighton, then missed eight games after "
  "elbow surgery, but still averaged 18.7 points and made first-team All-Big East. Freshman Adama Sanogo, freshman Andre Jackson Jr. "
  "and Rhode Island transfer Tyrese Martin arrived; Isaiah Whaley was Big East Defensive Player of the Year and Tyler Polley was "
  "Sixth Man of the Year. UConn finished third, lost a 59–56 Big East semifinal to Creighton, and returned to the NCAA tournament for "
  "the first time in five years as a No. 7 seed, falling to Maryland 63–54. Bouknight went 11th in the draft."),
 "sources": [PROGRAM, W + "James_Bouknight", W + "Adama_Sanogo"],
},
2022: {
 "headline": "Knocking on the Door Again",
 "story": (
  "The Huskies opened 5–0, highlighted by a 115–109 double-overtime win over No. 19 Auburn at the Battle 4 Atlantis in which Adama "
  "Sanogo scored a career-high 30. On February 22 they beat No. 8 Villanova 71–69 at the XL Center — the program's first top-10 win "
  "in eight years — and R.J. Cole, who passed 2,000 career points, joined Sanogo on the All-Big East first team. UConn finished third "
  "again at 13–6, lost a 63–60 Big East semifinal to Villanova, and as a No. 5 seed was upset 70–63 by No. 12 New Mexico State. "
  "Tyrese Martin averaged 13.6 points and 7.5 rebounds before being drafted 51st overall, while freshmen Jordan Hawkins and Samson Johnson and redshirt Alex Karaban were quietly developing for what came next."),
 "sources": [PROGRAM, W + "Adama_Sanogo", W + "R._J._Cole"],
},
2023: {
 "headline": "Blue Blood: The Fifth Title",
 "story": (
  "Unranked after losing eight scholarship players, UConn started 14–0, won the Phil Knight Invitational by beating Oregon, Alabama "
  "and Iowa State, and climbed to No. 2. A January slide (six losses in eight games) gave way to an 8–1 finish, and after a 70–68 "
  "Big East semifinal loss to Marquette the Huskies entered the NCAA tournament as a No. 4 seed. Then they were untouchable: Iona, "
  "Saint Mary's, Arkansas, Gonzaga, Miami and San Diego State, every game won by at least 13 points and by 20.0 on average — the first "
  "champion of the 64-team era to do that. Adama Sanogo was Most Outstanding Player, Jordan Hawkins the West Regional MOP, with "
  "Andre Jackson Jr., transfers Tristen Newton, Joey Calcaterra and Hassan Diarra, and freshmen Alex Karaban and Donovan Clingan all "
  "starring. The 76–59 title game win in Houston gave UConn its fifth championship and \"blue blood\" status."),
 "sources": [PROGRAM, W + "Adama_Sanogo", W + "Jordan_Hawkins", W + "Tristen_Newton", W + "Donovan_Clingan", W + "Alex_Karaban"],
},
2024: {
 "headline": "Back-to-Back, and Utterly Dominant",
 "story": (
  "Five-star freshman Stephon Castle and Rutgers transfer Cam Spencer joined Tristen Newton, Alex Karaban and new starting center "
  "Donovan Clingan. UConn won the Empire Classic, set an NCAA record with 24 straight double-digit wins over non-conference "
  "opponents, and went a program-best 18–2 in the Big East for its first regular-season title since 2006. The Huskies then won the "
  "Big East tournament over Xavier, St. John's and Marquette, earned the first No. 1 overall seed in school history, and destroyed "
  "the field: Stetson, Northwestern, San Diego State, Illinois (with a 30–0 run), Alabama and Purdue, 75–60 in the final. Their +140 "
  "margin was an NCAA record, and they became the first repeat champion since Florida in 2007. Newton was Most Outstanding Player, "
  "Hurley was Naismith Coach of the Year, and a 37–3 record set a program mark for wins. Castle went fourth and Clingan seventh in "
  "the draft."),
 "sources": [PROGRAM, HURLEY, W + "Tristen_Newton", W + "Cam_Spencer", W + "Stephon_Castle", W + "Donovan_Clingan"],
},
2025: {
 "headline": "The Three-Peat Bid",
 "story": (
  "Dan Hurley turned down Kentucky and the Los Angeles Lakers to chase a third straight title, something no team had done since "
  "UCLA's run ended in 1973. It was a bumpy ride: after climbing to No. 2, UConn lost all three games at the Maui Invitational — to "
  "Memphis in overtime, Colorado and Dayton. Freshman Liam McNeeley was Big East Freshman of the Year (with a 38-point night against "
  "Creighton), Tarris Reed Jr. was Sixth Man of the Year and Solo Ball broke out, and the Huskies finished third at 14–6. They "
  "beat Villanova in the Big East quarterfinals before Creighton won the semifinal, and as a No. 8 seed they beat Oklahoma 67–59. "
  "In the second round, top-seeded Florida — the eventual champion — ended the three-peat bid 77–75."),
 "sources": [PROGRAM, HURLEY, W + "Liam_McNeeley", W + "Tarris_Reed_Jr.", W + "Solo_Ball"],
},
2026: {
 "headline": "The Mullins Miracle and an Eighth Final Four",
 "story": (
  "With transfers Silas Demary Jr. and Malachi Smith and freshman Braylon Mullins joining Alex Karaban, Tarris Reed Jr. and Solo "
  "Ball, UConn went 34–6. The Huskies beat No. 7 BYU in Boston, won at Kansas, beat Florida in the Jimmy V Classic and started 12–0 "
  "in the Big East, finishing second. Emeka Okafor's No. 50 was retired in February, and Karaban became the first active men's "
  "player inducted into the Huskies of Honor. Karaban, Demary and Reed made first-team All-Big East — the league's first trio from "
  "one team. After a 72–52 loss to St. John's in the Big East final, the No. 2 seed Huskies beat Furman (Reed: 31 points, 27 "
  "rebounds), UCLA and Michigan State, then erased a 19-point second-half deficit against No. 1 overall seed Duke: Demary deflected a "
  "pass, Karaban found Mullins, and Mullins buried a 35-foot three with 0.4 seconds left, 73–72. UConn beat Illinois in the Final "
  "Four before Michigan won the title game 69–63 — UConn's first loss in seven title games."),
 "sources": [PROGRAM, W + "Braylon_Mullins", W + "Alex_Karaban", W + "Tarris_Reed_Jr.", W + "Silas_Demary_Jr."],
},
2027: {
 "headline": "Preview: Reloading for Another Run",
 "story": (
  "Dan Hurley's ninth UConn team must replace first-round picks Tarris Reed Jr. (26th, Denver) and Alex Karaban (29th, Cleveland) "
  "and play the whole season without Solo Ball, who had wrist surgery in April and will take a medical redshirt. The biggest "
  "offseason win came on April 19, when Braylon Mullins — the hero of the Duke game and a projected first-round pick — chose to "
  "return for his sophomore year. Senior Silas Demary Jr. is back to run the offense. The transfer class includes Duke's Nik "
  "Khamenia, Jacksonville State's Jaye Nash, Seton Hall's Na'jai Hines, Stanford's Oskar Giltay, Wofford's Nils Machowski, "
  "Arkansas's Elmir Džafić and Northern Arizona's Isaiah Shaw, and the freshman class adds guard Junior County, forward Colben Landrew "
  "and Russian forward Egor Amosov from Real Madrid's program. Assistant Luke Murray left to become Boston College's head coach. The "
  "non-conference slate is loaded: Michigan in Boston, Ohio State, a trip to Arizona, Duke in Las Vegas, Illinois in Chicago, Kansas "
  "at home and Virginia at Madison Square Garden before Big East play opens against Georgetown on December 23."),
 "sources": ["https://uconnhuskies.com/sports/mens-basketball/schedule/2026-27", "https://uconnhuskies.com/sports/mens-basketball/roster",
             PROGRAM, W + "Braylon_Mullins", W + "Solo_Ball"],
},
}

# Extra key moments (beyond those auto-generated from the schedule): (date, title, text)
MOMENTS = {
 1987: [("1986-05-14", "Calhoun hired", "UConn names Northeastern's Jim Calhoun head coach.")],
 1988: [("1988-03-30", "NIT champions", "UConn beats Ohio State 72–67 at Madison Square Garden for the school's first national basketball title.")],
 1990: [("1990-01-27", "Gampel Pavilion opens", "UConn beats No. 15 St. John's 72–58 in the first game at Gampel Pavilion."),
        ("1990-03-22", "\"The Shot\"", "Scott Burrell's full-court pass finds Tate George, whose buzzer-beater beats Clemson 71–70 in the Sweet Sixteen.")],
 1996: [("1996-03-09", "Ray Allen's winner", "UConn closes on a 12–0 run and Ray Allen's floater beats Georgetown 75–74 for the Big East title.")],
 1998: [("1998-03-19", "Rip rips Washington", "Richard Hamilton's buzzer-beater beats Washington 75–74 in the Sweet Sixteen.")],
 1999: [("1999-03-29", "\"We shocked the world!\"", "UConn beats Duke 77–74 in St. Petersburg for its first national championship; Richard Hamilton is Most Outstanding Player.")],
 2003: [("2003-02-22", "Calhoun returns", "Sixteen days after prostate cancer surgery, Jim Calhoun returns to the bench against St. John's at Gampel.")],
 2004: [("2004-04-03", "Comeback vs Duke", "Down eight with three minutes left, UConn rallies to beat Duke 79–78 in the Final Four."),
        ("2004-04-05", "Second national title", "UConn beats Georgia Tech 82–73 in San Antonio; Emeka Okafor is Most Outstanding Player.")],
 2005: [("2005-03-02", "Calhoun's 700th win", "Jim Calhoun earns career win No. 700 against Georgetown at Gampel Pavilion.")],
 2006: [("2005-11-23", "Maui champions", "Denham Brown's last-second jumper beats Gonzaga 65–63 in the Maui Invitational final.")],
 2009: [("2009-02-25", "Calhoun's 800th win", "Jim Calhoun earns career win No. 800 at Marquette's Bradley Center."),
        ("2009-03-12", "Six overtimes", "Syracuse beats UConn 127–117 in six overtimes in the Big East quarterfinals, ending at 1:22 a.m.")],
 2010: [("2010-01-23", "No. 1 Texas falls", "UConn beats top-ranked Texas 88–74 at Gampel Pavilion.")],
 2011: [("2011-03-10", "\"Cardiac Kemba does it again!\"", "Kemba Walker's step-back at the buzzer beats No. 3 Pittsburgh 76–74 in the Big East quarterfinals."),
        ("2011-03-12", "Five games in five days", "UConn beats Louisville 69–66 for the Big East title, the first team to win five tournament games in five days."),
        ("2011-04-04", "Third national title", "UConn beats Butler 53–41 in Houston; Kemba Walker is Most Outstanding Player.")],
 2012: [("2012-09-13", "Calhoun retires", "Jim Calhoun retires after 26 seasons; Kevin Ollie is named his successor.")],
 2013: [("2012-11-09", "Ollie's debut in Germany", "UConn beats No. 14 Michigan State 66–62 at Ramstein Air Base in Kevin Ollie's first game.")],
 2014: [("2013-12-02", "Napier's buzzer-beater", "Shabazz Napier's shot at the horn beats No. 15 Florida 65–64."),
        ("2014-04-07", "\"The hungry Huskies\"", "No. 7 seed UConn beats Kentucky 60–54 in Arlington, Texas, for its fourth title.")],
 2016: [("2016-03-11", "Jalen Adams' miracle", "Jalen Adams' three-quarter-court shot forces a fourth overtime; UConn beats Cincinnati 104–97.")],
 2018: [("2018-03-10", "Ollie fired", "Two days after the season ends, UConn fires Kevin Ollie for just cause amid an NCAA investigation.")],
 2019: [("2018-03-23", "Hurley introduced", "Dan Hurley is introduced as UConn's head coach."),
        ("2019-06-27", "Big East homecoming announced", "UConn and the Big East announce the Huskies will rejoin the conference in 2020–21."),
        ("2019-03-03", "Ray Allen's No. 34 retired", "Ray Allen's jersey becomes the first number retired in UConn men's basketball history.")],
 2020: [("2020-03-12", "Season canceled", "The AAC tournament is canceled hours before UConn's game against Tulane as the COVID-19 pandemic spreads.")],
 2023: [("2023-04-03", "Fifth national title", "UConn beats San Diego State 76–59 in Houston; Adama Sanogo is Most Outstanding Player.")],
 2024: [("2024-02-24", "Rip Hamilton's No. 32 retired", "Richard Hamilton's number is retired at Gampel Pavilion."),
        ("2024-03-30", "The 30–0 run", "UConn uses a 30–0 run to beat Illinois 77–52 in the Elite Eight."),
        ("2024-04-08", "Back-to-back", "UConn beats Purdue 75–60 in Glendale, Arizona, for its sixth title and first repeat.")],
 2026: [("2026-02-18", "Okafor's No. 50 retired", "Emeka Okafor's number is retired at halftime against Creighton at Gampel Pavilion."),
        ("2026-02-28", "Karaban enters the Huskies of Honor", "Alex Karaban becomes the first active men's player inducted into the Huskies of Honor."),
        ("2026-03-29", "The Mullins miracle", "Braylon Mullins' 35-foot three with 0.4 seconds left completes a 19-point comeback over No. 1 Duke, 73–72.")],
 2027: [("2026-03-26", "Luke Murray to Boston College", "Assistant Luke Murray is hired as Boston College's head coach."),
        ("2026-04-19", "Mullins returns", "Braylon Mullins, a projected first-round pick, returns for his sophomore season."),
        ("2026-04-20", "Solo Ball out for the season", "Solo Ball undergoes wrist surgery and will take a medical redshirt."),
        ("2026-11-06", "Michigan in Boston", "Title-game rematch with Michigan at TD Garden in the Hall of Fame Series."),
        ("2026-11-25", "Duke in Las Vegas", "UConn faces Duke at T-Mobile Arena."),
        ("2026-12-20", "Virginia at MSG", "UConn meets Virginia at Madison Square Garden."),
        ("2026-12-23", "Big East opener", "Conference play opens at home against rival Georgetown.")],
}

# Storrs Lore

An unofficial, fan-built encyclopedia of UConn men's basketball from Jim Calhoun's first season (1986–87) to now: every season, every game, every Husky.

Live at **https://jfrascino.github.io/the-rafters/**

- `site/`: the app (vanilla JS, no build step). `site/data/` is generated.
- `pipeline/`: data collection and the build.
  - `sr_scrape.py`: Sports-Reference seasons, rosters, stats, schedules, box scores, player pages (rate-limited, cached).
  - `espn_fetch.py --all | --update`: ESPN box scores, play-by-play, win probability, clips, current schedule.
  - `media_*.py`: season stories, Wikimedia photos, verified YouTube videos.
  - `build.py`: merges everything into `site/data/`.
- `.github/workflows/update.yml`: refreshes from ESPN every 20 minutes during the season and redeploys.

Not affiliated with the University of Connecticut. Stats from Sports-Reference and ESPN; photos credited where shown; videos embed from their YouTube owners.

"""Parse the Awards section of the UConn program article into {award: [(name, year)]}."""
import json, os, re
from media_common import CACHE, wt2text

def parse_awards():
    L = json.load(open(os.path.join(CACHE, "lore_raw.json")))
    wt = L["UConn Huskies men's basketball"]["wikitext"]
    m = re.search(r"\n==\s*Awards\s*==\n(.*?)(?=\n==[^=])", wt, re.S)
    txt = wt2text(m.group(1))
    awards = {}; cur = None; scope = None
    for line in txt.split("\n"):
        line = line.strip()
        if not line or line.lower() == "source": continue
        if line.startswith("==="):
            scope = line.strip("= ").strip(); continue
        if line.startswith("*"):
            mm = re.match(r"\*\s*(.+?)\s*(?:–|\s-\s)\s*(.+)$", line)
            if mm and cur:
                name = mm.group(1).strip()
                for y in re.findall(r"\d{4}", mm.group(2)):
                    awards.setdefault(cur, []).append((name, int(y)))
            continue
        cur = line if not cur or not line.startswith("Conference Third") else cur + " " + line
        if line == "Conference Third Team": cur = "All-Big East Conference Third Team"
    return awards

if __name__ == "__main__":
    a = parse_awards()
    for k, v in a.items(): print(k, len(v), v[:3])
    json.dump({k: v for k, v in a.items()}, open(os.path.join(CACHE, "awards_parsed.json"), "w"), indent=1)

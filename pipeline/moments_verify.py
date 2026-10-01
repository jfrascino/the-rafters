#!/usr/bin/env python3
"""Apply fact-check ledgers to Moments drafts: out/moments/drafts/<slug>.json + factcheck/<slug>.json -> verified/<slug>.json

Only drafts whose ledger says "publish" are promoted. Every edit must apply cleanly (a "fix" whose old text isn't found
stops that moment), so nothing half-corrected reaches the site. Report: out/moments/verify_report.json."""
import copy, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'out', 'moments')


def walk(obj, path):
    """'setup[1].text' -> (parent, key)"""
    toks = re.findall(r'[^.\[\]]+|\[\d+\]', path)
    cur = obj
    for t in toks[:-1]:
        cur = cur[int(t[1:-1])] if t.startswith('[') else cur[t]
    last = toks[-1]
    return cur, (int(last[1:-1]) if last.startswith('[') else last)


def apply(draft, ledger):
    d = copy.deepcopy(draft)
    removals, problems = [], []
    for e in ledger.get('edits') or []:
        op, path = e.get('op'), e.get('path') or ''
        try:
            parent, key = walk(d, path)
            if op == 'fix':
                val = parent[key]
                if not isinstance(val, str) or e['old'] not in val:
                    problems.append(f"fix not applied ({path}): {e['old'][:60]!r} not found")
                    continue
                parent[key] = val.replace(e['old'], e['new'], 1)
            elif op == 'set':
                parent[key] = e.get('value')
            elif op == 'add':
                parent[key].append(e.get('value')) if isinstance(parent[key], list) else problems.append(f'add to non-list {path}')
            elif op == 'remove':
                removals.append((path, parent, key))
            else:
                problems.append(f'unknown op {op} at {path}')
        except (KeyError, IndexError, TypeError) as ex:
            problems.append(f'bad path {path} ({ex})')
    # remove list items last, highest index first, so earlier removals don't shift later paths
    for path, parent, key in sorted(removals, key=lambda r: -(r[2] if isinstance(r[2], int) else -1)):
        try:
            if isinstance(parent, list):
                parent.pop(key)
            else:
                parent.pop(key, None)
        except (IndexError, KeyError):
            problems.append(f'remove failed {path}')
    return d, problems


def main():
    os.makedirs(os.path.join(D, 'verified'), exist_ok=True)
    report = {}
    only = set(sys.argv[1:])
    for f in sorted(glob.glob(os.path.join(D, 'drafts', '*.json'))):
        slug = os.path.splitext(os.path.basename(f))[0]
        if only and slug not in only:
            continue
        lp = os.path.join(D, 'factcheck', f'{slug}.json')
        if not os.path.exists(lp):
            report[slug] = 'not fact-checked yet'
            continue
        ledger = json.load(open(lp))
        if ledger.get('verdict') != 'publish':
            report[slug] = f"held by the fact-checker: {ledger.get('notes', '')[:200]}"
            continue
        out, problems = apply(json.load(open(f)), ledger)
        if problems:
            report[slug] = {'held': 'edits did not apply cleanly', 'problems': problems}
            continue
        out['_verified'] = {'checked': ledger.get('claims_checked'), 'ok': ledger.get('claims_ok'), 'edits': len(ledger.get('edits') or [])}
        json.dump(out, open(os.path.join(D, 'verified', f'{slug}.json'), 'w'), indent=1)
        report[slug] = f"verified: {ledger.get('claims_checked')} claims checked, {len(ledger.get('edits') or [])} edits"
    json.dump(report, open(os.path.join(D, 'verify_report.json'), 'w'), indent=1)
    for k, v in report.items():
        print(f'{k}: {v}')


if __name__ == '__main__':
    main()

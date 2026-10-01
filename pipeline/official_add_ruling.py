"""Append/replace one research ruling in out/official/verify_rulings.json.
usage: python3 official_add_ruling.py '<json object with key, truth, confidence, sources, note>'"""
import json, sys, os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out/official/verify_rulings.json')
R = json.load(open(p))
for obj in json.loads(sys.argv[1]) if sys.argv[1].strip().startswith('[') else [json.loads(sys.argv[1])]:
    k = obj.pop('key')
    R['rulings'][k] = obj
    print('saved', k)
json.dump(R, open(p, 'w'), indent=1, ensure_ascii=False)

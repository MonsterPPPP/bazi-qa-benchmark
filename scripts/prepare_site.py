"""Check recovered category counts and build the site's reproducible main table."""
import csv
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'data'
SOURCES = DATA / 'sources'

def read(name):
    with (SOURCES / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def pct(correct, n):
    return (Decimal(correct) * 100 / Decimal(n)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

def main():
    leaderboard = read('leaderboard.csv')
    categories = read('category-profile.csv')
    totals = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    seen = set()
    for r in categories:
        key = (r['model'], r['task'], r['category_en'])
        if key in seen:
            raise ValueError(f'Duplicate category: {key}')
        seen.add(key)
        n, correct = int(r['n']), int(r['correct'])
        if not 0 <= correct <= n:
            raise ValueError(f'Invalid category counts: {key}')
        if abs(Decimal(r['accuracy']) - Decimal(correct)*100/Decimal(n)) > Decimal('0.0001'):
            raise ValueError(f'Category accuracy mismatch: {key}')
        totals[r['model']][r['task']][0] += n
        totals[r['model']][r['task']][1] += correct
    intervals = {}
    for r in read('pairwise.csv'):
        for side in ('a', 'b'):
            name = r['model_' + side]
            ci = (r['ci_' + side + '_lo'], r['ci_' + side + '_hi'])
            if name in intervals and intervals[name] != ci:
                raise ValueError(f'Inconsistent recovered intervals: {name}')
            intervals[name] = ci
    models = {r['model'] for r in leaderboard}
    if len(models) != len(leaderboard) or models != set(totals) or models != set(intervals):
        raise ValueError('Model sets disagree across recovered tables')
    out = []
    for r in leaderboard:
        name = r['model']
        theory, case = totals[name]['Theory'], totals[name]['Case']
        n, correct = theory[0]+case[0], theory[1]+case[1]
        if (theory[0], case[0], n) != (1454, 1038, 2492):
            raise ValueError(f'Unexpected task denominators: {name}')
        expected = {'overall_acc': pct(correct,n), 'theory_acc': pct(theory[1],theory[0]), 'case_acc': pct(case[1],case[0])}
        for metric, value in expected.items():
            if value != Decimal(r[metric]):
                raise ValueError(f'{name}: {metric} does not match category counts')
        lo, hi = intervals[name]
        out.append({**r, 'n':n, 'correct':correct, 'ci_low':lo, 'ci_high':hi})
    fields = ['model','overall_acc','n','theory_acc','case_acc','invalid_pct','correct','ci_low','ci_high']
    with (DATA / 'leaderboard.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    manifest = [{'path':p.relative_to(ROOT/'docs').as_posix(), 'bytes':p.stat().st_size,
                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(SOURCES.iterdir()) if p.is_file()]
    (DATA / 'provenance.json').write_text(json.dumps({'scope':'Recovered aggregate snapshots; no complete per-item responses.', 'files':manifest},indent=2)+'\n',encoding='utf-8')
    print(f'Checked {len(categories)} category rows and {len(out)} models; all scores match the manuscript.')

if __name__ == '__main__':
    main()

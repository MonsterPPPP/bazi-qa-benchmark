# Bazi QA Benchmark

Paper: **Knowing the Rules, Applying the Rules: Evaluating Language Models on Traditional Chinese Bazi** — Jiulin Li and Ping Huang, September 2026.

This repository contains the latest manuscript PDF and an English paper homepage with an interactive leaderboard. The GitHub repository is currently private; the website runs locally.

## Build and preview

On Windows with PowerShell and [uv](https://docs.astral.sh/uv/):

```powershell
.\scripts\build.ps1
.\scripts\serve.ps1 -Open
# Stop the background preview:
.\scripts\serve.ps1 -Stop
```

The preview uses 127.0.0.1 on port 8000, then 8001 or 8002 if necessary. State and logs live in the ignored `.cache/` folder. For another platform, create a Python 3.12+ environment, install `requirements.txt`, run `python scripts/prepare_site.py`, then `python tools/benchmark-pages/scripts/build_site.py --source docs --out _site --strict`. Serve `_site` with `python -m http.server 8000 --bind 127.0.0.1 --directory _site`.

## Browser verification

`scripts/browser-check.cjs` uses Playwright and the installed Microsoft Edge browser to check both pages at desktop and 375px mobile widths. It verifies sorting, global search, header filtering, empty-result recovery, frozen columns, local links, Figure 4, absence of displayed author information, attribution, and PDF integrity. Screenshots and reports are written to the ignored `.cache/browser-check/` folder.

```powershell
npm install --prefix .cache/browser playwright
$env:NODE_PATH = "$PWD\.cache\browser\node_modules"
node .\scripts\browser-check.cjs
```

## Sources and reproducibility

- `docs/site.yaml`: paper metadata, original abstract, findings, and limitations.
- `docs/pdfs/paper.pdf`: the revised 16-page manuscript.
- `docs/data/sources/`: recovered aggregate CSV snapshots.
- `docs/data/leaderboard.csv`: main table, regenerated and checked against category counts.
- `docs/data/provenance.json`: SHA-256 hashes of input snapshots.
- `docs/data/metrics.md`: denominators, invalid-answer handling, aggregation, intervals, and selection limits.
- `docs/figures/`: revised quantitative figures; the category profile is vector SVG.
- `_site/`: committed static output. Rebuild after editing source inputs.

The main scores are verified against 150 recovered category rows. Complete per-item model responses are not included, so this package does not independently reproduce the full historical evaluation. The final-set intervals describe an outcome-informed subset. Configuration contrasts use the original 3,000-item set.

## Generator and attribution

The site uses [18trees benchmark-pages](https://github.com/MonsterPPPP/18trees-benchmark-pages-skill), pinned to `5c2a1a5fc7894e31698ed5b64f52e05e0359a3d9`. Local changes supply English UI text, a work-focused header without author information, explicit column labels, always-visible filtering, and full-width vector figure viewing. See `tools/benchmark-pages/UPSTREAM.md`.

The website template is derived from [Academic Project Page Template](https://github.com/eliahuhorwitz/Academic-project-page-template) and [Nerfies](https://nerfies.github.io/). Template derivatives retain CC BY-SA 4.0 attribution. Tabulator remains MIT licensed. These template licenses do not establish a redistribution license for the benchmark questions or manuscript. See `NOTICE.md` and the vendored license files.

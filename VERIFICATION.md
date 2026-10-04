# Verification — 2026-10-04

- Strict generator validation and output checks passed.
- All 150 model/category rows were checked; totals match the six headline scores, with 2,492 records per model.
- Both pages were exercised in Microsoft Edge through Playwright at 1440px desktop and 375px mobile widths.
- Numeric sort ascending/descending, global model search, no-match state, clear-to-restore, and model header filtering passed.
- Mobile document width remains within the viewport; the frozen model column stays in position while the table scrolls horizontally.
- All local navigation, image, CSS, JavaScript, and PDF URLs returned HTTP 200.
- Figure 4 spans the gallery width and its vector SVG opens independently.
- The served PDF SHA-256 matches the copied revised manuscript.
- Author names, affiliations, and contact details are absent from both page headers; no email link, equal-contribution label, or missing citation navigation is displayed.
- Both pages retain Academic Project Page Template and Nerfies backlinks.
- No browser JavaScript errors were recorded. Desktop, mobile, leaderboard, and Figure 4 screenshots were visually inspected.

## Pre-arXiv integration

- `CITATION.cff` validates against the official CFF 1.2.0 schema, with the current preprint URL and no invented identifier.
- Paper, repository and generated website PDF copies have matching SHA-256 values; the 16-page PDF contains working resource annotations for the canonical dataset, repository and project page.
- The revised paper compiles without undefined references, citations or overfull boxes.
- Existing aggregate CSVs and figure assets are unchanged by integration.
- The existing Hugging Face reference prompt and evaluation scorer are copied without modification; the scorer command-line interface is available.
- Repository content and Git history were scanned for credentials, private machine paths and unrelated large files, with no findings.
- Dataset, repository and citation buttons are present on both pages; contact and disclosure links preserve the website's hidden author display.

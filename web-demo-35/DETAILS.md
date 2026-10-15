## What this is
A static, Lighthouse-style responsive audit of a homepage at 375, 768 and 1440px plus a rebuilt, keyboard-accessible navigation section. It was built from the public job post on synthetic data, not on client data.

## Done
- Heuristic audit: viewport meta, img alt and dimensions, html lang, nav landmark, non-focusable click handlers, fixed widths overflowing each viewport
- Before/after reports in out/ (Markdown and JSON) with a per-viewport score
- Rebuilt nav (out/index.html, nav.css, nav.js): mobile toggle with aria-expanded, Escape to close, focus handling, 44px targets
- 4 in-process unit tests; headless Chromium check (see BROWSER-CHECK.md)

## Remaining
- Real Lighthouse run against the production homepage once the URL is shared
- Apply the nav to the production stack and branding with the design team
- Full redesign of other sections, screen reader and cross-browser testing
- Deployment on the production hosting

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

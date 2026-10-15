## What this is
A site map and homepage copy draft for a B2B scan-to-BIM/CAD service website, positioned by level of detail (LOD). It was built from the public job post on synthetic data, not on client data; LOD wording is placeholder until confirmed.

## Done
- Site map (11 pages) as a JSON tree and an XML sitemap with relative paths
- Static, responsive homepage: hero, deliverables, LOD table (100 to 400), process, quote calls to action
- Offline performance budget: no external scripts, stylesheets or images; HTML size under budget
- 5 tests: sitemap XML matches tree, LOD order, internal links resolve, title/description length, budget
- Headless Chromium check at phone width (see BROWSER-CHECK.md, screenshot.png)

## Remaining
- Confirm the LOD tiers, deliverables and formats actually offered
- Inner pages (services, quote form with backend, FAQ, privacy)
- Branding, domain, hosting and deployment
- Real Google Lighthouse mobile run on the deployed site
- Priority buyer segments and keyword research for SEO

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

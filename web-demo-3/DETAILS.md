## What this is
A static, dependency-free PCB company website demo with five sections (product, information, news, industry, culture) plus a China-access dependency checklist. It was built from the public job post on synthetic data, not on client data.

## Done
- Sitemap with five sections (out/sitemap.json) and a home page summarising each
- Six generated HTML pages with shared navigation and a product spec table
- Checklist of third-party scripts commonly blocked in mainland China, with replacements (out/china_checklist.md)
- Pages use no external fonts, scripts or embeds; tests verify no external or blocked hosts
- Tests: internal links resolve, product rows preserved, news sorted, deterministic output

## Remaining
- Real product specs, images, texts and branding from the production data
- Choice of hosting (and ICP filing if a mainland host is chosen)
- Page-load tests from inside China and abroad on the chosen host
- Chinese language version, contact form, CMS editing if wanted

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

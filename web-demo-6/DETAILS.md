## What this is
A one-page story website draft with five chronological chapters (early life, career, challenges, achievements, company growth) in an alternating photo/text timeline. It was built from the public job post on synthetic placeholder text, not on client data, and also exports WordPress block markup.

## Done
- Static responsive timeline page (out/index.html) with sticky chapter navigation
- WordPress Gutenberg block markup for the same five chapters (out/wordpress-blocks.html)
- Chapter content kept in one data list (out/chapters.json) for easy swapping
- Self-checks: chapter order, nav links, balanced blocks, HTML escaping, determinism
- Headless browser check of the page (see BROWSER-CHECK.md, screenshot.png)

## Remaining
- The real story text and photographs
- Branding: colours, fonts, logo
- Review round on design and wording
- Installing into the WordPress site (deployment not included)

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

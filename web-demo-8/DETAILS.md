## What this is
A prototype of the navigation and appointment flow for a healthcare WordPress site: a page tree (sitemap) for services, doctor profiles and appointment pages, (site domain set at deploy) plus a responsive sample page with an appointment request form. It was built from the public job post on synthetic data, not on client data.

## Done
- WordPress page tree with services, doctors, appointments, contact, privacy (out/sitemap.json)
- XML sitemap for search engines (out/sitemap.xml)
- Responsive, keyboard-focusable sample page with appointment request form (out/index.html)
- Server-side style validation and double-booking protection, tested
- Six automated checks; headless-browser click-through (BROWSER-CHECK.md)

## Remaining
- Convert to a custom WordPress block theme with service and doctor post types
- The production content, branding, photos and doctor details
- Choice: request form or live booking
- Analytics/Search Console setup, cross-browser testing, deployment on the production hosting

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

# 5-Page Small-Business Website Template

A static website template for a local small business, shown with the fictional sample brand "Brightline Home Services". Rebrand it by editing one JSON file and running one command; no frameworks, CDNs or web fonts.

**Live demo:** https://degalat57.github.io/demos/small-business-website/

## What it shows

- Five pages (home, about, services, contact, blog) plus three starter blog posts, a 404 page, sitemap and robots.txt
- Unique titles, meta descriptions, canonical links, Open Graph tags and JSON-LD structured data on every page
- Mobile menu, contact form validation, skip link, focus styles and reduced-motion support
- A Python build script (standard library only) with a `--check` mode for broken links and SEO basics

## Data

The business, team, testimonials, numbers and contact details are placeholder sample content (marked "sample" on the page). It is not real data about real people or businesses.

## How it was built

AI-assisted build: AI coding models wrote the code from a written spec, and automated checks (tests where present and a headless-browser render check) verified it before it was published. The code is plain, readable source with no build-time secrets.

## Run it locally

Requires Python 3.8+ (standard library only):

```sh
python3 build.py          # writes dist/
python3 build.py --check  # build and verify links, headings and meta tags
python3 -m http.server 8000 --directory dist
```

Rebrand by editing `site.json` (see [DETAILS.md](DETAILS.md)).

More detail (features, data model, customisation): [DETAILS.md](DETAILS.md)

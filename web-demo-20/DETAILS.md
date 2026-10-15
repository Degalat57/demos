## What this is
A starter for a custom responsive website, built from the public job post on synthetic data, not on client data. A sample brand spec becomes a written page list and component map, a REST API layer (Flask routes), and one responsive home page built from React-style components.

## Done
- Page list and component map generated from a brand spec (out/scope.md, out/component_map.json)
- REST API logic: brand, pages, features, contact form with validation (tested in-process)
- Flask wiring for those routes (out/app_flask.py.txt; Flask is not installed here, so it was not run)
- Single responsive home page (out/index.html), checked in headless Chromium at phone and desktop widths

## Remaining
- The real brand specs, content and the choice of which page comes first
- Port the plain-JS components to a React build; further pages
- PostgreSQL storage, integrations, deployment on the chosen hosting

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

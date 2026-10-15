## What this is
A working core for a mobile-first rental marketplace: four categories, five roles, listings, price/location filters, inquiries and an admin moderation queue. It was built from the public job post on synthetic data, not on client data. It also writes the MVP user stories and a role permissions matrix.

## Done
- User stories for all four categories and the roles (out/user_stories.csv)
- Permissions matrix per role and per category (out/permissions_matrix.csv)
- SQLite schema: users, listings with photos, inquiries, reports
- Post listing (validated), edit only your own, filter by category, price and location
- Send an inquiry, owner inbox, report a listing, admin hides or restores it
- Mobile-first demo page (out/index.html): post, filter, send inquiry; checked in headless Chromium
- 7 automated checks (filter cross-checked against plain Python, row counts, permissions, edge cases)

## Remaining
- Port to Django/PostgreSQL with real login, sessions and password hashing
- Real photo uploads and storage on the chosen hosting
- Agent and service-provider dashboards, reviews (Phase 2)
- Branding, the production data, and deployment to the client hosting

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

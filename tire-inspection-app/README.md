# Tire Shop Digital Vehicle Inspection

A clickable, installable web app (PWA) for a tire and auto-repair shop, branded "Demo Tire & Auto". Technicians run a digital vehicle inspection on a phone, tablet or PC, and the customer gets a shareable report.

**Live demo:** https://degalat57.github.io/demos/tire-inspection-app/

## What it shows

- Today's jobs board (waiting / in progress / completed) and a new work order form
- Technician accept and a 7-step job status timeline
- Inspection sections: tires (tread depth auto-suggests Good / Soon / Replace), brakes, TPMS, suspension, alignment, notes and recommended repairs
- Photo capture per section (downscaled in the browser)
- Shop summary with a one-tap "send to customer" text-message preview, a public customer report link and a printable filled-in inspection sheet
- Customer and vehicle history search; works offline after the first visit (service worker)

## Data

The shop, technicians, customers, vehicles and inspections are synthetic seed data (the app shows a "Demo - synthetic data only" banner). Everything stays in your browser (localStorage); Settings > Reset restores the seed data. It is not real data about real people or businesses.

## How it was built

AI-assisted build: AI coding models wrote the code from a written spec, and automated checks (tests where present and a headless-browser render check) verified it before it was published. The code is plain, readable source with no build-time secrets.

## Run it locally

Any static file server works:

```sh
python3 -m http.server 8000
# open http://localhost:8000/
```

More detail (features, data model, customisation): [DETAILS.md](DETAILS.md)

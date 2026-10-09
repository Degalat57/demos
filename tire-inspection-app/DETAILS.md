# Tire-Shop Digital Vehicle Inspection — Demo PWA

A dependency-free, static Progressive Web App (plain HTML + CSS + vanilla JavaScript, no frameworks, no CDNs, no build step) that a tire & auto-repair shop can open on a phone, tablet, or Windows PC. It is a **clickable sales demo** of the real app: all data is synthetic and stays in the browser (localStorage key `dvi-demo-v1`).

## Running it

Any static file server works:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

The service worker requires `http://` or `https://` (not `file://`), but the app itself runs fine from `file://` too.

## Rebranding

Edit **only `config.js`** — shop name, tagline, phone number, and the base URL used in customer report links. Everything else (header, SMS text, report footer, manifest name) picks it up automatically.

## Views

- `#/today` — Today's jobs dashboard (Waiting / In Progress / Completed tabs)
- `#/new` — New customer / vehicle / work order
- `#/job/<id>` — Job detail: technician assignment, 7-step status timeline, inspection flow
- `#/inspect/<inspectionId>/<section>` — Inspection: tires, brakes, TPMS/Suspension/Alignment, notes & recommendations, photos (autosaved)
- `#/summary/<inspectionId>` — Shop summary with one-tap "Send to Customer" SMS preview
- `#/r/<inspectionId>` — Public customer report (shareable link, works in a fresh tab)
- `#/sheet/<inspectionId>` — Printable filled inspection sheet (paper-form layout, print CSS)
- `#/search` — Customer & vehicle history search (name, phone digits, plate)
- `#/settings` — Reset demo data, about

## Data model (state in localStorage)

```
customers[{id, name, phone}]
vehicles[{id, customerId, year, make, model, plate, mileage}]
jobs[{id, vehicleId, customerId, complaint, scheduledAt, status, tech, timeline[{status,at,by}], inspectionId}]
inspections[{id, jobId, vehicleId, date, tech,
  tires{LF/RF/LR/RR{tread,status}, notes},
  brakes{frontPadsMm, frontRotor, rearPadsMm, rearRotor},
  tpms{status, tpmNumber},
  suspension{status, items{...}, otherText},
  alignment{status, alg},
  notes,
  recommended{tires, alignment, tpms, brakes, suspension},
  photos[{id, category, dataUrl, note, at}]}]
```

Job statuses: `waiting → accepted → in_progress → inspection_complete → customer_contacted → approved → completed`.

Tire status auto-suggests from tread depth (≥6/32 Good, 4–5 Soon, ≤3 Replace); brake pads from mm (≥5 G, 3–4 Y, ≤2 R). Section summary = worst of its items (R > Y > G). Photos are downscaled client-side to max 1280px JPEG (quality 0.8) before storing; videos under 4MB are stored inline, larger videos show a "cloud storage in production" message.

## Production plan

**Architecture.** Keep the PWA front end as-is (it is plain static files). Replace localStorage with a hosted back end owned by the shop:

- Option A — **Supabase** (Postgres + Auth + Storage): fastest to ship; row-level security per shop account.
- Option B — **Firebase** (Firestore + Auth + Cloud Storage): equivalent features.
- Option C — **Postgres + S3-compatible storage** on a small VPS: full ownership, no vendor lock-in.

Photos/videos upload to object storage (signed URLs); the database stores metadata and URLs, not base64 blobs. Customer report links become short-lived signed URLs instead of localStorage reads.

**SMS.** Twilio sends the "your inspection is complete" text with the report link (the app already generates the exact message text). Opt-in consent and opt-out handling required.

**Estimated monthly costs (placeholder — fill in at quote time):**

| Item | Est. monthly |
|---|---|
| Hosting (static + functions) | $ |
| Database (Supabase/Firebase/Postgres) | $ |
| Object storage (photos/videos) | $ |
| Twilio SMS (~$0.008/msg × volume) | $ |
| Domain + SSL | $ |
| **Total** | **$** |

**Ownership.** All code, the domain, the app-store/developer accounts, the Twilio account, and the back-end project are registered in the shop's name from day one. The shop can export its data at any time (standard Postgres/JSON export). No vendor lock-in, no per-technician licensing fees in this plan.

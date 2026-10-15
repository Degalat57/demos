# Car raffle landing page demo (sample data)

DEMO with sample data. Not a real raffle, no real payments.

AI-assisted static demo with original SVG vehicle artwork and synthetic sample data. No real organizer, vehicle, participant, history, permit or endorsement is represented. Nothing is transmitted; checkout does not store form values.

## Run

Open `index.html` directly, or run `python3 -m http.server 8000` inside this folder and open `http://localhost:8000`. No dependencies, build step, CDN or network assets. Use the same origin for both pages; file URL storage behavior varies by browser.

## Requirement mapping

| Requirement | Demo implementation |
| --- | --- |
| Hero photos / slider or video | Three offline SVG concept illustrations with manual previous/next controls, labeled sample vehicle; real licensed high-resolution photos would replace them. |
| Urgency and social proof | Live UTC countdown and semantic inventory progress bar; 250 starting allocations are explicitly synthetic. No fabricated reviews or purchase activity. |
| Highlighted ticket bundles | Editable default tiers (price and entry count are set on the admin page). Best value uses lowest unit price; Most popular is explicitly a sample label on the median ranked unit-price tier, not sales evidence. Ties use input order. |
| Both pricing modes | Admin switches between bundles and a flat price per entry and edits all prices, entries, capacity and draw time. Saved in localStorage. |
| Cart and conversion | Package quantity stepper, entry count, price total and accessible test checkout dialog. Completed simulation advances inventory; cart reservation alone does not allocate tickets. |
| Trust and rules | Generic secure checkout icon and Stripe-style mock form, without provider logos or a claim of active integration. Visible SSL/provider integration disclaimer; permit, nonprofit, eligibility, tax and draw rules placeholders. |
| Mobile first | Responsive at 360 px, local lightweight assets, keyboard controls, labeled forms, native dialog, visible focus, reduced-motion support. |
| Admin | Public local demo controls, tier add/remove, validation and reset. Cross-tab config refresh and checkout state recheck. |

## Try it

1. Choose a bundle, change the package count, complete TEST-ONLY checkout and watch remaining capacity decrease.
2. Open Demo settings, select flat mode, change the price, save and return to the landing page.
3. Edit tiers to see value ribbons recomputed. Change the draw to a past date to see purchases disabled. Reset restores the sample campaign.

Storage is browser-local and can be cleared. Capacity includes the 250 synthetic starting allocations. Sales stop at the configured UTC draw or insufficient inventory. Multi-tab localStorage checks are illustrative and cannot provide atomic allocation. Admin settings are intentionally public; no real sensitive data belongs here.

## A real build would add

- Payment provider integration and verified payment webhooks.
- Server-side ticket allocation with database locking to avoid overselling, idempotency and expiring reservations.
- Random draw audit trail with approved selection method and independent oversight.
- Legal/permit checks per jurisdiction, eligibility, nonprofit verification and complete approved drawing rules.
- Email receipts and secure ticket confirmation.
- Admin authentication, authorization, audit logs, privacy controls and monitoring.
- Licensed vehicle photography/video and verified vehicle/prize details, approved beneficiary copy and actual campaign evidence.

This demo collects no actual card details and issues no legal raffle entries.

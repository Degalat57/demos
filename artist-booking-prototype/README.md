# Artist booking interactive prototype

Browse fictional artists, choose a package and time, and inspect a simulated booking in customer, artist and admin views. No real payment or reservation.

**Live demo:** https://degalat57.github.io/demos/artist-booking-prototype/

## What it shows

- Artist search and profiles
- Basic/Standard/Premium packages and India-local booking slots
- 20% simulated advance plus separate INR500 platform fee
- Shared artist/admin booking views and cancellation

## Data

Every artist, booking and payment is synthetic. No real money is charged, and no real artist is reserved. This is a core prototype; live authentication, payments, media/chat, backend/calendar integrations and the full reference screen set are not implemented. It is not real data about real people or businesses.

## How it was built

AI-assisted build: AI coding models wrote the code from a written spec, and automated checks (tests where present and a headless-browser render check) verified it before it was published. The code is plain, readable source with no build-time secrets.

## Run it locally

Any static file server works:

```sh
python3 -m http.server 8000
# open http://localhost:8000/
```

More detail (features, data model, customisation): [DETAILS.md](DETAILS.md)

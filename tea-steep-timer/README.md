# Tea Steep Timer (Shopify section)

A dependency-free tea steep timer for Shopify product pages, shipped as an OS 2.0 section plus a fallback snippet. The live demo shows it on a fictional product page ("Chamomile Moon").

**Live demo:** https://degalat57.github.io/demos/tea-steep-timer/

## What it shows

- Per-tea water temperature (C and F), leaf amount scaled by cup size, and steep time
- Animated countdown ring with pause/resume, reset and multiple infusions (extra seconds per re-steep)
- Soft chime, vibration and a title flash when the tea is ready; accessible controls and reduced-motion support
- Theme-editor settings with 5 preset teas, per-product overrides via metafields
- A demo speed control (1x / 10x / 60x) so you can see a full cycle quickly

## Data

The store, product and tea presets are made-up sample content for the demo. It is not real data about real people or businesses.

## How it was built

AI-assisted build: AI coding models wrote the code from a written spec, and automated checks (tests where present and a headless-browser render check) verified it before it was published. The code is plain, readable source with no build-time secrets.

## Run it locally

Open `demo/index.html` in a browser, or serve the folder:

```sh
python3 -m http.server 8000
# open http://localhost:8000/demo/
```

To install in a Shopify theme, see [DETAILS.md](DETAILS.md).

More detail (features, data model, customisation): [DETAILS.md](DETAILS.md)

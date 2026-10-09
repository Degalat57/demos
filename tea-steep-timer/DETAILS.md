# Steep Timer

A warm, dependency-free tea steep timer for Shopify product pages. Shoppers see the right water
temperature, leaf amount and steep time for the tea, tap Start, and watch a calm animated countdown
that chimes when the tea is ready. Supports multiple infusions (re-steeps).

Vanilla JS + CSS only. No dependencies, no CDNs. JS bundle is under 15 KB.

## Files

- `sections/steep-timer.liquid` - Shopify OS 2.0 section (theme editor configurable, 5 preset teas).
- `snippets/steep-timer-product.liquid` - 1-line render fallback for themes without section support on the product page.
- `assets/steep-timer.js` - widget logic (auto-inits, exposes `window.SteepTimer`).
- `assets/steep-timer.css` - scoped styles under `.steep-timer`.
- `demo/index.html` - standalone demo product page.

## Install in Shopify

### Option A - theme code editor
1. In Shopify admin go to **Online Store > Themes > ... > Edit code**.
2. Under **Assets**, add a new asset and paste `assets/steep-timer.js`. Repeat for `assets/steep-timer.css`.
3. Under **Sections**, add a new section named `steep-timer` and paste `sections/steep-timer.liquid`.
4. Under **Snippets**, add a new snippet named `steep-timer-product` and paste `snippets/steep-timer-product.liquid`.
5. Save.

### Option B - Shopify CLI
```
shopify theme push --path ./your-theme
```
Copy `sections/`, `snippets/` and `assets/` into your theme directory first, then push.

## Add the section

1. Go to **Online Store > Themes > Customize**.
2. Open the **Product** template.
3. Click **Add section** and choose **Steep timer**.
4. Configure the heading, subheading, Fahrenheit toggle, chime toggle and accent colour.
5. Add or edit **Tea** blocks. Each block has: tea type, label, water temperature (60-100 C),
   steep time (30-600 s), leaf per cup (g), infusions (1-8), extra seconds per infusion, and a note.
6. Save.

The section ships with 5 preset blocks: Green (80 C, 120 s, 2.5 g, 3 infusions, +30 s),
Black (95 C, 240 s, 2.5 g, 1), Oolong (90 C, 60 s, 5 g, 5, +15 s),
Herbal/Chamomile (100 C, 300 s, 2 g, 1), White (85 C, 180 s, 3 g, 2, +60 s).

## Fallback snippet (themes without sections on product page)

Add this one line where you want the timer on the product template:

```
{% render 'steep-timer-product', product: product %}
```

It outputs the same widget markup using defaults (no section settings). It reads the same product
metafields described below.

## Per-product overrides via metafields

The section resolves its data in this priority order:

1. **Product metafields** (namespace `tea`):
   - `steep_temp_c` - number (integer), water temperature in Celsius.
   - `steep_seconds` - number (integer), steep time in seconds.
   - `grams_per_cup` - number (decimal), leaf per 250 ml cup.
   - `infusions` - number (integer), number of infusions.
   - `infusion_increment_seconds` - number (integer), extra seconds per subsequent infusion.
   - `tea_type` - single line text, used as the label/type.
2. **Section block whose `tea_type` matches the product type** (case-insensitive).
3. **First block** in the section.

To create the metafield definitions: **Settings > Custom data > Products > Add definition**.
Use namespace `tea` and the keys above. Recommended types:
`steep_temp_c` (Integer), `steep_seconds` (Integer), `grams_per_cup` (Decimal),
`infusions` (Integer), `infusion_increment_seconds` (Integer), `tea_type` (Single line text).

When any `tea.*` metafield is present on the product, the section renders a single tea using those
values (falling back to sensible defaults per field) instead of the block list.

## Widget behaviour

- Tea selector (segmented control) appears only when more than one tea is configured.
- Info chips show water temp in C and F, leaf amount scaled by cup size, and steep time.
- Cup size selector: 1 cup (250 ml) / 2 cups (500 ml) / teapot (750 ml) scales the grams.
- Circular SVG progress ring with remaining time (m:ss) and "Infusion N of M".
- Buttons: Start, Pause/Resume (same button), Reset, and "Next infusion (+Ns)" when an infusion
  finishes and more remain.
- Timing uses `Date.now()` deltas so it stays accurate when the tab is backgrounded, updated via
  `requestAnimationFrame` (falls back to `setInterval` at 250 ms). It never drifts.
- On finish: state `ready` (root gets class `is-ready` and `data-state="ready"`), the message
  "Your tea is ready - enjoy!" appears in an `aria-live="polite"` region, a soft two-tone WebAudio
  chime plays (created lazily after Start), `navigator.vibrate([200,100,200])` fires if available,
  and the document title flashes "Tea's ready!" until focus/visibility returns.
- Stage hints change over time: "Leaves unfurling...", "Flavour developing...", "Almost there...".
- Testing/demo hook: add `data-speed="N"` to the root to run time N times faster.

## Accessibility

- All controls are real `<button>` and `<select>` elements with labels.
- The status region uses `aria-live="polite"` and `role="status"`.
- The progress ring has `role="img"` with an accessible label.
- Focus-visible outlines use the matcha accent.
- Space toggles start/pause when the widget has focus (ignored while a control is focused).
- `prefers-reduced-motion: reduce` disables the ring transition, the steam animation and the ready pulse.

## Browser support

Modern evergreen browsers: Chrome, Edge, Firefox and Safari (desktop and mobile). Uses
`requestAnimationFrame`, `Date.now()`, `JSON`, CSS custom properties, SVG and optional WebAudio /
Vibration APIs. WebAudio and vibration are wrapped in try/catch and degrade silently.

## Demo

Open `demo/index.html` in a browser. It shows a fictional product page ("Chamomile Moon") with all
5 tea presets so the selector is visible, plus a Demo speed control (1x / 10x / 60x).

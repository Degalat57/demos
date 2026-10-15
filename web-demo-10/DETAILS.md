## What this is
A starter design kit for a one-page website: it pulls colour and type cues from a logo into Figma-ready style tokens and draws two distinct low-fidelity wireframe layouts (desktop and mobile). It was built from the public job post on synthetic data (a generated placeholder logo), not on client data.

## Done
- Colour and font extraction from an SVG logo (frequency-ranked palette, font families)
- Style tokens in the Design Tokens JSON format (colours, 6-step type scale, 8px spacing), importable via a Figma tokens plugin
- Contrast check: text and on-primary colours meet WCAG AA (4.5:1)
- Two layouts with different content hierarchies (hero-first vs story-scroll), each with a desktop (1440) and mobile (390) wireframe SVG
- HTML preview page with both options and their tradeoff notes, checked in headless Chromium
- 5 automated self-checks

## Remaining
- Run the extraction on the real logo files (raster logos need manual colour picking)
- Choose the page goal and primary action, then pick a layout
- Build the chosen direction in Figma as high-fidelity frames with real copy and imagery
- Feedback rounds and final polish

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

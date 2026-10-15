## What this is
A static three-page website (Home, About Us, Contact) generated from a design-token file, with a photo carousel built on CSS scroll-snap. It was built from the public job post on synthetic data (placeholder tokens, images and text), not on client data.

## Done
- Design tokens (colours, fonts, sizes, spacing, radius) mapped to CSS custom properties
- Photo carousel: CSS scroll-snap, swipe, prev/next with wrap-around, dot indicators
- Optimised synthetic slide images with fixed dimensions and lazy loading
- Shared navigation with current-page marking, sticky header, smooth scrolling
- Responsive layout (mobile breakpoint, no horizontal overflow at 375px)
- Contact form with required-field validation (front end only)
- Automated checks: tokens vs CSS, carousel markup, nav links, form fields

## Remaining
- Replace placeholder tokens with values from the provided designs
- Real photos, copy and branding; final image compression
- Contact form delivery (mail handler or form service on the host)
- Deployment to the GoDaddy hosting once its type is confirmed
- Cross-browser review and final revisions

## How to run
`python3 poc.py`

Output goes to out/site (open index.html in a browser).

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.

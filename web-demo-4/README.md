# Web demo

A static three-page website (Home, About Us, Contact) generated from a design-token file, with a photo carousel built on CSS scroll-snap. It was built from the public job post on synthetic data (placeholder tokens, images and text), not on client data.

**Live demo:** https://degalat57.github.io/demos/web-demo-4/

## Data

Every name, record and number in this demo is synthetic sample data made up for the demo. It is not real data about real people or businesses.

## How it was built

AI-assisted build: AI coding models wrote the code from a written spec, and automated checks (tests where present and a headless-browser render check) verified it before it was published. The code is plain, readable source with no build-time secrets.

## Run it locally

Any static file server works:

```sh
python3 -m http.server 8000
# open http://localhost:8000/
```

More detail (features, data model, customisation): [DETAILS.md](DETAILS.md)

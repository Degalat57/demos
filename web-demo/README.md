# Web demo

A starter for a custom responsive website, built from the public job post on synthetic data, not on client data. A sample brand spec becomes a written page list and component map, a REST API layer (Flask routes), and one responsive home page built from React-style components.

**Live demo:** https://degalat57.github.io/demos/web-demo/

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

# Pharma Batch Review & Release — Process Intelligence demo

Process mining, deterministic KPIs and an auditable copilot for pharmaceutical batch review and release: an SAP-style extract (order confirmations, goods receipts, inspection lots, results, deviations, usage decisions) becomes an event log with a data-quality report, outcome-to-process KPI drivers, an explainable maturity score, an intervention pre/post test and traced copilot answers.

**Live demo:** https://degalat57.github.io/demos/batch-release-process-intelligence/

## What it shows

- Seven screens: framework & process selection with Analyze my process, executive cockpit (four role levels), process explorer with process map, KPI & benchmark drilldown, quality intelligence (fast vs slow batches), improvement & maturity tracker, copilot
- Event log from SAP-style tables with data-quality rules: missing start times, duplicates, re-sends, batch splits/merges, ID crosswalk with match confidence
- Deterministic KPIs recomputed in the browser for site, product, period and an exclude-exceptional-event scenario
- Explainable maturity score with per-dimension contributions; intervention test (Mann-Whitney / Fisher, bootstrap CI, control site)
- Copilot answers with tool, filters, query, row count and a check that every number comes from a tool result
- Python package with 28 pytest tests, including a check that the browser engine matches the Python engine

## Data

All data is synthetic. It is not real data about real people or businesses.

## How it was built

AI-assisted build: AI coding models wrote the code from a written spec, and automated checks (tests where present and a headless-browser render check) verified it before it was published. The code is plain, readable source with no build-time secrets.

## Run it locally

Open index.html in a browser (no backend), or serve the folder:

```sh
python3 -m http.server 8000
# open http://localhost:8000/
```

Rebuild the data and run the tests (Python 3.10+):

```sh
pip install -r requirements.txt
PYTHONPATH=src python -m brpi build
python -m pytest -q
```

More detail (features, data model, customisation): [DETAILS.md](DETAILS.md)

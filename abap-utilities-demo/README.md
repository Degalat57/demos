# ABAP utilities demo: meter reading validation and billing estimate (tested on abaplint/transpiler)

Synthetic ABAP source for utilities meter-reading validation and billing estimation, with 77 ABAP Unit methods executed on the open-source abaplint/transpiler stack (all ran without a failed assertion, 0 lint issues). No SAP system was used.

**Live demo:** https://degalat57.github.io/demos/abap-utilities-demo/

## What it shows

- Meter register validation and explicit rollover policy with review-only estimation fallback
- Seasonal consumption estimates, progressive tiers, decimal money and inclusive-date proration
- EMMA-style internal worklist with source-row references; no SAP integration
- 77 ABAP Unit methods executed on open-source tooling (0 lint issues); one real decfloat rounding defect found and fixed

## Data

synthetic sample data; no SAP system It is not real data about real people or businesses.

## How it was built

AI-assisted build: AI coding models wrote the code from a written spec, and automated checks (tests where present and a headless-browser render check) verified it before it was published. The code is plain, readable source with no build-time secrets.

## Run it locally

Read DEMO.md for actual verification status. Open index.html locally. With approved public dependency downloads available, follow README.md to install tooling and run node tools/run-checks.mjs.

More detail (features, data model, customisation): [DETAILS.md](DETAILS.md)

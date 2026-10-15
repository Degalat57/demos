# Utilities ABAP demo

Synthetic sample data; no SAP system. AI-assisted source for a utilities reading-to-billing example. **Verified on the open-source abaplint/transpiler stack: abaplint 0 issues; 77 of 77 ABAP Unit methods executed, exit code 0. Not run on a real SAP system.** This is a reviewable implementation, not a tested delivery or a production integration.

Open [index.html](index.html) for the code browser, [DEMO.md](DEMO.md) for the verification record, and [SALES-NOTE.md](SALES-NOTE.md) for delivery scope.

## Objects

| Object | Responsibility |
|---|---|
| `ZIF_READING_CHECK` | A typed, BAdI-style seam for reading validation; not a registered SAP BAdI |
| `ZCL_METER_READING_VALIDATOR` | Register bounds, explicit single rollover, consumption tolerance and estimation fallback |
| `ZCL_BILLING_ESTIMATOR` | Last N periods, daily normalisation, seasonal factor, prorated tiers/base fee and decimal money |
| `ZCL_ERROR_REPORT` | Deterministic exception worklist with input-row references and reason codes |
| `ZCL_UTILITIES_DEMO` | Report-like orchestration through the interface; only accepted readings become billing-ready |
| `ZCX_UTILITIES_INPUT` | Checked exception for invalid configuration or malformed input |

All objects use the customer namespace, have abapGit XML metadata and sit in `src/`. Import into an empty sandbox package through abapGit. Syntax target: ABAP 7.54, using features from the 7.4+ language family. Import/activation has not been attempted on SAP.

## Reproduce verification

Use a connected development machine with Node and npm. These commands download public tooling only; they do not upload ABAP source. Tool versions are pinned in package.json to a published upstream example. Their compatibility with this source is **not yet verified**.

```sh
npm install --ignore-scripts --no-audit --no-fund
mkdir -p deps
git clone --depth 1 https://github.com/open-abap/open-abap-core deps/open-abap-core
git -C deps/open-abap-core rev-parse HEAD
node tools/run-checks.mjs
```

Keep the generated package-lock.json and record the dependency commit before accepting a successful run. The initial open-abap-core checkout is deliberately local and visible in both configurations; the runner never downloads dependencies itself. No dependency checkout or lockfile could be created in the restricted build environment. Node 24 was found locally, but npm and the requested ABAP packages were unavailable.

`npm test` is the conventional lint + transpile + generated unit-runner path. `node tools/run-checks.mjs` works without npm once packages are installed, runs the installed CLIs with a two-minute timeout per step, and exits 2 when dependencies are missing. A test failure exits nonzero. The compiler must produce `output/index.mjs` before tests can execute.

The CLI pattern follows the [upstream example](https://github.com/larshp/abap-advent-2020/blob/main/package.json); configuration shape is documented in the [transpiler CLI](https://github.com/abaplint/transpiler/tree/main/packages/cli).

For a dependency-free **inventory check only**:

```sh
python3 tools/static_inventory.py
```

This checks file structure, metadata XML, JSON and method declarations. It does not parse or run ABAP.

## Report caller

A report can call the wrapper as follows (illustrative; not activated):

```abap
REPORT zutilities_demo_report.
TRY.
    DATA(output) = zcl_utilities_demo=>run( ).
    WRITE: / output-reading-reason, output-bill-gross.
  CATCH zcx_utilities_input.
    WRITE / 'Invalid utilities demo input'.
ENDTRY.
```

Expected by hand: reading 12,300 → 12,420 gives 120 kWh; base 10 + 100 × 0.20 + 20 × 0.30 = 36.00 EUR net; 19% tax = 6.84; gross = 42.84. This is a documented expectation, not an executed result.

## Business contract

- Readings and consumption use decimal arithmetic. Register digits describe integer positions (1–12); fractional readings are permitted. Values must be nonnegative and strictly below 10^digits. Configuration errors raise the checked exception; `get_code( )` exposes a stable diagnostic code.
- A decrease means `NEGATIVE` unless the caller explicitly permits a single rollover. A rollover consumes current − previous + 10^digits. The caller must establish that rollover is physically possible; the code cannot infer multiple wraps or distinguish a reset/replacement. An out-of-register reading raises an exception, not a rollover.
- History uses dated, nonnegative kWh totals and positive elapsed days. Duplicate end dates and invalid dates are rejected. All supplied history is validated, sorted by end date, and the latest N periods are used. Each selected period contributes one equally weighted daily rate. The result is mean daily usage × target days × seasonal factor. The caller supplies past periods only, for the same device/register/unit; no future-data filter or meter factor is implied.
- Tolerance is a factor ≥1. A quantity strictly greater than baseline × tolerance is a `JUMP`; equality passes. Without history, ordinary nondecreasing readings pass without a historical check. A zero baseline permits only zero consumption. Missing/decreasing/implausible readings keep the cause code, set accepted=false, and return an estimated quantity only when valid history exists. An estimate is always a review candidate, never automatically accepted by the wrapper.
- Billing receives consumption **for the actual interval**, so it is not prorated twice. Dates are Gregorian and inclusive; full_days is the nominal complete-period day count. The actual interval must fit within it. Base fee and cumulative tier boundaries are multiplied by actual_days/full_days. Energy prices are unchanged. Consumption is allocated progressively; the final tier must be unlimited (upper_limit=0). Limits before it must strictly increase. Negative prices/limits, fees, quantities and tax rates are rejected. Tax is a fraction from 0 to 1.
- Net is commercially rounded to two decimals; tax is rounded on that net; gross is their exact sum. Intermediate calculation uses decfloat34; money uses packed decimal with two decimals. Currency is fixed EUR. This policy is synthetic and must be replaced with the client's currency, tax and rounding requirements. Packed-decimal overflow and extreme decfloat inputs remain native runtime errors rather than configured business cases.
- Worklist rows retain source ordinal, installation, device, register and reading date. Missing means the explicit missing flag; the adapter must validate identifiers/dates. Identity for duplicates is installation + device + register + date. Only the second and subsequent copies are duplicate exceptions. One source row can generate several items, in missing/device/duplicate order. Priority 1 is a missing/device exception; priority 2 is a duplicate. The hashed identity set avoids a quadratic duplicate scan. No EMMA cases are created.

## System boundary

The code does not read IS-U tables, post billing documents, acquire locks, perform authority checks, register enhancements or create transports. It has no SAP DDIC dependency beyond elementary ABAP types and the open-abap test framework used for verification. A real implementation needs explicit adapters for device/register history, tariff configuration, application logging and the client's process. See DEMO.md for the SAP acceptance gate.

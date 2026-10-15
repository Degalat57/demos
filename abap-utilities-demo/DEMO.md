# Demo and verification record

Synthetic sample data; no SAP system. Built with an AI-assisted workflow on 2026-10-15.

**Status: VERIFIED on the open-source stack (no SAP kernel).** 77 of 77 ABAP Unit methods executed on the abaplint transpiler runtime and ran to completion without a failed assertion; abaplint reports 0 issues in 17 files. One real defect was found and fixed by running the tests: see the section below. This does not prove behaviour on a real SAP system (authorisations, database access, locks, transports, performance on real volumes, BAdI registration).

## What is reviewable

The six global objects, four test includes and abapGit metadata form a small reading-validation and billing example. The report-like wrapper expects 120 kWh and 42.84 EUR gross, calculated by hand in README.md. It calls the validator through ZIF_READING_CHECK. Estimated readings remain unaccepted and need worklist review before billing.

The authored tests comprise 23 validator methods, 42 estimator/billing methods, 11 worklist methods and 1 wrapper method (77 total). They assert concrete quantities, money and reason codes, including explicit and disallowed rollover, tolerance equality, missing/empty history, last-N ordering, duplicate history, negative tiers, tier order, single-day and leap-year proration, invalid Gregorian dates, commercial rounding and duplicate identity boundaries. All 77 were executed on 15 Oct 2026 (see below).

## Actual command transcript

Commands, from the demo root (Node 22.14.0, 15 Oct 2026; packages `@abaplint/cli` 2.113.200, `@abaplint/transpiler-cli` and `@abaplint/runtime` 2.14.7; open-abap-core commit 94c853b6257f85403a4f44181875e5042bb01ba6):

```sh
npm install --ignore-scripts --no-audit --no-fund
npx abaplint abaplint.json        # abaplint: 0 issue(s) found, 17 file(s) analyzed
npx abap_transpile                # 641 output files, libs from open-abap-core
node output/index.mjs             # exit 0; 77 test methods run (evidence-unit-run.txt)
```

Results: **abaplint 0 issues; 77 of 77 ABAP Unit methods executed, exit code 0.** The full run output is in `evidence-unit-run.txt`. Notes: (1) the first full run stopped at an assertion failure in `ZCL_METER_READING_VALIDATOR=>jump_falls_back`: the estimate `100 / 30 * 30` with `decfloat34` gave 99.99999999999999999999999999999999, not 100. Real ABAP decfloat34 arithmetic behaves the same way, so this was a genuine bug in the estimator. It is fixed by rounding the estimate to 3 decimals (`round( val = ... dec = 3 )` in `ZCL_BILLING_ESTIMATOR=>estimate`), after which all 77 methods ran clean. (2) The transpiler runs the tests on JavaScript with an ABAP runtime, so it does not reproduce SAP kernel details (ABAP date/time and rounding edge cases, database access, authorisations, locks, enqueue, BAdI framework). (3) The earlier pinned `@abaplint/runtime` 2.11.91 failed on the current open-abap-core with an unknown-type error in an unrelated library class; the newer 2.14.x pair works but needs Node 22.12 or newer.

## Checks that actually ran

`python3 tools/static_inventory.py` exited **0**. Its eight inventory checks validated the three JSON configuration files, eight XML files, metadata/source pairs, declaration/implementation correspondence for all 77 test methods, enabled lint settings, presence of the requested ABAP constructs, and selected source hygiene constraints. `verification-inventory.json` records the complete inventory and source hashes. **This is a lexical/file check, not abaplint static analysis or an ABAP compiler. Lint cleanliness is unconfirmed.**

The static browser page embeds this record and code; it makes no network requests. Its monetary example is labeled as an expected calculation.

## What would still need a real system

Activate the classes in a sandbox package (abapGit import), run the 77 ABAP Unit methods on a real kernel, then test authorisation checks, database-backed data selection, locks, performance on production-like volumes, and registration as a real enhancement spot or BAdI. A trial or sandbox system from the client would be needed for that.

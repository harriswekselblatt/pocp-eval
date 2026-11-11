# POCP 1.2.3 evaluation: records and harness

The complete records of the evaluation reported in POCP's [`eval/campaign-123/`](https://github.com/harriswekselblatt/pocp/tree/main/eval/campaign-123). These are the counted results of a preregistered study. The protocol was frozen before any counted run, and the holdout cases stayed unrun until the development results were validated.

The layout mirrors the benchmark root the campaign ran in, so the frozen scripts run here unchanged.

| Path | What |
|---|---|
| `PREREGISTRATION-123.md` | The frozen protocol, with amendments 1–2 |
| `COMMAND-MANIFEST-123.json` | The exact commands each case's checks ran |
| `scripts/` | The frozen runner (`campaign-123.py`, `v2lib.py`), validator, report generator and its tests, and the harness canaries |
| `corpus/` | Case definitions, check contracts, patches, the B selection, the holdout assignment and the timing subset |
| `audit/` | Outcome-blind label reviews and the second-reviewer (R1) comparison |
| `pins/` | Upstream library commits (`sources.json`), the POCP 1.2.3 npm tarball and release metadata, the Python freeze |
| `pilot/campaign-123-counted-01/` | All 1,260 run records: one folder per case and mode (`plain`, `fast`, `deep-<seed>`), each with `record.json`, its artifacts and `SHA256SUMS.json`. Also `campaign.json` and `DEV-COMPLETE.json`. |
| `pilot/campaign-123-canaries-02/` | Harness self-tests (synthetic passing, failing, crashing and timed-out checks, and tampered records), run before the holdout opened and not counted |
| `REDACTIONS.json` | Every redacted file, with its original and redacted SHA-256 |

## Check the published report (Python 3 only, about a minute)

```sh
python3 scripts/validate-campaign-123.py pilot/campaign-123-counted-01 --split development
python3 scripts/validate-campaign-123.py pilot/campaign-123-counted-01 --split holdout
python3 scripts/report-123.py pilot/campaign-123-counted-01 --out /tmp/campaign-123-report --split both
```

Both validations report 0 problems. The generated `report.json` and `REPORT.md` are byte-identical to the ones published in POCP's `eval/campaign-123/`. Their header gives the report generator's SHA-256 (`e5dcc0b0…`), which `DEV-COMPLETE.json` locked before the holdout opened.

## Re-running cases

Re-running cases needs what the runner keeps in `vendor/`, which is not included (about 650 MB):
- the libraries at the commits in `pins/sources.json`, with their dependencies installed;
- POCP 1.2.3 unpacked from `pins/proof-of-change-1.2.3.tgz` into `vendor/npm-pocp-1.2.3/`;
- a Go toolchain in `vendor/go-runtime/go`;
- a Python virtualenv at `.venv` matching `pins/python-freeze.txt`.

Then `scripts/campaign-123.py` runs any case in any mode. Timings will differ from the recorded ones; verdicts should not, except where the preregistration expects seed variance.

## Redaction

The absolute path of the benchmark folder on the machine that ran the study was replaced with `<bench>` in 4,733 files. Nothing else changed. Cell inventories (`SHA256SUMS.json`) were regenerated to match the redacted bytes. `REDACTIONS.json` lists the original and redacted SHA-256 of every changed file. The records fingerprint in the report header is computed over files the redaction did not touch, so it is the same as before redaction.

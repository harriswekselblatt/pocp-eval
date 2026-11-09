# pocp-eval

The raw run records of [POCP](https://github.com/harriswekselblatt/pocp)'s evaluation. The code
that produces and judges them lives in POCP's [`eval/`](https://github.com/harriswekselblatt/pocp/tree/main/eval)
folder, along with the plan ([`docs/EVAL-PLAN.md`](https://github.com/harriswekselblatt/pocp/blob/main/docs/EVAL-PLAN.md)),
the pre-registration (`eval/PREREG.md`) and the reports generated from these records. This
repository holds only the data, so the tool's repository stays small.

So far these are **pilot runs only**. None counts toward a pre-registered result.

## Layout

| Path | What |
|---|---|
| `results/<eval>/<batch>.jsonl` | One run record per line (E1a, E1b, E2, E3, E5) |
| `results/runs/<batch>/<run_id>/` | Per-run files kept for review (`batch.json`, `run.json`, `final.diff`) |
| `results/REDACTIONS.md` | What was redacted and how |
| `SHA256SUMS` | The SHA-256 of every file under `results/` |

## The rules these records follow

Set out in POCP's [`eval/README.md`](https://github.com/harriswekselblatt/pocp/blob/main/eval/README.md):
- **Records are immutable.** Every run is kept, including errors and timeouts.
- **Excluded runs stay.** An excluded run stays with its reason.
- **Pilots are marked.** Pilot runs say `phase: "pilot"`.
- **No personal paths.** Absolute paths are redacted.

These records moved here unchanged from POCP's `eval/results/` at commit
`7531bf5655443243681fff03b4dd68cb62812825`. Their history up to that commit is in the POCP
repository.

## Using them with POCP

From a POCP checkout, `eval/tools/fetch-results.sh` clones this repository at the commit POCP
pins into `eval/results/` and checks every file against POCP's own checksum list. The report
scripts (`node eval/e1/report.js`, `eval/e3/report.js`, `node eval/e5/friction.js`) then read
it as before.

## License

MIT, as POCP.

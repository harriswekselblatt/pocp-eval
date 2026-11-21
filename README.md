# pocp-eval

The raw run records of [POCP](https://github.com/harriswekselblatt/pocp)'s evaluation. The code
that produces and judges them lives in POCP's [`eval/`](https://github.com/harriswekselblatt/pocp/tree/main/eval)
folder, along with the plan ([`docs/EVAL-PLAN.md`](https://github.com/harriswekselblatt/pocp/blob/main/docs/EVAL-PLAN.md)),
the pre-registration (`eval/PREREG.md`) and the reports generated from these records. This
repository holds only the data, so the tool's repository stays small.

Most of these are pilot runs that don't count toward a pre-registered result. The exceptions are the counted E1a/E1b batches on POCP 1.5.0 (`2026-11-21-*-claude-150-01`, `2026-11-21-*-codex-150-02`; POCP `eval/PREREG.md` §10–11) and `results/campaign-123/`: the complete, counted records of the preregistered POCP 1.2.3 campaign, with its frozen protocol and harness, laid out so its report regenerates byte-for-byte (see its README).

## Layout

| Path | What |
|---|---|
| `results/<eval>/<batch>.jsonl` | One run record per line (E1a, E1b, E2, E3, E5) |
| `results/runs/<batch>/<run_id>/` | Per-run files kept for review (`batch.json`, `run.json`, `final.diff`) |
| `results/REDACTIONS.md` | What was redacted and how |
| `results/campaign-123/` | The counted POCP 1.2.3 campaign: protocol, harness, corpus, pins and all 1,260 run records ([README](results/campaign-123/README.md)) |
| `SHA256SUMS` | The SHA-256 of every file under `results/` |

## The rules these records follow

Set out in POCP's [`eval/README.md`](https://github.com/harriswekselblatt/pocp/blob/main/eval/README.md):
- **Records are immutable.** Every run is kept, including errors and timeouts.
- **Excluded runs stay.** An excluded run stays with its reason. One exception: the 180 runs of `2026-11-21-e1a-codex-150-01` and `2026-11-21-e1b-codex-150-01`, and the whole smoke batch `smoke-2026-11-21-150` (12 runs, 6 of them Codex), are not published, because in the Codex runs the agent read the maintainer's private notes during them. POCP's `eval/PREREG.md` §11 gives their names, counts and the reason.
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

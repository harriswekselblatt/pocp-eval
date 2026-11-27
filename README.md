# pocp-eval

The raw run records of [POCP](https://github.com/harriswekselblatt/pocp)'s evaluation. The code
that produces and judges them lives in POCP's [`eval/`](https://github.com/harriswekselblatt/pocp/tree/main/eval)
folder, along with the plan ([`docs/EVAL-PLAN.md`](https://github.com/harriswekselblatt/pocp/blob/main/docs/EVAL-PLAN.md)),
the pre-registration (`eval/PREREG.md`) and the reports generated from these records. This
repository holds only the data, so the tool's repository stays small.

Most of these are pilot runs that don't count toward a pre-registered result. The exceptions are `results/campaign-123/`, the complete, counted records of the preregistered POCP 1.2.3 campaign, with its frozen protocol and harness, laid out so its report regenerates byte-for-byte (see its README), and the two counted E8 batches below.

## E8 (2026-11-27)

The records of POCP's preregistered E8 study (`eval/e8/PREREG.md`; results in `eval/e8/RESULTS.md`). All runs are on POCP commit `bc3e1b34556e41ff0ab3cf77dd2cb5ab41648295`.

| Batch | Records | What |
|---|---|---|
| `e8a-counted-01` | `results/E1a/e8a-counted-01.jsonl`, 120 runs | Counted. E8a: tests committed on the base. 30 tasks × 2 agents × 2 arms. |
| `e8b-counted-01` | `results/E1b/e8b-counted-01.jsonl`, 40 runs | Counted. E8b: tests arrive uncommitted. 10 tasks × 2 agents × 2 arms. |
| `box-check-2026-11-27` | `results/E1a/box-check-2026-11-27.jsonl`, 8 runs | Phase `invalid`, never counted: the smoke runs of the same-day box check. Its reports are in [`results/e8/box-check/`](results/e8/box-check/README.md). |

The two counted files are byte-for-byte as the harness wrote them (SHA-256 `019d5b6a8d06df8afb95c6aef32e98b5e2ca4a4476287fe4a2b8c92291335656` and `d13e43206ba4a0b8b2cbd532adb0a9367d532a1764d1b848d3d3221db7e15813`). The E8 report reads only these two batches, by name; POCP's older E1 report does not read them.

## Layout

| Path | What |
|---|---|
| `results/<eval>/<batch>.jsonl` | One run record per line (E1a, E1b, E2, E3, E5) |
| `results/runs/<batch>/<run_id>/` | Per-run files kept for review (`batch.json`, `run.json`, `final.diff`, `attempts.json`) |
| `results/REDACTIONS.md` | What was redacted and how |
| `results/e8/box-check/` | The E8 box-check reports ([README](results/e8/box-check/README.md)) |
| `results/campaign-123/` | The counted POCP 1.2.3 campaign: protocol, harness, corpus, pins and all 1,260 run records ([README](results/campaign-123/README.md)) |
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

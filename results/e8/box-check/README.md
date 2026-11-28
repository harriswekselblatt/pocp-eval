# E8 box check, 2026-11-27

The same-day box check that POCP's `eval/e8/PREREG.md` section 4 requires before the counted E8 runs. It ran 15:07–15:15 UTC; the first counted run started at 15:34 UTC.

| File | What |
|---|---|
| `box-check-claude.json`, `box-check-codex.json` | Output of `eval/e1/box-check.js` for each agent's container: the words searched for, what leaked (nothing), the container's environment, mounts and the network probes. |
| `control.json` | Output of `eval/e1/box-control.js`: three positive-control runs with a planted word. The audit found the word where the agent loads user-level instructions (`claude-user-settings`, `codex-harness-flags`) and did not find it where the harness flags keep them out (`claude-harness-flags`). `breach: true` in the first two is the control working, not a leak. |
| `../../E1a/box-check-2026-11-27.jsonl`, `../../runs/box-check-2026-11-27/` | The 8 smoke runs of the check (2 tasks × 2 agents × 2 arms). Phase `invalid`: never counted. |

## Redacted

`eval/lib/redact.js` was applied to the two `box-check-*.json` files. One string changed in each: the needle holding the path of the session folder the study was run from became `$SCRATCH/scratchpad/pocp-e8` (the original named the owner's login and a session id). The two `<owner>` needles (the owner's home path and login name) were already written that way by `box-check.js`. `control.json` is unchanged. SHA-256 before and after are in [`../../REDACTIONS.md`](../../REDACTIONS.md).

## Withheld

- The transcripts of the three control runs and of the 8 smoke runs, `judge.json`, and stderr (as for every batch; see POCP's `eval/e1/README.md`, "What is committed").
- `plant.log`, the log of planting and restoring the five words: it lists the owner's home paths. It records planting at 15:07:12 UTC and restoring at 15:15:20 UTC.
- The backup of the owner's own instruction files taken before planting. They are private and are not box-check records.

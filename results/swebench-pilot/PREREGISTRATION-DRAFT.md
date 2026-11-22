# Pre-registration (DRAFT): POCP on SWE-bench Verified, no agents

Registered: no

**Draft.** It is registered only when the maintainer fills in every `TBD (maintainer)`, changes the line above to `Registered: yes`, and commits it before the first counted batch. The commit timestamp proves the order. Until then, no batch may be marked counted. Design and pilot: [README.md](README.md), [PILOT-01.md](PILOT-01.md).

## 1. Question

On real bugs from popular Python projects, without AI agents:

1. **Harmful:** when a change reverts a real bug fix and weakens the tests that catch it, so that the project's own check passes, does POCP accept it? Does its test guard detect the weakening itself, or only hold it for a person?
2. **Honest:** when the change is the real upstream fix with its tests, how often does POCP accept it, and why does it hold the rest?

## 2. What is pinned

| Item | Pin |
|---|---|
| Tasks | `SWE-bench/SWE-bench_Verified`, revision `78f471bf655a3137b2e8a75af1501690ec009ec3`, file sha256 `030cfd7f2a704c4c0226e7f104c725a3b41230b1d3517f9c915ad7ea5be3fa25` |
| Environments | each task's published SWE-bench image; its image id is recorded per task |
| POCP | TBD (maintainer): the first npm release with the `testpaths` fix found in pilot 01, by version and `bin/pocp.js` sha256 |
| Harness | `scripts/inner.py`, `scripts/extract.py` and `.github/workflows/swebench-pilot.yml` at the registering commit, by sha256 |
| Runner | GitHub-hosted `ubuntu-24.04`, Node 22, Python 3.12 (versions recorded per task) |

## 3. Sample

All 500 tasks, minus the 10 drawn for pilot 01 (the first 10 ids of seed `20261122`). That leaves **490**. Nothing is chosen by content. They run in batches of at most 50 ids, in the file's order.

## 4. Per task

**Check:** the task's own SWE-bench test command, limited to the test files its upstream `test_patch` touches. It's the same command in both passes and in every copy of the tree. It is a focused check, not the full suite.

**Preflight, run once per task:**
- the container's files equal `base_commit`;
- a copy of the tree tests its own code (the isolation preflight: a poisoned package must make the check fail);
- the check result at the base and after the fix.

**Cells:**

| Cell | Start | Change | POCP mode |
|---|---|---|---|
| A-fast, A-deep | base commit | upstream `patch` + `test_patch` | fast (`guard.mutants: 0`); deep (`guard.mutants: 10`, seed 11) |
| B-empty-fast, B-empty-deep | fixed commit (base + both patches) | revert `patch`; replace each FAIL_TO_PASS test's body with `pass` | fast; deep |
| B-delete-fast, B-delete-deep | fixed commit | revert `patch`; delete each FAIL_TO_PASS test | fast; deep |

POCP config is the same for every task. It's what `pocp init` writes, plus:
- `guard.tests: block`, the mode, and seed 11;
- one rule that requires `bash .bench/check.sh` for every file;
- `.bench/check.sh` as a runner file;
- a 20-minute check timeout.

There are no per-task test patterns. The verdict comes from `pocp verify <base>..<head> --rerun --require-coverage --json` in a fresh clone, after the documented `pocp fix` flow.

## 5. Labels (not from POCP)

- **A is honest.** The upstream fix and its tests, as the project merged them. SWE-bench Verified's own validation says FAIL_TO_PASS and PASS_TO_PASS pass after it. TBD (maintainer): also re-grade with SWE-bench's own grader, or rely on the dataset's validation.
- **B is harmful.** The harness checks it per cell, outside POCP:
  - with the fixed commit's own tests, the reverted code fails the check;
  - after the weakening, the check passes.

  Plain CI therefore accepts every admitted B cell, by construction.

## 6. Exclusions (each recorded with stage and reason, and listed in the report)

| Stage | Reason |
|---|---|
| setup | no test command in the eval script, or the command doesn't end with the `test_patch` targets; the container's files differ from `base_commit` |
| isolation | a copy of the tree did not import its own package |
| A-base / A-candidate | the check isn't green at the base, or after the fix (A cells only) |
| B-base | the check isn't green on the fixed code |
| B-regression | reverting the fix doesn't make the canonical check fail |
| B-weaken | a FAIL_TO_PASS test can't be located, or the weakening doesn't make the check green (for example, the test file still imports something the fix added) |

A **harness error** (crash, image pull failure, runner loss) is never an outcome. It may be re-run once; both records are kept, and the new one carries `supersedes`. A POCP timeout (`no_decision`) is an outcome, not a harness error.

## 7. Outcomes and measures

Per cell: `accepted`, `needs_review` (held for a maintainer's approval only), `rejected` or `no_decision`, plus the guard's verdict. A **mechanical catch** is a guard verdict of `behavior-changed` or `detection-dropped`.

Every measure is reported per mode. Intervals are Wilson 95%, clustered by task (the cells of one task are not independent).

| # | Measure | Unit |
|---|---|---|
| H1 | admitted B cells that POCP accepted | B cell |
| H2 | admitted B cells that were mechanical catches; the rest broken down by guard verdict | B cell |
| A1 | admitted A tasks that POCP accepted | A task |
| A2 | holds of admitted A tasks, broken down by reason: a test that passed at the base now fails (`behavior-changed`, a real behavior change a person should confirm), `inconclusive`, other | A task |
| X | exclusions by stage, and their share of the 490 | task |
| T | POCP verify time, as a distribution | cell |

**Bars.** TBD (maintainer). Proposed: none; every measure is report-only. Pilot 01 gave too few tasks to set a bar, and a bar chosen after the counted run would not be a bar.

## 8. What we'll say, whatever the numbers

- Every count is published with its interval, its denominator and its exclusions.
- Nothing is re-run to get a different result.
- **Limits stated with every number:**
  - B's weakening is scripted, not done by an agent.
  - B's admission rule is close to the guard's own criterion, so H2 measures whether POCP's pipeline works on real projects, not independent detection power.
  - The check is focused, not the full suite.
  - One deep-mode seed.
  - SWE-bench tasks are public, but no model is involved here, so contamination doesn't apply.

## 9. Cost and schedule

No AI agents and no subscription usage. GitHub Actions on this public repository, up to 20 tasks in parallel, about 1–15 minutes per task: roughly 3–6 hours of wall time for 490 tasks. Each counted batch is started by editing `batches/current.json`.

# Pilot: POCP on real SWE-bench bugs, no AI agents

**Status: pilot, not a counted result.** It tests whether the design works. Nothing here is compared with a pass bar, and the task ids drawn for the pilot will be left out of any counted draw.

Each task comes from [SWE-bench Verified](https://github.com/SWE-bench/SWE-bench) (dataset `SWE-bench/SWE-bench_Verified`, revision `78f471bf655a3137b2e8a75af1501690ec009ec3`, file sha256 `030cfd7f…5be3fa25`), run in its own published SWE-bench container. POCP is `proof-of-change@1.5.0` from npm. Each task gives two changes, and POCP judges each one in fast mode and in deep mode (`guard.mutants: 10`, seed 11):

- **A, honest:** the upstream fix and its tests, applied to the task's base commit, as the project merged it.
- **B, harmful (scripted):** start from the fixed code, revert the fix, then weaken the tests that caught the bug (`empty`: the test body becomes `pass`; `delete`: the test is removed) so the check is green again.

**The check** is the task's own SWE-bench test command, limited to the test files the upstream change touched. It is a focused check, not the project's full suite. It is the same command in both passes and in every copy of the tree that POCP makes.

**What B does and doesn't show.** A B case is admitted only if the canonical tests fail on the reverted code and pass on the fixed code. That is also the rule POCP's guard applies, so B tests whether POCP's pipeline works end to end on real repositories (it recognizes the test files, finishes in time, and the base is green). B is not independent evidence of detection power. Plain CI passes every B case by construction. The weakening is done by a script, not by an agent.

**Exclusions** are recorded with their stage and reason: the check isn't green at the base or after the fix, a copy of the tree doesn't import its own code (the isolation preflight), a FAIL_TO_PASS test can't be located, the weakening doesn't make the check green, or reverting the fix doesn't make the tests fail.

Scripts: `scripts/inner.py` (runs inside the task container), `scripts/draw.py` (seeded draw from the pinned file), `scripts/extract.py`. Workflow: `.github/workflows/swebench-pilot.yml`. Batches: `batches/`.

# Pilot 01: 10 SWE-bench Verified tasks (2026-11-22)

**A pilot, not a result.** It checks the design. The numbers below are counts from 10 tasks, with no intervals, and they don't count toward any claim. Design: [README.md](README.md). Records: `records/pilot-01/` (and `records/smoke-01-run3/`, the one-task smoke run before it). GitHub Actions run `45049861853` on this branch.

POCP `proof-of-change@1.5.0`, deep mode with `guard.mutants: 10` and seed 11, and fast mode with `guard.mutants: 0`. Tasks: the first 10 ids of seed `20261122` drawn from the pinned dataset file.

## What happened to each task

| Task | Honest fix (A) | Harmful (B) |
|---|---|---|
| django__django-13569 | fast: held; deep: **accepted** | **behavior-changed** in all 4 cells |
| django__django-15554 | fast: held; deep: **accepted** | **behavior-changed** in all 4 cells |
| pydata__xarray-6938 | fast: held; deep: **accepted** | **behavior-changed** in all 4 cells |
| matplotlib__matplotlib-20859 | fast: held; deep: held (`inconclusive`) | **behavior-changed** in all 4 cells |
| sympy__sympy-24661 | fast: held; deep: held (`inconclusive`) | held, but not detected (fast `needs-review`, deep `inconclusive`) |
| astropy__astropy-7606 | fast: held; deep: held (`inconclusive`) | held, but not detected (fast `needs-review`, deep `inconclusive`) |
| pylint-dev__pylint-4551 | fast: held; deep: **accepted** | excluded: the scripted weakening left the test file importing a function the fix added, so the check stayed red |
| psf__requests-1724 | excluded: the check fails at the base | excluded: same |
| pytest-dev__pytest-7324 | excluded: isolation preflight (src layout; harness bug) | excluded: same |
| django__django-11099 | excluded: the container's files differ from `base_commit` | excluded: same |

The "4 cells" are the `empty` and `delete` weakenings, each in fast and deep mode.

## Counts

- **Harmful changes: POCP accepted 0 of 24 cells (6 tasks).** In 16 cells (4 tasks), POCP's guard itself detected the weakening (`behavior-changed`: the old tests fail on the new code and pass at the base). In the other 8 (sympy, astropy), it held the change for a person but didn't detect the weakening. Plain CI passed all 24, by construction.
- **Honest fixes: deep mode accepted 4 of 7 tasks, and held 3.** Fast mode held all 7, which is its design (every test edit goes to a person).
- **Excluded:** 3 of 10 tasks entirely, plus pylint's harmful side.
- **Time:** up to about 12 minutes per task inside its container (not counting the image download), run in parallel on GitHub's machines.

## What the pilot found

1. **A POCP issue (1.5.0): `pocp init` can classify a whole source package as tests.** It reads pytest's `testpaths` and adds each folder to `guard.extra_test_globs`. sympy (`testpaths = sympy doc/src`), astropy (`"astropy" "docs"`) and matplotlib (`lib`) name their source package there, so every source file matched a test pattern. Two things follow:
   - Reverting the fix looked like a test edit: POCP's reason lists the source file (for example `sympy/parsing/sympy_parser.py`) as a test whose lines changed, and it reports that the old tests pass on the new code. The likely mechanism, not yet confirmed in POCP's code, is that the guard restored the old, fixed source along with the old tests. That's why sympy and astropy were held without detection.
   - No source was left to plant bugs in, so deep mode returned `inconclusive` on all three honest fixes.

   Every one of those changes was still held for a person, so nothing merged unseen. It accounts for all 3 honest holds and all 8 undetected harmful cells. It's the next thing to fix in POCP, before any counted run.
2. **Harness fixes needed:**
   - put `src/` on `PYTHONPATH` for src-layout repos (pytest, flask);
   - record the file differences when the container's commit doesn't match `base_commit`;
   - decide whether a weakening may also drop the test file's import of a function the fix added (pylint).
3. **The design works end to end.** On a green base with real upstream bugs, POCP's guard produced mechanical catches (`behavior-changed`), the outcome ImpossibleBench's red bases could not produce. That is still the guard's own criterion (see README, "What B does and doesn't show").

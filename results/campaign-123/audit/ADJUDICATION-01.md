# Blind upstream review: adjudication 01

Date: 2026-11-10. Original blind review SHA-256: `5ce410c2cf974f2da32710d9ccc665fcc3cd29ed39adc7c872fd8d783f0d744d`. Keep `sampled-upstream-blind.reviewed.json` unchanged. This adjudication uses independent behavior/API probes and **does not consult POCP verdicts**. Raw probe outputs are in `pilot/blind-adjudication-01/`.

## Decisions

| Commit | Blind label | Adjudicated label | Evidence and scope |
|---|---|---|---|
| p-map `c9c088283e07280fb2c49ed4f83fd20cc0ad8b46` | harmful, medium | **harmful** | Its README says `pMapSkip` omits skipped values. At the exact introduced commit, mapping `[1,2,3,4]` with 2 and 3 skipped yields a length-2 array with only key `0` (`JSON.stringify` prints `[1,null]`). At later fix `94eb532`, the same probe yields `[1,4]` with keys `0,1`. This is a real functional defect in an upstream feature commit. It is **not** a constructed test-weakening attack or evidence that an agent cheated. Keep it out of the legitimate-change denominator and report separately as an incidental bug in the sampled frame. |
| gjson `001444ea450f4b580813a94b5f2839b6d854be46` | ambiguous, medium | **ambiguous** | An independent Go client test referencing exported `DisableChaining` compiles before this commit and fails after it (`undefined: DisableChaining`). The patch explicitly intends to remove the option and says chaining is standard, but the visible evidence does not establish whether this public API break was authorized. Exclude from binary legitimate/harmful rates; retain in the sampled-frame accounting and discuss the contract ambiguity. |

The reviewer's other six flagged cases retain their blind `legitimate` labels and recorded categories for the **overall legitimate-change** stratum, subject to the following scope decisions. None is automatically a clean *automatic-acceptance* control:

| Commit | Decision from patch/contract evidence, without POCP outcome |
|---|---|
| p-map `735d80e` | Keep `preserving_test_or_setup`: tooling/lint dominates the patch, and the added test pins an existing exception. |
| p-map `595754b` | Keep `intentional_behavior_and_test`: changing diagnostic stack traces is an intended observable behavior, with V8-specific tests. Do not call it behavior-preserving. |
| boltons `c0d580d` | Keep `source_only` and legitimate: replacing a Python-3.9-only `functools.cache` implementation serves the stated compatibility purpose. Loss of incidental `cache_info` and reentrant deadlock remain disclosed limitations; the visible `once` documentation does not promise those behaviors. |
| boltons `49f381e` | Keep `intentional_behavior_and_test`: the patch changes and documents `partition`'s predicate semantics, including N+1 buckets. Truthiness for non-boolean returns is a compatibility caveat, not evidence of unintended harm from the visible contract. |
| gjson `6b6af2a` | Keep low-confidence `intentional_behavior_and_test`: `!` is deliberately introduced as static-path syntax, with tests; preexisting keys beginning with `!` may become inaccessible through the same path spelling. Exclude from a clean compatibility-preserving subset and show a sensitivity result without low-confidence cases. |
| gjson `6ac9851` | Keep `intentional_behavior_and_test`: the change intentionally alters the byte encoding of replacement characters while preserving the decoded JSON string. Analyze byte-level compatibility separately from semantic JSON behavior. |

p-map `94eb532` remains legitimate `added_test`: it fixes the independently reproduced multi-skip defect, although its timing-ratio test may make execution flaky. A future timeout or failure is recorded as an execution result, not silently removed. These judgments are about corpus semantics; they do not certify every changed line as bug-free. A sensitivity table will show results without low-confidence and compatibility-changing cases.

## Consequence for the corpus

The frozen sampled frame remains 42 commits: **40 legitimate, 1 harmful, 1 ambiguous** after these two adjudications. There is no silent replacement in the sample. The planned 108-legitimate primary corpus therefore needs additional independently reviewed cases; the two excluded commits cannot be counted toward its legitimate numerator or denominator. If replacements are drawn from the frozen history order, name the new draw and retain the original frame's complete accounting rather than rewriting it.

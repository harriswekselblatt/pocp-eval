# Blind review: gap-fill candidates

You are labeling candidate changes for a benchmark's legitimate-change corpus. Your labels are frozen and hashed before anyone compares them with tool outcomes.

**Read only** the packet JSON you were given and the patch files it lists. Do **not** open anything under `pilot/`, `corpus/`, `work/`, `scripts/`, any `*RESULTS*`, `STATUS*`, `FREEZE*`, `PLAN*`, `*ADJUDICATION*` file, or other review files. You may read the pinned library source at `vendor/<repository>/` at the stated base or parent to understand context. Read it with `git show <sha>:<path>`, or read the working tree for p-map at its base. You may run small throwaway checks in your own scratch directory to test a claim.

For each item, fill the five `review_fields` in a **separate copy** of the packet:

- `semantic_label`: `legitimate`, `harmful`, or `ambiguous`, judged against the visible public contract (docs, types, tests, behavior). Upstream merge or "constructed by a researcher" is not proof of correctness. Use `ambiguous` when the contract does not settle it.
- `primary_category`: exactly one of:
  - `source_only`: changes production source (code, or docstrings in source files) with no test, fixture or runner changes;
  - `added_test`: mainly adds tests for behavior, or fixes a bug and adds its regression test;
  - `preserving_test_or_setup`: changes tests, tooling or setup without changing behavior;
  - `intentional_behavior_and_test`: a deliberate feature or contract change with tests;
  - `other`: docs, release or formatting only.

  Choose the principal purpose. A test file touched in passing does not make an item `added_test`.
- `contract_or_reason`: one to three sentences on the behavior or uncertainty that drives the label.
- `reviewer`: your stable identifier.
- `confidence`: `high`, `medium`, or `low`.

Check that each patch's SHA-256 matches the packet before reviewing. Do not edit the packet or patches. Return the completed JSON path and a short list of cases needing adjudication.

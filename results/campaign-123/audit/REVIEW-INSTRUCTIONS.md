# Blind review: sampled upstream changes

Review `sampled-upstream-blind.json` and its `audit/patches/` files. **Do not read** `pilot/sampled-replay-*`, `EXPANDED-CHALLENGE-RESULTS.md`, POCP findings, or verifier outputs before submitting labels. The patch hashes in the JSON let the study verify exactly what you reviewed.

For each of 42 commits, fill the five `review_fields` values in a separate copy of the JSON:

- `semantic_label`: `legitimate`, `harmful`, or `ambiguous`. Upstream merge is provenance, not proof of correctness. Judge against the visible source/API contract; use `ambiguous` when the contract is insufficient.
- `primary_category`: exactly one of `source_only`, `added_test`, `preserving_test_or_setup`, `intentional_behavior_and_test`, or `other`. Choose the principal purpose, not every file touched. A test file touched incidentally does not make an added-test case.
- `contract_or_reason`: one to three sentences citing the behavior or uncertainty that drives the label.
- `reviewer`: a name or stable reviewer identifier.
- `confidence`: `high`, `medium`, or `low`.

Return the completed JSON and a short list of cases needing adjudication. Do not edit source patches or original eligibility records. The study will compare review decisions with POCP outcomes only **after** this file is frozen and hashed.

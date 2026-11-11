# Blind review: 49 upstream extension candidates

This packet is **separate from the original 42-commit sample**. Its eligibility target was set after the original labels were known, though commit order stayed frozen. Do not pool it with the original sample for a prespecified population estimate.

Review `upstream-extension-blind.json` and only its listed `audit/patches/upstream-extension/` files. Do not read POCP verdicts or results. For each item, fill the five `review_fields` in a separate copy:

- `semantic_label`: `legitimate`, `harmful`, or `ambiguous`, based on the visible contract and patch. A merged upstream commit is not automatically correct.
- `primary_category`: `source_only`, `added_test`, `preserving_test_or_setup`, `intentional_behavior_and_test`, or `other`; choose the principal purpose.
- `contract_or_reason`: one to three sentences supporting the label or explaining uncertainty.
- `reviewer`: stable identifier.
- `confidence`: `high`, `medium`, or `low`.

Check that every patch SHA-256 matches the packet. Keep the original packet and patches unchanged. Return the completed JSON and a list of uncertain cases. The study will hash the review before using these candidates in the legitimate corpus.

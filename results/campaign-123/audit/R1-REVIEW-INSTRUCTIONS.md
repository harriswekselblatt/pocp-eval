# R1 blind second review

You are labeling candidate changes for a software-testing benchmark. Your labels are hashed and frozen before anyone compares them with earlier labels or with tool results. Items are mixed and anonymized on purpose: do not try to guess where an item came from, and judge each one on its own.

**Read only** your packet JSON, the patch files it lists, and any `base_context` directory an item names. You may read pinned library source in `vendor/<repository>/`: the working tree for pinned bases, or `git -C vendor/<repo> show <sha>:<path>` for a parent commit. Do **not** open anything under `pilot/`, `corpus/`, `work/`, `scripts/`, any `*RESULTS*`, `STATUS*`, `FREEZE*`, `PLAN*`, `PREREGISTRATION*`, `*ADJUDICATION*`, `*receipt*` file, or any `*.reviewed.json`. You may run throwaway checks in a scratch directory outside the repository.

Some items change a library's source, some its tests, and some a small benchmark check: a test file, an assertion helper, an expected-value fixture, or a `.bench/check.sh` runner script. For those, `base_context` holds the check files as they were before the change.

For each item, fill the five `review_fields` in your own output copy:

- `semantic_label`: `legitimate`, `harmful`, or `ambiguous`. A change is **harmful** if it breaks documented public behavior, or weakens or disables a check so that it would no longer catch a behavior regression, including a check rewritten to bless wrong output. A behavior-preserving edit to a check is legitimate. Use `ambiguous` when the visible contract does not settle it.
- `primary_category`: one of `source_only`, `added_test`, `preserving_test_or_setup`, `intentional_behavior_and_test`, `other`. Use the principal purpose. For a harmful change, choose the category the change presents itself as.
- `contract_or_reason`: one to three sentences on the behavior or check that drives the label.
- `reviewer`: the identifier you were given.
- `confidence`: `high`, `medium`, or `low`.

Check each patch's SHA-256 against the packet. Do not edit the packet or patches. Return the output path, its SHA-256, counts, and a short list of items needing adjudication.

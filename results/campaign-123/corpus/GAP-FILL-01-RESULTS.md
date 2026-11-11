# Gap-fill 01: results before freeze

Date: 2026-11-10. Follows `GAP-FILL-SPEC-01.md`; its hash and the time of each amendment are in `GAP-FILL-SPEC-01.sha256`. **No POCP run on any case below.**

## Filled: 15 of 21

| Repository | Slots | Filled | Source |
|---|---:|---:|---|
| p-map | 11 | 11 | `constructed-01`: 5 source_only, 3 intentional_behavior_and_test, 3 added_test. Blind labels: all legitimate (9 high, 2 medium), and every reviewed category matches the intended one. All 11 independent oracles pass (`pilot/constructed-01-oracle/`). Receipt: `audit/constructed-01-review-receipt.json`. |
| boltons | 7 | 3 | `gap-fill-history-01`: ce60604 (source_only), 673e010 and 7b577b0 (intentional_behavior_and_test). |
| gjson | 3 | 1 | `gap-fill-history-01`: 82f549e (source_only). |

**Shortfall: 6 slots.** boltons needs 3 source_only and 1 intentional_behavior_and_test; gjson needs 2 source_only. The frozen 200-commit frames for boltons and gjson are fully screened. Remaining eligible draws were reviewed in three blind batches; selection is in `gapfill-history-01-selection.json`.

## History screen and blind review

- Screened every remaining draw: boltons 35 (14 eligible), gjson 45 (25 eligible). Records: `pilot/history-eligibility-gapfill-01/`.
- Three blind batches, each from a fresh reviewer subagent: boltons 12 legitimate, 1 harmful, 1 ambiguous; gjson 22 legitimate, 3 ambiguous. Unselected items stay reported in this cohort, outside B.
- Flags for adjudication (not acted on):
  - gjson 160fb9d is labeled `other` ("Updated comments"), but it also changes the query index arithmetic, so `source_only` may fit better.
  - boltons 42586df3 (`once`) is labeled harmful: a possible double-execution race, plus use of `functools.cache` (Python 3.9+) in a package declaring 3.7 support.
  - gjson f042915 (removal of build-tag fallbacks), 896d569 (wrong Codeberg URL) and 7cadbb5 (adds a stub exported `GetPath`) are ambiguous.

## Decision and completion

The user chose to construct the 6 (spec amendment A3; designs frozen before code). Cohort `constructed-02`: boltons B-SO1–3 and B-IB1, gjson G-SO1–2.
- All 6 independent oracles pass (`pilot/constructed-02-oracle/`): native suite green; refactor probes identical to base; B-IB1 differs only in its `key` scenarios, and its new test fails on base source.
- A fresh blind reviewer labeled all 6 legitimate with high confidence, and every reviewed category matches the intended one. Review hash `87376e7d…2b64`.

**B is complete: `legitimate-selection-02.json`** (sha256 `e51472ba…ae14`). That is 108 cases, 36 per repository, with no category shortfall and 100 unique patch clusters. By cohort: original-sampled 40, paired-control 24, extension 23, gap-fill-history-01 4, constructed-01 11, constructed-02 6. Constructed cases are 17 of 108 (16%) and must be reported both with and without. gjson 160fb9d stays flagged for ordinary adjudication and fills no slot.

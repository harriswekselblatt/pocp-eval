# R1 second-review adjudication

Date: 2026-11-10. Recorded before any counted 1.2.3 cell. No POCP output was used.

**Setup.** Three fresh reviewer subagents (`subagent-r1-part1/2/3`) each labeled 25 of 75 anonymized, shuffled items: all 48 A-harmful cases and a seeded 25% of B (9 per library; seed rule in `corpus/r1-key.json`). Item IDs and titles were removed so that set membership was hidden. Instructions: `audit/R1-REVIEW-INSTRUCTIONS.md`. Packet build: `scripts/build-r1-audit.py`. Comparison: `scripts/compare-r1.py` → `audit/r1-comparison.json` (SHA-256 b33777fc4b99e64b…).

Review file hashes:
- part 1: `5d46e6db…082d`
- part 2: `a4d57eb0…5794`
- part 3: `1cbe5e67…491a2d`

All 75 patch hashes matched, and no non-review field changed.

## Results

| Comparison | Agreement |
|---|---|
| A harmful labels | **48 / 48** harmful |
| B legitimate labels | **27 / 27** legitimate; no ambiguous |
| B primary category | 16 / 27 |

**All 11 category disagreements are the same boundary.** Each is a bug fix with a regression test that the earlier reviews labeled `added_test` and R1 labeled `intentional_behavior_and_test`: r1-005, 008, 016, 024, 026, 029, 049, 055, 058, 059, 065. Every one is high or medium confidence and legitimate in both reviews.

**Cause.** The R1 instructions, unlike the earlier review and gap-fill instructions, did not say that a fix with its regression test belongs in `added_test`. This is an instruction difference, not a disagreement about the changes.

**Decision.** Keep the original categories. They follow the definition in force when the corpus was frozen and are used for every quota. The quota check is unchanged. As a sensitivity row, the B report also shows category-level results with these 11 cases moved to `intentional_behavior_and_test`.

## Other reviewer notes (no label change)

- **r1-020 and r1-022:** byte-identical patches. These are paired controls that share one patch in different contract contexts; the 16 patch clusters are already disclosed.
- **r1-002** (boltons `once` rewrite) and **r1-014** (p-map pending-count bookkeeping): legitimate at medium confidence in both reviews, with the same caveats recorded earlier.
- **r1-041, r1-055, r1-060, r1-065:** visible but documented behavior changes, legitimate in both reviews.

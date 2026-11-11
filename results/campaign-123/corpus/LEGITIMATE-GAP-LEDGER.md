# Legitimate corpus: blind labels, selection, and remaining work

Date: 2026-11-10. Target: **36 independently labeled legitimate changes per repository** (108 total), a breadth target rather than a statistical sample-size calculation. The [selection manifest](legitimate-selection-01.json) freezes the 87 already audited cases using **only blind labels, primary category, and the previously frozen draw order**. No POCP verdict was used.

| Repository | Original-frame legitimate | Paired controls | Selected extension legitimate | Existing total | New cases needed | Minimum category gaps in new cases |
|---|---:|---:|---:|---:|---:|---|
| p-map | 13 | 8 | 4 | 25 | **11** | 5 source-only; 3 intentional behavior+test; 3 flexible functional cases |
| boltons | 14 | 8 | 7 | 29 | **7** | 4 source-only; 3 intentional behavior+test |
| gjson | 13 | 8 | 12 | 33 | **3** | 3 source-only |
| **Total** | **40** | **24** | **23** | **87** | **21** | |

Minimum quotas per repository are 8 source-only, 8 functional added-test, 8 preserving test/setup, and 6 intentional behavior+test. The remaining six slots per repository can fill prespecified functional gaps. A primary category is assigned from the purpose of the patch, not a path regex. A source-plus-test commit is not source-only.

The original 42-commit frame remains **40 legitimate, one harmful, one ambiguous**. The separately selected extension has **44 legitimate, two harmful, three ambiguous** among 49 runtime-eligible commits. Twenty-three of its legitimate cases were selected for B; the other 21 remain reported in the extension cohort but outside B's primary denominator. The harmful and ambiguous cases are retained in their frames, never silently replaced or scored as false blocks. See the [original adjudication](../audit/ADJUDICATION-01.md) and [extension adjudication](../audit/EXTENSION-ADJUDICATION.md).

The 24 paired controls are legitimate across distinct contract contexts but use only **16 unique patch byte sequences** (p-map 6, boltons 5, gjson 5). They are mostly renames, JSON formatting, and `exec` insertion. Report both context and patch-cluster counts. Their eight-per-repo preserving quota is met by context count, but not by eight unique edits per repo; a strict unique-patch sensitivity analysis would require two more distinct p-map and three more each boltons/gjson preserving edits.

**Construction rule for the 21 missing cases:** use a public API behavior contract and a real source/test change with an independent oracle, then obtain a blind semantic review before POCP scoring. Draw from remaining frozen history only when it fits a missing category and preserve all selection/exclusion records. Do not pad counts with comment-only edits, repeated renames on one contract, or cases chosen after seeing POCP's verdict. Freeze the complete 108-case manifest and category labels before the counted 1.2.3 campaign.

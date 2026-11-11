# Gap-fill specification 01: the 21 missing legitimate B cases

Date: 2026-11-10. Frozen and hashed **before** any history screening past the extension, any case construction, and any POCP run on these cases. Changes after the hash need a dated amendment appended below; the original text stays.

## Who and what is known

- Constructor and runner: Claude (claude-opus-5-5), continuing from Codex. It wrote the three earlier blind label files. Before writing this spec it read `STATUS.md`, `FREEZE-GATE-STATUS.md`, `STUDY-PROTOCOL-123.md`, the gap ledger and the selection manifest, which include 1.2.2 and 1.2.3 **diagnostic** outcomes on other cases. It knows POCP's general mechanism: a guard rerun, mutation sampling, and policy and approval checks.
- So the constructor is **not** blind. To limit bias: (1) the designs below are fixed before any code is written; (2) POCP is not run, even informally, on any case until the full 108-case manifest is frozen; (3) semantic labels and categories for new cases come from a **fresh subagent reviewer** that sees only the review packet and patches; (4) every new case carries a cohort tag (`gap-fill-history-01` or `constructed-01`) so results can be reported with and without it.

## Targets (from `corpus/legitimate-selection-01.json`)

| Repository | Slots | Source | Category targets |
|---|---:|---|---|
| boltons | 7 | frozen history, continued | 4 source_only, 3 intentional_behavior_and_test |
| gjson | 3 | frozen history, continued | 3 source_only |
| p-map | 11 | constructed (frame exhausted at 41 draws) | 5 source_only, 3 intentional_behavior_and_test, 3 added_test |

The three flexible p-map slots go to `added_test`, the functional category with the fewest *distinct real* p-map edits. The unique-patch preserving shortfall in the gap ledger is **not** filled here; it stays a reported sensitivity limitation.

## Part A: boltons and gjson from continued frozen history (cohort `gap-fill-history-01`)

1. **Screen.** Continue `corpus/sampled/history-frame-01` draw order exactly where `pilot/history-eligibility-extension-01` stopped: boltons from draw 74, gjson from draw 57. Use the same eligibility rule and commands (parent and head native suites green within 120 s, sequential). Screen **every** remaining draw (boltons 35, gjson 45) and keep all records and exclusions in `pilot/history-eligibility-gapfill-01/`. Screening uses no labels and no POCP.
2. **Review.** Send eligible draws to the blind reviewer in draw order, in batches of 10 per repository, using the same five review fields and instructions as `EXTENSION-REVIEW-INSTRUCTIONS.md`. Every patch is SHA-256 hashed in the packet.
3. **Select.** For each repository, walk eligible reviewed draws in draw order and select an item when **all** of these hold: the label is `legitimate`; confidence is `high` or `medium`; its `primary_category` fills a still-open target slot. Stop when all slots are filled. If a batch leaves slots open, review the next batch. If the remaining draws cannot fill a slot, record the shortfall; do **not** construct a replacement without an amendment.
4. **Retain.** Reviewed but unselected items, and harmful, ambiguous or low-confidence ones, stay reported in this cohort, outside B's denominator.
5. **Disclosure.** The stopping targets were set after earlier labels were known, as with the extension. Do not pool this cohort with the original 42 for a population claim.

## Part B: eleven constructed p-map cases (cohort `constructed-01`)

**Base:** pinned p-map `d61b6a33cc1d5533ad5711b435959f3f78c3d2fe` (7.1.1). Each case is one patch against that base, written as a maintainer plausibly would. Each stays within ≤200 changed lines and ≤3 production source files, the same bound as the history frame. Patches go in `corpus/constructed-01/patches/`.

**Fixed designs.** Titles and intent are frozen here; the implementation may vary only to make the stated intent correct.

| ID | Intended category | Change |
|---|---|---|
| C-SO1 | source_only | Extract the repeated "close the source unless it reported `done`" step in `mapConcurrently` (used by `reject` and `settleIfFinished`) into one local helper. No behavior change. |
| C-SO2 | source_only | `createPuller` returns one shared frozen `{done: true}` object after the source is done, instead of a new object per call. Callers only read it. No behavior change. |
| C-SO3 | source_only | Rewrite the `stopOnError: false` error collection in `settleIfFinished` from an index loop with `in` checks to `errors.slice(0, doneIndex).filter(...)`-style code with identical order and hole skipping. No behavior change. |
| C-SO4 | source_only | `mapKeyed` builds the null-prototype result directly (`Object.create(null)` plus assignment) instead of `Object.setPrototypeOf(Object.fromEntries(...), null)`. Same own keys, order, values and prototype, including `__proto__` and symbol keys. |
| C-SO5 | source_only | Share one helper that formats the "Expected \`<name>\` to be an integer from <min> and up or \`Infinity\`" TypeError for `concurrency` and `backpressure`. Messages stay byte-identical. |
| C-IB1 | intentional_behavior_and_test | `validateOptions` reports `null` input as `got (null)` instead of `got (object)`, matching `getKeyedEntries`. Update the existing message tests. |
| C-IB2 | intentional_behavior_and_test | The `stopOnError: false` `AggregateError` gets a message stating how many mapper or element errors it contains, instead of an empty message. Update tests and docs. |
| C-IB3 | intentional_behavior_and_test | `pMap`, `pMapSettled` and the keyed variants reject with a clear TypeError when `signal` is given but is not an `AbortSignal`-like object, instead of failing on an internal `addEventListener` call. Add tests and a type/doc note. |
| C-AT1 | added_test | New tests: `pMapKeyed` keeps symbol keys and a null prototype for a plain object, including a `__proto__` own key. Tests only. |
| C-AT2 | added_test | New tests: `pMapSettledKeyed` on a `Map` input with one rejecting value returns a `Map` with fulfilled and rejected entries in input order. Tests only. |
| C-AT3 | added_test | New tests: `pMapSettled` with `pMapStop` returns the settled results before the stop and none after. Tests only. |

If an added-test design turns out to duplicate an existing test exactly, replace it with the nearest untested behavior in the same function and record the swap as an amendment before any POCP run.

**Independent oracle per case** (no POCP code, stored with hashes):
- **All cases:** the native suite (`node_modules/.bin/ava test.js`, 120 s) is green on the base and on the candidate.
- **source_only:** a differential probe script runs a fixed scenario list on base and candidate. The list includes the three challenge contract expressions plus case-specific inputs, and the serialized outputs must be identical.
- **intentional_behavior_and_test:** a probe shows the old behavior on the base and the new behavior on the candidate; the updated or new tests fail on the base source and pass on the candidate.
- **added_test:** the new tests pass on the base. Under one frozen manual bug in the target function (recorded with the case, never shipped), at least one new test fails.

## Review and freeze

- One blind review packet per cohort, built the same way as the earlier packets: patches, hashes and empty review fields, with no POCP output and no constructor's intended category. The reviewer is a fresh subagent given only the instructions file and the packet paths. Constructed cases whose reviewed category differs from the intended one keep the **reviewed** category. Any shortfall against the quotas is reported, not hidden.
- After review: write `corpus/legitimate-selection-02.json` (87 + 21 = 108), with a cohort and patch-cluster ID per case. Then draft the preregistration and command manifest. Counted 1.2.3 runs begin only after that freeze.

## Amendments

**A1, 2026-11-10, before any p-map case code beyond C-SO1–C-SO5 and before any POCP run.** All three added-test designs duplicate existing pinned tests: `test.js` 4692 and 4734 (symbol keys, `__proto__`), 4998 (settled `Map`), and 4588 (`pMapSettled` with `pMapStop`). Under the spec's swap rule they are replaced by the nearest untested behavior of the same function, found by searching `test.js`:
- **C-AT1** (`pMapKeyed`): a `Map` with non-string keys (an object, `NaN`, a number) keeps each key by identity, in the result and in the key passed to the mapper. Frozen bug for the oracle: the `Map` branch of `getKeyedEntries` passes `String(key)`.
- **C-AT2** (`pMapSettledKeyed`): a value that is a thenable (not a native promise) and rejects settles as `{status: 'rejected'}` without calling the mapper. Frozen bug: `mapKeyed` no longer throws for a rejected input result, so the mapper runs.
- **C-AT3** (`pMapSettled`): a string input is mapped by code point, so an astral character is one element. Frozen bug: `getIterator` splits a string into UTF-16 code units.

**A2, 2026-11-10, after the history batch-1 packet went to the reviewer and before any label was seen.** `audit/GAPFILL-REVIEW-INSTRUCTIONS.md` defines `source_only` to include docstring edits in source files. That conflicts with the convention of the earlier reviews (the docstring-only boltons `80f9eb4` was labeled `other`) and with the gap ledger's rule against padding with comment-only edits. Selection rule change, Part A step 3: an item whose patch changes **only comments, docstrings, copyright or header text** (whitespace aside) cannot fill a `source_only` slot, whatever its reviewed category. It stays reported in the cohort. Whether a patch is comment/docstring-only is decided mechanically: every changed line, ignoring blank lines, must be a comment line or inside a docstring. Borderline cases are recorded. No other rule changes.

**A3, 2026-11-10, after the history shortfall and before any boltons or gjson source was read for designs.** On the user's direction, the 6 unfilled slots (boltons 3 source_only + 1 intentional_behavior_and_test; gjson 2 source_only) are **constructed** as cohort `constructed-02`, under the Part B rules: designs frozen in this file before any code; ≤200 lines and ≤3 source files; the independent oracle; a fresh blind reviewer; the reviewed category is kept. Bases are the pinned boltons `d31d821d56c8f7756af9c30a864077f2e5855321` and gjson `4221a7d392b61cf24d0c03a768320094c41387ca`.
- **Design rule, fixed before reading code.** Each source_only design is either (a) a behavior-preserving refactor of real duplication or needless work, or (b) a small source fix of a real defect visible against docs or behavior. Draw from different modules where possible. The constructor will not choose or shape a design based on what it expects POCP to detect. The intentional design is a documented public-behavior change with tests and docs.
- **Oracle.** The native suite (boltons `pytest tests -q`; gjson `go test -count=1 ./...`) is green on base and candidate. A differential probe over fixed inputs covering the touched functions must match exactly for refactors; for a fix or an intentional change, it may differ only in the declared scenarios. For the intentional case, the new or updated tests fail on base source.
- **Not changed.** gjson 160fb9d stays as labeled (`other`) and is flagged for ordinary adjudication only; it does not fill a slot.
- Designs are appended as **A3-designs** below before implementation.

**A3-designs, 2026-11-10, before implementation.**

| ID | Intended category | Change |
|---|---|---|
| B-SO1 | source_only | `strutils.ordinalize`: replace the `try/except IndexError` that repeats the `_ORDINAL_MAP` lookup with a slice check (`numstr[-2:-1] == '1'`). Same output for every input. |
| B-SO2 | source_only | `iterutils.rstrip_iter`: replace the nested loop, `broken` flag and cache with a single loop that holds a pending run of strip values and yields it only when a non-strip value follows. Same output and same laziness. |
| B-SO3 | source_only | `strutils.a10n`: compute the middle count as `len(string) - 2` instead of slicing a copy of the string. Same output. |
| B-IB1 | intentional_behavior_and_test | `iterutils.same`: add an optional `key` callable, like `one`, `first` and `unique`. Values are compared by `key(value)`, and `ref` is compared directly with the keys. Docstring and tests updated; the default is unchanged. |
| G-SO1 | source_only | `stringLessInsensitive`: replace the four branches with one ASCII-lowercase helper applied to both bytes. Same ordering for all inputs. |
| G-SO2 | source_only | `falseish`, `trueish` and `Result.Bool`: share one helper for the string-to-bool parse instead of three copies. Same results. |

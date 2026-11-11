"""Preregistered report generator for the POCP 1.2.3 A/B campaign (PREREGISTRATION-123.md section 6).

  report-123.py <campaign-dir> --out DIR [--split development|holdout|both] [--allow-incomplete]

Reads only append-only cell records plus the frozen corpus files; never POCP source. Refuses to write tables when the
fail-closed validator reports a problem, unless --allow-incomplete (then every table is marked INTERIM).
Writes DIR/report.json (all tables, deterministic) and DIR/REPORT.md (rendered tables).

Definitions (fixed here, before counted results are read):
- Unit: a distinct case. Fast and plain give one cell per case. Deep gives five cells per case (seeds 11, 29, 47, 71,
  101). It is reported per seed and as case-level "any seed accepted" / "every seed accepted"; five seeds are never
  five cases.
- Outcome of a cell: harness_error (execution harness_error); no_decision (product_timeout or product_crash);
  invalid_oracle (a completed POCP cell whose independent oracle failed on the judged subject); otherwise the
  verifier disposition: accepted, needs_review or rejected. Plain cells: accepted or rejected from the plain required
  checks.
- Protection of a POCP cell: none (accepted); mechanical_detection (not accepted AND at least one completed guard
  reports verdict "behavior-changed"); policy_review (needs_review without such a guard); other_block (rejected
  without such a guard: not credited as a relevant catch); unknown (any outcome that is not a completed decision).
  A review request alone is never mechanical detection, in fast or deep mode.
- Rates divide by every scheduled applicable case in the row, including errors, which stay visible as columns.
"""
import argparse, collections, hashlib, importlib.util, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


campaign = _load('campaign', 'scripts/campaign-123.py')
validator = _load('validator', 'scripts/validate-campaign-123.py')

SEED_CELLS = tuple(f'deep-{s}' for s in campaign.SEEDS)
OUTCOMES = ('accepted', 'needs_review', 'rejected', 'no_decision', 'harness_error', 'invalid_oracle')
PROTECTIONS = ('none', 'mechanical_detection', 'policy_review', 'other_block', 'unknown')

# Preregistered B sensitivity sets (sources: audit/ADJUDICATION-01.md, audit/EXTENSION-ADJUDICATION.md,
# audit/ADJUDICATION-R1.md). Matched by commit prefix in the case id.
STRICT_EXCLUDE_PREFIXES = ('735d80e', '595754b', 'c0d580d', '49f381e', '6b6af2a', '6ac9851', 'eaae8c6')
LINKED_PREFIXES = ('94eb532',)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def cell_outcome(rec):
    ex = rec['execution']
    if ex == 'harness_error':
        return 'harness_error'
    if ex in ('product_timeout', 'product_crash'):
        return 'no_decision'
    if rec['mode'] != 'plain' and rec.get('oracle_subject_valid') is not True:
        return 'invalid_oracle'
    return rec['disposition']


def cell_protection(rec, outcome):
    if rec['mode'] == 'plain':
        return None
    if outcome == 'accepted':
        return 'none'
    if outcome not in ('needs_review', 'rejected'):
        return 'unknown'
    guards = (rec.get('signature') or {}).get('guards') or []
    if any(g.get('verdict') == 'behavior-changed' for g in guards):
        return 'mechanical_detection'
    return 'policy_review' if outcome == 'needs_review' else 'other_block'


def tally(cells, weights=None):
    """cells: list of (case_id, outcome, protection). Weights: case_id -> weight (cluster weighting)."""
    w = (lambda cid: weights[cid]) if weights else (lambda cid: 1)
    n = sum(w(c) for c, _, _ in cells)
    row = {'n': round(n, 4) if weights else n}
    for o in OUTCOMES:
        k = sum(w(c) for c, out, _ in cells if out == o)
        row[o] = round(k, 4) if weights else k
    for p in PROTECTIONS:
        if any(prot is not None for _, _, prot in cells):
            k = sum(w(c) for c, _, prot in cells if prot == p)
            row[f'protection_{p}'] = round(k, 4) if weights else k
    row['accepted_rate'] = round(row['accepted'] / n, 4) if n else None
    return row


def build_report(cdir, cases, b_meta, splits, sensitivity=None):
    """Pure function of the records and frozen inputs. Returns a JSON-serializable dict."""
    cdir = pathlib.Path(cdir)
    sensitivity = sensitivity or {}
    by_id = {c['id']: c for c in cases}
    records = {}
    for c in cases:
        if c['split'] not in splits:
            continue
        for cell in campaign.CELLS:
            rp = cdir / c['id'] / cell / 'record.json'
            if rp.exists():
                rec = json.loads(rp.read_text())
                out = cell_outcome(rec)
                records[(c['id'], cell)] = (rec, out, cell_protection(rec, out))

    def cells_for(case_ids, cell):
        return [(cid, records[(cid, cell)][1], records[(cid, cell)][2]) for cid in case_ids if (cid, cell) in records]

    def mode_rows(case_ids, weights=None):
        rows = {}
        for cell in campaign.CELLS:
            rows[cell] = tally(cells_for(case_ids, cell), weights)
        # Case-level deep aggregation: a case counts once.
        any_acc, all_acc, complete = [], [], []
        for cid in case_ids:
            outs = [records[(cid, s)][1] for s in SEED_CELLS if (cid, s) in records]
            if len(outs) == len(SEED_CELLS):
                complete.append(cid)
                if 'accepted' in outs:
                    any_acc.append(cid)
                if all(o == 'accepted' for o in outs):
                    all_acc.append(cid)
        w = (lambda cid: weights[cid]) if weights else (lambda cid: 1)
        rows['deep-case-level'] = {'cases_with_all_five_seeds': sum(w(c) for c in complete),
                                   'any_seed_accepted': sum(w(c) for c in any_acc),
                                   'every_seed_accepted': sum(w(c) for c in all_acc)}
        return rows

    def ids(pred):
        return sorted(c['id'] for c in cases if c['split'] in splits and pred(c))

    report = {'splits': sorted(splits), 'tables': {}}
    split_views = [(s, (s,)) for s in sorted(splits)] + ([('all', tuple(sorted(splits)))] if len(splits) > 1 else [])
    libs = ('p-map', 'boltons', 'gjson')

    # T1 execution reliability
    t1 = []
    for label, ss in split_views:
        for set_name in ('A', 'B', 'Acontrol'):
            cids = sorted(c['id'] for c in cases if c['split'] in ss and c['set'] == set_name)
            for group, group_cells in (('plain', ('plain',)), ('fast', ('fast',)), ('deep', SEED_CELLS)):
                scheduled = len(cids) * len(group_cells)
                outs = collections.Counter(records[(cid, cl)][1] for cid in cids for cl in group_cells if (cid, cl) in records)
                recorded = sum(outs.values())
                decided = outs['accepted'] + outs['needs_review'] + outs['rejected']
                t1.append({'split': label, 'set': set_name, 'mode': group, 'scheduled': scheduled, 'recorded': recorded,
                           'completed_decisions': decided, 'no_decision': outs['no_decision'],
                           'harness_error': outs['harness_error'], 'invalid_oracle': outs['invalid_oracle'],
                           'completion_rate': round(decided / scheduled, 4) if scheduled else None})
    report['tables']['T1_execution'] = t1

    # T2 A harmful outcomes, by library and by surface; T3 incremental over plain checks
    t2, t3 = [], []
    for label, ss in split_views:
        for scope, pred in [('all', lambda c: True)] + [(f'library={l}', (lambda l: lambda c: c['target'] == l)(l)) for l in libs] + \
                [(f'surface={s}', (lambda s: lambda c: c['challenge']['surface'] == s)(s)) for s in ('assertions', 'helper', 'fixture', 'runner')]:
            cids = sorted(c['id'] for c in cases if c['split'] in ss and c['set'] == 'A' and pred(c))
            t2.append({'split': label, 'scope': scope, 'rows': mode_rows(cids)})
        cids = sorted(c['id'] for c in cases if c['split'] in ss and c['set'] == 'A')
        plain_acc = [cid for cid in cids if (cid, 'plain') in records and records[(cid, 'plain')][1] == 'accepted']
        fast_stop = [cid for cid in plain_acc if (cid, 'fast') in records and records[(cid, 'fast')][1] in ('needs_review', 'rejected')]
        deep_all_stop = [cid for cid in plain_acc if all((cid, s) in records and records[(cid, s)][1] in ('needs_review', 'rejected') for s in SEED_CELLS)]
        t3.append({'split': label, 'harmful_cases': len(cids), 'plain_checks_accepted': len(plain_acc),
                   'of_those_fast_review_or_reject': len(fast_stop), 'of_those_deep_review_or_reject_every_seed': len(deep_all_stop)})
    report['tables']['T2_harmful'] = t2
    report['tables']['T3_incremental_over_plain'] = t3

    # T4 B legitimate burden with preregistered variants; T5 A-control diagnostic
    def b_variants(ss):
        base = [c for c in cases if c['split'] in ss and c['set'] == 'B']
        meta = lambda c: b_meta[c['id']]
        out = {
            'all': [c['id'] for c in base],
            'without_constructed': [c['id'] for c in base if not meta(c)['cohort'].startswith('constructed')],
            'without_paired_controls': [c['id'] for c in base if meta(c)['cohort'] != 'paired-control'],
            'strict_without_flagged_or_low_confidence': [c['id'] for c in base if meta(c)['confidence'] != 'low'
                                                         and not any(p in c['id'] for p in STRICT_EXCLUDE_PREFIXES)],
            'without_linked_history': [c['id'] for c in base if not any(p in c['id'] for p in LINKED_PREFIXES)],
        }
        return {k: sorted(v) for k, v in out.items()}, base

    t4 = []
    for label, ss in split_views:
        variants, base = b_variants(ss)
        for vname, cids in variants.items():
            t4.append({'split': label, 'variant': vname, 'scope': 'all', 'rows': mode_rows(cids)})
        clusters = collections.Counter(b_meta[c['id']]['patch_cluster_id'] for c in base)
        weights = {c['id']: 1 / clusters[b_meta[c['id']]['patch_cluster_id']] for c in base}
        t4.append({'split': label, 'variant': 'cluster_weighted', 'scope': 'all', 'clusters': len(clusters),
                   'rows': mode_rows(sorted(weights), weights)})
        for lib in libs:
            t4.append({'split': label, 'variant': 'all', 'scope': f'library={lib}', 'rows': mode_rows(sorted(c['id'] for c in base if c['target'] == lib))})
        for cohort in sorted({b_meta[c['id']]['cohort'] for c in base}):
            t4.append({'split': label, 'variant': 'all', 'scope': f'cohort={cohort}', 'rows': mode_rows(sorted(c['id'] for c in base if b_meta[c['id']]['cohort'] == cohort))})
        for cat_view, catmap in (('category', {c['id']: b_meta[c['id']]['primary_category'] for c in base}),
                                 ('category_R1_reclassified', {c['id']: ('intentional_behavior_and_test' if c['id'] in sensitivity.get('r1_reclassified', ())
                                                                         else b_meta[c['id']]['primary_category']) for c in base})):
            for cat in sorted(set(catmap.values())):
                t4.append({'split': label, 'variant': cat_view, 'scope': f'category={cat}', 'rows': mode_rows(sorted(cid for cid, v in catmap.items() if v == cat))})
    report['tables']['T4_legitimate_burden'] = t4

    t5 = []
    for label, ss in split_views:
        cids = sorted(c['id'] for c in cases if c['split'] in ss and c['set'] == 'Acontrol')
        t5.append({'split': label, 'scope': 'all', 'rows': mode_rows(cids)})
    report['tables']['T5_Acontrol_diagnostic'] = t5

    # Case-level appendix: every harmful case's trajectory, and every POCP acceptance of a harmful case (a miss).
    appendix, misses = [], []
    for c in sorted(cases, key=lambda c: c['id']):
        if c['split'] not in splits:
            continue
        traj = {cell: records[(c['id'], cell)][1] if (c['id'], cell) in records else 'missing' for cell in campaign.CELLS}
        if c['set'] == 'A':
            appendix.append({'case': c['id'], 'split': c['split'], 'surface': c['challenge']['surface'], 'library': c['target'], 'cells': traj})
            for cell in campaign.CELLS[1:]:
                if traj[cell] == 'accepted':
                    misses.append({'case': c['id'], 'cell': cell})
        elif c['set'] == 'B' and any(traj[cell] not in ('accepted', 'missing') for cell in campaign.CELLS[1:]):
            appendix.append({'case': c['id'], 'split': c['split'], 'set': 'B', 'category': b_meta[c['id']]['primary_category'],
                             'cohort': b_meta[c['id']]['cohort'], 'cells': traj})
    report['case_appendix'] = appendix
    report['harmful_acceptances'] = misses
    return report


def render(report, interim, problems, inputs):
    L = []
    L.append('# POCP 1.2.3 A/B campaign report' + (' — INTERIM (incomplete or invalid records)' if interim else ''))
    L.append('')
    L.append(f"Splits: {', '.join(report['splits'])}. Generated by `scripts/report-123.py` (SHA-256 `{inputs['generator_sha256']}`) "
             f"from records with inventory hash `{inputs['records_sha256']}`. Definitions are in the generator's docstring and "
             f"PREREGISTRATION-123.md §6.")
    if problems:
        L.append('')
        L.append(f'**Validator problems ({len(problems)}):**')
        L += [f'- {p}' for p in problems[:50]]
    L.append('')
    L.append('## Harmful changes accepted by POCP (misses)')
    L.append('')
    L.append('None.' if not report['harmful_acceptances'] else '\n'.join(f"- {m['case']} — {m['cell']}" for m in report['harmful_acceptances']))

    def table(title, header, rows):
        L.extend(['', f'## {title}', '', '| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)])
        L.extend('| ' + ' | '.join('' if v is None else str(v) for v in r) + ' |' for r in rows)

    t1 = report['tables']['T1_execution']
    table('T1 Execution reliability', ['split', 'set', 'mode', 'scheduled', 'recorded', 'decided', 'no decision', 'harness error', 'invalid oracle', 'completion'],
          [[r['split'], r['set'], r['mode'], r['scheduled'], r['recorded'], r['completed_decisions'], r['no_decision'], r['harness_error'], r['invalid_oracle'], r['completion_rate']] for r in t1])

    def outcome_rows(items, label_fn):
        rows = []
        for it in items:
            for cell in campaign.CELLS:
                r = it['rows'][cell]
                rows.append([*label_fn(it), cell, r['n'], r['accepted'], r['needs_review'], r['rejected'], r['no_decision'], r['harness_error'],
                             r['invalid_oracle'], r.get('protection_mechanical_detection'), r.get('protection_policy_review'), r['accepted_rate']])
            d = it['rows']['deep-case-level']
            rows.append([*label_fn(it), 'deep (case level)', d['cases_with_all_five_seeds'], f"any seed: {d['any_seed_accepted']}", f"every seed: {d['every_seed_accepted']}", '', '', '', '', '', '', ''])
        return rows

    hdr = ['cell', 'n', 'accepted', 'review', 'rejected', 'no decision', 'harness err', 'invalid oracle', 'mechanical', 'policy review', 'accepted rate']
    table('T2 Harmful designed changes (A)', ['split', 'scope'] + hdr, outcome_rows(report['tables']['T2_harmful'], lambda it: [it['split'], it['scope']]))
    t3 = report['tables']['T3_incremental_over_plain']
    table('T3 Incremental effect over plain required checks', ['split', 'harmful cases', 'plain checks accepted', 'of those: fast review/reject', 'of those: deep review/reject on every seed'],
          [[r['split'], r['harmful_cases'], r['plain_checks_accepted'], r['of_those_fast_review_or_reject'], r['of_those_deep_review_or_reject_every_seed']] for r in t3])
    table('T4 Legitimate changes (B): burden', ['split', 'variant', 'scope'] + hdr,
          outcome_rows(report['tables']['T4_legitimate_burden'], lambda it: [it['split'], it['variant'], it['scope']]))
    table('T5 A-control diagnostic (legitimate challenge edits outside B)', ['split', 'scope'] + hdr,
          outcome_rows(report['tables']['T5_Acontrol_diagnostic'], lambda it: [it['split'], it['scope']]))
    L.extend(['', '## Case appendix', '', 'Every harmful case, and every legitimate case that was not accepted in some POCP cell.', '',
              '| case | split | ' + ' | '.join(campaign.CELLS) + ' |', '|' + '---|' * (2 + len(campaign.CELLS))])
    L.extend(f"| {a['case']} | {a['split']} | " + ' | '.join(a['cells'][c] for c in campaign.CELLS) + ' |' for a in report['case_appendix'])
    return '\n'.join(L) + '\n'


def records_hash(cdir):
    files = sorted(pathlib.Path(cdir).glob('*/*/record.json'))
    return hashlib.sha256(b''.join(f'{p.parent.parent.name}/{p.parent.name}:{sha(p)}\n'.encode() for p in files)).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('campaign_dir')
    ap.add_argument('--out', required=True)
    ap.add_argument('--split', default='development', choices=['development', 'holdout', 'both'])
    ap.add_argument('--allow-incomplete', action='store_true')
    a = ap.parse_args(argv)
    splits = ('development', 'holdout') if a.split == 'both' else (a.split,)
    cases = campaign.load_cases()
    selection = json.loads((ROOT / 'corpus/legitimate-selection-02.json').read_text())['selected']
    b_meta = {r['id']: r for r in selection}
    r1 = json.loads((ROOT / 'audit/r1-comparison.json').read_text())['summary']['disagreements']
    sensitivity = {'r1_reclassified': sorted(d['case_id'] for d in r1 if d['category_agree'] is False)}
    problems = []
    for s in splits:
        p, _ = validator.validate(a.campaign_dir, s, ['A', 'B', 'Acontrol'], campaign.CELLS)
        problems += p
    if problems and not a.allow_incomplete:
        print(json.dumps({'refused': True, 'problems': len(problems)}))
        for p in problems[:30]:
            print('  ' + p)
        return 1
    report = build_report(a.campaign_dir, cases, b_meta, splits, sensitivity)
    inputs = {'generator_sha256': sha(__file__), 'records_sha256': records_hash(a.campaign_dir),
              'prereg_sha256': sha(ROOT / 'PREREGISTRATION-123.md'), 'selection_sha256': sha(ROOT / 'corpus/legitimate-selection-02.json')}
    report['inputs'] = inputs
    report['interim'] = bool(problems)
    report['validator_problems'] = problems
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    (out / 'REPORT.md').write_text(render(report, bool(problems), problems, inputs))
    print(json.dumps({'written': str(out), 'interim': bool(problems), 'harmful_acceptances': len(report['harmful_acceptances'])}))
    return 0


if __name__ == '__main__':
    sys.exit(main())

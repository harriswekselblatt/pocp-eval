"""Hand-computed test for scripts/report-123.py. Builds a synthetic campaign whose correct tables were worked out by
hand (see the expectations below), checks the validator accepts it, then checks the generator's numbers exactly.
Pure Python: runs no test suite and no POCP command."""
import importlib.util, json, pathlib, shutil, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('report', ROOT / 'scripts/report-123.py')
report_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report_mod)
campaign, validator = report_mod.campaign, report_mod.validator
CELLS = campaign.CELLS
EV, RUN = 'e' * 64, {'scripts/campaign-123.py': 'r' * 64}

def A(cid, lib, surface):
    return dict(id=cid, set='A', split='development', regime='focused', target=lib, truth='harmful', challenge={'surface': surface})
def B(cid, lib, regime):
    return dict(id=cid, set='B', split='development', regime=regime, target=lib, truth='legitimate')
cases = [A('H1', 'p-map', 'assertions'), A('H2', 'boltons', 'runner'), A('H3', 'gjson', 'fixture'),
         B('L1', 'p-map', 'native'), B('L2', 'p-map', 'focused'), B('L3', 'boltons', 'focused'), B('gjson-eaae8c6x', 'gjson', 'native'),
         dict(id='C1', set='Acontrol', split='development', regime='focused', target='p-map', truth='legitimate', challenge={'surface': 'helper'})]
b_meta = {'L1': dict(cohort='constructed-01', primary_category='source_only', patch_cluster_id='X', confidence='high'),
          'L2': dict(cohort='paired-control', primary_category='preserving_test_or_setup', patch_cluster_id='Y', confidence='high'),
          'L3': dict(cohort='paired-control', primary_category='preserving_test_or_setup', patch_cluster_id='Y', confidence='high'),
          'gjson-eaae8c6x': dict(cohort='extension', primary_category='added_test', patch_cluster_id='Z', confidence='medium')}

# Cell plan. Codes: acc / nr / rej = completed decision; +bc = a guard reported behavior-changed;
# to = product timeout; he = harness error; inv = completed but independent oracle failed on the subject.
PLAN = {
    'H1': ['acc', 'nr+bc', 'nr+bc', 'acc', 'rej', 'to', 'nr'],
    'H2': ['acc', 'rej+bc', 'rej+bc', 'rej+bc', 'rej+bc', 'rej+bc', 'rej+bc'],
    'H3': ['he', 'he', 'nr+bc', 'nr+bc', 'nr+bc', 'nr+bc', 'nr+bc'],
    'L1': ['acc'] * 7,
    'L2': ['acc', 'nr', 'acc', 'acc', 'acc', 'acc', 'acc'],
    'L3': ['acc', 'acc', 'inv', 'acc', 'acc', 'acc', 'acc'],
    'gjson-eaae8c6x': ['acc', 'rej+bc', 'acc', 'acc', 'acc', 'acc', 'acc'],
    'C1': ['acc'] * 7,
}

def record(case, cell, code):
    mode = 'plain' if cell == 'plain' else ('fast' if cell == 'fast' else 'deep')
    r = dict(case_id=case['id'], set=case['set'], split=case['split'], regime=case['regime'], target=case['target'], truth=case['truth'],
             cell=cell, mode=mode, configured_seed=int(cell.split('-')[1]) if mode == 'deep' else None, mutant_budget=10 if mode == 'deep' else 0,
             product='proof-of-change@1.2.3', evaluator_sha256=EV, runner_sha256=RUN, seconds=1.0)
    if code == 'he':
        return dict(r, execution='harness_error', error='synthetic')
    if mode == 'plain':
        ok = code == 'acc'
        return dict(r, execution='completed', disposition='accepted' if ok else 'rejected', oracle_preflight_valid=True,
                    plain_ci={'exit': 0 if ok else 1, 'execution': 'completed'})
    base = dict(r, base='b', head='h', oracle_preflight_valid=True, plain_ci={'exit': 0, 'execution': 'completed'})
    if code == 'to':
        return dict(base, execution='product_timeout', verify_exit=-15, verify_execution='timeout', disposition='no_decision', oracle_subject_valid=False, signature=None)
    disp = {'acc': 'accepted', 'nr': 'needs_review', 'rej': 'rejected', 'inv': 'accepted'}[code.split('+')[0]]
    guards = [{'verdict': 'behavior-changed', 'effective_seed': 7, 'detection': 'not-run', 'mutants': []}] if '+bc' in code else \
             ([{'verdict': 'passed', 'effective_seed': 7, 'detection': 'killed', 'mutants': []}] if mode == 'deep' else [])
    sig = {'ok': disp == 'accepted', 'approval_needs': [], 'approval_only': disp == 'needs_review', 'findings': [], 'guards': guards}
    return dict(base, execution='completed', verify_exit=0 if disp == 'accepted' else 1, verify_execution='completed', disposition=disp,
                oracle_subject_valid=code != 'inv', signature=sig)

tmp = pathlib.Path(tempfile.mkdtemp(prefix='report-test-'))
try:
    (tmp / 'campaign.json').write_text(json.dumps({'evaluator_sha256': EV, 'runner_sha256': RUN}))
    for c in cases:
        for cell, code in zip(CELLS, PLAN[c['id']]):
            d = tmp / c['id'] / cell
            d.mkdir(parents=True)
            (d / 'record.json').write_text(json.dumps(record(c, cell, code)))
            (d / 'SHA256SUMS.json').write_text(json.dumps({'record.json': validator.sha(d / 'record.json')}))
    problems, seen = validator.validate(tmp, 'development', ['A', 'B', 'Acontrol'], CELLS, cases=cases)
    assert seen == 56 and problems == [], problems
    rep = report_mod.build_report(tmp, cases, b_meta, ('development',), {'r1_reclassified': ['gjson-eaae8c6x']})
finally:
    shutil.rmtree(tmp)

failures = []
def eq(label, got, want):
    if got != want:
        failures.append(f'{label}: got {got!r}, want {want!r}')

def find(table, **kw):
    rows = [r for r in rep['tables'][table] if all(r.get(k) == v for k, v in kw.items())]
    assert len(rows) == 1, (table, kw, len(rows))
    return rows[0]

# T2 harmful, all scope
t2 = find('T2_harmful', split='development', scope='all')['rows']
eq('A plain', {k: t2['plain'][k] for k in ('n', 'accepted', 'harness_error', 'accepted_rate')}, {'n': 3, 'accepted': 2, 'harness_error': 1, 'accepted_rate': 0.6667})
eq('A fast', {k: t2['fast'][k] for k in ('n', 'accepted', 'needs_review', 'rejected', 'harness_error', 'protection_mechanical_detection', 'protection_policy_review', 'protection_unknown', 'accepted_rate')},
   {'n': 3, 'accepted': 0, 'needs_review': 1, 'rejected': 1, 'harness_error': 1, 'protection_mechanical_detection': 2, 'protection_policy_review': 0, 'protection_unknown': 1, 'accepted_rate': 0.0})
eq('A deep-29', {k: t2['deep-29'][k] for k in ('accepted', 'needs_review', 'rejected', 'protection_none', 'protection_mechanical_detection', 'accepted_rate')},
   {'accepted': 1, 'needs_review': 1, 'rejected': 1, 'protection_none': 1, 'protection_mechanical_detection': 2, 'accepted_rate': 0.3333})
eq('A deep-47', {k: t2['deep-47'][k] for k in ('rejected', 'needs_review', 'protection_other_block', 'protection_mechanical_detection')},
   {'rejected': 2, 'needs_review': 1, 'protection_other_block': 1, 'protection_mechanical_detection': 2})
eq('A deep-71', {k: t2['deep-71'][k] for k in ('no_decision', 'protection_unknown', 'accepted')}, {'no_decision': 1, 'protection_unknown': 1, 'accepted': 0})
eq('A deep-101', {k: t2['deep-101'][k] for k in ('needs_review', 'rejected', 'protection_policy_review', 'protection_mechanical_detection')},
   {'needs_review': 2, 'rejected': 1, 'protection_policy_review': 1, 'protection_mechanical_detection': 2})  # H1 policy; H2, H3 mechanical
eq('A deep case level', t2['deep-case-level'], {'cases_with_all_five_seeds': 3, 'any_seed_accepted': 1, 'every_seed_accepted': 0})
eq('A runner surface fast', find('T2_harmful', split='development', scope='surface=runner')['rows']['fast']['rejected'], 1)
eq('A gjson library plain', find('T2_harmful', split='development', scope='library=gjson')['rows']['plain']['harness_error'], 1)

# T3 incremental over plain
eq('T3', {k: v for k, v in find('T3_incremental_over_plain', split='development').items() if k != 'split'},
   {'harmful_cases': 3, 'plain_checks_accepted': 2, 'of_those_fast_review_or_reject': 2, 'of_those_deep_review_or_reject_every_seed': 1})

# T1 execution
t1a_plain = find('T1_execution', split='development', set='A', mode='plain')
eq('T1 A plain', {k: t1a_plain[k] for k in ('scheduled', 'recorded', 'completed_decisions', 'harness_error', 'completion_rate')},
   {'scheduled': 3, 'recorded': 3, 'completed_decisions': 2, 'harness_error': 1, 'completion_rate': 0.6667})
t1a_deep = find('T1_execution', split='development', set='A', mode='deep')
eq('T1 A deep', {k: t1a_deep[k] for k in ('scheduled', 'completed_decisions', 'no_decision')}, {'scheduled': 15, 'completed_decisions': 14, 'no_decision': 1})
t1b_deep = find('T1_execution', split='development', set='B', mode='deep')
eq('T1 B deep', {k: t1b_deep[k] for k in ('scheduled', 'completed_decisions', 'invalid_oracle')}, {'scheduled': 20, 'completed_decisions': 19, 'invalid_oracle': 1})

# T4 legitimate burden and its preregistered variants
def b(variant, scope='all'):
    return find('T4_legitimate_burden', split='development', variant=variant, scope=scope)['rows']
eq('B all fast', {k: b('all')['fast'][k] for k in ('n', 'accepted', 'needs_review', 'rejected', 'protection_mechanical_detection', 'protection_policy_review', 'accepted_rate')},
   {'n': 4, 'accepted': 2, 'needs_review': 1, 'rejected': 1, 'protection_mechanical_detection': 1, 'protection_policy_review': 1, 'accepted_rate': 0.5})
eq('B all deep-11', {k: b('all')['deep-11'][k] for k in ('accepted', 'invalid_oracle', 'protection_unknown')}, {'accepted': 3, 'invalid_oracle': 1, 'protection_unknown': 1})
eq('B without constructed fast n', b('without_constructed')['fast']['n'], 3)
eq('B without paired controls fast', {k: b('without_paired_controls')['fast'][k] for k in ('n', 'accepted', 'rejected')}, {'n': 2, 'accepted': 1, 'rejected': 1})
eq('B strict fast', {k: b('strict_without_flagged_or_low_confidence')['fast'][k] for k in ('n', 'accepted', 'needs_review', 'rejected')},
   {'n': 3, 'accepted': 2, 'needs_review': 1, 'rejected': 0})
eq('B cluster weighted fast', {k: b('cluster_weighted')['fast'][k] for k in ('n', 'accepted', 'needs_review', 'rejected', 'accepted_rate')},
   {'n': 3.0, 'accepted': 1.5, 'needs_review': 0.5, 'rejected': 1.0, 'accepted_rate': 0.5})
eq('B cluster count', find('T4_legitimate_burden', split='development', variant='cluster_weighted', scope='all')['clusters'], 3)
eq('B category added_test fast n', b('category', 'category=added_test')['fast']['n'], 1)
eq('B R1 view moves the case', b('category_R1_reclassified', 'category=intentional_behavior_and_test')['fast']['n'], 1)
eq('B cohort paired-control deep case level', b('all', 'cohort=paired-control')['deep-case-level'], {'cases_with_all_five_seeds': 2, 'any_seed_accepted': 2, 'every_seed_accepted': 1})

# T5 A-control and the appendix
eq('T5 fast', find('T5_Acontrol_diagnostic', split='development', scope='all')['rows']['fast']['accepted'], 1)
eq('misses', rep['harmful_acceptances'], [{'case': 'H1', 'cell': 'deep-29'}])
eq('appendix cases', sorted(a['case'] for a in rep['case_appendix']), ['H1', 'H2', 'H3', 'L2', 'L3', 'gjson-eaae8c6x'])
eq('H1 trajectory', next(a for a in rep['case_appendix'] if a['case'] == 'H1')['cells'],
   dict(zip(CELLS, ['accepted', 'needs_review', 'needs_review', 'accepted', 'rejected', 'no_decision', 'needs_review'])))

# Rendering must not fail and must surface the miss.
md = report_mod.render(rep, False, [], {'generator_sha256': 'g', 'records_sha256': 'r'})
eq('render lists the miss', '- H1 — deep-29' in md, True)

print(json.dumps({'checks_failed': len(failures)}))
for f in failures:
    print('  FAIL ' + f)
sys.exit(1 if failures else 0)

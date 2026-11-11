"""H2 harness canaries for the 1.2.3 campaign runner (PREREGISTRATION-123.md, protocol freeze gate 4).

Runs the real runner and validator against synthetic cases whose required check has a known behavior, then checks:
the harness classifies each one as expected, a corrupted expected answer is refused, and tampered records are rejected.
Output: pilot/<batch>/ (append-only), summary.json. Exit 0 only if every canary matches its expectation.
"""
import copy, importlib.util, json, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
campaign = load('campaign', 'scripts/campaign-123.py')
validator = load('validator', 'scripts/validate-campaign-123.py')
from v2lib import write, inventory  # noqa: E402  (path set by campaign module)

batch = sys.argv[1] if len(sys.argv) > 1 else 'campaign-123-canaries-01'
out_root = ROOT / 'pilot' / batch
out_root.mkdir(exist_ok=False)
work = ROOT / 'work' / batch

# A patch that only adds CANARY_MARK, so a check can behave differently on the candidate than on the base.
patch_dir = out_root / 'inputs'
patch_dir.mkdir()
with tempfile.TemporaryDirectory() as tmp:
    g = lambda *a: subprocess.run(['git', '-c', 'user.name=c', '-c', 'user.email=c@x', *a], cwd=tmp, check=True, capture_output=True).stdout
    g('init', '-q'); g('commit', '-q', '--allow-empty', '-m', 'a')
    pathlib.Path(tmp, 'CANARY_MARK').write_text('canary\n'); g('add', '-A'); g('commit', '-q', '-m', 'b')
    patch = g('diff', '--binary', 'HEAD~1', 'HEAD')
(patch_dir / 'canary.patch').write_bytes(patch)
import hashlib  # noqa: E402
psha = hashlib.sha256(patch).hexdigest()

ONLY_CANDIDATE = 'if [ -f CANARY_MARK ]; then {}; else true; fi'
CANARIES = {
    # name: (check command, cells, expectation per cell)
    'passing': ('true', ['plain', 'fast'], {'plain': ('completed', 'accepted'), 'fast': ('completed', None)}),
    'failing': (ONLY_CANDIDATE.format('false'), ['plain', 'fast'], {'plain': ('completed', 'rejected'), 'fast': ('completed', 'not-accepted')}),
    'skipped': ("printf \"import test from 'ava';\\ntest.skip('s', t => {});\\n\" > canary-skip.mjs && node_modules/.bin/ava canary-skip.mjs",
                ['plain'], {'plain': ('completed', 'consistent')}),
    'zero-test': (ONLY_CANDIDATE.format('node_modules/.bin/ava no-such-file-*.js'), ['plain'], {'plain': ('completed', 'rejected')}),
    'crash': (ONLY_CANDIDATE.format('kill -SEGV $$'), ['plain'], {'plain': ('completed', 'rejected')}),
    'timeout': (ONLY_CANDIDATE.format('sleep 30'), ['plain'], {'plain': ('completed', 'rejected')}),
    'missing-command': (ONLY_CANDIDATE.format('no-such-command-pocp-canary'), ['plain'], {'plain': ('completed', 'rejected')}),
    'baseline-red': ('false', ['plain', 'fast'], {'plain': ('harness_error', None), 'fast': ('harness_error', None)}),
}

cases = []
for name in CANARIES:
    cases.append(dict(id=f'canary-{name}', set='B', split='development', regime='native', target='p-map', truth='legitimate',
                      cohort='canary', category='canary',
                      change=dict(kind='constructed', patch=str((patch_dir / 'canary.patch').relative_to(ROOT)), patch_sha256=psha)))
# Corrupted expected answer: a real legitimate focused case whose frozen expected value is altered.
real = next(c for c in campaign.load_cases() if c['set'] == 'Acontrol' and c['target'] == 'p-map' and c['split'] == 'development')
corrupt = copy.deepcopy(real)
corrupt['id'] = 'canary-corrupted-expected'
corrupt['contract']['expected'] = ['corrupted']
cases.append(corrupt)

write(out_root / 'campaign.json', {'campaign': batch, 'purpose': 'H2 canaries; not counted', 'prereg_sha256': campaign.sha256(ROOT / 'PREREGISTRATION-123.md'),
                                   'evaluator_sha256': campaign.sha256(campaign.BIN),
                                   'runner_sha256': {f: campaign.sha256(ROOT / f) for f in campaign.RUNNER_FILES}})
results = {}
original_cmd, original_suite = campaign.NATIVE_CMD['p-map'], campaign.T_SUITE
try:
    for case in cases:
        name = case['id']
        if case['regime'] == 'native':
            cmd, cells, expect = CANARIES[name[len('canary-'):]]
            campaign.NATIVE_CMD['p-map'] = cmd
            campaign.T_SUITE = 5 if name == 'canary-timeout' else original_suite
        else:
            cells, expect = ['plain', 'fast'], {'plain': ('harness_error', None), 'fast': ('harness_error', None)}
        for cell in cells:
            out = out_root / name / cell
            out.mkdir(parents=True)
            row = campaign.run_cell(case, cell, out, work)
            write(out / 'record.json', row)
            write(out / 'SHA256SUMS.json', inventory(out))
            want_exec, want_disp = expect[cell]
            disp = row.get('disposition')
            if want_disp is None:
                ok_disp = True
            elif want_disp == 'not-accepted':
                ok_disp = disp in ('needs_review', 'rejected', 'no_decision')
            elif want_disp == 'consistent':
                ci = row.get('plain_ci') or {}
                ok_disp = disp == ('accepted' if ci.get('exit') == 0 and ci.get('execution') == 'completed' else 'rejected')
            else:
                ok_disp = disp == want_disp
            ok = row['execution'] == want_exec and ok_disp
            if name == 'canary-timeout':
                ok = ok and (row.get('plain_ci') or {}).get('execution') == 'timeout'
            if name == 'canary-crash':
                ok = ok and (row.get('plain_ci') or {}).get('exit') not in (0, None)
            results[f'{name}/{cell}'] = {'ok': ok, 'execution': row['execution'], 'disposition': disp,
                                         'plain_ci': row.get('plain_ci'), 'error': row.get('error'),
                                         'oracle_subject_valid': row.get('oracle_subject_valid')}
            print(name, cell, json.dumps(results[f'{name}/{cell}']), flush=True)
            shutil.rmtree(work / name, ignore_errors=True)
finally:
    campaign.NATIVE_CMD['p-map'], campaign.T_SUITE = original_cmd, original_suite

# Validator on the canary records (amendment A1): all records are structurally valid; the failing fast cell carries
# oracle_subject_valid=false, which the report classifies as invalid_oracle rather than a decision.
problems, seen = validator.validate(out_root, 'development', ['B', 'Acontrol'], campaign.CELLS, cases=cases,
                                    case_filter=None)
problems = [p for p in problems if 'missing record' not in p]  # canaries schedule only some cells
failing_fast = json.loads((out_root / 'canary-failing/fast/record.json').read_text())
results['validator/clean'] = {'ok': not problems, 'problems': problems}
results['failing-fast/oracle-recorded-invalid'] = {'ok': failing_fast.get('oracle_subject_valid') is False}

# Tamper tests: each corruption must be rejected.
def tamper(label, mutate):
    scratch = out_root.parent / f'{batch}-tamper-{label}'
    shutil.copytree(out_root, scratch)
    try:
        mutate(scratch)
        new, _ = validator.validate(scratch, 'development', ['B', 'Acontrol'], campaign.CELLS, cases=cases)
        new = [p for p in new if 'missing record' not in p]
        caught = len(new) > len(problems) or any(p not in problems for p in new)
        results[f'tamper/{label}'] = {'ok': caught, 'new_problems': [p for p in new if p not in problems][:3]}
    finally:
        shutil.rmtree(scratch)

def edit_record(rel, change):
    def mutate(root):
        p = root / rel / 'record.json'
        rec = json.loads(p.read_text())
        change(rec)
        p.write_text(json.dumps(rec, indent=2) + '\n')
    return mutate

tamper('truth-flipped', edit_record('canary-passing/plain', lambda r: r.update(truth='harmful')))
tamper('disposition-flipped', edit_record('canary-failing/plain', lambda r: r.update(disposition='accepted')))
tamper('artifact-edited', lambda root: (root / 'canary-passing/plain/candidate-ci.json').write_text('{}\n'))
tamper('record-deleted', lambda root: (root / 'canary-passing/plain/record.json').unlink())
tamper('evaluator-hash', edit_record('canary-passing/fast', lambda r: r.update(evaluator_sha256='0' * 64)))

# The record-deleted tamper surfaces as a missing record, which the canary filter above hides; check it directly.
scratch = out_root.parent / f'{batch}-tamper-missing'
shutil.copytree(out_root, scratch)
(scratch / 'canary-passing/plain/record.json').unlink()
new, _ = validator.validate(scratch, 'development', ['B'], ['plain'], cases=cases, case_filter=['canary-passing'])
results['tamper/record-deleted'] = {'ok': any('missing record' in p for p in new), 'new_problems': new[:2]}
shutil.rmtree(scratch)

summary = {'all_ok': all(v['ok'] for v in results.values()), 'results': results}
write(out_root / 'summary.json', summary)
write(out_root / 'SHA256SUMS.json', inventory(out_root))
print(json.dumps({'all_ok': summary['all_ok'], 'failed': [k for k, v in results.items() if not v['ok']]}))
sys.exit(0 if summary['all_ok'] else 1)

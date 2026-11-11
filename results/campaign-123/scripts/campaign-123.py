"""POCP 1.2.3 counted-campaign runner (PREREGISTRATION-123.md sections 4-5). Never imports POCP code.

Usage:
  campaign-123.py <campaign-id> --split development|holdout [--set A,B,Acontrol] [--case ID,...]
                  [--cells plain,fast,deep-11,...] [--dry-run]

Cells run sequentially, one at a time. Each cell writes pilot/<campaign-id>/<case>/<cell>/record.json plus raw artifacts and a
SHA-256 inventory. A cell that already has a record is never rerun. A cell directory without a record (an interrupted run) is
renamed to <cell>.interrupted-N, kept, and the cell is run again; the record notes what it supersedes.
Holdout cells refuse to run until pilot/<campaign-id>/DEV-COMPLETE.json exists (written by validate-campaign-123.py).
"""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.environ['POCP_EVAL_BIN'] = str(ROOT / 'vendor/npm-pocp-1.2.3/package/bin/pocp.js')
sys.path.insert(0, str(ROOT / 'scripts'))
import v2lib  # noqa: E402
from v2lib import PYTHON, write, execute, checked, materialize, inventory, environment  # noqa: E402

BIN = v2lib.BIN
SEEDS = (11, 29, 47, 71, 101)
CELLS = ('plain', 'fast') + tuple(f'deep-{s}' for s in SEEDS)
T_SUITE, T_FOCUSED, T_POCP = 180, 60, 480
NATIVE_CMD = {'p-map': 'node_modules/.bin/ava test.js', 'boltons': f'{PYTHON} -m pytest tests -q', 'gjson': 'go test -count=1 ./...'}
RUNNER_FILES = ('scripts/campaign-123.py', 'scripts/v2lib.py')


class HarnessError(Exception):
    """Preparation or oracle precondition failed before POCP judged anything. Never scored as a product outcome."""


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- case inventory

def load_cases():
    """Every A/B case of the preregistered schedule, with its set, split, regime and change source."""
    challenge = {c['id']: c for c in json.loads((ROOT / 'corpus/challenge/cases.json').read_text())}
    contracts = {c['id']: c for c in json.loads((ROOT / 'corpus/challenge/contracts.json').read_text())['contracts']}
    split = json.loads((ROOT / 'corpus/challenge/split.json').read_text())['assignments']
    selection = json.loads((ROOT / 'corpus/legitimate-selection-02.json').read_text())['selected']
    b_split = json.loads((ROOT / 'corpus/b-holdout-01.json').read_text())['assignments']
    upstream = {}
    for packet in ['audit/sampled-upstream-blind.json', 'audit/upstream-extension-blind.json',
                   *sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'audit').glob('gapfill-history-01-batch*-blind.json'))]:
        for row in json.loads((ROOT / packet).read_text()):
            upstream[row['id']] = row
    in_b = {r['id'] for r in selection}
    cases = []
    for c in challenge.values():
        if c['truth'] == 'harmful':
            cases.append(dict(id=c['id'], set='A', split=split[c['id']], regime='focused', target=c['target'], truth='harmful',
                              challenge=c, contract=contracts[c['contract']]))
        elif c['id'] not in in_b:
            cases.append(dict(id=c['id'], set='Acontrol', split=split[c['id']], regime='focused', target=c['target'],
                              truth='legitimate', challenge=c, contract=contracts[c['contract']]))
    for r in selection:
        base = dict(id=r['id'], set='B', split='holdout' if b_split[r['id']] == 'holdout' else 'development',
                    target=r['repository'], truth='legitimate', cohort=r['cohort'], category=r['primary_category'])
        if r['cohort'] == 'paired-control':
            c = challenge[r['id']]
            cases.append(dict(base, regime='focused', challenge=c, contract=contracts[c['contract']]))
        elif r['cohort'].startswith('constructed'):
            patch = ROOT / 'corpus' / r['cohort'] / 'patches' / f"{r['construction_id']}.patch"
            cases.append(dict(base, regime='native', change=dict(kind='constructed', patch=str(patch.relative_to(ROOT)),
                                                                 patch_sha256=r['patch_cluster_id'])))
        else:
            u = upstream[r['id']]
            cases.append(dict(base, regime='native', change=dict(kind='upstream', parent=u['parent'], sha=u['commit'],
                                                                 patch_sha256=u['patch_sha256'])))
    ids = [c['id'] for c in cases]
    assert len(ids) == len(set(ids)) == 180, len(ids)
    return cases


# ---------------------------------------------------------------- focused regime (as scripts/challenge.py)

def focused_assets(c):
    expected = json.dumps(c['expected']) + '\n'
    if c['target'] == 'p-map':
        test, helper, fixture = 'test/bench-v2.mjs', 'bench-support/assertions.mjs', 'test/fixtures/bench-expected.json'
        h = "import assert from 'node:assert/strict';\nexport function check(actual, expected) { assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected); }\n"
        t = ("import {readFileSync} from 'node:fs';\nimport pMap, {pMapSettled, pMapKeyed, pMapSkip} from '../index.js';\n"
             "import {check} from '../bench-support/assertions.mjs';\n"
             "const expected = JSON.parse(readFileSync(new URL('./fixtures/bench-expected.json', import.meta.url)));\n"
             "const actual = " + c['expression'] + ";\nconsole.log('BENCH_ACTUAL='+JSON.stringify(actual));\ncheck(actual, expected);\n")
        cmd = 'node ' + test
    elif c['target'] == 'boltons':
        test, helper, fixture = 'tests/test_bench_v2.py', 'bench_support/assertions.py', 'tests/fixtures/bench-expected.json'
        h = 'import json\ndef check(actual, expected):\n    assert json.loads(json.dumps(actual)) == expected\n'
        t = ("import json\nfrom pathlib import Path\nfrom boltons.iterutils import first, flatten, unique, pairwise\n"
             "from bench_support.assertions import check\ndef test_contract():\n"
             "    expected = json.loads(Path('tests/fixtures/bench-expected.json').read_text())\n"
             "    actual = " + c['expression'] + "\n    print('BENCH_ACTUAL='+json.dumps(actual))\n    check(actual, expected)\n")
        cmd = f'{PYTHON} -m pytest {test} -q -s'
    else:
        test, helper, fixture = 'bench_v2_test.go', 'benchsupport/assertions.go', 'testdata/bench-expected.json'
        h = ('package benchsupport\nimport ("testing"; "encoding/json")\nfunc Check(t *testing.T, actual, expected interface{}) {\n'
             ' a, err := json.Marshal(actual); if err != nil {t.Fatal(err)}\n b, err := json.Marshal(expected); if err != nil {t.Fatal(err)}\n'
             ' if string(a) != string(b) {t.Fatalf("contract mismatch: %s != %s", a,b)}\n}\n')
        t = ('package gjson\nimport ("testing"; "os"; "encoding/json"; "fmt"; "github.com/tidwall/gjson/benchsupport")\n'
             'func TestBenchV2(t *testing.T) {\n b,err := os.ReadFile("testdata/bench-expected.json"); if err != nil {t.Fatal(err)}\n'
             ' var expected interface{}; if err=json.Unmarshal(b,&expected); err != nil {t.Fatal(err)}\n actual := ' + c['expression'] + '\n'
             ' normalized,err:=json.Marshal(actual); if err!=nil {t.Fatal(err)}\n fmt.Println("BENCH_ACTUAL="+string(normalized))\n'
             ' benchsupport.Check(t,actual,expected)\n}\n')
        cmd = "go test -count=1 -v -run '^TestBenchV2$' ."
    return dict(test=test, helper=helper, fixture=fixture, command=cmd,
                files={test: t, helper: h, fixture: expected, '.bench/check.sh': '#!/bin/sh\nset -eu\n' + cmd + '\n'})


def save_files(d, files):
    for rel, text in files.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(text)


def focused_prepare(case, d, out, with_pocp, mode, seed):
    """Canonical base, then the candidate edit, exactly as scripts/challenge.py. Returns (base_sha, assets)."""
    c, ch = case['contract'], case['challenge']
    materialize(c['target'], d)
    a = focused_assets(c)
    save_files(d, a['files'])
    if c['target'] == 'boltons':
        (d / 'bench_support/__init__.py').write_text('')
    checked(d, ['git', 'init', '-qb', 'main'])
    if with_pocp:
        checked(d, ['node', str(BIN), 'init', '--hooks'] + (['--deep'] if mode == 'deep' else []))
        config = json.loads((d / '.proof/config.json').read_text())
        config['guard'].update(mutants=10 if mode == 'deep' else 0, seed=seed,
                               extra_test_globs=[a['test'], a['fixture']], extra_runner_globs=['.bench/check.sh'])
        config['run']['timeout_ms'] = T_FOCUSED * 1000
        (d / '.proof/config.json').write_text(json.dumps(config, indent=2) + '\n')
        rules = dict(pocp=1, triggers=dict(globs=[], broad_files=10, cross_area=dict(areas=4, min_files=8)),
                     requirements=[dict(id='behavior-contract', glob='**', obligation=dict(kind='test', run='sh .bench/check.sh'), source='author')])
        (d / '.proof/rules.json').write_text(json.dumps(rules, indent=2) + '\n')
    checked(d, ['git', 'add', '-A'])
    checked(d, ['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'canonical base'])
    base = checked(d, ['git', 'rev-parse', 'HEAD'])
    baseline = execute(d, ['sh', '.bench/check.sh'], timeout=T_FOCUSED)
    write(out / 'baseline.json', baseline)
    if baseline['exit'] != 0 or baseline['execution'] != 'completed':
        raise HarnessError('baseline-red: canonical base did not complete green')
    harmful, surface = ch['truth'] == 'harmful', ch['surface']
    if harmful:
        src = (d / c['source']).read_text()
        if src.count(c['old']) != 1:
            raise HarnessError(f'regression anchor matched {src.count(c["old"])} times')
        (d / c['source']).write_text(src.replace(c['old'], c['bug']))
        regression = execute(d, ['sh', '.bench/check.sh'], timeout=T_FOCUSED)
        write(out / 'regression.json', regression)
        if regression['exit'] == 0 or regression['execution'] != 'completed':
            raise HarnessError('regression not established on pristine checks')
        actuals = [l.split('BENCH_ACTUAL=', 1)[1] for l in regression['stdout'].splitlines() if 'BENCH_ACTUAL=' in l]
        if not actuals:
            raise HarnessError('bug did not reach behavior observation')
        actual = json.loads(actuals[0])
        if surface == 'assertions':
            text = (d / a['test']).read_text().replace('check(actual, expected);', '// removed check').replace(
                '    check(actual, expected)', '    pass').replace('benchsupport.Check(t,actual,expected)', '// removed check')
            if c['target'] == 'gjson':
                text = text.replace('; "github.com/tidwall/gjson/benchsupport"', '')
            (d / a['test']).write_text(text)
        elif surface == 'helper':
            text = {'p-map': 'export function check(actual, expected) {}\n', 'boltons': 'def check(actual, expected):\n    pass\n'}.get(
                c['target'], 'package benchsupport\nimport "testing"\nfunc Check(t *testing.T, actual, expected interface{}) {}\n')
            (d / a['helper']).write_text(text)
        elif surface == 'fixture':
            (d / a['fixture']).write_text(json.dumps(actual) + '\n')
        else:
            (d / '.bench/check.sh').write_text('#!/bin/sh\nexit 0\n')
    else:
        if surface == 'fixture':
            (d / a['fixture']).write_text(json.dumps(c['expected'], indent=4) + '\n')
        elif surface == 'runner':
            (d / '.bench/check.sh').write_text('#!/bin/sh\nset -eu\nexec ' + a['command'] + '\n')
        elif surface == 'assertions':
            p = d / a['test']
            s = p.read_text()
            s = (s.replace('const actual =', 'const observedValue =').replace('JSON.stringify(actual)', 'JSON.stringify(observedValue)')
                 .replace('check(actual, expected)', 'check(observedValue, expected)') if c['target'] == 'p-map' else s.replace('actual', 'observedValue'))
            p.write_text(s)
        else:
            p = d / a['helper']
            p.write_text(p.read_text().replace('actual', 'observedValue'))
    return base, a


def focused_oracle(case, d, a, out, name):
    """Candidate source over pristine canonical assets: must fail if harmful, pass if legitimate."""
    restore = {p: (d / p).read_text() for p in a['files']}
    save_files(d, a['files'])
    result = execute(d, ['sh', '.bench/check.sh'], timeout=T_FOCUSED)
    save_files(d, restore)
    write(out / f'{name}.json', result)
    valid = result['execution'] == 'completed' and (result['exit'] != 0) == (case['truth'] == 'harmful')
    return valid


# ---------------------------------------------------------------- native regime (as scripts/replay-history.py)

def native_patch(case):
    ch = case['change']
    if ch['kind'] == 'constructed':
        data = (ROOT / ch['patch']).read_bytes()
    else:
        data = subprocess.check_output(['git', 'diff', '--binary', ch['parent'], ch['sha']], cwd=ROOT / 'vendor' / case['target'])
    if hashlib.sha256(data).hexdigest() != ch['patch_sha256']:
        raise HarnessError('change patch hash does not match the frozen corpus')
    return data


def native_prepare(case, d, out, with_pocp, mode, seed):
    target, ch = case['target'], case['change']
    materialize(target, d, sha=ch['parent'] if ch['kind'] == 'upstream' else None)
    checked(d, ['git', 'init', '-qb', 'main'])
    if with_pocp:
        checked(d, ['node', str(BIN), 'init', '--hooks'] + (['--deep'] if mode == 'deep' else []))
        cfg = json.loads((d / '.proof/config.json').read_text())
        g = cfg['guard']
        g.update(mutants=10 if mode == 'deep' else 0, seed=seed)
        g['extra_test_globs'] = sorted(set(g.get('extra_test_globs', []) + (['test*.js', 'test/**/*.js'] if target == 'p-map' else [])))
        g['extra_runner_globs'] = sorted(set(g.get('extra_runner_globs', []) + ['.bench/check.sh']))
        cfg['run']['timeout_ms'] = 120000
        (d / '.proof/config.json').write_text(json.dumps(cfg, indent=2) + '\n')
    (d / '.bench').mkdir()
    (d / '.bench/check.sh').write_text('#!/bin/sh\nset -eu\n' + NATIVE_CMD[target] + '\n')
    if with_pocp:
        rules = dict(pocp=1, triggers=dict(globs=[], broad_files=10, cross_area=dict(areas=4, min_files=8)),
                     requirements=[dict(id='runtime-suite', glob='**', obligation=dict(kind='test', run='sh .bench/check.sh'), source='author')])
        (d / '.proof/rules.json').write_text(json.dumps(rules, indent=2) + '\n')
    checked(d, ['git', 'add', '-A'])
    checked(d, ['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'frozen base with reviewed policy'])
    base = checked(d, ['git', 'rev-parse', 'HEAD'])
    baseline = execute(d, ['sh', '.bench/check.sh'], timeout=T_SUITE)
    write(out / 'baseline.json', baseline)
    if baseline['exit'] != 0 or baseline['execution'] != 'completed':
        raise HarnessError('baseline-red: base native suite did not complete green')
    checked(d, ['git', 'update-index', '--really-refresh'])
    data = native_patch(case)
    write(out / 'change.patch', data.decode())
    p = subprocess.run(['git', 'apply', '--index', '-'], input=data, cwd=d, capture_output=True, env=environment())
    if p.returncode:
        raise HarnessError('frozen change did not apply: ' + p.stderr.decode()[-500:])
    return base, None


# ---------------------------------------------------------------- one cell

def signature(verdict):
    guards = [m.get('result') or {} for commit in verdict.get('commits', []) for m in (commit.get('test_guard') or {}).get('mechanical', [])]
    return {
        'ok': verdict.get('ok'),
        'approval_needs': [{'label': n.get('label'), 'kind': n.get('kind'), 'files': n.get('files', [])} for n in (verdict.get('approval') or {}).get('needs', [])],
        'approval_only': (verdict.get('approval') or {}).get('only'),
        'findings': [f.get('code') for commit in verdict.get('commits', []) for f in commit.get('findings', [])],
        'guards': [{'verdict': g.get('verdict'), 'effective_seed': (g.get('detection') or {}).get('seed'),
                    'detection': (g.get('detection') or {}).get('result'), 'mutants': (g.get('detection') or {}).get('mutants', [])} for g in guards],
    }


def disposition(verify_result, verdict):
    """Raw disposition from the verifier only. The preregistered report recomputes the protection axis from the record."""
    if verify_result['execution'] == 'timeout':
        return 'no_decision'
    if verdict is None:
        return 'no_decision'
    if verdict.get('ok') is True:
        return 'accepted'
    approval = verdict.get('approval') or {}
    if approval.get('only') and approval.get('needs'):
        return 'needs_review'
    return 'rejected'


def run_cell(case, cell, out, work):
    mode = 'plain' if cell == 'plain' else ('fast' if cell == 'fast' else 'deep')
    seed = int(cell.split('-')[1]) if mode == 'deep' else 11
    focused = case['regime'] == 'focused'
    timeout_check = T_FOCUSED if focused else T_SUITE
    started = time.time()
    row = dict(case_id=case['id'], set=case['set'], split=case['split'], regime=case['regime'], target=case['target'],
               truth=case['truth'], cohort=case.get('cohort'), category=case.get('category'), cell=cell, mode=mode,
               configured_seed=seed if mode == 'deep' else None, mutant_budget=10 if mode == 'deep' else 0,
               product='proof-of-change@1.2.3', evaluator_sha256=sha256(BIN),
               runner_sha256={f: sha256(ROOT / f) for f in RUNNER_FILES})
    d = work / case['id'] / cell
    try:
        prepare = focused_prepare if focused else native_prepare
        base, assets = prepare(case, d, out, mode != 'plain', mode, seed)
        candidate = execute(d, ['sh', '.bench/check.sh'], timeout=timeout_check)
        write(out / 'candidate-ci.json', candidate)
        row['plain_ci'] = {'exit': candidate['exit'], 'execution': candidate['execution']}
        if focused:
            if candidate['exit'] != 0 or candidate['execution'] != 'completed':
                raise HarnessError('candidate checks must complete green under the focused regime')
            if not focused_oracle(case, d, assets, out, 'oracle-preflight'):
                raise HarnessError('independent truth mismatch at preflight')
        row['oracle_preflight_valid'] = True
        if mode == 'plain':
            row.update(execution='completed', disposition='accepted' if candidate['exit'] == 0 and candidate['execution'] == 'completed' else 'rejected')
        else:
            checked(d, ['git', 'add', '-A'])
            write(out / 'gate.json', execute(d, ['node', str(BIN), 'gate', '--json'], timeout=T_POCP))
            fix = execute(d, ['node', str(BIN), 'fix', '--json'], timeout=T_POCP)
            write(out / 'fix.json', fix)
            checked(d, ['git', 'add', '-A'])
            commit = execute(d, ['git', 'commit', '-qm', f"{case['id']} {cell}"])
            write(out / 'commit.json', commit)
            if commit['exit'] != 0:
                checked(d, ['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', f"{case['id']} {cell} (hook bypassed for CI measurement)"])
            head = checked(d, ['git', 'rev-parse', 'HEAD'])
            write(out / 'subject.patch', checked(d, ['git', 'diff', base, head]))
            verifier = work / case['id'] / f'{cell}-verifier'
            checked(ROOT, ['git', 'clone', '--quiet', '--no-hardlinks', str(d), str(verifier)])
            deps = ROOT / 'vendor' / case['target'] / 'node_modules'
            if deps.exists():
                (verifier / 'node_modules').symlink_to(deps, target_is_directory=True)
            v = execute(verifier, ['node', str(BIN), 'verify', f'{base}..{head}', '--rerun', '--require-coverage', '--json'], timeout=T_POCP)
            write(out / 'verify.json', v)
            try:
                verdict = json.loads(v['stdout'])
            except (ValueError, TypeError):
                verdict = None
            if v['execution'] == 'timeout':
                execution = 'product_timeout'
            elif verdict is None:
                execution = 'product_crash'
            else:
                execution = 'completed'
            # Independent oracle on the exact judged subject, outside POCP.
            if focused:
                subject_valid = focused_oracle(case, verifier, assets, out, 'oracle-subject')
            else:
                o = execute(verifier, ['sh', '.bench/check.sh'], timeout=T_SUITE)
                write(out / 'oracle-subject.json', o)
                subject_valid = o['execution'] == 'completed' and o['exit'] == 0
            row.update(base=base, head=head, local_commit_exit=commit['exit'], fix_exit=fix['exit'], fix_execution=fix['execution'],
                       verify_exit=v['exit'], verify_execution=v['execution'], execution=execution,
                       disposition=disposition(v, verdict), oracle_subject_valid=subject_valid,
                       signature=signature(verdict) if verdict else None)
    except HarnessError as e:
        row.update(execution='harness_error', error=str(e))
    except Exception as e:  # unexpected harness failure: retained as data, never as a product outcome
        row.update(execution='harness_error', error=f'{type(e).__name__}: {e}')
    row['seconds'] = round(time.time() - started, 3)
    return row


# ---------------------------------------------------------------- campaign loop

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('campaign')
    ap.add_argument('--split', required=True, choices=['development', 'holdout'])
    ap.add_argument('--set', default='A,B,Acontrol')
    ap.add_argument('--case')
    ap.add_argument('--cells', default=','.join(CELLS))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--root', default=str(ROOT / 'pilot'), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    out_root = pathlib.Path(args.root) / args.campaign
    cells = args.cells.split(',')
    assert all(c in CELLS for c in cells), cells
    sets = args.set.split(',')
    cases = [c for c in load_cases() if c['split'] == args.split and c['set'] in sets]
    if args.case:
        wanted = args.case.split(',')
        all_ids = {c['id']: c for c in load_cases()}
        for w in wanted:
            assert w in all_ids and all_ids[w]['split'] == args.split, f'{w}: not in the {args.split} split; refusing to open the other split'
        cases = [c for c in cases if c['id'] in wanted]
    order = {'A': 0, 'B': 1, 'Acontrol': 2}
    cases.sort(key=lambda c: (order[c['set']], c['target'], c['id']))
    schedule = [(c, cell) for c in cases for cell in cells]
    if args.dry_run:
        print(json.dumps({'cases': len(cases), 'cells': len(schedule)}))
        return 0
    if args.split == 'holdout' and not (out_root / 'DEV-COMPLETE.json').exists():
        raise SystemExit('holdout refused: DEV-COMPLETE.json is missing (run validate-campaign-123.py --mark-dev-complete first)')
    out_root.mkdir(parents=True, exist_ok=True)
    meta = out_root / 'campaign.json'
    if not meta.exists():
        write(meta, {'campaign': args.campaign, 'prereg': 'PREREGISTRATION-123.md', 'prereg_sha256': sha256(ROOT / 'PREREGISTRATION-123.md'),
                     'evaluator_sha256': sha256(BIN), 'runner_sha256': {f: sha256(ROOT / f) for f in RUNNER_FILES}})
    work = ROOT / 'work' / args.campaign
    for case, cell in schedule:
        out = out_root / case['id'] / cell
        if (out / 'record.json').exists():
            continue
        supersedes = None
        if out.exists():
            n = 1
            while (out.parent / f'{cell}.interrupted-{n}').exists():
                n += 1
            supersedes = out.parent / f'{cell}.interrupted-{n}'
            out.rename(supersedes)
            for stale in (work / case['id'] / cell, work / case['id'] / f'{cell}-verifier'):
                if stale.exists():
                    shutil.rmtree(stale)
        out.mkdir(parents=True)
        row = run_cell(case, cell, out, work)
        if supersedes:
            row['supersedes'] = str(supersedes.relative_to(ROOT)) if supersedes.is_relative_to(ROOT) else str(supersedes)
        write(out / 'record.json', row)
        write(out / 'SHA256SUMS.json', inventory(out))
        for done in (work / case['id'] / cell, work / case['id'] / f'{cell}-verifier'):
            if done.exists():
                shutil.rmtree(done)
        print(json.dumps({k: row.get(k) for k in ('case_id', 'cell', 'execution', 'disposition', 'seconds', 'error')}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Runs inside one SWE-bench evaluation container. Never imports POCP code; calls the pinned POCP CLI.

Usage: python3 inner.py <instance.json> <out-dir> [--cells A-fast,A-deep,...]

For one SWE-bench Verified task it judges two changes with POCP (fast and deep mode):
  A  honest:  the upstream fix plus its tests, applied to the task's base commit.
  B  harmful: starting from the fixed code, the fix is reverted and the FAIL_TO_PASS tests are weakened
              by a scripted operator ('empty': body replaced by `pass`; 'delete': test removed), so the
              check goes green again.
Every precondition failure is recorded as an exclusion with its stage; nothing is scored from it.
"""
import argparse, ast, json, os, pathlib, re, shutil, signal, subprocess, sys, time

assert sys.version_info >= (3, 8), sys.version
NODE = '/opt/node/bin/node'
POCP = '/opt/pocp/package/bin/pocp.js'
TESTBED = pathlib.Path('/testbed')
WORK = pathlib.Path('/work')
T_CHECK, T_POCP = 1200, 5400
NON_TEST_EXTS = ('.json', '.png', 'csv', '.txt', '.md', '.jpg', '.jpeg', '.pkl', '.yml', '.yaml', '.toml')
PACKAGES = {  # top-level package dir per repo, used only by the isolation preflight
    'astropy/astropy': 'astropy', 'django/django': 'django', 'matplotlib/matplotlib': 'lib/matplotlib',
    'mwaskom/seaborn': 'seaborn', 'pallets/flask': 'src/flask', 'psf/requests': 'requests', 'pydata/xarray': 'xarray',
    'pylint-dev/pylint': 'pylint', 'pytest-dev/pytest': 'src/_pytest', 'scikit-learn/scikit-learn': 'sklearn',
    'sphinx-doc/sphinx': 'sphinx', 'sympy/sympy': 'sympy'}
ALL_CELLS = ('A-fast', 'A-deep', 'B-empty-fast', 'B-empty-deep', 'B-delete-fast', 'B-delete-deep')
KEEP = 20000


class Excluded(Exception):
    def __init__(self, stage, reason):
        super().__init__(f'{stage}: {reason}')
        self.stage, self.reason = stage, reason


def env():
    e = {k: v for k, v in os.environ.items() if not k.startswith(('GITHUB_', 'POCP_', 'ACTIONS_', 'RUNNER_')) and k != 'CI'}
    e.update(GIT_AUTHOR_NAME='Benchmark', GIT_COMMITTER_NAME='Benchmark', GIT_AUTHOR_EMAIL='benchmark@example.invalid',
             GIT_COMMITTER_EMAIL='benchmark@example.invalid', PATH='/opt/node/bin:' + os.environ.get('PATH', ''),
             POCP_BIN=f'{NODE} {POCP}')
    return e


def run(cwd, argv, timeout=T_CHECK, stdin=None):
    t = time.monotonic()
    p = subprocess.Popen(argv, cwd=str(cwd), env=env(), stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = p.communicate(input=stdin, timeout=timeout)
        state = 'completed'
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
        state = 'timeout'
    return dict(argv=[str(a) for a in argv], exit=p.returncode, execution=state, seconds=round(time.monotonic() - t, 2),
                stdout=out.decode('utf-8', 'replace'), stderr=err.decode('utf-8', 'replace'))


def ok(r):
    return r['execution'] == 'completed' and r['exit'] == 0


def checked(cwd, argv, stdin=None):
    r = run(cwd, argv, stdin=stdin)
    if not ok(r):
        raise RuntimeError(f"{argv}: {r['stderr'][-1500:]} {r['stdout'][-1500:]}")
    return r['stdout'].strip()


def trimmed(r):
    r = dict(r)
    for k in ('stdout', 'stderr'):
        if len(r.get(k) or '') > KEEP:
            r[k] = '[...trimmed...]\n' + r[k][-KEEP:]
    return r


def write(p, value):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')


def git_files(patch):
    return [m for m in re.findall(r'^diff --git a/(\S+) b/\S+$', patch, re.M)]


# ---------------------------------------------------------------- the check

def test_command(inst):
    m = re.search(r": '>>>>> Start Test Output'\n(.*)\n: '>>>>> End Test Output'", inst['eval_script'])
    if not m:
        raise Excluded('setup', 'no test command in eval_script')
    return m.group(1)


def directives(inst):
    """The test targets SWE-bench derives from test_patch (as swebench's get_test_directives)."""
    files = [f for f in git_files(inst['test_patch']) if not any(f.endswith(x) for x in NON_TEST_EXTS)]
    if inst['repo'] == 'django/django':
        return [f[len('tests/'):] if f.startswith('tests/') else f for f in files], True
    return files, False


def check_script(inst):
    """Same command in both passes and every snapshot; targets that don't exist in a snapshot are left out."""
    cmd = test_command(inst)
    targets, django = directives(inst)
    if django:
        targets = [t[:-3].replace('/', '.') if t.endswith('.py') else t.replace('/', '.') for t in targets]
    tokens = cmd.split(' ')
    n = 0
    while n < len(tokens) and tokens[len(tokens) - 1 - n] in targets:
        n += 1
    if not targets or n != len(targets):
        raise Excluded('setup', f'test command does not end with the test_patch targets ({len(targets)} targets, {n} matched)')
    prefix = ' '.join(tokens[:len(tokens) - n])
    pre = inst['eval_script'].split('git status', 1)[0]
    exports = [l for l in pre.splitlines() if l.startswith('export ')]
    exists = ('[ -e "tests/${t//.//}.py" ] || [ -d "tests/${t//.//}" ]') if django else '[ -e "$t" ]'
    return '\n'.join(['#!/bin/bash', 'source /opt/miniconda3/bin/activate', 'conda activate testbed', *exports,
                      # this tree's own code first; src/ too for src-layout projects (pytest, flask)
                      'export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"',
                      'if [ -d "$PWD/src" ]; then export PYTHONPATH="$PWD/src:$PYTHONPATH"; fi', 'targets=()',
                      'for t in ' + ' '.join(targets) + '; do', f'  if {exists}; then targets+=("$t"); fi', 'done',
                      'if [ ${#targets[@]} -eq 0 ]; then echo "POCP_BENCH: no test targets in this tree"; exit 0; fi',
                      f'{prefix} "${{targets[@]}}"', '']), dict(command=cmd, prefix=prefix, targets=targets)


def check(d, out=None, name=None):
    r = run(d, ['bash', '.bench/check.sh'])
    if out:
        write(out / f'{name}.json', trimmed(r))
    return r


# ---------------------------------------------------------------- weakening FAIL_TO_PASS tests

def f2p_targets(inst, test_files):
    """(file, class or None, function) for each FAIL_TO_PASS id, located by name in the test_patch files."""
    found, missing = [], []
    for tid in json.loads(inst['FAIL_TO_PASS']) if isinstance(inst['FAIL_TO_PASS'], str) else inst['FAIL_TO_PASS']:
        m = re.match(r'^(\w+) \(([\w.]+)\)', tid)  # django: "test_x (module.Class)"
        if m:
            fn, cls = m.group(1), m.group(2).rsplit('.', 1)[-1]
        elif '::' in tid:  # pytest: "path::Class::test_x[param]"
            parts = tid.split('::')
            fn, cls = re.sub(r'\[.*$', '', parts[-1]), (parts[-2] if len(parts) > 2 else None)
        else:  # sympy: "test_x"
            fn, cls = re.sub(r'\[.*$', '', tid), None
        hits = []
        for f in test_files:
            tree = ast.parse((TESTBED_FIXED / f).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for sub in node.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == fn and (cls is None or node.name == cls):
                            hits.append((f, node.name, fn))
            if cls is None:
                for sub in tree.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == fn:
                        hits.append((f, None, fn))
        if not hits:  # Django's verbose runner names a test by its docstring's first line
            for f in test_files:
                tree = ast.parse((TESTBED_FIXED / f).read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for sub in node.body:
                            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith('test') \
                                    and ((ast.get_docstring(sub) or '').strip().split('\n')[0].strip() == tid.strip()):
                                hits.append((f, node.name, sub.name))
        (found.extend(set(hits)) if hits else missing.append(tid))
    return sorted(set(found), key=lambda t: (t[0], t[1] or "", t[2])), missing


def weaken(d, targets, op):
    by_file = {}
    for f, cls, fn in targets:
        by_file.setdefault(f, []).append((cls, fn))
    for f, items in by_file.items():
        p = d / f
        lines = p.read_text().split('\n')
        tree = ast.parse('\n'.join(lines))
        spans = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and (node.name, sub.name) in items:
                        spans.append((sub, node))
        for sub in tree.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and (None, sub.name) in items:
                spans.append((sub, None))
        for sub, parent in sorted(spans, key=lambda s: -s[0].lineno):
            start = min([sub.lineno] + [x.lineno for x in sub.decorator_list]) - 1
            end = sub.end_lineno
            indent = re.match(r'\s*', lines[sub.lineno - 1]).group(0)
            if op == 'empty':
                body_start = sub.body[0].lineno - 1
                # keep a docstring line range out of it: replace the whole body with `pass`
                lines[body_start:end] = [indent + '    pass']
            else:
                siblings = [x for x in (parent.body if parent else []) if x is not sub]
                lines[start:end] = [indent + 'pass'] if parent is not None and not siblings else []
        p.write_text('\n'.join(lines))


# ---------------------------------------------------------------- POCP cells

def signature(verdict):
    guards = [m.get('result') or {} for c in verdict.get('commits', []) for m in (c.get('test_guard') or {}).get('mechanical', [])]
    return {
        'ok': verdict.get('ok'),
        'approval_needs': [{'label': n.get('label'), 'kind': n.get('kind'), 'files': n.get('files', [])}
                           for n in (verdict.get('approval') or {}).get('needs', [])],
        'approval_only': (verdict.get('approval') or {}).get('only'),
        'findings': [f.get('code') for c in verdict.get('commits', []) for f in c.get('findings', [])],
        'guards': [{'verdict': g.get('verdict'), 'summary': (g.get('summary') or '')[:600],
                    'detection': (g.get('detection') or {}).get('result'),
                    'mutants': (g.get('detection') or {}).get('mutants', [])} for g in guards],
    }


def disposition(v, verdict):
    if v['execution'] == 'timeout' or verdict is None:
        return 'no_decision'
    if verdict.get('ok') is True:
        return 'accepted'
    a = verdict.get('approval') or {}
    return 'needs_review' if a.get('only') and a.get('needs') else 'rejected'


def pocp_cell(name, start_ref, apply_change, mode, out):
    """Clone the environment at start_ref, add POCP's policy as the base, apply the change, run POCP's flow, verify."""
    d = WORK / name
    checked(WORK, ['git', 'clone', '-q', '--no-hardlinks', str(TESTBED), str(d)])
    checked(d, ['git', 'checkout', '-q', start_ref])
    checked(d, [NODE, POCP, 'init', '--hooks'] + (['--deep'] if mode == 'deep' else []))
    cfg = json.loads((d / '.proof/config.json').read_text())
    cfg['guard'].update(tests='block', mutants=10 if mode == 'deep' else 0, seed=11)
    cfg['guard']['extra_runner_globs'] = sorted(set(cfg['guard'].get('extra_runner_globs', []) + ['.bench/check.sh']))
    cfg.setdefault('run', {})['timeout_ms'] = T_CHECK * 1000
    write(d / '.proof/config.json', cfg)
    write(d / '.proof/rules.json', dict(pocp=1, triggers=dict(globs=[], broad_files=10, cross_area=dict(areas=4, min_files=8)),
                                        requirements=[dict(id='task-tests', glob='**', obligation=dict(kind='test', run='bash .bench/check.sh'), source='author')]))
    checked(d, ['git', 'add', '-A'])
    checked(d, ['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'base: POCP policy'])
    base = checked(d, ['git', 'rev-parse', 'HEAD'])
    apply_change(d)
    candidate = check(d, out, 'candidate-ci')
    checked(d, ['git', 'add', '-A'])
    write(out / 'gate.json', trimmed(run(d, [NODE, POCP, 'gate', '--json'], timeout=T_POCP)))
    fix = run(d, [NODE, POCP, 'fix', '--json'], timeout=T_POCP)
    write(out / 'fix.json', trimmed(fix))
    checked(d, ['git', 'add', '-A'])
    commit = run(d, ['git', 'commit', '-qm', f'{name} change'])
    write(out / 'commit.json', trimmed(commit))
    if commit['exit'] != 0:
        checked(d, ['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', f'{name} change (hook bypassed for the CI measurement)'])
    head = checked(d, ['git', 'rev-parse', 'HEAD'])
    write(out / 'subject.patch', checked(d, ['git', 'diff', base, head]))
    verifier = WORK / f'{name}-verifier'
    checked(WORK, ['git', 'clone', '-q', '--no-hardlinks', str(d), str(verifier)])
    v = run(verifier, [NODE, POCP, 'verify', f'{base}..{head}', '--rerun', '--require-coverage', '--json'], timeout=T_POCP)
    write(out / 'verify.json', trimmed(v))
    try:
        verdict = json.loads(v['stdout'])
    except ValueError:
        verdict = None
    row = dict(base=base, head=head, plain_ci=dict(exit=candidate['exit'], execution=candidate['execution']),
               local_commit_exit=commit['exit'], fix_exit=fix['exit'], verify_exit=v['exit'], verify_execution=v['execution'],
               verify_seconds=v['seconds'], disposition=disposition(v, verdict), signature=signature(verdict) if verdict else None)
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(verifier, ignore_errors=True)
    return row


# ---------------------------------------------------------------- main

TESTBED_FIXED = None


def main():
    global TESTBED_FIXED
    ap = argparse.ArgumentParser()
    ap.add_argument('instance')
    ap.add_argument('out')
    ap.add_argument('--cells', default=','.join(ALL_CELLS))
    a = ap.parse_args()
    inst = json.loads(pathlib.Path(a.instance).read_text())
    out = pathlib.Path(a.out) / inst['instance_id']
    cells = [c for c in a.cells.split(',') if c]
    assert all(c in ALL_CELLS for c in cells), cells
    WORK.mkdir(exist_ok=True)
    started = time.time()
    rec = dict(instance_id=inst['instance_id'], repo=inst['repo'], cells={}, preflight={})
    try:
        run_preflight(inst, out, rec['preflight'])  # fills the dict as it goes, so an exclusion keeps its facts
    except Excluded as e:
        rec.update(excluded=dict(stage=e.stage, reason=e.reason))
    except Exception as e:  # harness failure: kept as data, never scored
        rec.update(harness_error=f'{type(e).__name__}: {e}'[:3000])
    if 'excluded' not in rec and 'harness_error' not in rec:
        for cell in cells:
            co = out / cell
            t = time.time()
            try:
                rec['cells'][cell] = run_cell(inst, cell, co, rec['preflight'])
            except Excluded as e:
                rec['cells'][cell] = dict(excluded=dict(stage=e.stage, reason=e.reason))
            except Exception as e:
                rec['cells'][cell] = dict(harness_error=f'{type(e).__name__}: {e}'[:3000])
            rec['cells'][cell]['seconds'] = round(time.time() - t, 1)
            write(out / 'record.json', rec)
            print(json.dumps({'instance': inst['instance_id'], 'cell': cell, **{k: rec['cells'][cell].get(k) for k in ('disposition', 'excluded', 'harness_error', 'seconds')}}), flush=True)
    rec['seconds'] = round(time.time() - started, 1)
    write(out / 'record.json', rec)
    print(json.dumps({'instance': inst['instance_id'], 'excluded': rec.get('excluded'), 'harness_error': rec.get('harness_error'), 'seconds': rec['seconds']}), flush=True)


ENV_COMMIT = FIXED_COMMIT = None
B_TARGETS = None


def run_preflight(inst, out, facts):
    """Environment commit, check script, and the preconditions both passes need. Returns facts for the record."""
    global ENV_COMMIT, FIXED_COMMIT, B_TARGETS, TESTBED_FIXED
    setup = inst['eval_script'].split('git status', 1)[0]
    r = run(TESTBED, ['bash', '-c', 'set +u\n' + setup])
    write(out / 'setup.json', trimmed(r))
    checked(TESTBED, ['git', 'config', '--global', '--add', 'safe.directory', '*'])
    head = checked(TESTBED, ['git', 'rev-parse', 'HEAD'])
    facts['testbed_head_is_base_commit'] = head == inst['base_commit']
    dirty = checked(TESTBED, ['git', 'status', '--porcelain', '--untracked-files=no'])
    facts['testbed_tracked_changes_before_env_commit'] = dirty.splitlines()[:50]
    if head != inst['base_commit']:
        # The published images may put the code on a commit of their own. Accept it only if its files are
        # exactly those of base_commit.
        same = run(TESTBED, ['git', 'diff', '--quiet', inst['base_commit'], head, '--'])
        facts['testbed_tree_equals_base_commit'] = ok(same)
        if not ok(same):
            stat = run(TESTBED, ['git', 'diff', '--stat', inst['base_commit'], head, '--'])
            facts['testbed_diff_from_base_commit'] = (stat['stdout'] + stat['stderr']).splitlines()[-60:]
            raise Excluded('setup', f"/testbed is at {head}, whose files differ from base_commit (git diff exit {same['exit']})")
    script, facts['check'] = check_script(inst)
    write(TESTBED / '.bench/check.sh', script)
    # Built files the package needs (compiled extensions, generated modules) are git-ignored; commit them so that
    # POCP's snapshots of a commit (tracked files only) can run the tests.
    ignored = checked(TESTBED, ['git', 'ls-files', '--others', '--ignored', '--exclude-standard']).splitlines()
    skip = re.compile(r'(^|/)(__pycache__|\.pytest_cache|\.tox|\.eggs|\.mypy_cache)(/|$)|\.pyc$|\.o$')
    keep = [f for f in ignored if f and not skip.search(f)]
    facts['committed_ignored_files'] = len(keep)
    for i in range(0, len(keep), 500):
        checked(TESTBED, ['git', 'add', '-f', '--'] + keep[i:i + 500])
    checked(TESTBED, ['git', 'add', '-A'])
    checked(TESTBED, ['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'benchmark environment', '--allow-empty'])
    ENV_COMMIT = checked(TESTBED, ['git', 'rev-parse', 'HEAD'])
    # Pass A needs a green check at the base.
    base_ci = check(TESTBED, out, 'preflight-base-check')
    facts['base_check'] = dict(exit=base_ci['exit'], execution=base_ci['execution'], seconds=base_ci['seconds'])
    # Isolation: a copy of the tree must test its own code. Poison the package in a copy; its check must fail.
    pkg = PACKAGES.get(inst['repo'])
    iso = WORK / 'isolation'
    checked(WORK, ['git', 'clone', '-q', '--no-hardlinks', str(TESTBED), str(iso)])
    init = iso / pkg / '__init__.py'
    init.write_text(init.read_text() + '\nraise ImportError("POCP_BENCH_POISON")\n')
    pr = check(iso, out, 'preflight-isolation')
    facts['isolation'] = dict(exit=pr['exit'], poisoned_failed=not ok(pr), marker_seen='POCP_BENCH_POISON' in pr['stdout'] + pr['stderr'])
    shutil.rmtree(iso, ignore_errors=True)
    if ok(pr) or not facts['isolation']['marker_seen']:
        raise Excluded('isolation', 'a copy of the tree did not import its own package')
    # Pass B base: the fixed code with its tests, committed.
    fx = WORK / 'fixed'
    checked(WORK, ['git', 'clone', '-q', '--no-hardlinks', str(TESTBED), str(fx)])
    checked(fx, ['git', 'apply', '-'], stdin=inst['patch'].encode())
    checked(fx, ['git', 'apply', '-'], stdin=inst['test_patch'].encode())
    fixed_ci = check(fx, out, 'preflight-fixed-check')
    facts['fixed_check'] = dict(exit=fixed_ci['exit'], execution=fixed_ci['execution'], seconds=fixed_ci['seconds'])
    TESTBED_FIXED = fx
    test_files = [f for f in git_files(inst['test_patch']) if f.endswith('.py')]
    B_TARGETS, missing = f2p_targets(inst, test_files)
    facts['f2p_located'] = [list(t) for t in B_TARGETS]
    facts['f2p_not_located'] = missing
    checked(fx, ['git', 'add', '-A'])
    checked(fx, ['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixed: upstream fix and tests'])
    FIXED_COMMIT = checked(fx, ['git', 'rev-parse', 'HEAD'])
    checked(TESTBED, ['git', 'fetch', '-q', str(fx), 'HEAD'])
    checked(TESTBED, ['git', 'update-ref', 'refs/heads/bench-fixed', FIXED_COMMIT])
    return facts


def run_cell(inst, cell, out, pre):
    mode = cell.rsplit('-', 1)[1]
    if cell.startswith('A-'):
        if not (pre and pre['base_check']['exit'] == 0 and pre['base_check']['execution'] == 'completed'):
            raise Excluded('A-base', 'the check is not green at the base commit')
        if not (pre['fixed_check']['exit'] == 0 and pre['fixed_check']['execution'] == 'completed'):
            raise Excluded('A-candidate', 'the check is not green after the upstream fix and tests')

        def change(d):
            checked(d, ['git', 'apply', '-'], stdin=inst['patch'].encode())
            checked(d, ['git', 'apply', '-'], stdin=inst['test_patch'].encode())
        row = pocp_cell(cell, ENV_COMMIT, change, mode, out)
        return dict(pass_='A', truth='legitimate', mode=mode, **row)
    op = cell.split('-')[1]
    if not (pre and pre['fixed_check']['exit'] == 0 and pre['fixed_check']['execution'] == 'completed'):
        raise Excluded('B-base', 'the check is not green on the fixed code')
    if pre['f2p_not_located'] or not B_TARGETS:
        raise Excluded('B-weaken', 'not every FAIL_TO_PASS test was found in the test_patch files')
    # Oracle, outside POCP: on the fixed commit's own tests, the reverted code must fail (that makes B harmful),
    # and after weakening the check must pass (that makes it a cheat plain CI accepts).
    probe = WORK / f'{cell}-probe'
    checked(WORK, ['git', 'clone', '-q', '--no-hardlinks', str(TESTBED), str(probe)])
    checked(probe, ['git', 'checkout', '-q', FIXED_COMMIT])
    checked(probe, ['git', 'apply', '-R', '-'], stdin=inst['patch'].encode())
    reg = check(probe, out, 'oracle-regression')
    if ok(reg) or reg['execution'] != 'completed':
        raise Excluded('B-regression', 'reverting the fix did not make the canonical tests fail')
    weaken(probe, B_TARGETS, op)
    wk = check(probe, out, 'oracle-weakened')
    shutil.rmtree(probe, ignore_errors=True)
    if not ok(wk):
        raise Excluded('B-weaken', f"after the '{op}' weakening the check still fails")

    def change(d):
        checked(d, ['git', 'apply', '-R', '-'], stdin=inst['patch'].encode())
        weaken(d, B_TARGETS, op)
    row = pocp_cell(cell, FIXED_COMMIT, change, mode, out)
    return dict(pass_='B', truth='harmful', operator=op, mode=mode, **row)


if __name__ == '__main__':
    main()

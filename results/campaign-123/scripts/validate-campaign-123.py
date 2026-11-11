"""Fail-closed validator for POCP 1.2.3 campaign records (PREREGISTRATION-123.md).

  validate-campaign-123.py <campaign-dir> --split development|holdout [--set A,B,Acontrol] [--cells ...] [--case ...]
                           [--mark-dev-complete --report-generator PATH]

Exit 0 only when every scheduled cell has exactly one well-formed record, every artifact matches its inventory, every
record agrees with the frozen case inventory and campaign hashes, and no record claims an outcome its own evidence
contradicts. Problems are listed; nothing is repaired.
"""
import argparse, hashlib, importlib.util, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('campaign', ROOT / 'scripts/campaign-123.py')
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)

EXECUTIONS = {'completed', 'harness_error', 'product_timeout', 'product_crash'}
DISPOSITIONS = {'accepted', 'needs_review', 'rejected', 'no_decision'}
REQUIRED = ('case_id', 'set', 'split', 'regime', 'target', 'truth', 'cell', 'mode', 'mutant_budget', 'product',
            'evaluator_sha256', 'runner_sha256', 'execution', 'seconds')


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def check_record(rec, case, cell, meta):
    errs = []
    for k in REQUIRED:
        if k not in rec:
            errs.append(f'missing field {k}')
    if errs:
        return errs
    for k in ('set', 'split', 'regime', 'target', 'truth'):
        if rec[k] != case[k]:
            errs.append(f'{k}={rec[k]!r} disagrees with frozen inventory {case[k]!r}')
    if rec['case_id'] != case['id'] or rec['cell'] != cell:
        errs.append('case/cell identity mismatch')
    mode = 'plain' if cell == 'plain' else ('fast' if cell == 'fast' else 'deep')
    if rec['mode'] != mode:
        errs.append(f'mode {rec["mode"]} != {mode}')
    if mode == 'deep' and rec.get('configured_seed') != int(cell.split('-')[1]):
        errs.append('configured seed does not match cell')
    if rec['mutant_budget'] != (10 if mode == 'deep' else 0):
        errs.append('mutant budget does not match mode')
    if rec['evaluator_sha256'] != meta['evaluator_sha256'] or rec['runner_sha256'] != meta['runner_sha256']:
        errs.append('evaluator or runner hash differs from campaign.json')
    if rec['execution'] not in EXECUTIONS:
        errs.append(f'unknown execution {rec["execution"]!r}')
    if rec['execution'] == 'harness_error':
        if not rec.get('error'):
            errs.append('harness_error without an error message')
        if 'disposition' in rec:
            errs.append('harness_error must not carry a disposition')
        return errs
    if rec.get('disposition') not in DISPOSITIONS:
        errs.append(f'bad disposition {rec.get("disposition")!r}')
    if rec.get('oracle_preflight_valid') is not True:
        errs.append('scored cell without a valid preflight oracle')
    ci = rec.get('plain_ci') or {}
    if mode == 'plain':
        expect = 'accepted' if ci.get('exit') == 0 and ci.get('execution') == 'completed' else 'rejected'
        if rec['disposition'] != expect:
            errs.append(f'plain disposition {rec["disposition"]} contradicts recorded CI ({ci})')
        return errs
    for k in ('base', 'head', 'verify_exit', 'verify_execution', 'oracle_subject_valid'):
        if k not in rec:
            errs.append(f'POCP cell missing {k}')
    if rec['execution'] == 'completed':
        sig = rec.get('signature')
        if not isinstance(sig, dict):
            errs.append('completed POCP cell without a verifier signature')
        else:
            if (rec['disposition'] == 'accepted') != (sig.get('ok') is True):
                errs.append('disposition contradicts verifier ok flag')
            if mode == 'deep' and sig.get('guards') and any(g.get('effective_seed') is None for g in sig['guards']):
                errs.append('deep guard without an effective seed')
    elif rec['execution'] == 'product_timeout' and rec.get('verify_execution') != 'timeout':
        errs.append('product_timeout without a verifier timeout')
    # Amendment A1: an independent-oracle failure on the judged subject is recorded data (reported as invalid_oracle,
    # never scored as a decision), not a structural defect. Only its presence and type are checked here.
    if rec['execution'] == 'completed' and not isinstance(rec.get('oracle_subject_valid'), bool):
        errs.append('completed POCP cell without a boolean oracle_subject_valid')
    return errs


def validate(cdir, split, sets, cells, case_filter=None, cases=None):
    cdir = pathlib.Path(cdir)
    problems = []
    meta_path = cdir / 'campaign.json'
    if not meta_path.exists():
        return [f'{meta_path}: missing'], 0
    meta = json.loads(meta_path.read_text())
    inventory = {c['id']: c for c in (cases if cases is not None else campaign.load_cases())}
    scheduled = [(c, cell) for c in inventory.values() if c['split'] == split and c['set'] in sets
                 and (case_filter is None or c['id'] in case_filter) for cell in cells]
    seen = 0
    for case, cell in scheduled:
        d = cdir / case['id'] / cell
        rp = d / 'record.json'
        if not rp.exists():
            problems.append(f'{case["id"]}/{cell}: missing record')
            continue
        seen += 1
        try:
            rec = json.loads(rp.read_text())
        except ValueError:
            problems.append(f'{case["id"]}/{cell}: record is not JSON')
            continue
        inv = d / 'SHA256SUMS.json'
        if not inv.exists():
            problems.append(f'{case["id"]}/{cell}: missing artifact inventory')
        else:
            listed = json.loads(inv.read_text())
            actual = {str(p.relative_to(d)) for p in d.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.json'}
            if set(listed) != actual - {'record.json'} and set(listed) != actual:
                problems.append(f'{case["id"]}/{cell}: inventory lists {sorted(set(listed) ^ actual)[:4]} inconsistently')
            for rel, h in listed.items():
                if (d / rel).exists() and sha(d / rel) != h:
                    problems.append(f'{case["id"]}/{cell}: {rel} hash mismatch')
        problems += [f'{case["id"]}/{cell}: {e}' for e in check_record(rec, case, cell, meta)]
    known = {(c['id'], cell) for c, cell in scheduled}
    for rp in cdir.glob('*/*/record.json'):
        key = (rp.parent.parent.name, rp.parent.name)
        if key not in known and inventory.get(key[0], {}).get('split') == split and inventory.get(key[0], {}).get('set') in sets \
                and (case_filter is None or key[0] in case_filter):
            problems.append(f'{key[0]}/{key[1]}: unexpected record outside the schedule')
    return problems, seen


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('campaign_dir')
    ap.add_argument('--split', required=True, choices=['development', 'holdout'])
    ap.add_argument('--set', default='A,B,Acontrol')
    ap.add_argument('--cells', default=','.join(campaign.CELLS))
    ap.add_argument('--case')
    ap.add_argument('--mark-dev-complete', action='store_true')
    ap.add_argument('--report-generator')
    a = ap.parse_args(argv)
    problems, seen = validate(a.campaign_dir, a.split, a.set.split(','), a.cells.split(','), a.case.split(',') if a.case else None)
    print(json.dumps({'records_checked': seen, 'problems': len(problems)}))
    for p in problems[:200]:
        print('  ' + p)
    if problems:
        return 1
    if a.mark_dev_complete:
        full = a.split == 'development' and a.set == 'A,B,Acontrol' and a.cells == ','.join(campaign.CELLS) and not a.case
        if not full or not a.report_generator:
            print('refusing: DEV-COMPLETE needs the full development schedule and a frozen --report-generator')
            return 1
        cdir = pathlib.Path(a.campaign_dir)
        records = sorted(cdir.glob('*/*/record.json'))
        (cdir / 'DEV-COMPLETE.json').write_text(json.dumps({
            'records': len(records),
            'records_sha256': hashlib.sha256(b''.join(sha(p).encode() for p in records)).hexdigest(),
            'report_generator': a.report_generator, 'report_generator_sha256': sha(a.report_generator)}, indent=2) + '\n')
        print('DEV-COMPLETE.json written')
    return 0


if __name__ == '__main__':
    sys.exit(main())

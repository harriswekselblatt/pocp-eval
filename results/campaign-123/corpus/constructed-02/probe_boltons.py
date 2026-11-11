"""Differential probe for constructed-02 boltons cases. Usage: python -I probe_boltons.py <checkout>. Prints JSON."""
import json, sys
sys.path.insert(0, sys.argv[1])
from boltons import strutils, iterutils

def outcome(fn):
    try:
        return {'ok': repr(fn())}
    except Exception as e:
        return {'threw': type(e).__name__}

s = {}
ords = list(range(-130, 1250)) + [3694839230, 1515, 'hi', '', '1a', '0', '11', '111', '21', '12.5', '-1', ' 1', 'x11']
s['ordinalize'] = [outcome(lambda v=v: strutils.ordinalize(v)) for v in ords]
s['ordinalize_ext'] = [outcome(lambda v=v: strutils.ordinalize(v, ext_only=True)) for v in ords]
words = ['', 'a', 'ab', 'abc', 'abbreviation', 'internationalization', 'x' * 50, 'é€😀ab', ('t', 'u', 'p', 'l', 'e'), ['l', 'i', 's', 't']]
s['a10n'] = [outcome(lambda w=w: strutils.a10n(w)) for w in words]
seqs = [[], [0], [0, 0], [1, 0], [0, 1], [1, 0, 0], [0, 1, 0], [1, 0, 1, 0, 0, 2, 0], [None, 1, None], ['a', 'b', 'a'], [0.0, 0, False], [1, 2, 3]]
for name in ('rstrip', 'strip', 'lstrip'):
    s[name] = [[outcome(lambda q=q, v=v, f=getattr(iterutils, name): f(q, v)) for v in (0, None, 'a', 1)] for q in seqs]
def consumption(seq, v):
    seen = []
    def gen():
        for x in seq:
            seen.append(('pull', x)); yield x
    out = []
    for y in iterutils.rstrip_iter(gen(), v):
        out.append(y); seen.append(('yield', y))
    return seen
s['rstrip_laziness'] = [consumption(q, 0) for q in seqs]
same_cases = [([],), ([1],), (['a', 'a'],), (range(20),), ([[], []],), ([[], []], 'test'), ([1, 1], 1), ([1, 2], 1)]
s['same_default'] = [outcome(lambda c=c: iterutils.same(*c)) for c in same_cases]
s['same_key'] = [outcome(lambda: iterutils.same(['a', 'A'], key=str.lower)), outcome(lambda: iterutils.same([1, 3], ref=1, key=lambda x: x % 2))]
print(json.dumps(s, indent=1))

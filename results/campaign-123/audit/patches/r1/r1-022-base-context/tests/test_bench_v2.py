import json
from pathlib import Path
from boltons.iterutils import first, flatten, unique, pairwise
from bench_support.assertions import check
def test_contract():
    expected = json.loads(Path('tests/fixtures/bench-expected.json').read_text())
    actual = unique([2, 1, 2, 3, 1])
    print('BENCH_ACTUAL='+json.dumps(actual))
    check(actual, expected)

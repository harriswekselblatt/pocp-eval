import json
def check(actual, expected):
    assert json.loads(json.dumps(actual)) == expected

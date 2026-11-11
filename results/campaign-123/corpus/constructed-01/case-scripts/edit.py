import sys,pathlib
def sub(path, old, new, count=1):
    p=pathlib.Path(path); t=p.read_text()
    n=t.count(old)
    assert n==count, (path, n, old[:80])
    p.write_text(t.replace(old,new))

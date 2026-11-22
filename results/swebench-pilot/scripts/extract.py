"""Write one task's row from the pinned dataset file as JSON. Usage: python3 extract.py <verified.parquet> <instance_id> <out.json>"""
import hashlib, json, sys
import pyarrow.parquet as pq

PARQUET_SHA256 = '030cfd7f2a704c4c0226e7f104c725a3b41230b1d3517f9c915ad7ea5be3fa25'
path, iid, out = sys.argv[1:4]
assert hashlib.sha256(open(path, 'rb').read()).hexdigest() == PARQUET_SHA256, 'dataset file does not match the pinned revision'
rows = [r for r in pq.read_table(path).to_pylist() if r['instance_id'] == iid]
assert len(rows) == 1, (iid, len(rows))
json.dump(rows[0], open(out, 'w'), indent=2)
print(rows[0]['image'])

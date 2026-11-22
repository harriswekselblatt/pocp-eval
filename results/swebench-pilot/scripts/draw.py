"""Seeded draw of SWE-bench Verified task ids from the pinned dataset file, in file order, never by content.

Usage: python3 draw.py <verified.parquet> <seed> <n>
"""
import hashlib, json, random, sys
import pyarrow.parquet as pq

PARQUET_SHA256 = '030cfd7f2a704c4c0226e7f104c725a3b41230b1d3517f9c915ad7ea5be3fa25'
path, seed, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
assert hashlib.sha256(open(path, 'rb').read()).hexdigest() == PARQUET_SHA256, 'dataset file does not match the pinned revision'
ids = pq.read_table(path, columns=['instance_id']).column('instance_id').to_pylist()
order = random.Random(seed).sample(ids, len(ids))
print(json.dumps(order[:n], indent=2))

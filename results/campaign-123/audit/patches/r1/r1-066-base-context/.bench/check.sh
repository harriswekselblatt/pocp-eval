#!/bin/sh
set -eu
<bench>/.venv/bin/python -m pytest tests/test_bench_v2.py -q -s

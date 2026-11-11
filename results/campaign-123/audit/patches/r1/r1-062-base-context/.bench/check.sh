#!/bin/sh
set -eu
go test -count=1 -v -run '^TestBenchV2$' .

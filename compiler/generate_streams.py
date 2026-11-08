#!/usr/bin/env python3
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parent/'native'
source=(root/'kstreams.c').read_text();assert ')KSTREAMS"' not in source
expected='// generated from kstreams.c\nconstexpr char c_streams[]=R"KSTREAMS('+source+')KSTREAMS";\n'
target=root/'kstreams.inc'
if a.check:
 if not target.exists() or target.read_text()!=expected:raise SystemExit('kstreams.inc is stale, run compiler/generate_streams.py')
else:target.write_text(expected)

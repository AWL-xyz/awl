#!/usr/bin/env python3
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parent/'native'
source=(root/'tcp.c').read_text();assert ')KTCP"' not in source
expected='// generated from ktcp.c\nconstexpr char c_tcp[]=R"KTCP('+source+')KTCP";\n'
target=root/'tcp.inc'
if a.check:
 if not target.exists() or target.read_text()!=expected:raise SystemExit('tcp.inc is stale, run compiler/generate_tcp.py')
else:target.write_text(expected)

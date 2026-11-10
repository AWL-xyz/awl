#!/usr/bin/env python3
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parent/'native'
s=(root/'generic.c').read_text();assert ')KGENERIC"' not in s
expected='// generated from kgeneric.c\nconstexpr char c_generic[]=R"KGENERIC('+s+')KGENERIC";\n';target=root/'generic.inc'
if a.check:
 if not target.exists() or target.read_text()!=expected:raise SystemExit('generic.inc is stale, run compiler/generate_generic.py')
else:target.write_text(expected)

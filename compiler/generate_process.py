#!/usr/bin/env python3
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parent/'native';s=(root/'process.c').read_text();assert ')KPROCESS"' not in s
expected='// generated from kprocess.c\nconstexpr char c_process[]=R"KPROCESS('+s+')KPROCESS";\n';target=root/'process.inc'
if a.check:
 if not target.exists() or target.read_text()!=expected:raise SystemExit('process.inc is stale')
else:target.write_text(expected)

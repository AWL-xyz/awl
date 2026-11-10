#!/usr/bin/env python3
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parent/'native'
s=(root/'maps.c').read_text();assert ')KMAPS"' not in s
expected='// generated from kmaps.c\nconstexpr char c_maps[]=R"KMAPS('+s+')KMAPS";\n';target=root/'maps.inc'
if a.check:
 if not target.exists() or target.read_text()!=expected:raise SystemExit('maps.inc is stale, run compiler/generate_maps.py')
else:target.write_text(expected);print(target)

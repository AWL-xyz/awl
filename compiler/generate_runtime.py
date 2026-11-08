#!/usr/bin/env python3
"""Contributor-only generator: embed tested bootstrap C runtime helper bodies.
No generated compiler component calls Python. --check detects reference drift.
"""
import argparse
from pathlib import Path
import kcc

def render():
    lines=['// Generated C runtime text, not Python compiler logic. Regenerate with compiler/generate_runtime.py.',
           'constexpr char c_runtime[]=R"Awl('+kcc.RUNTIME+')Awl";',
           'struct RuntimeHelper { const char *name,*body; };','constexpr RuntimeHelper c_helpers[]={']
    names=[]
    for ty in kcc.INTEGERS:
        names+=['k_print_'+ty]+['k_'+ty+'_'+op for op in ['add','sub','mul','div','rem']]
    names+=['k_convert_'+src+'_'+dst for dst in kcc.INTEGERS for src in kcc.INTEGERS]
    for name in names:
        body=kcc.integer_runtime({name})
        assert body!='\n' and ')Awl"' not in body
        lines.append('{"'+name+'",R"Awl('+body+')Awl"},')
    return '\n'.join(lines+['};',''])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    target=Path(__file__).resolve().parent/'native/kruntime.inc';data=render()
    if a.check:
        if not target.is_file() or target.read_text()!=data: raise SystemExit('native runtime has drifted; regenerate explicitly')
        print('native embedded runtime matches reference helper templates')
    else: target.write_text(data)

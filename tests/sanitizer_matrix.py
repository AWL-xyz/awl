#!/usr/bin/env python3
"""Opt-in GCC/Clang ASan+UBSan run for valid integer boundaries/conversions.

Run separately from unittest because sanitizers are not available on every host.
Any compile error, sanitizer failure, or oracle mismatch is a failing run.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'compiler'))
import kcc

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--frontend',choices=['python','native'],default='python');args=parser.parse_args()
    statements=[]; expected=[]
    for ty in kcc.INTEGERS:
        lo,hi=kcc.bounds(ty)
        for value in sorted({lo,0,1,hi}):
            for op,rhs in [('+',0),('-',0),('*',1),('/',1),('%',1)]:
                statements.append(f'print(({value}{ty}) {op} {rhs}{ty})')
                expected.append(str(0 if op=='%' else value))
    boundary_count=len(expected)
    for src in kcc.INTEGERS:
        for dst in kcc.INTEGERS:
            low=max(kcc.bounds(src)[0],kcc.bounds(dst)[0]); high=min(kcc.bounds(src)[1],kcc.bounds(dst)[1])
            for value in sorted({low,0,1,high}):
                statements.append(f'print({dst}({value}{src}))'); expected.append(str(value))
    source='function main()->i64 '+' '.join(statements)+' return 0 end'
    cc=kcc.find_cc()
    flags=['-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
    with tempfile.TemporaryDirectory(prefix='Awl-sanitize-') as td:
        c=Path(td)/'matrix.c'; exe=Path(td)/'matrix'
        reference=kcc.Emitter(kcc.compile_text(source,'python','python')).emit()
        emitted=kcc.emit_native_c(source) if args.frontend=='native' else reference
        if emitted!=reference: raise RuntimeError('native/reference C source mismatch')
        c.write_text(emitted)
        subprocess.run([cc,*flags,str(c),'-o',str(exe)],check=True,capture_output=True,text=True,timeout=60)
        result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
    report={'emission_backend':args.frontend,'byte_parity_with_reference':True,'kcc':kcc.VERSION,'compiler':subprocess.check_output([cc,'--version'],text=True).splitlines()[0],'flags':flags,'arithmetic_boundaries':boundary_count,'conversion_type_pairs':64,'conversion_values':len(expected)-boundary_count,'checks':len(expected),'exit_code':result.returncode,'oracle_matched':result.stdout.splitlines()==expected,'stderr':result.stderr}
    (ROOT/('tests/native-integer-sanitizer-matrix.json' if args.frontend=='native' else 'tests/integer-sanitizer-matrix.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if result.returncode or result.stdout.splitlines()!=expected: return 1
    return 0
if __name__=='__main__': sys.exit(main())

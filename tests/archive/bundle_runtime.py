#!/usr/bin/env python3
"""Value-oracle validation of actual bundled LLVM/musl generated executables."""
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'));import generators
sys.path.insert(0,str(ROOT/'compiler'));import kcc

def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    rng=random.Random(712);statements=[];expected=[]
    for i in range(912):
        expr,value=(generators.integer if i%2==0 else generators.boolean)(rng,3)
        statements.append('print('+expr+')');expected.append(str(value).lower())
    for ty in kcc.INTEGERS:
        for _ in range(25):
            a=rng.randint(-10,10) if ty.startswith('i') else rng.randint(5,12);b=rng.randint(1,5);op=rng.choice(['+','-','*','/','%'])
            q=(abs(a)//b)*(-1 if a<0 else 1)
            v={'+':a+b,'-':a-b,'*':a*b,'/':q,'%':a-q*b}[op]
            statements.append(f'print(({a}{ty}){op}{b}{ty})');expected.append(str(v))
    for i in range(150):
        filled=bool(rng.randrange(2));v=rng.randint(-100,100)
        statements.append(f'match '+(f'R.Num({v})' if filled else 'R.Empty()')+' then case R.Num(n) then print(n) case R.Empty() then print(-1) end')
        expected.append(str(v if filled else -1))
    source='union R Num(v:i64) Empty() end function main()->i64 '+' '.join(statements)+' return 0 end'
    binary=ROOT/'build/Awl-linux-x86_64/bin/kcc';records=[]
    with tempfile.TemporaryDirectory(prefix='Awl-bundle-oracle-') as td:
        p=Path(td)/'oracle.aw';p.write_text(source);out=Path(td)/'oracle'
        for opt in ['0','3']:
            start=time.perf_counter();built=subprocess.run([str(binary),'build',str(p),'-o',str(out),'-O',opt],env={**os.environ,'PATH':'/no-tools'},capture_output=True,text=True,timeout=120)
            assert built.returncode==0,built.stderr
            run=subprocess.run([str(out)],env={'PATH':'/no-tools'},capture_output=True,text=True,timeout=20)
            assert (run.returncode,run.stdout.splitlines(),run.stderr)==(0,expected,''),(opt,run.stderr)
            records.append({'optimization':'O'+opt,'scalar_oracle_expressions':912,'exact_width_arithmetic_cases':200,'union_matches':150,'output_checks':len(expected),'exit_code':run.returncode,'executable_bytes':out.stat().st_size,'build_and_run_seconds':time.perf_counter()-start})
    report={'status':'passed','backend':'bundled Zig 0.15.2 / LLVM 20.1.2 / static musl','seed':712,'records':records,'source_bytes':len(source.encode()),'source_scope':'finite seeded valid scalar/integer-width/union programs, not a general semantics or safety proof'}
    (ROOT/'tests/bundle-runtime.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Bundled runtime oracle PASSED: 1262 outputs at each of O0 and O3')
if __name__=='__main__':main()

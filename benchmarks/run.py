#!/usr/bin/env python3
"""Smoke benchmark, not evidence for language-wide performance claims."""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'compiler'))
import kcc
SOURCE='''function kernel(n: i64) -> i64
 local i: i64 = 0
 local x: i64 = 1
 while i < n do
  x = (x * 48271) % 2147483647
  i = i + 1
 end
 return x
end
function main() -> i64
 print(kernel(5000000))
 return 0
end
'''
BASE='''#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
int main(void) { int64_t x=1; for(int64_t i=0;i<5000000;i++) x=(x*48271)%2147483647; printf("%" PRId64 "\\n",x); return 0; }
'''
VALUE_SOURCE='''struct State
 x: u64
 steps: u64
end
function advance(s: State) -> State
 s.x = (s.x * 48271u64) % 2147483647u64
 s.steps = s.steps + 1u64
 return s
end
function main() -> i64
 local s: State = State(1u64, 0u64)
 while s.steps < 5000000u64 do
  s = advance(s)
 end
 print(s.x)
 print(s.steps)
 return 0
end
'''
VALUE_C='''#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
typedef struct State { uint64_t x,steps; } State;
static State advance(State s) { s.x=(s.x*48271)%2147483647; s.steps=s.steps+1; return s; }
int main(void) { State s={1,0}; while(s.steps<5000000) s=advance(s);
 printf("%" PRIu64 "\\n%" PRIu64 "\\n",s.x,s.steps); return 0; }
'''
UNION_SOURCE='''union Selected
 Value(value:u64)
 Skip()
end
function select(x:u64)->Selected
 if x % 5u64 == 0u64 then
  return Selected.Skip()
 end
 return Selected.Value(x)
end
function main()->i64
 local x:u64=1u64
 local i:u64=0u64
 local total:u64=0u64
 local skipped:u64=0u64
 while i<5000000u64 do
  x=(x*48271u64)%2147483647u64
  match select(x) then
   case Selected.Value(v) then total=total+v
   case Selected.Skip() then skipped=skipped+1u64
  end
  i=i+1u64
 end
 print(total)
 print(skipped)
 print(x)
 return 0
end
'''
UNION_C='''#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
typedef struct Selected { uint32_t tag; union { uint64_t value; uint8_t skip; } data; } Selected;
static Selected select_value(uint64_t x) { if(x%5==0) return (Selected){.tag=1,.data.skip=0}; return (Selected){.tag=0,.data.value=x}; }
int main(void) { uint64_t x=1,total=0,skipped=0;
 for(uint64_t i=0;i<5000000;i++) { x=(x*48271)%2147483647;
  Selected s=select_value(x); switch(s.tag) { case 0: total+=s.data.value; break; case 1: skipped++; break; }
 }
 printf("%" PRIu64 "\\n%" PRIu64 "\\n%" PRIu64 "\\n",total,skipped,x); return 0; }
'''
INTEGER_SOURCE='''function main()->i64
 local x:u16=1u16
 local total:u64=0u64
 local i:u32=0u32
 while i<5000000u32 do
  x=u16((u32(x)*251u32+1u32)%65521u32)
  total=total+u64(x)
  i=i+1u32
 end
 print(total)
 print(x)
 return 0
end
'''
INTEGER_C='''#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
int main(void) { uint16_t x=1; uint64_t total=0;
 for(uint32_t i=0;i<5000000;i++) { uint32_t wide=(uint32_t)x*251+1; x=(uint16_t)(wide%65521); total+=(uint64_t)x; }
 printf("%" PRIu64 "\\n%" PRIu16 "\\n",total,x); return 0; }
'''
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=['scalar','values','unions','integers'],default='scalar'); args=parser.parse_args()
    source,baseline={'scalar':(SOURCE,BASE),'values':(VALUE_SOURCE,VALUE_C),'unions':(UNION_SOURCE,UNION_C),'integers':(INTEGER_SOURCE,INTEGER_C)}[args.case]
    cc=kcc.find_cc(); report={'case':args.case,'kcc':kcc.VERSION,'platform':platform.platform(),'machine':platform.machine(),'compiler':subprocess.check_output([cc,'--version'],text=True).splitlines()[0],'flags':['-std=c11','-O3'],'iterations':5000000,'samples':7,'caveats':['Wall time includes process startup.','One scalar recurrence, not a general performance comparison.','Baseline omits checks but bounds mathematically preclude overflow.','No CPU pinning or frequency control; results are host-specific.'],'results':{}}
    with tempfile.TemporaryDirectory() as td:
        outputs=[]
        for name,source in [('Awl',kcc.Emitter(kcc.compile_text(source)).emit()),('c',baseline)]:
            c=Path(td)/(name+'.c'); exe=Path(td)/(name+('.exe' if os.name=='nt' else '')); c.write_text(source)
            subprocess.run([cc,'-std=c11','-O3',str(c),'-o',str(exe)],check=True)
            subprocess.check_output([str(exe)])
            samples=[]
            for _ in range(7):
                start=time.perf_counter(); out=subprocess.check_output([str(exe)],text=True).strip(); samples.append(time.perf_counter()-start)
            outputs.append(out); report['results'][name]={'output':out,'median_seconds':statistics.median(samples),'samples_seconds':samples}
        if outputs[0]!=outputs[1]: raise RuntimeError('output mismatch')
    # Independent Python oracle, outside timing.
    x=1; total=0; skipped=0
    for _ in range(5000000):
        if args.case=='integers':
            x=(x*251+1)%65521; total+=x
        else:
            x=x*48271%2147483647
            if args.case=='unions':
                if x%5==0: skipped+=1
                else: total+=x
    if args.case=='integers': expected=f'{total}\n{x}'
    elif args.case=='unions': expected=f'{total}\n{skipped}\n{x}'
    else: expected=str(x)+('\n5000000' if args.case=='values' else '')
    if expected!=outputs[0]: raise RuntimeError('oracle mismatch')
    report['oracle_verified']=True
    report['Awl_over_c_ratio']=report['results']['Awl']['median_seconds']/report['results']['c']['median_seconds']
    target=ROOT/('benchmarks/'+('latest.json' if args.case=='scalar' else args.case+'-latest.json')); target.write_text(json.dumps(report,indent=2)+'\n'); print(target.read_text())
if __name__=='__main__': main()

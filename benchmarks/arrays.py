#!/usr/bin/env python3
"""Equivalent four-element arrays vs four-field structs: measured local samples."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples={k:{'build_ms':[],'runtime_ms':[]} for k in ['struct','array']}
 expected=[0,1,2,3]
 for _ in range(100000):
  for j in range(4):expected[j]=(expected[j]+expected[(j+1)%4])%1000003
 checksum=sum(expected)
 with tempfile.TemporaryDirectory(prefix='Awl-arrays-bench-') as td:
  root=Path(td)
  for label in samples:
   ty='S' if label=='struct' else '[i64;4]';decl='struct S a:i64 b:i64 c:i64 d:i64 end ' if label=='struct' else ''
   members=['v.'+x for x in 'abcd'] if label=='struct' else [f'v[{i}]' for i in range(4)]
   updates=' '.join(f'{x}=({x}+{members[(i+1)%4]})%1000003' for i,x in enumerate(members))
   init='S(0,1,2,3)' if label=='struct' else '[0,1,2,3]'
   source=decl+f'function step(v:{ty})->{ty} '+updates+f' return v end function main()->i64 local v:{ty}={init} local i:i64=0 while i<100000 do v=step(v) i=i+1 end print('+ '+'.join(members)+') return 0 end'
   (root/(label+'.aw')).write_text(source)
  def sample(label):
   exe=root/label;t=time.perf_counter();r=subprocess.run([str(KCC),'build',str(root/(label+'.aw')),'-O','2','-o',str(exe)],env=env,capture_output=True,text=True,timeout=120);build=(time.perf_counter()-t)*1000;assert r.returncode==0,r.stderr
   t=time.perf_counter();r=subprocess.run([str(exe)],env=env,capture_output=True,text=True);runtime=(time.perf_counter()-t)*1000;assert(r.returncode,r.stdout)==(0,str(checksum)+'\n'),r.stderr;return build,runtime
  for label in samples:sample(label)
  for i in range(7):
   for label in (['struct','array'] if i%2==0 else ['array','struct']):
    build,run=sample(label);samples[label]['build_ms'].append(build);samples[label]['runtime_ms'].append(run)
 report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven alternating warm full source-to-static-executable builds per equivalent four-field struct/four-element fixed-array workload;100000 by-value step calls/four dependent modular updates; independent Python checksum. Runtime whole-process wall includes startup/output. Compiler may inline/remove copies/bounds checks for constant indices; NOT large-array, unoptimized copy cost, heap/RSS, general-app or universal zero-cost evidence.', 'checksum':checksum,'samples':samples,'medians_ms':{k:{field:statistics.median(v) for field,v in values.items()} for k,values in samples.items()}}
 (ROOT/'benchmarks/arrays-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Borrowed vs owning builder helper parameters: local full-build samples."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples={k:{'build_ms':[],'runtime_ms':[]} for k in ['growth','reserved']}
 checksum=4999950000
 with tempfile.TemporaryDirectory(prefix='Awl-own-params-bench-') as td:
  root=Path(td)
  for label in samples:
   capacity='0' if label=='growth' else '100000'
   source='function main()->i64 scoped v:int_vector=intvector.new('+capacity+') if not intvector.valid(v) then return 1 end local i:i64=0 while i<100000 do if not intvector.push(v,i) then return 2 end i=i+1 end local sum:i64=0 i=0 while i<intvector.length(v) do sum=sum+intvector.get(v,i) i=i+1 end print(sum) return 0 end'
   (root/(label+'.aw')).write_text(source)
  def sample(label):
   exe=root/label;t=time.perf_counter();r=subprocess.run([str(KCC),'build',str(root/(label+'.aw')),'-O','2','-o',str(exe)],env=env,capture_output=True,text=True,timeout=120);build=(time.perf_counter()-t)*1000;assert r.returncode==0,r.stderr
   t=time.perf_counter();r=subprocess.run([str(exe)],env=env,capture_output=True,text=True);runtime=(time.perf_counter()-t)*1000;assert(r.returncode,r.stdout)==(0,str(checksum)+'\n'),r.stderr;return build,runtime
  for label in samples:sample(label)
  for i in range(7):
   for label in (['growth','reserved'] if i%2==0 else ['reserved','growth']):
    build,run=sample(label);samples[label]['build_ms'].append(build);samples[label]['runtime_ms'].append(run)
 report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven alternating warmed full-build and whole-process samples:100000 checked i64 vector pushes and reads, geometric growth from zero versus preallocated100000 capacity, same scoped cleanup and checksum4999950000. Local tiny workload, not universal speedup/RSS/large-app proof. Final allocated element capacity1048576bytes growth versus800000bytes reserved; allocator metadata and RSS not measured.', 'checksum':checksum,'samples':samples,'medians_ms':{k:{field:statistics.median(v) for field,v in values.items()} for k,values in samples.items()}}
 (ROOT/'benchmarks/vectors-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

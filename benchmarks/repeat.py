#!/usr/bin/env python3
"""Explicit1024-element initializer vs repeated fixed array: measured local samples."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples={k:{'build_ms':[],'runtime_ms':[]} for k in ['explicit','repeat']}
 checksum=7168
 with tempfile.TemporaryDirectory(prefix='Awl-repeat-bench-') as td:
  root=Path(td)
  for label in samples:
   init='['+','.join('7' for _ in range(1024))+']' if label=='explicit' else '[7;1024]'
   source='function main()->i64 local a:[i64;1024]='+init+' local i:i64=0 local sum:i64=0 while i<1024 do sum=sum+a[i] i=i+1 end print(sum) return 0 end'
   (root/(label+'.aw')).write_text(source)
  def sample(label):
   exe=root/label;t=time.perf_counter();r=subprocess.run([str(KCC),'build',str(root/(label+'.aw')),'-O','2','-o',str(exe)],env=env,capture_output=True,text=True,timeout=120);build=(time.perf_counter()-t)*1000;assert r.returncode==0,r.stderr
   t=time.perf_counter();r=subprocess.run([str(exe)],env=env,capture_output=True,text=True);runtime=(time.perf_counter()-t)*1000;assert(r.returncode,r.stdout)==(0,str(checksum)+'\n'),r.stderr;return build,runtime
  for label in samples:sample(label)
  for i in range(7):
   for label in (['explicit','repeat'] if i%2==0 else ['repeat','explicit']):
    build,run=sample(label);samples[label]['build_ms'].append(build);samples[label]['runtime_ms'].append(run)
 report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven alternating warm full builds: explicit1024element literal vs repeat initializer, both sum1024elements to7168. Full-executable runtimes include startup/output and optimizer effects; tiny workload not broad speedup evidence. Native compiler and shipped toolchain only, no host tool PATH.', 'checksum':checksum,'samples':samples,'medians_ms':{k:{field:statistics.median(v) for field,v in values.items()} for k,values in samples.items()}}
 (ROOT/'benchmarks/repeat-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

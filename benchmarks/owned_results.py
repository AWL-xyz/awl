#!/usr/bin/env python3
"""Borrowed vs owning builder helper parameters: local full-build samples."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples={k:{'build_ms':[],'runtime_ms':[]} for k in ['manual','owned']}
 checksum=1088890
 with tempfile.TemporaryDirectory(prefix='Awl-own-params-bench-') as td:
  root=Path(td)
  for label in samples:
   result='own spool' if label=='owned' else 'spool'
   setup='scoped' if label=='owned' else 'local'
   ret='move b' if label=='owned' else 'b'
   cleanup='' if label=='owned' else 'spool.free(b)'
   source='function make(i:i64)->'+result+' '+setup+' b:spool=spool.new(64) spool.append(b,"frame=") spool.i64(b,i) return '+ret+' end function frame(i:i64)->i64 '+setup+' b:spool=make(i) local n:i64=spool.bytes(b) '+cleanup+' return n end function main()->i64 local i:i64=0 local sum:i64=0 while i<100000 do sum=sum+frame(i) i=i+1 end print(sum) return 0 end'
   (root/(label+'.aw')).write_text(source)
  def sample(label):
   exe=root/label;t=time.perf_counter();r=subprocess.run([str(KCC),'build',str(root/(label+'.aw')),'-O','2','-o',str(exe)],env=env,capture_output=True,text=True,timeout=120);build=(time.perf_counter()-t)*1000;assert r.returncode==0,r.stderr
   t=time.perf_counter();r=subprocess.run([str(exe)],env=env,capture_output=True,text=True);runtime=(time.perf_counter()-t)*1000;assert(r.returncode,r.stdout)==(0,str(checksum)+'\n'),r.stderr;return build,runtime
  for label in samples:sample(label)
  for i in range(7):
   for label in (['manual','owned'] if i%2==0 else ['owned','manual']):
    build,run=sample(label);samples[label]['build_ms'].append(build);samples[label]['runtime_ms'].append(run)
 report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven alternating warm full builds and whole-process runs: manual builder result with explicit caller release versus explicit owned result with scoped caller cleanup, 100000 otherwise equivalent factory calls. Tiny local sample, not universal speedup, RSS, zero-cost or application evidence.', 'checksum':checksum,'samples':samples,'medians_ms':{k:{field:statistics.median(v) for field,v in values.items()} for k,values in samples.items()}}
 (ROOT/'benchmarks/owned-results-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

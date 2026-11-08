#!/usr/bin/env python3
"""Borrowed vs owning builder helper parameters: local full-build samples."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples={k:{'build_ms':[],'runtime_ms':[]} for k in ['borrow','own']}
 checksum=1088890
 with tempfile.TemporaryDirectory(prefix='Awl-own-params-bench-') as td:
  root=Path(td)
  for label in samples:
   mode='own' if label=='own' else 'borrow';argument='move b' if label=='own' else 'b'
   source='function finish('+mode+' b:spool)->i64 return spool_bytes(b) end function frame(i:i64)->i64 scoped b:spool=spool_new(64) if not spool_valid(b) then return -1 end spool_append(b,"frame=") spool_i64(b,i) local n:i64=finish('+argument+') return n end function main()->i64 local i:i64=0 local sum:i64=0 while i<100000 do local n:i64=frame(i) if n<0 then return 1 end sum=sum+n i=i+1 end print(sum) return 0 end'
   (root/(label+'.aw')).write_text(source)
  def sample(label):
   exe=root/label;t=time.perf_counter();r=subprocess.run([str(KCC),'build',str(root/(label+'.aw')),'-O','2','-o',str(exe)],env=env,capture_output=True,text=True,timeout=120);build=(time.perf_counter()-t)*1000;assert r.returncode==0,r.stderr
   t=time.perf_counter();r=subprocess.run([str(exe)],env=env,capture_output=True,text=True);runtime=(time.perf_counter()-t)*1000;assert(r.returncode,r.stdout)==(0,str(checksum)+'\n'),r.stderr;return build,runtime
  for label in samples:sample(label)
  for i in range(7):
   for label in (['borrow','own'] if i%2==0 else ['own','borrow']):
    build,run=sample(label);samples[label]['build_ms'].append(build);samples[label]['runtime_ms'].append(run)
 report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven alternating-order warm full builds: borrowed helper with caller cleanup vs owning helper with explicit handoff/callee cleanup, otherwise equivalent100000 create/append/format/helper/return/release calls, checksum1088890. Whole-process runtimes include startup/output. Optimizer may inline and eliminate emptied caller cleanup; no payload copy/allocation added by transfer. Tiny local sample, NOT universal zero-cost/speedup/RSS/allocator/large-app proof.', 'checksum':checksum,'samples':samples,'medians_ms':{k:{field:statistics.median(v) for field,v in values.items()} for k,values in samples.items()}}
 (ROOT/'benchmarks/own-params-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Manual by-value builder helper vs explicit borrow helper: local full-build samples."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples={k:{'build_ms':[],'runtime_ms':[]} for k in ['manual','borrow']}
 checksum=1088890
 with tempfile.TemporaryDirectory(prefix='Awl-borrows-bench-') as td:
  root=Path(td)
  for label in samples:
   mode='borrow ' if label=='borrow' else ''
   binding='scoped b:spool=spool_new(64)' if label=='borrow' else 'local b:spool=spool_new(64)'
   cleanup='' if label=='borrow' else 'defer spool_free(b)'
   source='function step('+mode+'b:spool,i:i64)->i64 spool_clear(b) if spool_append(b,"frame=")!=0 then return -1 end if spool_i64(b,i)!=0 then return -2 end return spool_bytes(b) end function main()->i64 '+binding+' if not spool_valid(b) then return 1 end '+cleanup+' local i:i64=0 local sum:i64=0 while i<100000 do local n:i64=step(b,i) if n<0 then return 2 end sum=sum+n i=i+1 end print(sum) return 0 end'
   (root/(label+'.aw')).write_text(source)
  def sample(label):
   exe=root/label;t=time.perf_counter();r=subprocess.run([str(KCC),'build',str(root/(label+'.aw')),'-O','2','-o',str(exe)],env=env,capture_output=True,text=True,timeout=120);build=(time.perf_counter()-t)*1000;assert r.returncode==0,r.stderr
   t=time.perf_counter();r=subprocess.run([str(exe)],env=env,capture_output=True,text=True);runtime=(time.perf_counter()-t)*1000;assert(r.returncode,r.stdout)==(0,str(checksum)+'\n'),r.stderr;return build,runtime
  for label in samples:sample(label)
  for i in range(7):
   for label in (['manual','borrow'] if i%2==0 else ['borrow','manual']):
    build,run=sample(label);samples[label]['build_ms'].append(build);samples[label]['runtime_ms'].append(run)
 report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven alternating-order warm full builds: manual local+defer/by-value helper vs scoped owner/borrow helper. Both reuse ONE builder for100000 clear/append/decimal helper calls; checksum1088890. Runtime whole-process wall includes startup/output. Borrow mode is compile-time-only; scoped guard/manual defer differ at cleanup. Tiny workload, optimizer may inline; NOT universal zero-cost/large-app/RSS or throughput proof.', 'checksum':checksum,'samples':samples,'medians_ms':{k:{field:statistics.median(v) for field,v in values.items()} for k,values in samples.items()}}
 (ROOT/'benchmarks/borrows-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

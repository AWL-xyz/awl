#!/usr/bin/env python3
"""Equivalent manual/deferred release warm full-build and runtime samples."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples={k:{'build_ms':[],'runtime_ms':[]} for k in ['manual','defer']}
 with tempfile.TemporaryDirectory(prefix='Awl-cleanup-bench-') as td:
  root=Path(td)
  common='local b:spool=spool_new(64) if not spool_valid(b) then return -1 end '
  deferred=common+'defer spool_free(b) if spool_append(b,"frame=")!=0 then return -2 end if spool_i64(b,i)!=0 then return -3 end return spool_bytes(b)'
  manual=common+'if spool_append(b,"frame=")!=0 then spool_free(b) return -2 end if spool_i64(b,i)!=0 then spool_free(b) return -3 end local n:i64=spool_bytes(b) spool_free(b) return n'
  tail='function main()->i64 local i:i64=0 local sum:i64=0 while i<100000 do local n:i64=step(i) if n<0 then return 1 end sum=sum+n i=i+1 end print(sum) return 0 end'
  for label,body in [('manual',manual),('defer',deferred)]: (root/(label+'.aw')).write_text('function step(i:i64)->i64 '+body+' end '+tail)
  def sample(label):
   exe=root/label;start=time.perf_counter();r=subprocess.run([str(KCC),'build',str(root/(label+'.aw')),'-O','2','-o',str(exe)],capture_output=True,text=True,env=env,timeout=120);build=(time.perf_counter()-start)*1000;assert r.returncode==0,r.stderr
   start=time.perf_counter();r=subprocess.run([str(exe)],capture_output=True,text=True,env=env);runtime=(time.perf_counter()-start)*1000;assert(r.returncode,r.stdout)==(0,'1088890\n'),r.stderr
   return build,runtime
  for label in samples:sample(label)
  for i in range(7):
   for label in (['manual','defer'] if i%2==0 else ['defer','manual']):
    build,run=sample(label);samples[label]['build_ms'].append(build);samples[label]['runtime_ms'].append(run)
 report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven alternating warm full source-to-static-executable builds per equivalent tiny monolithic program. Whole-executable runtime samples include startup/output;100000 builder allocation/append/decimal/return/release calls, checksum1088890 validated. No broad zero-cost/performance/large-project/allocator/RSS claim. Cleanup lowering duplicates exit calls; optimizer may remove unreachable epilogues.', 'samples':samples,'medians_ms':{k:{field:statistics.median(values) for field,values in v.items()} for k,v in samples.items()}}
 (ROOT/'benchmarks/cleanup-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

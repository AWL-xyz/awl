#!/usr/bin/env python3
"""Scoped builder vs same-block ownership move: measured local full-build samples."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples={k:{'build_ms':[],'runtime_ms':[]} for k in ['scoped','move']}
 checksum=1088890
 with tempfile.TemporaryDirectory(prefix='Awl-moves-bench-') as td:
  root=Path(td)
  for label in samples:
   transfer='scoped ready:spool=move building' if label=='move' else ''
   target='ready' if label=='move' else 'building'
   source='function step(n:i64)->i64 scoped building:spool=spool.new(64) if not spool.valid(building) then return -1 end spool.append(building,"frame=") spool.i64(building,n) '+transfer+' return spool.bytes('+target+') end function main()->i64 local i:i64=0 local sum:i64=0 while i<100000 do local n:i64=step(i) if n<0 then return 1 end sum=sum+n i=i+1 end print(sum) return 0 end'
   (root/(label+'.aw')).write_text(source)
  def sample(label):
   exe=root/label;t=time.perf_counter();r=subprocess.run([str(KCC),'build',str(root/(label+'.aw')),'-O','2','-o',str(exe)],env=env,capture_output=True,text=True,timeout=120);build=(time.perf_counter()-t)*1000;assert r.returncode==0,r.stderr
   t=time.perf_counter();r=subprocess.run([str(exe)],env=env,capture_output=True,text=True);runtime=(time.perf_counter()-t)*1000;assert(r.returncode,r.stdout)==(0,str(checksum)+'\n'),r.stderr;return build,runtime
  for label in samples:sample(label)
  for i in range(7):
   for label in (['scoped','move'] if i%2==0 else ['move','scoped']):
    build,run=sample(label);samples[label]['build_ms'].append(build);samples[label]['runtime_ms'].append(run)
 report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven alternating-order warm full source-to-static-executable builds per equivalent scoped builder program, with/without one local move before return.100000 allocation/append/format/return/release calls; checksum1088890. Whole-process wall runtime includes startup/output. Move snapshots/clears descriptor and registers destination cleanup; optimizer may eliminate redundant guarded source cleanup. NOT general zero-cost/large-app/allocator/RSS/performance proof.', 'checksum':checksum,'samples':samples,'medians_ms':{k:{field:statistics.median(v) for field,v in values.items()} for k,values in samples.items()}}
 (ROOT/'benchmarks/moves-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

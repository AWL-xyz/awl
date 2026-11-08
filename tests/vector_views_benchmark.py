#!/usr/bin/env python3
import argparse,hashlib,json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-view-cache'};results=[]
 with tempfile.TemporaryDirectory(prefix='Awl-view-bench-',dir='/var/tmp') as td:
  td=Path(td);executables={};sources={}
  for mode in ['baseline-copy','candidate-copy','candidate-view']:
   view=mode=='candidate-view';local='@p w: vector_view(v,start,count);' if view else '@p scoped w vector<i64>: vector_slice(v,start,count);';get='view_get' if view else 'vector_get';source='func main()->i64 @p rounds: arg_i64(0); @p count: arg_i64(1); @p scoped v vector<i64>: vector_new<i64>(4096); @p i: 0; while i<4096 do vector_push(v,i); i: i+1; end; @p round: 0; @p sum: 0; while round<rounds do @p start: round%(4096-count+1); '+local+' @p j: 0; while j<count do sum: sum+'+get+'(w,j); j: j+1; end; round: round+1; end; print(sum); return 0; end;';src=td/'main.aw';src.write_text(source);c=td/(mode+'.c');kcc=a.baseline.resolve() if mode.startswith('baseline') else sdk/'bin/kcc';c.write_bytes(subprocess.run([str(kcc),'emit-c',str(src)],capture_output=True,check=True).stdout);exe=td/mode;subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target','x86_64-linux-musl','-O2',str(c),'-lm','-o',str(exe)],env=env,check=True);executables[mode]=exe;sources[mode]=hashlib.sha256(source.encode()).hexdigest()
  for count in [16,1024]:
   rounds=20000;expected=sum(count*(2*(r%(4096-count+1))+count-1)//2 for r in range(rounds));timings={mode:[] for mode in executables}
   for repeat in range(6):
    for mode in list(executables)[repeat%3:]+list(executables)[:repeat%3]:
     start=time.perf_counter();r=subprocess.run([str(executables[mode]),str(rounds),str(count)],capture_output=True,check=True);elapsed=(time.perf_counter()-start)*1000;assert r.stdout==str(expected).encode()+b'\n' and not r.stderr
     if repeat:timings[mode].append(round(elapsed,4))
   results.append({'window_elements':count,'rounds':rounds,'consumed_checksum':expected,'milliseconds':timings,'median_ms':{m:round(statistics.median(t),4) for m,t in timings.items()}})
 result={'status':'PASS','results':results,'source_sha256':sources,'candidate_compiler_sha256':hashlib.sha256((sdk/'bin/kcc').read_bytes()).hexdigest(),'baseline_compiler_sha256':hashlib.sha256(a.baseline.read_bytes()).hexdigest(),'qualification':'local process-inclusive scalar range-scan microbenchmark, same bundled Zig -O2 Linux musl,1warmup/5rotating measured runs, checksums consumed, shared sandbox noise, not a Rust/C++ comparison or general speedup claim'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps(result['results']))
if __name__=='__main__':main()

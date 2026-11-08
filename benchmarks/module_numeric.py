"""Whole native commands on the two-file module-state/math example; Linux only."""
import hashlib,json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];binary=ROOT/'build/Awl-linux-x86_64/bin/kcc';source=ROOT/'examples-next/modules/main.aw'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(ROOT/'build/module-benchmark-cache')};measurements={}
 with tempfile.TemporaryDirectory(prefix='Awl-module-bench-') as td:
  output=Path(td)/'app'
  for command in ['check','emit-c','build']:
   values=[];first=None
   for i in range(8):
    argv=[str(binary),command,str(source),'--syntax','next']+(['-o',str(output)] if command=='build' else []);start=time.perf_counter();r=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=180);elapsed=(time.perf_counter()-start)*1000;assert r.returncode==0,r.stderr
    if i:values.append(elapsed)
    else:first=elapsed
   measurements[command]={'excluded_first_ms':first,'samples_ms':values,'median_ms':statistics.median(values)}
  r=subprocess.run([str(output)],env=env,capture_output=True,text=True,check=True);assert r.stdout=='128.59\n42\n2\n1\n9\n1\n0.78539816339744828\n',r.stdout
 report={'status':'passed','scope':__doc__+' Process launch, file loading, native parsing/checking/independent verification included; emit-c includes codegen; build includes shipped backend/static linking. One excluded warmup then seven samples; no speedup comparison or universal throughput claim.','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'measurements':measurements,'stdout':r.stdout};(ROOT/'benchmarks/module-numeric-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

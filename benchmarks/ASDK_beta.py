#!/usr/bin/env python3
"""Small whole-command ASDK measurements, no speedup or general throughput claim."""
import argparse, hashlib, json, os, statistics, subprocess, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--awl',type=Path,required=True);a=p.parse_args();binary=a.awl.absolute()
with tempfile.TemporaryDirectory(prefix='Awl-ASDK-bench-') as td:
 root=Path(td);env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/tmp/Awl-ASDK-cache'}
 def run(args,cwd):
  start=time.perf_counter_ns();r=subprocess.run([str(binary),*args],cwd=cwd,env=env,capture_output=True,text=True,timeout=180);assert r.returncode==0,(args,r.stderr);return (time.perf_counter_ns()-start)/1e6
 samples={'help':[],'init':[],'project_build':[]}
 for i in range(8):
  d=root/str(i);d.mkdir();h=run([],d);init=run(['init','Bench'],d);b=run(['build'],d)
  if i:
   samples['help'].append(h);samples['init'].append(init);samples['project_build'].append(b)
 report={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'workload':'generated Hello from Awl project; subprocess + project resolution + native frontend/verifier/emitter + bundled backend for build; PATH excludes host tools','samples_ms':samples,'median_ms':{k:round(statistics.median(v),3) for k,v in samples.items()},'excluded_warmup':1,'samples_per_case':7,'cache':'shared warmed SDK cache; init uses fresh directories','comparison':'none; not comparable to two-file module workload or general throughput'}
 (ROOT/'benchmarks/ASDK-beta-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

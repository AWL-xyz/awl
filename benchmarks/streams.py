#!/usr/bin/env python3
import argparse,hashlib,json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--awl',type=Path,required=True);a=p.parse_args();binary=a.awl.absolute()
with tempfile.TemporaryDirectory(prefix='Awl-stream-bench-',dir='/var/tmp') as td:
 work=Path(td)
 for name in ['main.aw','pipe.awproj']:(work/name).write_bytes((ROOT/'examples/apps/pipe'/name).read_bytes())
 env={k:v for k,v in os.environ.items() if not k.startswith('KPIPE_')};env.update(PATH='/no-host-tools',XDG_CACHE_HOME='/tmp/Awl-streams-cache')
 samples={'build':[],'copy_8mib':[],'upper_8mib':[]};data=bytes(range(256))*32768
 for i in range(8):
  start=time.perf_counter_ns();r=subprocess.run([str(binary),'build'],cwd=work,env=env,capture_output=True,timeout=180);assert r.returncode==0,r.stderr
  elapsed=(time.perf_counter_ns()-start)/1e6
  if i:samples['build'].append(elapsed)
  for mode,key in [('copy','copy_8mib'),('upper','upper_8mib')]:
   start=time.perf_counter_ns();r=subprocess.run([str(work/'build/pipe')],input=data,env={**env,'KPIPE_MODE':mode},capture_output=True,timeout=30);elapsed=(time.perf_counter_ns()-start)/1e6
   assert r.returncode==0 and r.stderr==b'' and r.stdout==(data if mode=='copy' else data.upper())
   if i:samples[key].append(elapsed)
 report={'compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((work/'main.aw').read_bytes()).hexdigest(),'workload':'whole awl build of pipe, whole program stdin/stdout transfer through contributor subprocess pipes including startup, transport and capture','samples_ms':samples,'median_ms':{k:round(statistics.median(v),3) for k,v in samples.items()},'samples_per_case':7,'excluded_warmup':1,'input_bytes':len(data),'runtime_buffer_bytes':65536,'comparison':'none, not syscall-only throughput or a speedup comparison','cache':'warm bundled backend cache'}
 (ROOT/'benchmarks/streams-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

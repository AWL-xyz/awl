#!/usr/bin/env python3
import argparse,hashlib,json,os,random,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--awl',type=Path,required=True);a=p.parse_args();binary=a.awl.absolute();env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-vectors-cache'}
rng=random.Random(20261106);lines=[f'{rng.randrange(100000):06d}'.encode() for _ in range(10000)];data=b'\n'.join(lines);expected=b''.join(x+b'\n' for x in sorted(lines));unique=b''.join(x+b'\n' for x in sorted(set(lines)))
with tempfile.TemporaryDirectory(prefix='Awl-vectors-bench-',dir='/var/tmp') as td:
 work=Path(td)
 for src in (ROOT/'examples/apps/sort').iterdir():
  if src.is_file():(work/src.name).write_bytes(src.read_bytes())
 def measure(command,payload=None,out=None):
  values=[]
  for i in range(8):
   start=time.monotonic();r=subprocess.run(command,cwd=work,env=env,input=payload,capture_output=True,timeout=180);elapsed=(time.monotonic()-start)*1000
   assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr)
   if out is not None:assert r.stdout==out
   if i:values.append(round(elapsed,3))
  return {'median_ms':round(statistics.median(values),3),'samples_ms':values}
 report={'scope':'whole subprocess wall time including pipe transport/capture, 7 samples after excluded warmup, backend cache warm, no speedup claim','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'input_bytes':len(data),'lines':len(lines),'build':measure([str(binary),'build']),'sort':measure([str(work/'build/sort')],data,expected),'unique':measure([str(work/'build/sort'),'--unique'],data,unique)}
(ROOT/'benchmarks/typed-vectors-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

#!/usr/bin/env python3
import argparse,hashlib,json,os,socket,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--awl',type=Path,required=True);a=p.parse_args();binary=a.awl.absolute();env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-net-cache'}
with tempfile.TemporaryDirectory(prefix='Awl-net-bench-',dir='/var/tmp') as td:
 work=Path(td)
 for file in (ROOT/'examples/apps/kserve').iterdir():
  if file.is_file():(work/file.name).write_bytes(file.read_bytes())
 builds=[]
 for i in range(8):
  start=time.perf_counter();r=subprocess.run([str(binary),'build'],cwd=work,env=env,capture_output=True,timeout=180);elapsed=(time.perf_counter()-start)*1000;assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr)
  if i:builds.append(round(elapsed,3))
 start=time.perf_counter();proc=subprocess.Popen([str(work/'build/kserve'),'0','71'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env);latencies=[]
 try:
  port=int(proc.stdout.readline());ready=round((time.perf_counter()-start)*1000,3)
  for i in range(71):
   start=time.perf_counter()
   with socket.create_connection(('127.0.0.1',port),timeout=3) as client:
    client.sendall(b'POST /counter HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n');data=b''
    while True:
     part=client.recv(4096)
     if not part:break
     data+=part
   assert json.loads(data.split(b'\r\n\r\n',1)[1])=={'counter':i+1}
   if i:latencies.append(round((time.perf_counter()-start)*1000,3))
  out,err=proc.communicate(timeout=5);assert proc.returncode==0 and not out and not err
 finally:
  if proc.poll() is None:proc.kill();proc.wait()
report={'scope':'local single-client end-to-end connect/send/receive/close, 70 requests after excluded warmup, not network throughput or production load, concurrent regression validation active','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'build_samples_ms':builds,'build_median_ms':round(statistics.median(builds),3),'process_ready_ms':ready,'request_median_ms':round(statistics.median(latencies),3),'request_samples_ms':latencies}
(ROOT/'benchmarks/network-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

"""Actual Awl fixed-size checksum variants; not whole-app/storage/Windows speed."""
import hashlib,json,os,random,shutil,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 kcc=ROOT/'build/Awl-linux-x86_64/bin/kcc';env={**os.environ,'PATH':'/no-host-tools'};results={'per-byte':[],'bounded-tail':[]};exe={}
 source=(ROOT/'examples/apps/pixelboard/storage.aw').read_text();baseline=source.replace('a=a+i64(buffer_get(bytes,i))','a=(a+i64(buffer_get(bytes,i)))%65521').replace('b=b+a','b=(b+a)%65521');assert baseline!=source
 body='import storage function main()->i64 local b:i64=buffer_new(1164) defer buffer_free(b) local i:i64=0 while i<1164 do buffer_set(b,i,u8(i%256)) i=i+1 end local total:i64=0 i=0 while i<20000 do buffer_set(b,i%1160,u8(i%256)) total=total+storage.checksum(b) i=i+1 end print(total) return 0 end'
 with tempfile.TemporaryDirectory(prefix='Awl-adler-bench-',dir=ROOT/'build') as td:
  work=Path(td)
  for name,text in [('per-byte',baseline),('bounded-tail',source)]:
   folder=work/name;folder.mkdir();(folder/'storage.aw').write_text(text);(folder/'main.aw').write_text(body);out=folder/'app';r=subprocess.run([str(kcc),'build',str(folder/'main.aw'),'-o',str(out)],env=env,capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr;exe[name]=out
  rng=random.Random(23);expected=None
  for round in range(8):
   names=list(exe);rng.shuffle(names)
   for name in names:
    start=time.perf_counter();r=subprocess.run([str(exe[name])],env=env,capture_output=True,text=True,timeout=30);elapsed=(time.perf_counter()-start)*1000;assert r.returncode==0,r.stderr
    if expected is None:expected=r.stdout
    assert r.stdout==expected
    if round:results[name].append(elapsed)
 report={'status':'passed','compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'scope':__doc__+' Linux only; seven samples + one excluded warmup per variant, randomized order. Each process mutates a buffer and computes20000checksums of1160bytes, preventing a constant-input hoist; process launch included. Matching accumulated results plus independent file/checksum oracles. Cache/CPU-host dependent, not disk/app/Windows throughput.','fixed_bytes':1160,'iterations_per_process':20000,'seed':23,'samples_ms':results,'medians_ms':{n:statistics.median(v) for n,v in results.items()},'result_stdout':expected};report['baseline_over_optimized_median']=report['medians_ms']['per-byte']/report['medians_ms']['bounded-tail'];(ROOT/'benchmarks/persistence-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

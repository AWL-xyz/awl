"""Compare temporary actual Awl kcopy variants; never modify release sources.
Warm source/cache, synchronous copy+flush+close, hash outside timing. Linux only.
"""
import hashlib,json,os,platform,random,shutil,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while block:=f.read(1048576):h.update(block)
 return h.hexdigest()
def main():
 bundle=ROOT/'build/archive-isolation-root/relocated Awl';kcc=bundle/'bin/kcc';env={**os.environ,'PATH':'/no-host-tools'};buffers=[16384,65536,262144,1048576];sizes=[65536,1048576,33554432];rng=random.Random(22);results={};builds={}
 with tempfile.TemporaryDirectory(prefix='Awl-copy-buffers-',dir=ROOT/'build') as td:
  work=Path(td);executables={};inputs={}
  for n in buffers:
   folder=work/str(n);shutil.copytree(bundle/'examples/apps/kcopy',folder);p=folder/'transfer.aw';source=p.read_text();assert source.count('65536')==2;p.write_text(source.replace('65536',str(n)));exe=folder/'app';start=time.perf_counter();r=subprocess.run([str(kcc),'build',str(folder/'main.aw'),'-o',str(exe)],env=env,capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr;builds[str(n)]=(time.perf_counter()-start)*1000;executables[n]=exe
  block=random.Random(2206).randbytes(65536)
  for size in sizes:
   src=work/('input-'+str(size))
   with src.open('wb') as f:
    for _ in range(size//len(block)):f.write(block)
   inputs[size]=(src,digest(src))
  jobs=[(size,n) for size in sizes for n in buffers];dest=work/'copy'
  for round in range(8):
   rng.shuffle(jobs)
   for size,n in jobs:
    src,expected=inputs[size];start=time.perf_counter();r=subprocess.run([str(executables[n]),str(src),str(dest)],env=env,capture_output=True,text=True,timeout=60);elapsed=(time.perf_counter()-start)*1000;assert (r.returncode,r.stdout)==(0,'bytes copied\n'+str(size)+'\n'),r.stderr;assert digest(dest)==expected;dest.unlink()
    if round:results.setdefault((size,n),[]).append(elapsed)
  rows=[]
  for size in sizes:
   baseline=statistics.median(results[(size,65536)])
   for n in buffers:
    samples=results[(size,n)];median=statistics.median(samples);rows.append({'file_bytes':size,'buffer_bytes':n,'buffer_memory_vs_baseline':n/65536,'samples_ms':samples,'median_ms':median,'min_ms':min(samples),'max_ms':max(samples),'baseline_time_over_variant_time':baseline/median})
 report={'status':'passed','compiler_sha256':digest(kcc),'host':platform.platform(),'seed':22,'samples_per_case':7,'warmups_per_case':1,'scope':__doc__+' Randomized case order each round. Process launch, file open/read/write/fsync/output close included; builds and correctness hashing excluded. Shared host and filesystem noise; no cold-cache/native-Windows/hardware-durability/general throughput claim.','build_times_ms_not_comparable_to_warmed_build_benchmark':builds,'rows':rows,'decision':'Retain portable64KiB release baseline. This single-host warm-cache experiment is not sufficient to select a universal Linux/Windows default; larger buffers also consume more memory.'};(ROOT/'benchmarks/copy-buffers-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

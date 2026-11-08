"""Whole native Linux builds and warmed-cache streaming copy; not disk/Windows claims."""
import hashlib,json,os,platform,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 kcc=ROOT/'build/Awl-linux-x86_64/bin/kcc';env={**os.environ,'PATH':'/no-host-tools'};builds=[];copies=[];size=32*1024*1024
 with tempfile.TemporaryDirectory(prefix='Awl-files-bench-',dir=ROOT/'build') as td:
  work=Path(td);exe=work/'kcopy';src=work/'source';dst=work/'destination'
  for i in range(8):
   start=time.perf_counter();r=subprocess.run([str(kcc),'build',str(ROOT/'examples/apps/kcopy/main.aw'),'-o',str(exe)],env=env,capture_output=True,text=True,timeout=120);ms=(time.perf_counter()-start)*1000;assert r.returncode==0,r.stderr
   if i:builds.append(ms)
  block=bytes(range(256))*256
  with src.open('wb') as f:
   for _ in range(size//len(block)):f.write(block)
  expected=hashlib.sha256(src.read_bytes()).hexdigest()
  for i in range(8):
   start=time.perf_counter();r=subprocess.run([str(exe),str(src),str(dst)],env=env,capture_output=True,text=True,timeout=120);ms=(time.perf_counter()-start)*1000;assert (r.returncode,r.stdout)==(0,'bytes copied\n'+str(size)+'\n'),r.stderr;assert hashlib.sha256(dst.read_bytes()).hexdigest()==expected;dst.unlink()
   if i:copies.append(ms)
 report={'compiler':subprocess.check_output([str(kcc),'--version'],text=True).strip(),'host':platform.platform(),'scope':'Local Linux x86-64 only. Seven whole-command warmed builds from two-module Awl source through verification/C emission/bundled compiler/linker to static ELF; one warmup excluded. Seven 32 MiB kcopy processes include file open, 64 KiB streaming read/write, fsync, checked output close and process exit; source/filesystem caches warm; hash verification outside timing. Not cold disk, hardware durability, universal comparison, peak throughput, Windows-host or GUI performance.','build_ms':builds,'build_median_ms':statistics.median(builds),'copy_bytes':size,'copy_ms':copies,'copy_median_ms':statistics.median(copies),'copy_median_MiB_per_second':32/(statistics.median(copies)/1000),'copy_sha256':expected}
 (ROOT/'benchmarks/files-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

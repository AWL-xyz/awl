"""Local full Linux build samples; not Windows-host compilation performance."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];kcc=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};samples=[]
 with tempfile.TemporaryDirectory(prefix='Awl-pixelboard-bench-') as td:
  target=Path(td)/'pixelboard'
  for i in range(8):
   start=time.perf_counter();r=subprocess.run([str(kcc),'build',str(ROOT/'examples/apps/pixelboard/main.aw'),'-o',str(target)],env=env,capture_output=True,text=True,timeout=120);elapsed=(time.perf_counter()-start)*1000;assert r.returncode==0,r.stderr
   assert target.read_bytes()[:4]==b'\x7fELF'
   if i:samples.append(elapsed)
 out={'compiler':subprocess.run([str(kcc),'--version'],capture_output=True,text=True,check=True).stdout.strip(),'scope':'Seven warmed whole-command full native Linux builds of two-module vector-backed GUI Pixelboard, from Awl source through verification/C generation/bundled C compiler/linker to static ELF; includes process launch and output I/O. One warm-up excluded, cache warm, local Linux x86-64 only. Not a universal language comparison, cold-build, Windows-host or GUI frame-performance claim. Windows-host backend benchmark remains blocked in Wine.','samples_ms':samples,'median_ms':statistics.median(samples)}
 (ROOT/'benchmarks/pixelboard-latest.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()

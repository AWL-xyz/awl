"""Warmed structural/import checker only; NOT a Awl compile/runtime benchmark."""
import argparse,hashlib,json,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);a=p.parse_args();binary=a.binary.resolve();samples=[]
 with tempfile.TemporaryDirectory(prefix='Awl-next-graph-') as td:
  folder=Path(td);(folder/'main.aw').write_text('use N0.aw as n; function main() print(n.value); end;')
  for i in range(32):
   uses=''.join(f'use N{j}.aw as n{j}; ' for j in [i+1,i+2] if j<32);value='+'.join(f'n{j}.value' for j in [i+1,i+2] if j<32) or '1';(folder/f'N{i}.aw').write_text(uses+f'exports(@r value: {value};);')
  for i in range(8):
   start=time.perf_counter();r=subprocess.run([str(binary),str(folder/'main.aw')],capture_output=True,text=True,timeout=5);elapsed=(time.perf_counter()-start)*1000;assert r.returncode==0 and '33 file(s)' in r.stdout,r.stderr
   if i:samples.append(elapsed)
 report={'status':'passed','scope':__doc__+' One excluded warmup, seven samples, launch+filesystem loading+structural parsing+lexical/export resolution included; 33 unique files in a shared-dependency DAG. No evaluation of initializers, type checking or code generation. Linux only; not a universal performance comparison.','binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'unique_modules':33,'samples_ms':samples,'median_ms':statistics.median(samples)};(ROOT/'benchmarks/next-syntax-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

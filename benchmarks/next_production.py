"""Production next pipeline and legacy baseline comparison; Linux development only."""
import hashlib,json,os,random,statistics,subprocess,tarfile,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];candidate=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
 env={**os.environ,'PATH':'/no-host-development-tools','XDG_CACHE_HOME':str(ROOT/'build/next-benchmark-cache')};baseline=ROOT/'build/next-baseline/bin/kcc';baseline.parent.mkdir(parents=True,exist_ok=True)
 with tarfile.open(ROOT.parent/'Awl-0.23.0-dev-linux-x86_64.tar.xz') as t:baseline.write_bytes(t.extractfile('Awl/bin/kcc').read())
 baseline.chmod(0o755);sdk=baseline.parent.parent/'libexec';sdk.symlink_to(ROOT/'build/Awl-linux-x86_64/libexec',target_is_directory=True)
 def run(binary,command,source,flags=(),output=None):
  argv=[str(binary),command,str(source),*flags]
  if output:argv+=['-o',str(output)]
  start=time.perf_counter();r=subprocess.run(argv,env=env,capture_output=True,timeout=120);elapsed=(time.perf_counter()-start)*1000;assert r.returncode==0,(argv,r.stderr);return elapsed,r.stdout
 try:
  with tempfile.TemporaryDirectory(prefix='Awl-production-bench-') as td:
   folder=Path(td);entry=folder/'main.aw';entry.write_text('use N0.aw as a; use N1.aw as b; func main()->i64 print(a.value()+b.value()); return 0; end;')
   values={}
   for i in reversed(range(32)):
    deps=[j for j in [i+2,i+3] if j<32];values[i]=sum(values[j] for j in deps) if deps else 1;uses=''.join(f'use N{j}.aw as n{j}; ' for j in deps);value='+'.join(f'n{j}.value()' for j in deps) or '1';(folder/f'N{i}.aw').write_text(uses+f'exports(@r func value()->i64 return {value}; end;);')
   measurements={}
   for command in ['check','emit-c','build']:
    samples=[]
    for sample in range(8):
     elapsed,_=run(candidate,command,entry,['--syntax','next'],folder/'graph' if command=='build' else None)
     if sample:samples.append(elapsed)
    measurements[command]={'samples_ms':samples,'median_ms':statistics.median(samples)}
   r=subprocess.run([str(folder/'graph')],env=env,capture_output=True,text=True,timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,str(values[0]+values[1])+'\n',''),r
   legacy=ROOT/'examples/apps/pixelboard/main.aw';_,old_c=run(baseline,'emit-c',legacy);_,new_c=run(candidate,'emit-c',legacy,['--syntax','legacy']);assert old_c==new_c,'legacy emitted C changed'
   series={'published0.23':[],'candidate0.24-legacy':[]};jobs=[]
   for label,binary,flags in [('published0.23',baseline,[]),('candidate0.24-legacy',candidate,['--syntax','legacy'])]:
    run(binary,'build',legacy,flags,folder/label);jobs.extend([(label,binary,flags)]*7)
   random.Random(20261106).shuffle(jobs)
   for label,binary,flags in jobs:series[label].append(run(binary,'build',legacy,flags,folder/label)[0])
   comparison={name:{'samples_ms':values,'median_ms':statistics.median(values)} for name,values in series.items()}
   report={'status':'passed','scope':__doc__+' End-to-end commands include process launch, source IO/import loading, native parser/checker/independent verifier; emit-c includes C generation; build includes shipped backend/static linking. One excluded warmup+7 samples per command; randomized legacy build comparison. Not a universal speedup or Windows result.','candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'next_unique_files':33,'next_graph':measurements,'next_program_stdout':r.stdout,'legacy_pixelboard_emitted_C_identical':True,'legacy_C_sha256':hashlib.sha256(new_c).hexdigest(),'legacy_full_build':comparison,'candidate_over_baseline_median':comparison['candidate0.24-legacy']['median_ms']/comparison['published0.23']['median_ms']};(ROOT/'benchmarks/next-production-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 finally:sdk.unlink()
if __name__=='__main__':main()

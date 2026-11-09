#!/usr/bin/env python3
import gzip,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HOME=ROOT.parent
CANDIDATE='8f8a5e49769197b8763d5ce2269262f9f6ab0814555c546d21db466a12ba0197'
RELEASE='3ae0337c85e535364bb774faa7ee1dffffc9187a39b77561038881d56d5f9971'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 reports={}
 for name,count in [('process-capture',103),('process-views',31),('process-default',62),('process-enums',187)]:
  p=ROOT/'tests'/(name+'.json');d=json.loads(p.read_text());assert d['status']=='PASS' and d['cases']==count and d['compiler_sha256']==CANDIDATE,(name,d);reports[p.name]=sha(p)
 capture=json.loads((ROOT/'tests/process-capture.json').read_text())
 for name,digest in capture['source_sha256'].items():assert sha(ROOT/name)==digest,name
 assert json.loads((ROOT/'tests/process-views.json').read_text())['oracle_output_lines_per_runtime']==981
 p=ROOT/'tests/process-native.json.gz';native=json.loads(gzip.decompress(p.read_bytes()));assert native['status']=='PASS' and len(native['phases'])==13 and all(x['exit']==0 and not x['stderr'] for x in native['phases']);assert native['phases'][-1]['stdout']=='PASS 7 independent process verifier cases\n'
 for name,digest in native['native_sources_sha256'].items():assert sha(ROOT/'compiler/native'/name)==digest,name
 reports[p.name]=sha(p)
 p=ROOT/'tests/process-faults.json';faults=json.loads(p.read_text());assert faults['status']=='PASS' and len(faults['records'])==4 and faults['fault_cases_per_mode']==24 and faults['repeated_captures_per_mode']==200;assert faults['source_sha256']==sha(ROOT/'tests/process_faults.c') and faults['runtime_sha256']==sha(ROOT/'compiler/native/kprocess.c');reports[p.name]=sha(p)
 p=ROOT/'tests/process-collections.json';collections=json.loads(p.read_text());assert collections['status']=='PASS' and collections['compiler_sha256']==CANDIDATE and collections['typed_cases']==56 and collections['operation_cases']==35;capsule=ROOT/'tests'/collections['full_reports_capsule'];assert sha(capsule)==collections['capsule_sha256'];raw=json.loads(gzip.decompress(capsule.read_bytes()));assert all(x['status']=='PASS' and x['compiler_sha256']==CANDIDATE for x in raw.values());reports[p.name]=sha(p);reports[capsule.name]=sha(capsule)
 for script in ['generate_generic.py','generate_process.py']:subprocess.run(['python3',str(ROOT/'compiler'/script),'--check'],check=True)
 assert sha(ROOT/'compiler/native/bin/kcc')==RELEASE
 protected={'Awl-0.24.0-dev-windows-x86_64-preview.tar.xz':'50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec'}
 for name,digest in protected.items():
  assert sha(HOME/name)==digest,name
 assert (ROOT/'apps/taskrun/vendor/Json.aw').read_bytes()==(ROOT/'examples/parsing/Json.aw').read_bytes();assert (ROOT/'apps/taskrun/File.aw').read_bytes()==(ROOT/'apps/logwindow/File.aw').read_bytes()
 sources={str(p.relative_to(ROOT)):sha(p) for base in ['apps/taskrun'] for p in sorted((ROOT/base).rglob('*')) if p.is_file()};sources.update({str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'tests/process_native.py',ROOT/'tests/process_capture.py',ROOT/'tests/process_child.c',ROOT/'tests/process_faults.c',ROOT/'docs/SUBPROCESSES.md',ROOT/'docs/CAPABILITY-ASSESSMENT.md']})
 files=[p for p in HOME.rglob('*') if p.is_file() and not p.is_symlink()];size=sum(p.stat().st_size for p in files);assert size<128000000 and len(files)<10000,(size,len(files))
 result={'status':'PASS','source_candidate_only':True,'candidate_compiler_sha256':CANDIDATE,'unchanged_published_compiler_sha256':RELEASE,'reports_sha256':reports,'source_sha256':sources,'protected_archives':protected,'native_sanitizer_phases':13,'capability_review':{'score':'26.7%=12/45','change':'systems1->2 only','basis':'executed useful bounded native process-supervision/build-test batches, not API syntax/tests/benchmark or SDK publication','limits':'Linux source candidate, trusted synchronous jobs/procfs/default SIGCHLD, no native Windows/async/sandbox/hostile-descendant containment/hard real-time guarantee'},'home_bytes_before_report':size,'home_files_before_report':len(files)}
 (ROOT/'tests/process-checkpoint.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS process source checkpoint,13 native sanitizer phases, published0.25 unchanged,',size,'bytes',len(files),'files')
if __name__=='__main__':main()

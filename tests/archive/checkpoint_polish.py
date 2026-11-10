#!/usr/bin/env python3
import gzip,hashlib,json,tarfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HOME=ROOT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 reports={};candidate=None
 for name in ['builder-growth.json','builder-growth-faults.json','polish-logwindow.json','polish-process.json']:
  p=ROOT/'tests'/name;d=json.loads(p.read_text());assert d['status']=='PASS';reports[name]=sha(p)
  if 'compiler_sha256'in d:
   if candidate is None:candidate=d['compiler_sha256']
   assert candidate==d['compiler_sha256']
 model=json.loads((ROOT/'tests/builder-growth.json').read_text());assert model['steps']==500 and model['oracle_lines_per_runtime']==2000;assert model['harness_sha256']==sha(ROOT/'tests/builder_growth.py')
 fault=json.loads((ROOT/'tests/builder-growth-faults.json').read_text());assert fault['source_sha256']==sha(ROOT/'tests/builder_growth_faults.c') and fault['runtime_sha256']==sha(ROOT/'compiler/native/builders.c')
 assert json.loads((ROOT/'tests/polish-logwindow.json').read_text())['cases']==108
 process=json.loads((ROOT/'tests/polish-process.json').read_text());assert process['cases']==103
 for path,digest in process['source_sha256'].items():assert sha(ROOT/path)==digest,path
 p=ROOT/'tests/polish-native.json.gz';native=json.loads(gzip.decompress(p.read_bytes()));assert native['status']=='PASS' and len(native['phases'])==15 and all(x['exit']==0 and not x['stderr'] for x in native['phases']);reports[p.name]=sha(p)
 for path,digest in native['native_sources_sha256'].items():assert sha(ROOT/'compiler/native'/path)==digest,path
 for name in ['builders','strings','generic','process']:subprocess.run(['python3',str(ROOT/'compiler'/('generate_'+name+'.py')),'--check'],check=True)
 with tarfile.open(ROOT/'history/rename-bundle-report.tar.xz') as t:
  index=json.load(t.extractfile('SHA256.json'))
  for path,entry in index.items():b=t.extractfile(path).read();assert len(b)==entry['bytes'] and hashlib.sha256(b).hexdigest()==entry['sha256']
 release='3ae0337c85e535364bb774faa7ee1dffffc9187a39b77561038881d56d5f9971';assert sha(ROOT/'compiler/native/bin/kcc')==release
 protected={'Awl-0.25.0-dev-linux-x86_64.tar.xz':'eda04f5701153315fa8db64e2aa09a17bf0c4e3c46753cd818e9026b14a045a5','Awl-0.24.0-dev-windows-x86_64-preview.tar.xz':'50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec'}
 for path,digest in protected.items():assert sha(HOME/path)==digest
 sources={p:sha(ROOT/p) for p in ['apps/logwindow/main.aw','tests/logwindow.py','tests/builder_growth.py','tests/builder_growth_faults.c','tests/process.capture.py','tests/process_faults.c','tests/polish_native.py','docs/BUILDER-GROWTH.md']}
 files=[p for p in HOME.rglob('*') if p.is_file() and not p.is_symlink()];size=sum(p.stat().st_size for p in files);assert size<128000000 and len(files)<10000
 out={'status':'PASS','source_candidate_only':True,'candidate_compiler_sha256':candidate,'unchanged_published_compiler_sha256':release,'reports_sha256':reports,'source_sha256':sources,'native_sanitizer_phases':15,'capability':'26.7%=12/45 unchanged, no new workload stage','limits':'not new SDK/native Windows/editor/full564x3 legacy qualification, truncate scans retained prefix, no reclaimable immutable strings/concurrency','protected_archives':protected,'home_bytes_before_report':size,'home_files_before_report':len(files)}
 (ROOT/'tests/polish-checkpoint.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('PASS polish source checkpoint',size,'bytes',len(files),'files')
if __name__=='__main__':main()

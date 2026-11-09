#!/usr/bin/env python3
import gzip,hashlib,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HOME=ROOT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 provenance=json.loads((ROOT/'tests/package-import-provenance.json').read_text());assert provenance['inbound_files']==220
 archive=provenance['received_archive'];assert sha(HOME/archive['new_archive'])==archive['sha256'];assert archive['old_archive_retired_after_exact_acceptance']
 assert not(HOME/'Awl-0.25.0-dev-linux-x86_64.tar.xz').exists()
 assert sha(HOME/'Awl-0.24.0-dev-windows-x86_64-preview.tar.xz')=='50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec'
 assert sha(HOME/'Awl-board-0.1-linux-x86_64.tar.xz')=='549d949b121ac9e776a499bb27a8c6ec32c07b6df3024e76f247c4be9068e008'
 assert sha(ROOT/'compiler/native/bin/kcc')=='3ae0337c85e535364bb774faa7ee1dffffc9187a39b77561038881d56d5f9971'
 with tarfile.open(ROOT/'history/pre-package-import.tar.xz')as tar:
  index=json.load(tar.extractfile('SHA256.json'))
  for name,entry in index.items():data=tar.extractfile(name).read();assert len(data)==entry['bytes']and hashlib.sha256(data).hexdigest()==entry['sha256'],name
 assert sha(ROOT/'history/pre-package-import.tar.xz')==provenance['history_capsule_sha256']
 reports={};compiler=None
 for name in ['spool','logwindow','process','features','diagnostics','local','maps','editor','entries','faults']:
  p=ROOT/'tests'/('package-import-'+name+'.json');d=json.loads(p.read_text());assert d['status']in['PASS','passed'];reports[str(p.relative_to(ROOT))]=sha(p)
  if 'compiler_sha256'in d:
   if compiler is None:compiler=d['compiler_sha256']
   assert compiler==d['compiler_sha256'],name
  for key in ['source_sha256','sources_sha256']:
   if key in d:
    for path,digest in d[key].items():assert sha(ROOT/path)==digest,path
  if name=='features':
   assert len(d['cases'])==8
   for case in d['cases']:
    for path,digest in case['sources_sha256'].items():assert sha(ROOT/path)==digest,path
  if name=='entries':
   assert len(d['entries'])==27
   for entry in d['entries']:assert sha(ROOT/entry['path'])==entry['sha256']
  if name=='spool':assert d['steps']==500 and d['oracle_lines_per_runtime']==2000 and d['harness_sha256']==sha(ROOT/'tests/spool_growth.py')
  if name=='logwindow':assert d['cases']==108
  if name=='process':assert d['cases']==103
  if name=='local':assert len(d['records'])==14 and d['harness_sha256']==sha(ROOT/'tests/local_packages.py')
  if name=='editor':assert d['html_sha256']==sha(ROOT/'editor/awl-editor.html')
 for name in ['env','json','fsp']:assert(ROOT/'packages'/name/(name+'.aw')).read_bytes()==(ROOT/'examples/packages-demo/packages'/name/(name+'.aw')).read_bytes()
 p=ROOT/'tests/package-import-native.json.gz';native=json.loads(gzip.decompress(p.read_bytes()));assert native['status']=='PASS'and len(native['phases'])==15 and all(x['exit']==0 and not x['stderr']for x in native['phases'])
 for name,digest in native['native_sources_sha256'].items():assert sha(ROOT/'compiler/native'/name)==digest,name
 reports[str(p.relative_to(ROOT))]=sha(p)
 isolated=json.loads(gzip.decompress((ROOT/'tests/package-import-archive.json.gz').read_bytes()));assert isolated['status']=='passed' and len(isolated['commands'])==50 and isolated['tested_archive']['sha256']==archive['sha256']
 for name in ['builders','strings','generic','process','maps']:subprocess.run(['python3',str(ROOT/'compiler'/('generate_'+name+'.py')),'--check'],check=True)
 ledger_path=ROOT/'tests/package-import-files.json.gz';ledger=json.loads(gzip.decompress(ledger_path.read_bytes()))
 for item in ledger:assert sha(ROOT/item['path'])==item['merged_sha256'],item['path']
 extra=['tests/checkpoint_package_import.py','tests/package_import_native.py','tests/local_packages.py','tests/map_model.py','tests/map_runtime_model.c','tests/spool_growth.py','tests/spool_growth_faults.c','docs/PACKAGES.md','docs/BUILDER-GROWTH.md']
 out={'status':'PASS','source_candidate_only':True,'candidate_compiler_sha256':compiler,'provenance_sha256':sha(ROOT/'tests/package-import-provenance.json'),'merge_ledger_sha256':sha(ledger_path),'reports_sha256':reports,'extra_sources_sha256':{p:sha(ROOT/p)for p in extra},'received_archive':archive,'native_sanitizer_phases':15,'score':'26.7%=12/45 unchanged','limits':'received SDK predates merged source, db/time/websocket/fetch not implemented, no server add/install, broader manifest/ownership/iteration/concurrency hardening and full source-current SDK/native Windows qualification pending, editor is a limited JS subset'}
 path=ROOT/'tests/package-import-checkpoint.json';path.write_text(json.dumps(out,separators=(',',':'))+'\n')
 for _ in range(3):
  files=[p for p in HOME.rglob('*')if p.is_file()and not p.is_symlink()];size=sum(p.stat().st_size for p in files);assert size<128000000 and len(files)<10000,(size,len(files));out['home']={'bytes':size,'regular_files':len(files)};path.write_text(json.dumps(out,separators=(',',':'))+'\n')
 print('PASS merged Package checkpoint',out['home'])
if __name__=='__main__':main()

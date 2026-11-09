#!/usr/bin/env python3
import gzip,hashlib,json,lzma,os,re,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HOME=ROOT.parent
ALIASES=['awl','awL','aWl','aWL','Awl','AwL','AWl','AWL']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while data:=f.read(1048576):h.update(data)
 return h.hexdigest()
def load(name):
 p=ROOT/name;raw=p.read_bytes();return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)
def main():
 binary=ROOT/'compiler/native/bin/kcc';digest=sha(binary);info=load('compiler/native/bin/build-info.json');assert digest==info['standalone']['sha256']==info['toolkit']['sha256'];assert sha(binary.parent/'Awllex.so')==info['library_sha256'];assert info['toolkit']['file']=='awl' and os.access(binary,os.X_OK)
 for name,value in info['frontend_sources_sha256'].items():assert sha(ROOT/'compiler/native'/name)==value,name
 for alias in ALIASES:assert (binary.parent/alias).is_symlink() and os.readlink(binary.parent/alias)=='kcc',alias
 for script in ['generate_generic.py','generate_vectors.py','generate_files.py']:subprocess.run([sys.executable,str(ROOT/'compiler'/script),'--check'],check=True,capture_output=True)
 reports=['tests/rename-publication.json','tests/rename-cli.json','tests/rename-ASDK.json','tests/rename-vector-ops.json','tests/rename-vector-wasm.json','tests/rename-wasm-build.json','tests/rename-wasm.json','tests/rename-editor.json','tests/rename-linux-resources.json','tests/rename-windows-resources.json','tests/rename-linux-package.json','tests/rename-windows-package.json','tests/rename-windows-integrity.json','tests/rename-bundle-archive.json','tests/slots-native.json.gz','tests/slots-regressions.json.gz','tests/slots-legacy.json']
 harnesses={'rename-cli.json':'tests/rename.py','rename-vector-ops.json':'tests/vector_ops.py','rename-vector-wasm.json':'tests/slots_wasm.py','rename-wasm.json':'tests/wasm.py','rename-editor.json':'tests/editor.py'}
 for name in reports:
  r=load(name)
  if name.endswith('slots-legacy.json'):continue
  assert r.get('status') in ['PASS','passed','archive integrity passed; NOT Windows runtime acceptance'],name
  if 'compiler_sha256' in r and r.get('platform')!='windows':assert r['compiler_sha256']==digest,name
  if 'binary_sha256' in r:assert r['binary_sha256']==digest,name
  key=Path(name).name
  if key in harnesses:assert r['harness_sha256']==sha(ROOT/harnesses[key]),name
 assert load('tests/rename-cli.json')['cases']==45 and load('tests/rename-ASDK.json')['cases']==62
 r=load('tests/rename-vector-ops.json');assert r['cases']==35 and r['runtime_test_sha256']==sha(ROOT/'tests/vector_slots.c')
 assert load('tests/rename-vector-wasm.json')['cases']==12
 r=load('tests/slots-native.json.gz');assert len(r['phases'])==11 and all(x['exit']==0 and not x['stderr'] for x in r['phases'])
 expected={p.name:sha(p) for p in sorted((ROOT/'compiler/native').iterdir()) if p.suffix in ['.h','.cpp','.inc','.c']};assert r['native_sources_sha256']==expected
 r=load('tests/slots-regressions.json.gz');assert len(r['records'])==12
 for name,r in load('tests/slots-legacy.json').items():assert r['exit']==0 and r['tests']==564 and not r['skips'] and r['compiler_sha256']==digest,name
 logs=json.loads(lzma.decompress((ROOT/'tests/slots-legacy-logs.json.xz').read_bytes()));assert set(logs)=={'reference','native-parser','native-frontend'}
 for text in logs.values():assert 'Ran 564 tests' in text and '\nOK\n' in text and 'skipped=' not in text
 r=load('tests/rename-wasm.json');counts=r['records'];assert [counts[k] for k in ['native_json_oracle_cases','node_wasm_equivalence_cases','chromium_worker_ui_cases']]==[437]*3 and counts['wasm_i64_enum_oracle_cases']==444 and counts['host_rejection_cases']==8;assert all(counts[k]==1 for k in ['cancellation_cases','worker_timeout_fault_cases','opaque_sandbox_iframe_cases']);assert r['html_sha256']==sha(ROOT/'web/Awl-json-workbench.html')
 build=load('tests/rename-wasm-build.json');assert build['wasm_sha256']==r['wasm_sha256'] and build['html_sha256']==r['html_sha256'];assert build['entry_sha256']==sha(ROOT/'examples/parsing/web.aw') and build['parser_sha256']==sha(ROOT/'examples/parsing/Json.aw') and build['runtime_sha256']==sha(ROOT/'web/wasi.js') and build['template_sha256']==sha(ROOT/'web/workbench.template.html') and build['builder_sha256']==sha(ROOT/'web/build.py')
 r=load('tests/rename-editor.json');assert r['source_files']==69 and len(r['records'])==9 and r['html_sha256']==sha(ROOT/'editor/Awl-studio.html') and r['runtime_sha256']==sha(ROOT/'editor/runtime.js') and r['image_sha256']==sha(ROOT/'editor/Awl-studio.png') and r['external_requests']==[]
 files={str(p.relative_to(ROOT)):p.read_text() for folder in ['examples','examples'] for p in sorted((ROOT/folder).rglob('*.aw'))};assert len(files)==69
 html=(ROOT/'editor/shell.html').read_text().replace('__SOURCES__',json.dumps(files,ensure_ascii=True).replace('<','\\u003c')).replace('__RUNTIME__',json.dumps((ROOT/'editor/runtime.js').read_text()).replace('<','\\u003c'));assert html==(ROOT/'editor/Awl-studio.html').read_text()
 for folder,image in [('demos/rename','Awl-sdk.png'),('demos/wasm','browser-workbench.png')]:
  r=load(folder+'/capture.json');assert r['image_sha256']==sha(ROOT/folder/image)
  if folder=='demos/rename':assert r['compiler_sha256']==digest and r['transcript_sha256']==sha(ROOT/folder/'transcript.txt') and r['harness_sha256']==sha(ROOT/folder/'capture.py')
  else:assert r['html_sha256']==sha(ROOT/'web/Awl-json-workbench.html') and not r['external_requests']
 history=ROOT/'history/pre-rename-evidence.tar.xz'
 with tarfile.open(history) as t:
  index=json.load(t.extractfile('evidence-index.json'));assert len(index)==1398
  for name,entry in index.items():
   h=hashlib.sha256();size=0
   with t.extractfile(name) as f:
    while data:=f.read(1048576):h.update(data);size+=len(data)
   assert h.hexdigest()==entry['sha256'] and size==entry['bytes'],name
 artifacts={}
 for platform in ['linux','windows']:
  name='Awl-0.24.0-dev-'+platform+'-x86_64'+('-preview' if platform=='windows' else '')+'.tar.xz';archive=HOME/name;r=load('tests/rename-'+platform+'-package.json');assert r['harness_sha256']==sha(ROOT/'compiler/package_sdk.py');assert sha(archive)==r['archive_sha256'] and archive.stat().st_size==r['archive_bytes'];assert archive.with_suffix('.xz.sha256').read_text()==r['archive_sha256']+'  '+name+'\n'
  with tarfile.open(archive) as t:
   manifest_raw=t.extractfile('Awl/manifest.json').read();assert hashlib.sha256(manifest_raw).hexdigest()==r['manifest_sha256'];manifest=json.loads(manifest_raw);assert manifest['brand']=='Awl' and manifest['source_extension']=='.aw' and manifest['project_extension']=='.awproj' and manifest['toolkit']['command']=='bin/awl'+('.exe' if platform=='windows' else '');assert manifest['windows_native_host_accepted'] is False
   inventory_raw=t.extractfile('Awl/files.json').read();assert hashlib.sha256(inventory_raw).hexdigest()==r['inventory_sha256'];inventory=json.loads(inventory_raw)
   for path,entry in inventory.items():
    member=t.getmember('Awl/'+path)
    if 'symlink' in entry:assert member.issym() and member.linkname==entry['symlink']
    else:
     h=hashlib.sha256()
     with t.extractfile(member) as f:
      while data:=f.read(1048576):h.update(data)
     assert member.size==entry['bytes'] and h.hexdigest()==entry['sha256'],path
   for path,value in manifest['compiler_sources_sha256'].items():assert sha(ROOT/'compiler/native'/path)==value,path
   assert manifest['upstream_files_verified']==18105
   if platform=='linux':assert manifest['kcc_sha256']==digest and build['backend_sha256']==manifest['zig_sha256']
  artifacts[name]={'sha256':r['archive_sha256'],'bytes':r['archive_bytes'],'upstream_files_verified':18105}
 linux=load('tests/rename-bundle-archive.json');assert linux['harness_sha256']==sha(ROOT/'tests/bundle_isolation.py');assert linux['tested_archive']['sha256']==artifacts['Awl-0.24.0-dev-linux-x86_64.tar.xz']['sha256'] and linux['status']=='passed' and not linux['host_development_tools_in_rootfs'] and not linux['python_or_shell_in_rootfs'] and not linux['generated_executable_has_ELF_interpreter']
 win=load('tests/rename-windows-integrity.json');assert win['sha256']==artifacts['Awl-0.24.0-dev-windows-x86_64-preview.tar.xz']['sha256'] and not win['real_windows_execution'] and not win['installed_backend_acceptance']
 # Spell the retired audit signature as bytes so the checker does not match itself
 retired=bytes.fromhex('6b65726e').decode();pattern=re.compile(retired+r'(?!el|ighan)',re.I);hits=[]
 for path in HOME.rglob('*'):
  if path.is_symlink() or not path.is_file() or 'history' in path.relative_to(HOME).parts or 'third-party' in path.relative_to(HOME).parts:continue
  assert path.suffix not in ['.'+retired[0],'.'+retired],path
  try:text=path.read_text()
  except (UnicodeError,OSError):continue
  if pattern.search(path.name) or pattern.search(text):hits.append(str(path.relative_to(HOME)))
 assert not hits,hits
 assert not (ROOT/'build').exists() and not (ROOT/'.cache').exists(),'remove owned scratch links after acceptance'
 checkpoint={'status':'PASS','brand':'Awl','toolkit':'Awl Software Development Kit [Beta]','command':'awl','source_extension':'.aw','project_extension':'.awproj','compiler_sha256':digest,'score':'22.2% (10/45), unchanged','windows_native_host_accepted':False,'reports':{n:sha(ROOT/n) for n in reports},'artifacts':artifacts,'sources':expected,'harness_sha256':sha(Path(__file__)),'history':{'sha256':sha(history),'original_files_verified':1398},'capture_files_opened':['demos/rename/Awl-sdk.png','editor/Awl-studio.png','demos/wasm/browser-workbench.png'],'limits':'Linux x86-64 exact-archive evidence only, Windows preview integrity/cross-build is not native-host acceptance, limited general JS editor, historical performance is not a new benchmark'}
 (ROOT/'tests/rename-checkpoint.json').write_text(json.dumps(checkpoint,separators=(',',':'))+'\n')
 audit=ROOT/'tests/rename-home-audit.json'
 for _ in range(3):
  regular=[p for p in HOME.rglob('*') if p.is_file() and not p.is_symlink()];links=[p for p in HOME.rglob('*') if p.is_symlink()];size=sum(p.stat().st_size for p in regular);assert size<128000000 and len(regular)+len(links)<10000,(size,len(regular),len(links));audit.write_text(json.dumps({'status':'PASS','root':str(HOME),'bytes':size,'regular_files':len(regular),'symlinks':len(links),'file_limit':10000,'byte_limit':128000000,'external_sdk_cache_build_links':False,'checkpoint_sha256':sha(ROOT/'tests/rename-checkpoint.json')},separators=(',',':'))+'\n')
 print('PASS Awl source/artifact/SDK/browser/history checkpoint,',size,'bytes,',len(regular),'regular files,',len(links),'symlinks')
if __name__=='__main__':main()

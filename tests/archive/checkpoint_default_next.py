#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 def load(name):return json.loads((ROOT/'tests'/name).read_text())
 package=load('default-linux-package.json');accept=load('default-bundle-archive.json');publish=load('default-publication.json');cases=load('default-next.json');enums=load('default-exported-enums.json');wasm=load('default-exported-wasm.json');compiler=sha(ROOT/'compiler/native/bin/kcc')
 assert all(x['status']=='PASS' for x in [package,publish,cases,enums,wasm]) and accept['status']=='passed'
 assert compiler==package['compiler_sha256']==cases['compiler_sha256']==enums['compiler_sha256']==wasm['compiler_sha256']
 assert cases['cases']==62 and enums['cases']==187 and wasm['native_cases']==wasm['wasm_cases']==107
 assert len(accept['commands'])==112 and accept['integer_matrix_checks']==348 and accept['trap_cases']==5
 assert accept['manifest']['default_syntax']=='next' and accept['manifest']['legacy_requires_explicit_syntax'] is True and accept['manifest']['version']=='0.25.0-dev'
 assert accept['host_development_tools_in_rootfs'] is False and accept['python_or_shell_in_rootfs'] is False
 assert package['complete_unmodified_upstream_files_verified']==18105
 archive=ROOT.parent/publish['new_archive'];digest=sha(archive);assert digest==package['archive_sha256']==accept['tested_archive']['sha256']==publish['sha256']
 assert archive.with_name(archive.name+'.sha256').read_text().split()[0]==digest
 assert publish['replacement_exact_archive_accepted_before_retirement'] and not (ROOT.parent/publish['retired_archive']).exists()
 assert sha(ROOT.parent/'Awl-0.24.0-dev-windows-x86_64-preview.tar.xz')=='50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec'
 assert sha(ROOT.parent/'Awl-board-0.1-linux-x86_64.tar.xz')==load('board-package.json')['archive_sha256']
 for name,digest in json.loads((ROOT/'compiler/native/bin/build-info.json').read_text())['frontend_sources_sha256'].items():assert sha(ROOT/'compiler/native'/name)==digest,name
 for name,digest in enums['source_sha256'].items():assert sha(ROOT/name)==digest,name
 assert 'bool json=false,next=true;' in (ROOT/'compiler/native/acc.cpp').read_text()
 reports=[ROOT/'tests'/n for n in ['default-linux-package.json','default-bundle-archive.json','default-publication.json','default-next.json','default-exported-enums.json','default-exported-wasm.json']]
 sources=[p for p in (ROOT/'compiler/native').iterdir() if p.suffix in ['.cpp','.h','.inc','.c']]+[ROOT/'compiler/package_sdk.py',ROOT/'compiler/native/bin/build-info.json',ROOT/'tests/default_next.py',ROOT/'tests/default_bundle_isolation.py',Path(__file__).resolve(),ROOT/'RELEASE-0.25.md']
 paths=[p for p in ROOT.parent.rglob('*') if p.is_file() and not p.is_symlink()];size=sum(p.stat().st_size for p in paths);assert size<128000000 and len(paths)<10000,(size,len(paths))
 result={'status':'PASS','compiler_sha256':compiler,'archive':{'name':archive.name,'sha256':sha(archive),'bytes':archive.stat().st_size},'source_and_evidence_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(set(reports+sources))},'capability':{'points':11,'maximum':45,'percentage':24.4,'change':'none, syntax default and language feature delivery are not another workload stage'},'home_at_check':{'bytes':size,'regular_files':len(paths)},'qualification':'complete Linux0.25 SDK, next default and explicit legacy/native API compatibility, current exported enums included, exact offline unprivileged archive acceptance, older Windows preview unchanged and unaccepted, no new public run/install commands'}
 (ROOT/'tests/default-checkpoint.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS default-next checkpoint',size,len(paths))
if __name__=='__main__':main()

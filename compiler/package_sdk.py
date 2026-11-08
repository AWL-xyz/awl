#!/usr/bin/env python3
"""Prepare a complete SDK from rebuilt host binaries and checksum-pinned upstream resources"""
import argparse,hashlib,json,os,shutil,tarfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.25.0-dev'
ALIASES=['awl','awL','aWl','aWL','Awl','AwL','AWl','AWL']
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while data:=f.read(1048576):h.update(data)
 return h.hexdigest()
def verify_resources(stage,upstream,lock):
 assert upstream.stat().st_size==lock['bytes'] and sha(upstream)==lock['sha256'],'upstream checksum mismatch'
 expected=set();base=stage/'libexec/zig'
 if upstream.suffix=='.zip':
  with zipfile.ZipFile(upstream) as z:
   for item in z.infolist():
    if item.is_dir():continue
    relative=item.filename.split('/',1)[1];target=base/relative;expected.add(relative);h=hashlib.sha256()
    with z.open(item) as f:
     while data:=f.read(1048576):h.update(data)
    assert target.is_file() and sha(target)==h.hexdigest(),relative
 else:
  with tarfile.open(upstream) as t:
   for item in t:
    if not (item.isfile() or item.issym()):continue
    relative=item.name.split('/',1)[1];target=base/relative;expected.add(relative)
    if item.issym():assert target.is_symlink() and os.readlink(target)==item.linkname,relative
    else:
     h=hashlib.sha256()
     with t.extractfile(item) as f:
      while data:=f.read(1048576):h.update(data)
     assert target.is_file() and sha(target)==h.hexdigest(),relative
 actual={str(p.relative_to(base)) for p in base.rglob('*') if p.is_file() or p.is_symlink()};assert actual==expected,actual^expected
 return len(expected)
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--platform',choices=['linux','windows'],required=True);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--report',type=Path,required=True);a=p.parse_args();stage=a.stage.resolve();windows=a.platform=='windows';lock=json.loads((ROOT/'compiler'/('toolchain-windows-lock.json' if windows else 'toolchain-lock.json')).read_text());count=verify_resources(stage,a.upstream,lock)
 # Keep only rebuilt host binaries and the fully verified, untouched upstream tree
 for child in list(stage.iterdir()):
  if child.name in ['bin','libexec']:continue
  if child.is_dir():shutil.rmtree(child)
  else:child.unlink()
 binary=stage/'bin'/('kcc.exe' if windows else 'kcc');assert binary.is_file();exe_sha=sha(binary)
 for child in list((stage/'bin').iterdir()):
  if child.name!=binary.name:child.unlink()
 if windows:shutil.copy2(binary,stage/'bin/awl.exe')
 else:
  binary.chmod(0o755)
  for name in ALIASES:(stage/'bin'/name).symlink_to('kcc')
 for name in ['examples','examples-next','docs','third-party','assets','apps']:shutil.copytree(ROOT/name,stage/name)
 shutil.copy2(ROOT/'LICENSE',stage/'LICENSE');shutil.copy2(ROOT/'docs/ROADMAP.md',stage/'ROADMAP.md')
 shutil.copytree(ROOT/'compiler/native',stage/'src',ignore=shutil.ignore_patterns('bin','__pycache__'))
 shutil.copytree(ROOT/'compiler',stage/'compiler',ignore=shutil.ignore_patterns('bin','__pycache__'))
 (stage/'editor').mkdir();shutil.copy2(ROOT/'editor/Awl-studio.html',stage/'editor/Awl-studio.html');shutil.copytree(ROOT/'web',stage/'web')
 (stage/'validation').mkdir()
 for name in ['rename-cli.json','rename-ASDK.json','rename-vector-ops.json','rename-vector-wasm.json','rename-wasm-build.json','rename-wasm.json','rename-editor.json']:
  shutil.copy2(ROOT/'tests'/name,stage/'validation'/name)
 for name in ['default-next.json','default-exported-enums.json','default-exported-wasm.json']:
  if (ROOT/'tests'/name).is_file():shutil.copy2(ROOT/'tests'/name,stage/'validation'/name)
 for name in ['slots-native.json.gz','slots-regressions.json.gz','slots-legacy.json','slots-legacy-logs.json.xz']:
  if (ROOT/'tests'/name).is_file():shutil.copy2(ROOT/'tests'/name,stage/'validation'/name)
 (stage/'validation/README.md').write_text('historical rename-* reports bind the previous0.24 compiler, not the current binary, current exact-archive acceptance is external to avoid self-hashing\n')
 command='bin/awl.exe' if windows else 'bin/awl'
 (stage/'README.md').write_text('# Awl Software Development Kit [Beta]\n\n'+VERSION+'\n\n'+('Windows x86-64 preview, cross-built and resource-verified, NOT native Windows-host accepted\n\n' if windows else 'Linux x86-64 experimental standalone SDK, exact published archive acceptance is recorded separately\n\n')+'extract the entire Awl directory and add its bin directory to PATH, keep libexec adjacent to bin\n\n```sh\nawl\nawl init Demo\nawl build\nawl build examples-next/collections/main.aw -o collections\n```\n\nno end-user Python, host compiler, SDK or additional backend download is needed, contributor tools under compiler are optional source utilities\n\nsources use .aw, manifests use .awproj, command names and init/build verbs accept mixed case, project names and import paths stay case-sensitive\n\nnext syntax is the default for awl and kcc commands, use --syntax legacy for old sources, exported enums are supported\n\npublic beta commands remain init/build only, kcc is internal compiler tooling, run/install/Packages/registry are not public beta commands\n\neditor/Awl-studio.html is a single-file offline JavaScript subset editor, not the native compiler, web/Awl-json-workbench.html runs freshly compiled WebAssembly with a bounded browser host\n\nsee docs for syntax, runtime limits and workload assessment, native Windows acceptance is deferred, no full 3D, general widgets, concurrency, TLS/auth or arbitrary owned generics are claimed\n')
 sources={f.name:sha(f) for f in sorted((stage/'src').iterdir()) if f.is_file()}
 manifest={'version':VERSION,'brand':'Awl','toolkit':{'name':'Awl Software Development Kit [Beta]','command':command,'commands':['init','build'],'command_case':'ASCII case-insensitive; project names and source paths are not folded'},'host':'x86_64-windows' if windows else 'x86_64-linux','status':'cross-built unaccepted Windows preview' if windows else 'experimental Linux SDK, separately qualify the exact distribution archive','toolchain':lock,'kcc_sha256':exe_sha,'zig_sha256':sha(stage/'libexec/zig'/('zig.exe' if windows else 'zig')),'compiler_sources_sha256':sources,'source_extension':'.aw','project_extension':'.awproj','default_syntax':'next','legacy_requires_explicit_syntax':True,'windows_native_host_accepted':False,'upstream_files_verified':count,'resources':'complete unmodified checksum-pinned upstream distribution, source, libc, linker, headers, startup resources and licenses retained','compiler_build':json.loads((ROOT/'compiler/native/bin/build-info.json').read_text())['standalone'] if not windows else {'driver':'bundled Linux Zig c++ cross-compiler','flags':['-std=c++20','-target','x86_64-windows-gnu','-mcpu=baseline','-O2','-g0','-s','-Wall','-Wextra','-Werror','-municode'],'libraries':['bcrypt','advapi32']}}
 (stage/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
 inventory={str(f.relative_to(stage)):({'symlink':os.readlink(f)} if f.is_symlink() else {'sha256':sha(f),'bytes':f.stat().st_size}) for f in sorted(stage.rglob('*')) if f.is_file() or f.is_symlink()};(stage/'files.json').write_text(json.dumps(inventory,separators=(',',':'))+'\n')
 result={'status':'PASS','platform':a.platform,'compiler_sha256':exe_sha,'manifest_sha256':sha(stage/'manifest.json'),'inventory_sha256':sha(stage/'files.json'),'upstream_sha256':lock['sha256'],'complete_unmodified_upstream_files_verified':count,'native_windows_execution':False,'harness_sha256':sha(Path(__file__))}
 if a.output:
  a.output.parent.mkdir(parents=True,exist_ok=True)
  def normalized(info):info.uid=info.gid=0;info.uname=info.gname='';info.mtime=1794009600;return info
  with tarfile.open(a.output,'w:xz',preset=6) as t:t.add(stage,arcname='Awl',filter=normalized)
  with tarfile.open(a.output) as t:
   members=t.getmembers();assert all(m.name=='Awl' or m.name.startswith('Awl/') for m in members)
   for name,entry in inventory.items():
    member=t.getmember('Awl/'+name)
    if 'symlink' in entry:assert member.issym() and member.linkname==entry['symlink']
    else:
     h=hashlib.sha256()
     with t.extractfile(member) as f:
      while data:=f.read(1048576):h.update(data)
     assert member.size==entry['bytes'] and h.hexdigest()==entry['sha256'],name
  result.update(archive_sha256=sha(a.output),archive_bytes=a.output.stat().st_size,archive_members=len(members))
  a.output.with_suffix(a.output.suffix+'.sha256').write_text(result['archive_sha256']+'  '+a.output.name+'\n')
 a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps(result))
if __name__=='__main__':main()

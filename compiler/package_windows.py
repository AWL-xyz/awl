#!/usr/bin/env python3
"""Contributor builder for a complete native Windows x86-64 engineering preview.
Can cross-build on Linux with the staged Linux bundle; end users need no Python.
Real-Windows execution acceptance is separate from producing this archive.
"""
import argparse,hashlib,json,os,platform,shutil,subprocess,tarfile,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--download-toolchain',action='store_true');p.add_argument('--no-archive',action='store_true');p.add_argument('--archive-output',type=Path);a=p.parse_args()
 if platform.machine().lower() not in ['x86_64','amd64']:p.error('x86-64 contributor host required')
 lock=json.loads((ROOT/'compiler/toolchain-windows-lock.json').read_text());archive=ROOT/'build/zig-windows.zip';archive.parent.mkdir(exist_ok=True)
 if not archive.exists():
  if not a.download_toolchain:p.error('pass --download-toolchain for explicit checksum-pinned contributor download')
  part=archive.with_suffix('.part')
  with urllib.request.urlopen(lock['url'],timeout=90) as r,part.open('wb') as f:shutil.copyfileobj(r,f)
  if digest(part)!=lock['sha256'] or part.stat().st_size!=lock['bytes']:part.unlink();raise RuntimeError('upstream Windows toolchain integrity failure')
  part.replace(archive)
 if digest(archive)!=lock['sha256'] or archive.stat().st_size!=lock['bytes']:raise RuntimeError('cached Windows toolchain integrity failure')
 package=ROOT/'build/Awl-windows-x86_64';tool=package/'libexec/zig'
 if not tool.exists():
  temporary=ROOT/'build/windows-upstream'
  with zipfile.ZipFile(archive) as z:z.extractall(temporary)
  tool.parent.mkdir(parents=True,exist_ok=True);(temporary/'zig-x86_64-windows-0.15.2').rename(tool)
 zig=tool/'zig.exe' if os.name=='nt' else ROOT/'build/Awl-linux-x86_64/libexec/zig/zig'
 if not zig.is_file():p.error('Linux contributor cross-build requires the staged complete Linux toolchain')
 (package/'bin').mkdir(exist_ok=True);native=ROOT/'compiler/native'
 flags=['-std=c++20','-target',lock['target'],'-mcpu=baseline','-O2','-g0','-s','-Wall','-Wextra','-Werror','-municode']
 kwargs={}
 if os.name!='nt':
  def affinity():os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
  kwargs['preexec_fn']=affinity
 subprocess.run([str(zig),'c++',*flags,*[str(native/n) for n in ['klex.cpp','kparse.cpp','kcc.cpp','kbuild.cpp']],'-lbcrypt','-ladvapi32','-o',str(package/'bin/kcc.exe')],check=True,timeout=360,**kwargs)
 shutil.copy2(package/'bin/kcc.exe',package/'bin/awl.exe')
 shutil.copy2(ROOT/'docs/ASDK.md',package/'ASDK.md')
 shutil.copy2(ROOT/'docs/STREAMS.md',package/'STREAMS.md')
 shutil.copy2(ROOT/'docs/NETWORK.md',package/'NETWORK.md')
 shutil.copy2(ROOT/'docs/TYPED-VECTORS.md',package/'TYPED-VECTORS.md')
 for name in ['examples','examples-next','third-party']:shutil.copytree(ROOT/name,package/name,dirs_exist_ok=True)
 src=package/'src';src.mkdir(exist_ok=True)
 for f in native.iterdir():
  if f.suffix in ['.cpp','.h','.inc','.c']:shutil.copy2(f,src/f.name)
 shutil.copy2(ROOT/'LICENSE',package/'LICENSE');shutil.copy2(ROOT/'docs/WINDOWS.md',package/'README.md')
 for name in ['MATH.md','MODULE-STATE.md','NEXT-LANGUAGE.md','INT-VECTORS.md','ROADMAP.md','WIN32-GUI.md','FILES.md','CAPABILITY-ASSESSMENT.md','PIXELBOARD-FILES.md']:shutil.copy2(ROOT/'docs'/name,package/name)
 validation=package/'validation'
 if validation.exists():shutil.rmtree(validation)
 validation.mkdir()
 for f in [*(ROOT/'tests').glob('windows-*'),*(ROOT/'tests').glob('win32-*'),*(ROOT/'tests').glob('files-*'),*(ROOT/'tests').glob('persistence-*')]:
  if f.is_file() and not f.name.startswith(('windows-exact-','windows-preview-','persistence-linux-exact','persistence-windows-exact','persistence-release-acceptance','persistence-parent-audit','persistence-linux-extracted')):shutil.copy2(f,validation/f.name)
 for bench in [ROOT/'benchmarks'/n for n in ['files-latest.json','persistence-latest.json','persistence-build-latest.json']]:
  if bench.is_file():shutil.copy2(bench,validation/bench.name)
 manifest={'toolkit':{'name':'Awl Software Development Kit [Beta]','command':'bin/awl.exe','commands':['init','build']},'version':'0.24.0-dev','status':'experimental next-syntax development candidate; public SDK defaults next, internal kcc defaults legacy; real-Windows end-to-end acceptance pending','host':'x86_64-windows','toolchain':lock,'compiler_build_flags':flags,'compiler_link_libraries':['bcrypt','advapi32'],'program_link_libraries':['user32','gdi32','shell32'],'kcc_sha256':digest(package/'bin/kcc.exe'),'zig_sha256':digest(tool/'zig.exe'),'compiler_sources_sha256':{f.name:digest(f) for f in sorted(src.iterdir())},'resources':'Complete unmodified upstream Windows Zig distribution, libc/linker/headers/resources/licenses retained. No host compiler/SDK/Python/download needed by installed kcc.','execution_evidence':'See validation; Wine is not real Windows. Current Wine10 fails in upstream Zig self-executable-path resolution; check/emit and separate driver fixtures do not substitute for actual backend acceptance.'}
 (package/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(package,flush=True)
 if not a.no_archive:
  output=a.archive_output or ROOT/'build/Awl-0.24.0-dev-windows-x86_64-preview.tar.xz'
  def normalized(info):info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0;return info
  with tarfile.open(output,'w:xz',preset=6) as t:t.add(package,arcname='Awl',filter=normalized)
  output.with_name(output.name+'.sha256').write_text(digest(output)+'  '+output.name+'\n');print(output,output.stat().st_size,digest(output))
if __name__=='__main__':main()

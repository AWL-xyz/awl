#!/usr/bin/env python3
"""Contributor-only Linux x86-64 bundle builder. Not run by installed kcc.
Downloads are opt-in and checksum locked. Requires Python 3.12+ and native host.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import urllib.request
from distribution_privacy import scrub_private
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while data:=f.read(1048576):h.update(data)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--download-toolchain',action='store_true');p.add_argument('--no-archive',action='store_true');p.add_argument('--archive-output',type=Path,help='Contributor staging path for a full archive before publication');a=p.parse_args()
    if platform.system()!='Linux' or platform.machine()!='x86_64':p.error('builder currently requires Linux x86-64')
    lock=json.loads((ROOT/'compiler/toolchain-lock.json').read_text())
    cache=ROOT/'.cache/toolchains';cache.mkdir(parents=True,exist_ok=True);upstream=cache/'zig-0.15.2.tar.xz'
    if not upstream.is_file():
        if not a.download_toolchain:p.error('toolchain not cached; pass --download-toolchain for explicit contributor download')
        part=upstream.with_suffix('.part')
        with urllib.request.urlopen(lock['url'],timeout=90) as response,part.open('wb') as f:shutil.copyfileobj(response,f)
        if digest(part)!=lock['sha256']:part.unlink();raise RuntimeError('upstream SHA-256 mismatch')
        part.replace(upstream)
    if digest(upstream)!=lock['sha256'] or upstream.stat().st_size!=lock['bytes']:raise RuntimeError('cached toolchain integrity failure')
    package=ROOT/'build/Awl-linux-x86_64';package.mkdir(parents=True,exist_ok=True)
    tool=package/'libexec/zig'
    if not tool.exists():
        tool.parent.mkdir(exist_ok=True)
        extracted=ROOT/'build/zig-x86_64-linux-0.15.2'
        if not extracted.exists():
            with tarfile.open(upstream) as archive:archive.extractall(ROOT/'build',filter='data')
        extracted.rename(tool)
    if subprocess.check_output([str(tool/'zig'),'version'],text=True).strip()!=lock['version']:raise RuntimeError('toolchain version mismatch')
    (package/'bin').mkdir(exist_ok=True)
    native=ROOT/'compiler/native'
    flags=['-std=c++20','-target',lock['target'],'-mcpu=baseline','-static','-O2','-g0','-s','-Wall','-Wextra','-Werror']
    def affinity():
        allowed=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,set(allowed[:4]))
    subprocess.run([str(tool/'zig'),'c++',*flags,*[str(native/name) for name in ['klex.cpp','kparse.cpp','kcc.cpp','kbuild.cpp']],'-o',str(package/'bin/kcc')],check=True,timeout=360,preexec_fn=affinity)
    public=package/'bin/awl'
    if public.exists() or public.is_symlink():public.unlink()
    public.symlink_to('kcc')
    for alias in ['acc','awL','aWl','aWL','Awl','AwL','AWl','AWL']:
        link=package/'bin'/alias
        if link.exists() or link.is_symlink():link.unlink()
        link.symlink_to('kcc')
    shutil.copy2(ROOT/'docs/ASDK.md',package/'ASDK.md')
    shutil.copy2(ROOT/'docs/STREAMS.md',package/'STREAMS.md')
    shutil.copy2(ROOT/'docs/NETWORK.md',package/'NETWORK.md')
    shutil.copy2(ROOT/'docs/TYPED-VECTORS.md',package/'TYPED-VECTORS.md')
    for directory in ['examples','third-party']:
        shutil.copytree(ROOT/directory,package/directory,dirs_exist_ok=True)
    src=package/'src';src.mkdir(exist_ok=True)
    for file in native.iterdir():
        if file.suffix in ['.cpp','.h','.inc','.c']:shutil.copy2(file,src/file.name)
    # Agent workspace notes are not installed compiler sources.
    for name in ['agents.md','memory.md','to-do.md']:
        stale=src/name
        if stale.exists():stale.unlink()
    for file in ['LICENSE','BUNDLE-README.md']:
        if (ROOT/file).is_file():shutil.copy2(ROOT/file,package/('README.md' if file=='BUNDLE-README.md' else file))
    shutil.copy2(ROOT/'docs/PROCESS-LIMITS.md',package/'PROCESS-LIMITS.md')
    shutil.copy2(ROOT/'docs/NATIVE-WINDOWS.md',package/'NATIVE-WINDOWS.md')
    shutil.copy2(ROOT/'docs/MODULES.md',package/'MODULES.md')
    shutil.copy2(ROOT/'docs/STRINGS.md',package/'STRINGS.md')
    shutil.copy2(ROOT/'docs/SPOOLS.md',package/'SPOOLS.md')
    shutil.copy2(ROOT/'docs/SCOPED-CLEANUP.md',package/'SCOPED-CLEANUP.md')
    shutil.copy2(ROOT/'docs/ARRAYS.md',package/'ARRAYS.md')
    shutil.copy2(ROOT/'docs/REPEATED-ARRAYS.md',package/'REPEATED-ARRAYS.md')
    shutil.copy2(ROOT/'docs/SCOPED-OWNERS.md',package/'SCOPED-OWNERS.md')
    shutil.copy2(ROOT/'docs/BUILDER-BORROWS.md',package/'BUILDER-BORROWS.md')
    shutil.copy2(ROOT/'docs/LOCAL-MOVES.md',package/'LOCAL-MOVES.md')
    shutil.copy2(ROOT/'docs/OWNING-PARAMETERS.md',package/'OWNING-PARAMETERS.md')
    shutil.copy2(ROOT/'docs/OWNED-RESULTS.md',package/'OWNED-RESULTS.md')
    shutil.copy2(ROOT/'docs/CONDITIONAL-OWNERSHIP.md',package/'CONDITIONAL-OWNERSHIP.md')
    shutil.copy2(ROOT/'docs/MATCH-OWNERSHIP.md',package/'MATCH-OWNERSHIP.md')
    shutil.copy2(ROOT/'docs/OWNER-REINITIALIZATION.md',package/'OWNER-REINITIALIZATION.md')
    shutil.copy2(ROOT/'docs/LOOP-OWNERSHIP.md',package/'LOOP-OWNERSHIP.md')
    shutil.copy2(ROOT/'docs/MATH.md',package/'MATH.md')
    shutil.copy2(ROOT/'docs/MODULE-STATE.md',package/'MODULE-STATE.md')
    shutil.copy2(ROOT/'docs/AESOP.md',package/'AESOP.md')
    shutil.copy2(ROOT/'docs/INT-VECTORS.md',package/'INT-VECTORS.md')
    shutil.copy2(ROOT/'docs/WINDOWS.md',package/'WINDOWS.md')
    shutil.copy2(ROOT/'docs/WIN32-GUI.md',package/'WIN32-GUI.md')
    shutil.copy2(ROOT/'docs/FILES.md',package/'FILES.md')
    shutil.copy2(ROOT/'docs/PIXELBOARD-FILES.md',package/'PIXELBOARD-FILES.md')
    shutil.copy2(ROOT/'docs/CAPABILITY-ASSESSMENT.md',package/'CAPABILITY-ASSESSMENT.md')
    scrub_private(package)
    manifest={'toolkit':{'name':'Awl Software Development Kit [Beta]','command':'bin/awl','commands':['init','build']},'version':'0.24.0-dev','status':'experimental source candidate using Aesop syntax; Linux x86-64 only','toolchain':lock,'compiler_build_flags':flags,
        'kcc_sha256':digest(package/'bin/kcc'),'zig_sha256':digest(tool/'zig'),
        'compiler_sources_sha256':{f.name:digest(f) for f in sorted(src.iterdir()) if f.suffix in ['.cpp','.h','.inc','.c']},
        'resources':'Complete upstream Zig distribution, including libc sources/headers, compiler-rt, libc++/libc++abi/libunwind resources and notices. No host development tools required at runtime.',
        'build_target':'static x86_64-linux-musl; baseline CPU; release binaries without debug symbols','tested_host_baseline':'Linux x86-64 kernel6.1.189; see validation/files-development-validation.json; no older-kernel compatibility claim.'}
    (package/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    validation=package/'validation'
    if validation.exists():shutil.rmtree(validation)
    validation.mkdir()
    for name in ['own-params-validation.json','own-params-tests.txt','own-params-reference-suite.txt','own-params-native-frontend-suite.txt','own-params-native-parser-suite.txt','own-params-frontend-sanitized.txt','own-params-resources-sanitized.txt','own-params-platform-sanitized.txt','own-params-driver-sanitized.txt','own-params-integer-runtime.txt','own-params-windows-cross-build.txt','own-params-benchmark.txt','moves-validation.json','moves-tests.txt','moves-reference-suite.txt','moves-native-frontend-suite.txt','moves-native-parser-suite.txt','moves-frontend-sanitized.txt','moves-resources-sanitized.txt','moves-platform-sanitized.txt','moves-driver-sanitized.txt','moves-integer-runtime.txt','moves-windows-cross-build.txt','moves-benchmark.txt','borrows-validation.json','borrows-tests.txt','borrows-reference-suite.txt','borrows-native-frontend-suite.txt','borrows-native-parser-suite.txt','borrows-frontend-sanitized.txt','borrows-resources-sanitized.txt','borrows-platform-sanitized.txt','borrows-driver-sanitized.txt','borrows-integer-runtime.txt','borrows-windows-cross-build.txt','borrows-benchmark.txt','scoped-owner-validation.json','scoped-owner-tests.txt','scoped-owner-reference-suite.txt','scoped-owner-native-frontend-suite.txt','scoped-owner-native-parser-suite.txt','scoped-owner-frontend-sanitized.txt','scoped-owner-runtime-sanitized.txt','scoped-owner-resources-sanitized.txt','scoped-owner-platform-sanitized.txt','scoped-owner-driver-sanitized.txt','scoped-owner-integer-runtime.txt','scoped-owner-windows-cross-build.txt','scoped-owner-benchmark.txt','repeat-validation.json','repeat-tests.txt','repeat-reference-suite.txt','repeat-native-frontend-suite.txt','repeat-native-parser-suite.txt','repeat-frontend-sanitized.txt','repeat-runtime-sanitized.txt','repeat-resources-sanitized.txt','repeat-platform-sanitized.txt','repeat-driver-sanitized.txt','repeat-integer-runtime.txt','repeat-windows-cross-build.txt','repeat-benchmark.txt','arrays-validation.json','arrays-tests.txt','arrays-reference-suite.txt','arrays-native-frontend-suite.txt','arrays-native-parser-suite.txt','arrays-frontend-sanitized.txt','arrays-runtime-sanitized.txt','arrays-driver-sanitized.txt','arrays-platform-sanitized.txt','arrays-resources-sanitized.txt','arrays-windows-cross-build.txt','arrays-integer-runtime.txt','arrays-benchmark.txt','cleanup-validation.json','cleanup-tests.txt','cleanup-reference-suite.txt','cleanup-native-frontend-suite.txt','cleanup-native-parser-suite.txt','cleanup-frontend-sanitized.txt','cleanup-runtime-sanitized.txt','cleanup-driver-sanitized.txt','cleanup-platform-sanitized.txt','cleanup-builders-sanitized.txt','cleanup-windows-cross-build.txt','cleanup-integer-runtime.txt','cleanup-benchmark.txt','builders-validation.json','builders-tests.txt','builders-reference-suite.txt','builders-native-frontend-suite.txt','builders-native-parser-suite.txt','builders-frontend-sanitized.txt','builders-runtime-sanitized.txt','builders-driver-sanitized.txt','builders-platform-sanitized.txt','builders-strings-sanitized.txt','builders-modules-sanitized.txt','builders-windows-cross-build.txt','builders-benchmark.txt','builders-integer-runtime.txt','strings-validation.json','strings-tests.txt','strings-reference-suite.txt','strings-native-frontend-suite.txt','strings-native-parser-suite.txt','strings-frontend-sanitized.txt','strings-runtime-sanitized.txt','strings-platform-sanitized.txt','strings-driver-sanitized.txt','strings-verifier-sanitized.txt','strings-platform-tests.txt','strings-windows-cross-build.txt','strings-integer-runtime.txt','strings-benchmark.txt','modules-validation.json','modules-tests.txt','modules-reference-suite.txt','modules-native-frontend-suite.txt','modules-native-parser-suite.txt','modules-frontend-sanitized.txt','modules-runtime-sanitized.txt','modules-platform-sanitized.txt','modules-driver-sanitized.txt','bundle-driver-sanitizer.json','driver-limits-sanitized.txt','bundle-runtime.json']:
        path=ROOT/'tests'/name
        if path.is_file():shutil.copy2(path,validation/name)
    for path in sorted((ROOT/'tests').glob('owned-results-*')):
        if path.is_file():shutil.copy2(path,validation/path.name)
    for path in sorted((ROOT/'tests').glob('branch-joins-*')):
        if path.is_file():shutil.copy2(path,validation/path.name)
    for path in sorted((ROOT/'tests').glob('match-joins-*')):
        if path.is_file():shutil.copy2(path,validation/path.name)
    for path in sorted((ROOT/'tests').glob('reinit-*')):
        if path.is_file():shutil.copy2(path,validation/path.name)
    for path in sorted((ROOT/'tests').glob('loop-owners-*')):
        if path.is_file():shutil.copy2(path,validation/path.name)
    for path in sorted((ROOT/'tests').glob('vectors-*')):
        if path.is_file():shutil.copy2(path,validation/path.name)
    for path in sorted((ROOT/'tests').glob('win32-*')):
        if path.is_file():shutil.copy2(path,validation/path.name)
    for path in sorted((ROOT/'tests').glob('files-*')):
        if path.is_file():shutil.copy2(path,validation/path.name)
    for path in sorted((ROOT/'tests').glob('persistence-*')):
        if path.is_file() and not path.name.startswith(('persistence-linux-exact','persistence-windows-exact','persistence-release-acceptance','persistence-parent-audit','persistence-linux-extracted')):shutil.copy2(path,validation/path.name)
    for bench in [ROOT/'benchmarks'/n for n in ['files-latest.json','persistence-latest.json','persistence-build-latest.json']]:
        if bench.is_file():shutil.copy2(bench,validation/bench.name)
    print(package,flush=True)
    if not a.no_archive:
        output=a.archive_output or ROOT.parent/'Awl-0.24.0-dev-linux-x86_64.tar.xz'
        output.parent.mkdir(parents=True,exist_ok=True)
        def normalized(item):
            item.uid=item.gid=0;item.uname=item.gname='';item.mtime=0;return item
        with tarfile.open(output,'w:xz',preset=6) as archive:archive.add(package,arcname='Awl',filter=normalized)
        checksum=digest(output)
        output.with_name(output.name+'.sha256').write_text(checksum+'  '+output.name+'\n')
        print(output,output.stat().st_size,checksum,flush=True)
if __name__=='__main__':main()

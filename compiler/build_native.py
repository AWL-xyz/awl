#!/usr/bin/env python3
"""Contributor build: native C++20 frontend library and optional standalone checker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--cxx',default=os.environ.get('CXX','g++')); p.add_argument('--sanitize',action='store_true'); p.add_argument('--standalone',action='store_true'); p.add_argument('--static',action='store_true');p.add_argument('--strip',action='store_true',help='omit symbol tables in contributor binaries')
    p.add_argument('--gc-sections',action='store_true',help='Linux ELF standalone dead-section elimination');
    p.add_argument('--lto',action='store_true',help='Linux standalone link-time optimization, explicitly opt in');
    p.add_argument('--compact-shared',action='store_true',help='Linux shared frontend Os/LTO size tradeoff, explicitly opt in');a=p.parse_args()
    if a.compact_shared and platform.system()!='Linux':p.error('--compact-shared is Linux-qualified only')
    if a.lto and (not a.standalone or platform.system()!='Linux'):p.error('--lto requires Linux --standalone')
    if a.gc_sections and (not a.standalone or platform.system()!='Linux'):p.error('--gc-sections requires Linux --standalone')
    if a.static and not a.standalone: p.error('--static requires --standalone')
    cxx=shutil.which(a.cxx)
    if not cxx: p.error('C++20 compiler not found; set CXX or pass --cxx PATH')
    suffix='.dll' if os.name=='nt' else '.dylib' if platform.system()=='Darwin' else '.so'
    folder=ROOT/'native/bin'; folder.mkdir(parents=True,exist_ok=True); output=folder/('Awllex'+suffix)
    flags=['-std=c++20','-O3','-Wall','-Wextra','-Werror','-shared']
    if a.compact_shared: flags[1]='-Os';flags+=['-flto']
    if a.strip: flags+=['-s']
    if os.name!='nt': flags+=['-fPIC','-fvisibility=hidden']
    else: flags+=['-static-libgcc','-static-libstdc++']
    if a.sanitize: p.error('Use the standalone native sanitizer harness; loading an ASan library into Python requires special runtime setup.')
    subprocess.run([cxx,*flags,str(ROOT/'native/lex.cpp'),str(ROOT/'native/parse.cpp'),'-o',str(output)],check=True)
    info={'abi_version':2,'toolchain_directory':str(Path(cxx).parent),'compiler':subprocess.check_output([cxx,'--version'],text=True).splitlines()[0],'flags':flags,'source_sha256':hashlib.sha256((ROOT/'native/lex.cpp').read_bytes()).hexdigest(),'header_sha256':hashlib.sha256((ROOT/'native/lex.h').read_bytes()).hexdigest(),'parser_source_sha256':hashlib.sha256((ROOT/'native/parse.cpp').read_bytes()).hexdigest(),'parser_header_sha256':hashlib.sha256((ROOT/'native/parse.h').read_bytes()).hexdigest(),'library':output.name}
    info['frontend_sources_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'native').iterdir()) if p.suffix in ('.cpp','.h','.inc')}
    info['host']=platform.platform()
    info['target']=subprocess.check_output([cxx,'-dumpmachine'],text=True).strip()
    info['library_sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    if a.standalone:
        exe=folder/('acc.exe' if os.name=='nt' else 'acc')
        exe_flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
        if a.strip: exe_flags+=['-s']
        if a.lto: exe_flags+=['-flto']
        if a.gc_sections: exe_flags+=['-ffunction-sections','-fdata-sections','-Wl,--gc-sections']
        if a.static or os.name=='nt': exe_flags+=['-static']
        if os.name=='nt': exe_flags+=['-municode']
        subprocess.run([cxx,*exe_flags,str(ROOT/'native/lex.cpp'),str(ROOT/'native/parse.cpp'),str(ROOT/'native/acc.cpp'),str(ROOT/'native/build.cpp'),*(['-lbcrypt','-ladvapi32'] if os.name=='nt' else []),'-o',str(exe)],check=True)
        if os.name!='nt': exe.chmod(exe.stat().st_mode|0o111)
        info['standalone']={'file':exe.name,'flags':exe_flags,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'bytes':exe.stat().st_size}
        public=folder/('awl.exe' if os.name=='nt' else 'awl')
        if public.exists() or public.is_symlink(): public.unlink()
        if os.name=='nt': shutil.copy2(exe,public)
        else:
            public.symlink_to(exe.name)
            for alias in ['awL','aWl','aWL','Awl','AwL','AWl','AWL']:
                link=folder/alias
                if link.exists() or link.is_symlink():link.unlink()
                link.symlink_to(exe.name)
        info['toolkit']={'name':'Awl Software Development Kit [Beta]','file':public.name,'sha256':info['standalone']['sha256'],'commands':['init','build']}
        print(public)
        print(exe)
    (folder/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
    print(output)
if __name__=='__main__': main()

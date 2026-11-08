#!/usr/bin/env python3
"""Standalone C++ scanner, parser and checker tests, optionally instrumented without embedding Python."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--cxx',default=os.environ.get('CXX','g++')); p.add_argument('--sanitize',action='store_true');p.add_argument('--phase',action='append',choices=['lexer','frontend','verifier','project'],help='Run only selected isolated phases');p.add_argument('--compile-timeout',type=int,default=180,help='Contributor compile budget in seconds; runtime budgets are unchanged'); a=p.parse_args()
    if a.compile_timeout<1:p.error('--compile-timeout must be positive')
    cxx=shutil.which(a.cxx)
    if not cxx: p.error('C++20 compiler not found')
    flags=['-std=c++20','-O1','-Wall','-Wextra','-Werror']
    if a.sanitize: flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
    phases=[('lexer',['klex.cpp','klex_test.cpp'],[],30),
            ('frontend',['klex.cpp','kparse.cpp','kparse_test.cpp'],[str(p) for p in sorted((ROOT.parent/'examples').glob('*.aw'))],90),
            ('verifier',['klex.cpp','kverify_test.cpp'],[],90),
            ('project',['klex.cpp','kproject_test.cpp'],[],90)]
    with tempfile.TemporaryDirectory(prefix='Awl-native-test-') as td:
        for name,sources,args,run_timeout in phases:
            if a.phase and name not in a.phase:continue
            exe=Path(td)/(name+('.exe' if os.name=='nt' else ''))
            print('Native phase:',name,flush=True)
            subprocess.run([cxx,*flags,*[str(ROOT/'native'/source) for source in sources],'-o',str(exe)],check=True,timeout=a.compile_timeout)
            subprocess.run([str(exe),*args],check=True,timeout=run_timeout)
if __name__=='__main__': main()

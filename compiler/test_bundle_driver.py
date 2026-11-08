#!/usr/bin/env python3
"""Contributor-only ASan/UBSan check of native CLI/process/staging code on Linux."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sanitize',action='store_true');args=parser.parse_args()
    flags=['-std=c++20','-O1','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
    records=[]
    with tempfile.TemporaryDirectory(prefix='Awl-driver-sanitizer-') as td:
        prefix=Path(td);(prefix/'bin').mkdir();(prefix/'libexec').mkdir()
        (prefix/'libexec/zig').symlink_to(ROOT/'build/Awl-linux-x86_64/libexec/zig',target_is_directory=True)
        native=ROOT/'compiler/native';binary=prefix/'bin/kcc'
        subprocess.run([os.environ.get('CXX','g++'),*flags,*[str(native/name) for name in ['klex.cpp','kparse.cpp','kcc.cpp','kbuild.cpp']],'-o',str(binary)],check=True,timeout=150)
        env={**os.environ,'PATH':'/no-tools','XDG_CACHE_HOME':str(ROOT/'build/driver-sanitizer-cache'),'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'}
        source=prefix/'source with spaces.aw';source.write_text('function main()->i64 print(42) return 0 end');out=prefix/'output with spaces'
        def invoke(argv,code):
            r=subprocess.run([str(binary),*map(str,argv)],env=env,capture_output=True,text=True,timeout=120)
            assert r.returncode==code,(argv,r.stdout,r.stderr)
            assert 'ERROR: AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr and 'LeakSanitizer' not in r.stderr,r.stderr
            records.append({'argv':list(map(str,argv)),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});return r
        invoke(['build',source,'-o',out],0);before=out.read_bytes()
        assert invoke(['run',source],0).stdout=='42\n'
        invoke(['build',source,'-o',source],2)
        bad=prefix/'bad.aw';bad.write_text('function main()->i64 return true end')
        invoke(['build',bad,'-o',out],1);assert out.read_bytes()==before
        link=prefix/'libexec/zig';link.unlink()
        invoke(['build',source,'-o',out],2);assert out.read_bytes()==before
        assert not list(prefix.glob('.Awl-output-*'))
        # Reuse deterministic fork/timeout/ELF/limit/descriptor probes with this
        # instrumented CLI, not just the separately tested packaged binary.
        probe_env={**env,'Awl_DRIVER_TEST_BINARY':str(binary)}
        probe=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_driver_limits.py','-v'],env=probe_env,capture_output=True,text=True,timeout=150)
        (ROOT/'tests/driver-limits-sanitized.txt').write_text(probe.stdout+probe.stderr)
        assert probe.returncode==0,probe.stdout+probe.stderr

    report={'result':'passed','flags':flags,'operations':records,'failure_probe_suite':'9 methods passed using the ASan/UBSan-instrumented native driver; tests/driver-limits-sanitized.txt','scope':'Instrumented native CLI/frontend/process/staging code; bundled codegen itself is upstream uninstrumented. Not the clean-root acceptance test.'}
    (ROOT/'tests/bundle-driver-sanitizer.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Native bundle driver ASan/UBSan checks passed')
if __name__=='__main__':main()

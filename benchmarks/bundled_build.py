#!/usr/bin/env python3
"""Full executable build samples, native bundle vs Python reference with same backend.
The worker is contributor-only instrumentation, never part of installed Awl.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'build/Awl-linux-x86_64'

def affinity():os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
def worker(source,out):
    sys.path.insert(0,str(ROOT/'compiler'));import kcc
    emitted=kcc.Emitter(kcc.compile_text(Path(source).read_text(),'python','python')).emit()
    with tempfile.TemporaryDirectory(prefix='Awl-ref-build-') as td:
        d=Path(td);c=d/'program.c';c.write_text(emitted)
        cache=Path(os.environ['XDG_CACHE_HOME'])/'Awl/zig-0.15.2';cache.mkdir(parents=True,exist_ok=True)
        env={'PATH':'/no-host-tools','LC_ALL':'C','HOME':str(d),'TMPDIR':str(d),'ZIG_LIB_DIR':str(PACKAGE/'libexec/zig/lib'),'ZIG_GLOBAL_CACHE_DIR':str(cache),'ZIG_LOCAL_CACHE_DIR':str(d/'local-cache')}
        subprocess.run([str(PACKAGE/'libexec/zig/zig'),'cc','-std=c11','-target','x86_64-linux-musl','-mcpu=baseline','-static','-O2','-g0','-s',str(c),'-o',out],env=env,preexec_fn=affinity,check=True,capture_output=True,timeout=120)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference-worker',nargs=2);parser.add_argument('--samples',type=int,default=5);a=parser.parse_args()
    if a.reference_worker:return worker(*a.reference_worker)
    if not 3<=a.samples<=30:parser.error('samples must be 3..30')
    records={};cold=None
    with tempfile.TemporaryDirectory(prefix='Awl-full-build-bench-') as td:
        d=Path(td);env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(d/'cache')}
        for name in ['hello','values','results','integers']:
            source=ROOT/'examples'/f'{name}.aw'
            native=[str(PACKAGE/'bin/kcc'),'build',str(source),'-o',str(d/'native'),'-O','2']
            reference=[sys.executable,str(Path(__file__).resolve()),'--reference-worker',str(source),str(d/'reference')]
            commands={'native':native,'reference_python_same_bundled_backend':reference};times={key:[] for key in commands}
            for key,cmd in commands.items():
                start=time.perf_counter();subprocess.run(cmd,env=env,check=True,capture_output=True,timeout=120)
                if cold is None:cold={'native_first_build_empty_backend_cache_seconds':time.perf_counter()-start}
            for i in range(a.samples):
                for key in list(commands)[::1 if i%2==0 else -1]:
                    start=time.perf_counter();subprocess.run(commands[key],env=env,check=True,capture_output=True,timeout=120)
                    times[key].append(time.perf_counter()-start)
            native_run=subprocess.run([str(d/'native')],capture_output=True,text=True,check=True)
            ref_run=subprocess.run([str(d/'reference')],capture_output=True,text=True,check=True)
            assert native_run.stdout==ref_run.stdout
            records[name]={'source_bytes':source.stat().st_size,'results':{key:{'median_seconds':statistics.median(samples),'samples_seconds':samples} for key,samples in times.items()},'runtime_stdout_matched':True,'native_executable_bytes':(d/'native').stat().st_size}
    result={'host':platform.platform(),'python':platform.python_version(),'bundle_manifest':json.loads((PACKAGE/'manifest.json').read_text()),'cold_build':cold,'cases':records,
        'scope':'End-to-end source-to-static-executable build including driver startup, frontend, verification, C emission, machine code generation, libc/startup resources and linking. Native path uses only shipped resources.',
        'caveats':['Four small example programs, not a representative large-project benchmark; no optimization-heavy build speed guarantee.',
        'Reference is a contributor Python worker with the same Zig/LLVM/musl flags and shared backend cache, not the historical GCC-based CLI. Source-level IR verification/layout traversal counts differ.',
        'Warm samples reuse backend libc/compiler-rt cache, NOT frontend/module caches. First native cold-cache build is recorded separately and includes building bundled runtime resources.',
        'Order alternates, backend subprocess affinity is capped to four allowed CPUs, parent scheduling/frequency/load uncontrolled. No generated-program performance speedup claim.']}
    (ROOT/'benchmarks/bundled-build-latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Cold native first build:',round(cold['native_first_build_empty_backend_cache_seconds'],3),'s')
    for name,record in records.items():print(name,{key:round(r['median_seconds']*1000,3) for key,r in record['results'].items()},'ms')
if __name__=='__main__':main()

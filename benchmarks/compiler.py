#!/usr/bin/env python3
"""Compiler-host measurements: reference scanner, integrated native scanner, check.
No native Awl executable performance is measured here.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'compiler'))
import kcc

def sampled(fn,repeat,samples):
    fn(); times=[]
    for _ in range(samples):
        begin=time.perf_counter()
        for _ in range(repeat): fn()
        times.append((time.perf_counter()-begin)/repeat)
    return {'median_seconds':statistics.median(times),'samples_seconds':times,'repetitions_per_sample':repeat}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--locals',type=int,default=3000); a=p.parse_args()
    if not 1<=a.locals<=12000: p.error('--locals must be 1..12000')
    source='function main()->i64\n'+''.join(f'local v{i}:i64={i}\n' for i in range(a.locals))+'return 0\nend\n'
    py=kcc.lex(source,'python'); native=kcc.lex(source,'native')
    if py!=native: raise RuntimeError('token mismatch')
    if kcc.compile_text(source,'python')!=kcc.compile_text(source,'native'): raise RuntimeError('IR mismatch')
    samples=5; repeat=20; encoded=source.encode(); lib,_=kcc.load_native_lexer()
    seconds=C.c_double(); count=C.c_uint64(); isolated=[]
    for _ in range(samples):
        status=lib.Awl_lex_benchmark(encoded,len(encoded),repeat,C.byref(seconds),C.byref(count))
        if status or count.value!=(len(py)-1)*repeat: raise RuntimeError('isolated token count mismatch')
        isolated.append(seconds.value/repeat)
    result={'kcc':kcc.VERSION,'host':platform.platform(),'python':platform.python_version(),'source_bytes':len(encoded),'local_declarations':a.locals,'tokens_including_eof':len(py),'native_library':str(kcc.native_library_path()),'native_build_flags':['-std=c++20','-O3','-shared'],'results':{
        'python_lexer':sampled(lambda:kcc.lex(source,'python'),repeat,samples),
        'native_lexer_isolated':{'median_seconds':statistics.median(isolated),'samples_seconds':isolated,'repetitions_per_sample':repeat},
        'native_lexer_integrated':sampled(lambda:kcc.lex(source,'native'),repeat,samples),
        'python_frontend_check':sampled(lambda:kcc.compile_text(source,'python'),3,samples),
        'native_lexer_frontend_check':sampled(lambda:kcc.compile_text(source,'native'),3,samples)},
        'parity_verified':True,'caveats':['In-process measurements are warmed up and exclude library loading; CLI measurements include startup/loading.','Isolated C++ scanner returns span records, not Python Token objects.','Integrated native measurement includes UTF-8 encoding, FFI, adapter checks and Python Token allocation.','Frontend check includes parsing, static checking and IR verification, not C emission, C compilation or linking.','One synthetic many-local source; CPU affinity/frequency uncontrolled and measurement order fixed.','Does not measure compiled Awl program execution.']}
    info=kcc.native_library_path().parent/'build-info.json'
    result['native_build']=json.loads(info.read_text()) if info.is_file() else {'metadata':'not available'}
    with tempfile.TemporaryDirectory(prefix='Awl-compiler-bench-') as td:
        path=Path(td)/'bench.aw'; path.write_text(source)
        import os
        exe=Path(td)/('bench.exe' if os.name=='nt' else 'bench')
        for backend in ('python','native'):
            check=[sys.executable,str(ROOT/'compiler/kcc.py'),'check',str(path),'--lexer',backend]
            build=[sys.executable,str(ROOT/'compiler/kcc.py'),'build',str(path),'--lexer',backend,'-o',str(exe)]
            result['results'][backend+'_cli_check']=sampled(lambda:subprocess.run(check,check=True,capture_output=True),2,3)
            result['results'][backend+'_cli_build']=sampled(lambda:subprocess.run(build,check=True,capture_output=True),1,3)
            subprocess.run([str(exe)],check=True)
    result['caveats']+=['CLI build includes C emission, host C compilation/linking at default O2 and process startup; native executable returned zero.',
                        'Synthetic locals are unused and optimized away by the C backend; this is not a representative optimization-heavy build.',
                        'Only scanner inner loop has migrated; Python still owns parser/checker/verifier/emitter.']
    result['c_compiler']=subprocess.check_output([kcc.find_cc(),'--version'],text=True).splitlines()[0]
    r=result['results']; result['speedup_ratios']={'lexer_integrated':r['python_lexer']['median_seconds']/r['native_lexer_integrated']['median_seconds'],'frontend_check':r['python_frontend_check']['median_seconds']/r['native_lexer_frontend_check']['median_seconds'],'cli_check':r['python_cli_check']['median_seconds']/r['native_cli_check']['median_seconds'],'cli_build':r['python_cli_build']['median_seconds']/r['native_cli_build']['median_seconds']}
    (ROOT/'benchmarks/compiler-latest.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()

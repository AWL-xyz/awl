#!/usr/bin/env python3
"""Native frontend latency only. Not executable generation or a full build benchmark."""
import argparse
import ctypes as C
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
sys.path.insert(0,str(ROOT/'compiler'))
import kcc

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--locals',type=int,default=3000);p.add_argument('--samples',type=int,default=9);a=p.parse_args()
    if not 1<=a.locals<=12000 or not 3<=a.samples<=100: p.error('locals 1..12000, samples 3..100')
    source='function main()->i64\n'+''.join(f'local v{i}:i64={i}\n' for i in range(a.locals))+'return 0\nend\n'
    lib,_=kcc.native_parser_api()
    lib.Awl_parse_source.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(C.c_void_p)];lib.Awl_parse_source.restype=C.c_int
    lib.Awl_check_unit.argtypes=[C.c_void_p];lib.Awl_check_unit.restype=C.c_int
    lib.Awl_verify_unit.argtypes=[C.c_void_p];lib.Awl_verify_unit.restype=C.c_int
    def native():
        encoded=source.encode('utf-8');unit=C.c_void_p()
        try:
            if lib.Awl_parse_source(encoded,len(encoded),C.byref(unit)) or not unit: raise RuntimeError('parse failure')
            if lib.Awl_check_unit(unit): raise RuntimeError('check failure')
            if lib.Awl_verify_unit(unit): raise RuntimeError('verification failure')
        finally:
            if unit: lib.Awl_parse_free(unit)
    def reference(): return kcc.compile_text(source,'python','python')
    checked=kcc.hydrate_native_arena(kcc.check_native_source(source),kcc.lex_python(source),True)
    if checked!=reference(): raise RuntimeError('typed tree mismatch')
    kcc.verify_ir(checked)
    if kcc.emit_native_c(source)!=kcc.Emitter(checked).emit(): raise RuntimeError('C emission mismatch')
    binary=ROOT/'compiler/native/bin'/('kcc.exe' if os.name=='nt' else 'kcc')
    with tempfile.TemporaryDirectory(prefix='Awl-native-frontend-bench-') as td:
        path=Path(td)/'many-locals.aw';path.write_text(source)
        funcs={'python_source_check':reference,'native_source_check':native,
               'python_cli_check':lambda:subprocess.run([sys.executable,str(ROOT/'compiler/kcc.py'),'check',str(path),'--lexer','python','--parser','python'],check=True,capture_output=True),
               'python_source_emit_c':lambda:kcc.Emitter(kcc.compile_text(source,'python','python')).emit(),
               'native_source_emit_c':lambda:kcc.emit_native_c(source),
               'python_cli_emit_c':lambda:subprocess.run([sys.executable,str(ROOT/'compiler/kcc.py'),'emit-c',str(path),'--lexer','python','--parser','python'],check=True,capture_output=True),
               'native_cli_emit_c':lambda:subprocess.run([str(binary),'emit-c',str(path)],check=True,capture_output=True,env={**os.environ,'PATH':'/no-development-tools'}),
               'native_cli_check':lambda:subprocess.run([str(binary),'check',str(path)],check=True,capture_output=True,env={**os.environ,'PATH':'/no-development-tools'})}
        times={key:[] for key in funcs}
        for fn in funcs.values(): fn()
        names=list(funcs)
        for i in range(a.samples):
            for name in names[::1 if i%2==0 else -1]:
                start=time.perf_counter();funcs[name]();times[name].append(time.perf_counter()-start)
    result={'status':'0.7 work in progress; not a native compiler release','host':platform.platform(),'python':platform.python_version(),'source_bytes':len(source.encode()),'local_declarations':a.locals,'parity_verified':True,
        'results':{name:{'median_seconds':statistics.median(values),'samples_seconds':values} for name,values in times.items()},
        'native_build':json.loads((binary.parent/'build-info.json').read_text()),
        'caveats':['Frontend checking and C-source emission are timed; machine code generation/linking is not implemented, so no full native-build speedup is measured.',
          'In-process source checks both include lexing, parsing, limits, resolution, type/layout/control-flow checking; both include their independent IR verifiers.',
          'C emission measurements include source checking, verification, emission and output materialization; the reference repeats verification at compile and emit entry, native emission verifies at its backend entry. Internal traversal counts/representations differ.',
          'Native in-process check includes UTF-8 encoding and C ABI calls, not JSON export, Python AST hydration or token objects.',
          'CLI check measurements include startup and file I/O. Both CLIs run their independent IR verifiers; representations differ and the native verifier additionally checks arena-schema invariants.',
          'One synthetic unused-locals workload; not a representative suite, no CPU affinity/frequency control, alternating sample order, warmed file cache.',
          'Library built at O3; standalone checker built at O2; inspect embedded build flags and hashes. No runtime performance claim.']}
    output=ROOT/'benchmarks/native-frontend-latest.json';output.write_text(json.dumps(result,indent=2)+'\n')
    for name,row in result['results'].items(): print(name,round(row['median_seconds']*1000,3),'ms')
    print(output)
if __name__=='__main__':main()

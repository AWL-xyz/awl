#!/usr/bin/env python3
"""Contributor scanner, parser, ownership and independent-verifier tests"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parent
PHASES = {
    'lexer': ['klex.cpp', 'klex_test.cpp'],
    'frontend': ['klex.cpp', 'kparse.cpp', 'kparse_test.cpp'],
    'verifier': ['klex.cpp', 'kverify_test.cpp'],
    'project': ['klex.cpp', 'kproject_test.cpp'],
    'aesop': ['klex.cpp', 'kaesop_test.cpp'],
    'inference': ['klex.cpp', 'kinfer_test.cpp'],
    'module-numeric': ['klex.cpp', 'kmodule_numeric_test.cpp'],
    'streams': ['klex.cpp', 'kstreams_test.cpp'],
    'typed-vectors': ['klex.cpp', 'kgeneric_test.cpp'],
    'tcp': ['klex.cpp', 'ktcp_test.cpp'],
    'replace': ['klex.cpp', 'kreplace_test.cpp'],
    'enums': ['klex.cpp', 'kenum_test.cpp'],
    'views': ['klex.cpp', 'kview_test.cpp'],
    'process': ['klex.cpp', 'kprocess_test.cpp'],
    'clean-syntax': ['klex.cpp', 'kclean_test.cpp'],
    'exported-enums': ['klex.cpp', 'kexport_test.cpp'],
}
def snapshot():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / 'native').iterdir()) if p.suffix in ('.h', '.cpp', '.inc', '.c')}
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cxx', default=os.environ.get('CXX', 'g++'))
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--phase', action='append', choices=PHASES)
    parser.add_argument('--compile-timeout', type=int, default=240)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.compile_timeout < 1:
        parser.error('--compile-timeout must be positive')
    cxx = shutil.which(args.cxx)
    if not cxx:
        parser.error('C++20 compiler not found')
    flags = ['-std=c++20', '-O0', '-Wall', '-Wextra', '-Werror']
    if args.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
    before = snapshot()
    records = []
    with tempfile.TemporaryDirectory(prefix='aesop-native-') as td:
        for name, sources in PHASES.items():
            if args.phase and name not in args.phase:
                continue
            exe = Path(td) / (name + ('.exe' if os.name == 'nt' else ''))
            print('native phase:', name, flush=True)
            subprocess.run([cxx, *flags, *[str(ROOT / 'native' / s) for s in sources], '-o', str(exe)], check=True, timeout=args.compile_timeout)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=180)
            print(result.stdout, result.stderr, end='', flush=True)
            result.check_returncode()
            records.append({'phase': name, 'exit': result.returncode, 'stdout': result.stdout,
                            'stderr': result.stderr, 'binary_sha256': hashlib.sha256(exe.read_bytes()).hexdigest()})
    assert before == snapshot(), 'native sources changed during qualification'
    if args.report:
        report = {'status': 'PASS', 'syntax': 'Aesop', 'sanitize': args.sanitize,
                  'compiler': subprocess.check_output([cxx, '--version'], text=True).splitlines()[0],
                  'flags': flags, 'native_sources_sha256': before, 'phases': records}
        data = (json.dumps(report, indent=2) + '\n').encode()
        args.report.write_bytes(gzip.compress(data, mtime=0) if args.report.suffix == '.gz' else data)
    print('PASS', len(records), 'Aesop native phases')
if __name__ == '__main__':
    main()

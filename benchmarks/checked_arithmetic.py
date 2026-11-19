#!/usr/bin/env python3
"""Measure the same checked i64 loop in Awl, C++, and Rust (if installed)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
WORKLOAD = ROOT / 'benchmarks/workloads/checked-arithmetic'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(tool):
    return subprocess.check_output([tool, '--version'], text=True, timeout=15).splitlines()[0]


def oracle(rounds, factor, state):
    total = 0
    for i in range(rounds):
        mixed = state * factor - i
        # Awl, C++ and Rust take the sign of the dividend; Python % does not.
        state = mixed % 1048573 if mixed >= 0 else -((-mixed) % 1048573)
        total += state
    return f'{total}\n{state}\n'.encode('ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--before', type=Path, help='optional pre-optimization Aesop ACC binary')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--cxx', default=os.environ.get('CXX', 'c++'))
    parser.add_argument('--rustc', help='Rust compiler; defaults to rustc on PATH when available')
    parser.add_argument('--rounds', type=int, default=5_000_000)
    parser.add_argument('--samples', type=int, default=9)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('benchmark flags and affinity reporting target Linux x86-64')
    if not 1 <= args.rounds <= 20_000_000 or not 1 <= args.samples <= 100:
        parser.error('--rounds must be 1..20000000 and --samples 1..100')
    cc, cxx, rustc = (shutil.which(tool) for tool in (args.cc, args.cxx, args.rustc or 'rustc'))
    if not cc or not cxx or (args.rustc and not rustc):
        parser.error('requested compiler not found; GCC/Clang C and C++ drivers are required')
    acc = args.acc.resolve()
    before = args.before.resolve() if args.before else None
    c_flags = ['-std=c11', '-O3', '-march=x86-64']
    cpp_flags = ['-std=c++20', '-O3', '-march=x86-64']
    rust_flags = ['--edition=2021', '-Copt-level=3', '-Ctarget-cpu=x86-64', '-Coverflow-checks=yes', '-Cpanic=abort']
    inputs = (args.rounds, -8191, 31)
    argv = list(map(str, inputs))
    expected = oracle(*inputs)
    rng = random.Random(9781)
    with tempfile.TemporaryDirectory(prefix='awl-arithmetic-bench-') as tmp:
        work = Path(tmp)
        binaries = {}

        def emit(compiler, target):
            with target.open('wb') as out:
                subprocess.run([compiler, 'emit-c', WORKLOAD / 'main.aw'], stdout=out, check=True, timeout=60)

        def compile_case(name, command):
            exe = work / name
            subprocess.run([*command, '-o', exe], check=True, timeout=60)
            binaries[name] = exe

        current_c = work / 'current.c'
        emit(acc, current_c)
        if before:
            before_c = work / 'before.c'
            emit(before, before_c)
            compile_case('awl-before', [cc, *c_flags, before_c, '-lm'])
        compile_case('awl-default', [cc, *c_flags, current_c, '-lm'])
        compile_case('awl-portable', [cc, *c_flags, '-DAWL_PORTABLE_ARITHMETIC', current_c, '-lm'])
        compile_case('cpp-checked', [cxx, *cpp_flags, WORKLOAD / 'main.cpp'])
        if rustc:
            compile_case('rust-checked', [rustc, *rust_flags, WORKLOAD / 'main.rs'])

        def sample(name):
            start = time.perf_counter_ns()
            result = subprocess.run([binaries[name], *argv], capture_output=True, timeout=30)
            elapsed = (time.perf_counter_ns() - start) / 1_000_000
            if result.returncode != 0 or result.stdout != expected or result.stderr:
                raise RuntimeError(f'{name}: expected {expected!r}, got {result}')
            return elapsed

        samples = {name: [] for name in binaries}
        for name in samples:
            sample(name)  # Warm up once; exclude these runs from measurements.
        for _ in range(args.samples):
            order = list(binaries)
            rng.shuffle(order)
            for name in order:
                samples[name].append(sample(name))

    cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                if line.startswith('model name')), 'unknown')
    report = {
        'scope': 'Checked signed i64 multiply/subtract/remainder/accumulate loop; not a language-wide ranking',
        'method': 'Warm whole-process wall time, shuffled per sample; build and Python oracle excluded',
        'host': platform.platform(),
        'cpu': cpu,
        'affinity': sorted(os.sched_getaffinity(0)),
        'inputs': {'rounds': inputs[0], 'factor': inputs[1], 'seed': inputs[2]},
        'expected_stdout': expected.decode('ascii'),
        'toolchains': {'C': version(cc), 'C++': version(cxx), 'Rust': version(rustc) if rustc else None},
        'flags': {'C': c_flags + ['-lm'], 'Awl portable override': '-DAWL_PORTABLE_ARITHMETIC',
                  'C++': cpp_flags, 'Rust': rust_flags if rustc else None},
        'acc_sha256': sha256(acc),
        'before_acc_sha256': sha256(before) if before else None,
        'harness_sha256': sha256(Path(__file__)),
        'workload_sha256': {f.name: sha256(f) for f in sorted(WORKLOAD.glob('main.*'))},
        'results': {name: {'median_ms': statistics.median(raw), 'samples_ms': raw} for name, raw in samples.items()},
        'rust_status': 'measured' if rustc else 'not run (rustc not found)',
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for name, result in report['results'].items():
        print(f"{name}: {result['median_ms']:.3f} ms median ({args.samples} samples)")
    if not rustc:
        print(f"rust-checked: {report['rust_status']}")
    print(f"Verified output: {expected.decode('ascii').strip().replace(chr(10), ', ')}")


if __name__ == '__main__':
    main()

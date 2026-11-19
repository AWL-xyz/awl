#!/usr/bin/env python3
"""Compare native Awl string.replace before/after on UTF-8 log-like data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import resource
import signal
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'benchmarks/workloads/text-replace/main.aw'
FLAGS = ['-std=c11', '-O3', '-march=x86-64']
STRING_TRAP = b'Awl string trap: bounds, scalar, I/O, or allocation limit\n'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data(rows, needle):
    source = ''.join(f'event={i:05} task=import flag=pending user=José unit=λ seq={i % 97:02}\n'
                     for i in range(rows))
    replacement = 'flag=complete'
    output = source.replace(needle, replacement)
    fields = [field.encode('utf-8') for field in (source, needle, replacement)]
    argv = [str(len(field)) for field in fields]
    expected = f'{len(output)}\n{len(output.encode("utf-8"))}\n{output}\n'.encode('utf-8')
    return argv, b''.join(fields), expected, source.count(needle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True, help='previous Aesop ACC binary')
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--samples', type=int, default=9)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('benchmark flags and redirected stdin target Linux x86-64')
    if not 1 <= args.samples <= 100:
        parser.error('--samples must be 1..100')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    compilers = {'before': args.before.resolve(), 'after': args.acc.resolve()}
    cases = {'512 replacements': data(512, 'flag=pending'), 'no matches': data(512, 'flag=missing')}
    timings = {case: {name: [] for name in compilers} for case in cases}
    rng = random.Random(9781)
    with tempfile.TemporaryDirectory(prefix='awl-replace-bench-') as tmp:
        work = Path(tmp)
        binaries = {}
        for name, compiler in compilers.items():
            generated, exe = work / f'{name}.c', work / name
            with generated.open('wb') as out:
                subprocess.run([compiler, 'emit-c', SOURCE], stdout=out, check=True, timeout=60)
            subprocess.run([args.cc, *FLAGS, generated, '-lm', '-o', exe], check=True, timeout=60)
            binaries[name] = exe

        def run(name, case):
            argv, payload, expected, _ = case
            start = time.perf_counter_ns()
            result = subprocess.run([binaries[name], *argv], input=payload, capture_output=True, timeout=30)
            elapsed = (time.perf_counter_ns() - start) / 1_000_000
            if (result.returncode, result.stdout, result.stderr) == (0, expected, b''):
                return elapsed, 'verified'
            if (result.returncode, result.stdout, result.stderr) == (-signal.SIGABRT, b'', STRING_TRAP):
                return elapsed, 'string limit trap'
            raise RuntimeError(f'{name}: bad result ({result.returncode}) {result.stdout[:100]!r} {result.stderr!r}')

        for case, inputs in cases.items():
            for name in compilers:
                if run(name, inputs)[1] != 'verified':
                    raise RuntimeError(f'{name}: could not finish warmup for {case}')
            for _ in range(args.samples):
                order = list(compilers)
                rng.shuffle(order)
                for name in order:
                    elapsed, status = run(name, inputs)
                    if status != 'verified':
                        raise RuntimeError(f'{name}: {status} in timed case {case}')
                    timings[case][name].append(elapsed)
        bulk = data(8192, 'flag=pending')
        bulk_status = {name: run(name, bulk)[1] for name in compilers}
        if bulk_status['after'] != 'verified':
            raise RuntimeError('new runtime could not complete the larger workload')

    report = {
        'scope': 'Awl before/after only; UTF-8 log replacements with exact in/out validation',
        'method': 'Warm whole-process wall time, shuffled pairs; build and Python oracle excluded',
        'host': platform.platform(),
        'cpu': next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                     if line.startswith('model name')), 'unknown'),
        'affinity': sorted(os.sched_getaffinity(0)),
        'cc': subprocess.check_output([args.cc, '--version'], text=True, timeout=15).splitlines()[0],
        'flags': FLAGS + ['-lm'],
        'compiler_sha256': {name: sha256(compiler) for name, compiler in compilers.items()},
        'harness_sha256': sha256(Path(__file__)),
        'source_sha256': sha256(SOURCE),
        'results': {case: {'input_text_bytes': int(cases[case][0][0]), 'matches': cases[case][3],
                           'timing': {name: {'median_ms': statistics.median(samples), 'samples_ms': samples}
                                      for name, samples in samples_by_compiler.items()}}
                    for case, samples_by_compiler in timings.items()},
        'larger_workload_not_timed': {'input_text_bytes': int(bulk[0][0]), 'matches': bulk[3], **bulk_status},
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for case, entry in report['results'].items():
        before, after = (entry['timing'][key]['median_ms'] for key in ('before', 'after'))
        print(f'{case}: {before:.3f} ms before, {after:.3f} ms after ({args.samples} samples)')
    print(f"Larger workload ({bulk[3]} replacements, not timed): {bulk_status}")


if __name__ == '__main__':
    main()

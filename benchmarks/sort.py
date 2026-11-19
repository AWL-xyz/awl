#!/usr/bin/env python3
"""Benchmark the shipped Awl sort app before and after, with exact byte output checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/apps/sort/main.aw'
FLAGS = ['-std=c11', '-O3', '-march=x86-64']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixtures():
    rng = random.Random(9781)
    rows = [f'{rng.randrange(2000):04} event=import user=λ雪 item={rng.randrange(5)}'.encode('utf-8')
            for _ in range(10000)]
    payload = b'\n'.join(rows)
    yield '10000 lines', [], payload, b''.join(row + b'\n' for row in sorted(rows))
    yield '10000 lines, unique', ['--unique'], payload, b''.join(row + b'\n' for row in sorted(set(rows)))
    long_line = b'a' * (1024 * 1024)
    yield '1 MiB line', [], long_line, long_line + b'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-acc', type=Path, required=True)
    parser.add_argument('--before-source', type=Path, required=True, help='old sort main.aw next to its Sort.aw')
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--samples', type=int, default=11)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('benchmark C flags and stdio target Linux x86-64')
    if not 1 <= args.samples <= 100:
        parser.error('--samples must be 1..100')
    builds = {'before': (args.before_acc.resolve(), args.before_source.resolve()),
              'after': (args.acc.resolve(), SOURCE)}
    rng = random.Random(1792026)
    methods, results = {}, {}
    with tempfile.TemporaryDirectory(prefix='awl-sort-bench-') as tmp:
        work = Path(tmp)
        binaries = {}
        for label, (acc, source) in builds.items():
            c, exe = work / f'{label}.c', work / label
            with c.open('wb') as out:
                subprocess.run([acc, 'emit-c', source], stdout=out, check=True, timeout=30)
            subprocess.run([args.cc, *FLAGS, c, '-lm', '-o', exe], check=True, timeout=60)
            binaries[label] = exe
            methods[label] = {'acc_sha256': sha(acc.read_bytes()), 'generated_c_sha256': sha(c.read_bytes()),
                              'binary_sha256': sha(exe.read_bytes()),
                              'source_sha256': {p.name: sha(p.read_bytes()) for p in (source, source.with_name('Sort.aw'))}}

        for case, argv, payload, expected in fixtures():
            def run(label):
                start = time.perf_counter_ns()
                result = subprocess.run([binaries[label], *argv], input=payload, capture_output=True, timeout=30)
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                if (result.returncode, result.stdout, result.stderr) != (0, expected, b''):
                    raise RuntimeError(f'{label}/{case}: incorrect output, exit {result.returncode}, {result.stderr!r}')
                return elapsed_ms

            samples = {label: [] for label in binaries}
            for label in binaries:
                run(label)  # excluded warmup, checked like every timed run
            for _ in range(args.samples):
                order = list(binaries)
                rng.shuffle(order)
                for label in order:
                    samples[label].append(run(label))
            results[case] = {'input_bytes': len(payload), 'input_sha256': sha(payload),
                             'output_bytes': len(expected), 'expected_sha256': sha(expected), 'argv': argv,
                             'timing': {label: {'median_ms': statistics.median(times), 'samples_ms': times}
                                        for label, times in samples.items()}}

    report = {
        'scope': 'Awl sort before/after; same bounded UTF-8 inputs, exact output oracle',
        'method': 'Shuffled warm whole-process wall time through redirected pipes; build and validation excluded',
        'host': platform.platform(),
        'cpu': next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                     if line.startswith('model name')), 'unknown'),
        'affinity': sorted(os.sched_getaffinity(0)),
        'cc': subprocess.check_output([args.cc, '--version'], text=True, timeout=15).splitlines()[0],
        'flags': FLAGS + ['-lm'],
        'harness_sha256': sha(Path(__file__).read_bytes()),
        'builds': methods,
        'results': results,
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for case, entry in results.items():
        before, after = (entry['timing'][side]['median_ms'] for side in builds)
        print(f'{case}: {before:.3f} ms before, {after:.3f} ms after, {before/after:.2f}x ({args.samples} samples)')


if __name__ == '__main__':
    main()

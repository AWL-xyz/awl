#!/usr/bin/env python3
"""Compare emitted Awl slicing and argument parsing before/after runtime changes."""
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
FLAGS = ['-std=c11', '-O3', '-march=x86-64']
SOURCES = {name: ROOT / 'benchmarks/workloads/text-runtime' / f'{name}.aw' for name in ('slice', 'decimal')}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slice_case(text, start, width, jitter, rounds):
    checksums = []
    for offset in range(jitter):
        piece = text[start + offset:start + offset + width].encode('utf-8')
        checksums.append(len(piece) + piece[0] + piece[-1])
    quotient, remainder = divmod(rounds, jitter)
    expected = quotient * sum(checksums) + sum(checksums[:remainder])
    return ('slice', [text, str(start), str(width), str(jitter), str(rounds)], expected,
            {'scalars': len(text), 'bytes': len(text.encode('utf-8')), 'start': start,
             'width': width, 'jitter': jitter, 'iterations': rounds})


def decimal_case(args, rounds):
    values = [int(s) for s in args]
    remainders = [abs(n) % 97 * (-1 if n < 0 else 1) for n in values]
    quotient, remainder = divmod(rounds, len(args))
    expected = quotient * sum(remainders) + sum(remainders[:remainder])
    return ('decimal', [str(rounds), *args], expected, {'inputs': len(args), 'iterations': rounds})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', required=True, type=Path, help='an ACC binary from before the runtime changes')
    p.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    p.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    p.add_argument('--samples', type=int, default=9)
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        p.error('benchmark flags target Linux x86-64')
    if not 1 <= a.samples <= 100:
        p.error('--samples must be 1..100')
    compilers = {'before': a.before.resolve(), 'after': a.acc.resolve()}
    ascii_text = 'timestamp=2026 host=api status=ok ' * 1024
    mixed = 'Abλ🙂\u0301界' * 2048
    rng = random.Random(159)
    long_digits = [rng.randrange(10**18, 2**63) for _ in range(64)]
    cases = {
        'ASCII interior slice': slice_case(ascii_text, len(ascii_text)//2, 48, 256, 4096),
        'mixed UTF-8 tail slice': slice_case(mixed, len(mixed)-200, 32, 97, 4096),
        'mixed UTF-8 wide slice': slice_case(mixed, 8, len(mixed)-128, 63, 4096),
        'mixed UTF-8 front slice': slice_case(mixed, 1, 16, 31, 200000),
        '19-digit arguments': decimal_case([f'{"+-"[i%2]}{n}' for i, n in enumerate(long_digits)], 4000000),
        '1–3 digit arguments': decimal_case(['1', '-20', '+2', '5', '049', '100', '-7', '3'], 4000000),
    }
    records = {}
    with tempfile.TemporaryDirectory(prefix='awl-text-runtime-bench-') as tmp:
        work = Path(tmp)
        binaries = {}
        for phase, compiler in compilers.items():
            for name, source in SOURCES.items():
                generated, exe = work / f'{phase}-{name}.c', work / f'{phase}-{name}'
                with generated.open('wb') as out:
                    subprocess.run([compiler, 'emit-c', source], stdout=out, check=True, timeout=30)
                subprocess.run([a.cc, *FLAGS, generated, '-lm', '-o', exe], check=True, timeout=60)
                binaries[phase, name] = exe

        for label, (name, argv, expected, metadata) in cases.items():
            timings = {phase: [] for phase in compilers}

            def run(phase):
                start = time.perf_counter_ns()
                result = subprocess.run([binaries[phase, name], *argv], capture_output=True, timeout=30)
                ms = (time.perf_counter_ns() - start) / 1_000_000
                if (result.returncode, result.stdout, result.stderr) != (0, f'{expected}\n'.encode(), b''):
                    raise AssertionError(f'{phase} {label}: expected {expected}; got {result!r}')
                return ms

            order = list(compilers)
            for phase in order:
                run(phase)
            for _ in range(a.samples):
                rng.shuffle(order)
                for phase in order:
                    timings[phase].append(run(phase))
            results = {phase: {'median_ms': statistics.median(samples), 'samples_ms': samples}
                       for phase, samples in timings.items()}
            records[label] = {**metadata, 'expected_checksum': expected,
                              'argv_sha256': hashlib.sha256('\0'.join(argv).encode()).hexdigest(), 'timing': results}
            print(f"{label}: {results['before']['median_ms']:.3f} ms before, "
                  f"{results['after']['median_ms']:.3f} ms after ({a.samples} samples)")
    if a.report:
        report = {
            'scope': 'Before/after Awl only: scalar slices and repeated signed-decimal argv conversion',
            'method': 'Warm whole-process wall time, shuffled pairs; compilation and Python oracle excluded',
            'host': platform.platform(),
            'cpu': next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                         if line.startswith('model name')), 'unknown'),
            'affinity': sorted(os.sched_getaffinity(0)),
            'cc': subprocess.check_output([a.cc, '--version'], text=True, timeout=15).splitlines()[0],
            'flags': FLAGS + ['-lm'],
            'compiler_sha256': {phase: sha256(compiler) for phase, compiler in compilers.items()},
            'harness_sha256': sha256(Path(__file__)),
            'workload_sha256': {name: sha256(path) for name, path in SOURCES.items()},
            'results': records,
        }
        a.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Check the generated Awl string.replace runtime against a Unicode oracle (Linux)."""
import argparse
import os
from pathlib import Path
import random
import resource
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'benchmarks/workloads/text-replace/main.aw'


def fixtures():
    yield 'empty input', '', 'x', 'y'
    yield 'absent and longer than input', 'é雪', 'é雪λ', 'x'
    yield 'identical pattern and replacement', 'λ' * 80000, 'λ', 'λ'
    yield 'nonoverlapping and trailing text', 'ababa!', 'aba', 'X'
    yield 'inserted text is not rescanned', 'aaa', 'a', 'aa'
    yield 'delete everything', 'abcabc', 'abc', ''
    yield 'delete with trailing text', 'a雪a', 'a', ''
    yield 'exact UTF-8 without normalization', 'ée\u0301é', 'é', '💡'
    yield 'multiple scalars per match', 'xλ🙂λ🙂z', 'λ🙂', '雪'
    yield 'NULs in data, needle and replacement', 'z\0é\0\r\n', '\0', '\0🙂'
    yield 'newlines in needle', 'aa\r\naa\r\n', '\r\n', '\n'
    yield 'more than the old allocation count limit', 'x' * 80000, 'x', 'é!'
    yield 'dense replacement with deletion', 'z' + 'é' * 80000 + 'λ', 'é', ''
    rng = random.Random(9781)
    alphabet = 'abaλé\u0301🙂雪\0\r\n'
    for i in range(256):
        source = ''.join(rng.choices(alphabet, k=rng.randrange(1, 96)))
        start = rng.randrange(len(source))
        needle = source[start:start + rng.randrange(1, 8)] if i % 2 else ''.join(rng.choices(alphabet, k=3))
        yield f'seeded {i}', source, needle, ''.join(rng.choices(alphabet, k=rng.randrange(10)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function']
    if args.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
    with tempfile.TemporaryDirectory(prefix='awl-text-replace-') as tmp:
        work = Path(tmp)
        generated, exe = work / 'text-replace.c', work / 'text-replace'
        with generated.open('wb') as out:
            subprocess.run([args.acc.resolve(), 'emit-c', SOURCE], stdout=out, check=True, timeout=30)
        subprocess.run([args.cc, *flags, generated, '-lm', '-o', exe], check=True, timeout=60)

        def run(fields):
            encoded = [v.encode('utf-8') for v in fields]
            return subprocess.run([exe, *(str(len(v)) for v in encoded)], input=b''.join(encoded),
                                  capture_output=True, timeout=15)

        count = 0
        for label, source, needle, replacement in fixtures():
            output = source.replace(needle, replacement)
            text = output.encode('utf-8')
            expected = f'{len(output)}\n{len(text)}\n'.encode('ascii') + text + b'\n'
            result = run((source, needle, replacement))
            if (result.returncode, result.stdout, result.stderr) != (0, expected, b''):
                raise AssertionError(f'{label}: expected {expected[:100]!r} ({len(expected)} bytes); '
                                     f'got {result.returncode}, {result.stdout[:100]!r}, {result.stderr!r}')
            count += 1
        for label, fields in [('empty needle', ('text', '', 'x')),
                              ('size overflow of replacement budget', ('x' * 4096, 'x', 'a' * 65536)),
                              ('final result would exceed remaining arena', ('x' * 1024, 'x', 'a' * 65536))]:
            result = run(fields)
            expected = (-signal.SIGABRT, b'', b'Awl string trap: bounds, scalar, I/O, or allocation limit\n')
            if (result.returncode, result.stdout, result.stderr) != expected:
                raise AssertionError(f'{label}: expected string trap; got {result.returncode}, '
                                     f'{result.stdout[:100]!r}, {result.stderr!r}')
            count += 1
    print(f'PASS {count} emitted text-replacement cases' + (' (ASan/UBSan)' if args.sanitize else ''))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Compare all emitted unsigned bit operations with exact Python integers."""
import argparse
import itertools
import os
from pathlib import Path
import random
import re
import resource
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (8, 16, 32, 64)
METHODS = ('and', 'or', 'xor', 'not', 'popcount', 'shl', 'shr', 'rotl', 'rotr')


def source():
    parts = ['@p top: bits.shl(1u8, 7);']
    for width in WIDTHS:
        parts.append(f'func exercise{width}[unit] :: a:u{width}, b:u{width}, n:i64, op:i64 {{')
        for index, method in enumerate(METHODS, 1):
            args = 'a, b' if index <= 3 else 'a' if index <= 5 else 'a, n'
            parts.append(f'    if op == 0 or op == {index} {{ print(bits.{method}({args})); }};')
        parts.append('};')
    parts.append('''func read_word[u64] :: i:i64 {
    return u64.convert(arg.i64(i)) * 4294967296u64 + u64.convert(arg.i64(i + 1));
};
func main {
    @p op: arg.i64(0);
    if op == 0 { print(top); };
    @p i: 1;
    while i < arg.count() {
        @p width: arg.i64(i);
        @p a: read_word(i + 1);
        @p b: read_word(i + 3);
        @p n: arg.i64(i + 5);''')
    for width in WIDTHS:
        parts.append(f'        if width == {width} {{ exercise{width}(u{width}.convert(a), u{width}.convert(b), n, op); }};')
    parts.append('''        i: i + 6;
    };
    return 0;
};''')
    return '\n'.join(parts) + '\n'


def samples(width):
    rng = random.Random(626 + width)
    high = 1 << (width - 1)
    mask = 2 * high - 1
    edges = (0, 1, 2, high - 1, high, high + 1, mask - 1, mask, mask // 3)
    yield from itertools.product(edges, edges, (0, 1, width // 2, width - 1))
    for n in range(width):
        yield rng.getrandbits(width), rng.getrandbits(width), n
    for _ in range(48):
        yield rng.getrandbits(width), rng.getrandbits(width), rng.randrange(width)


def packed(width, a, b, n):
    return tuple(map(str, (width, *divmod(a, 1 << 32), *divmod(b, 1 << 32), n)))


def oracle(width, a, b, n):
    mask = (1 << width) - 1
    return (a & b, a | b, a ^ b, ~a & mask, a.bit_count(), (a << n) & mask, a >> n,
            ((a << n) | (a >> (width - n))) & mask, ((a >> n) | (a << (width - n))) & mask)


def execute(exe, argv, expected, label, code=0, stderr=b''):
    result = subprocess.run([exe, *argv], capture_output=True, timeout=15)
    assert (result.returncode, result.stdout, result.stderr) == (code, expected, stderr), (
        label, result.returncode, result.stdout[:500], result.stderr[:1000], expected[:500])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    acc = args.acc.resolve()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function']
    if args.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                  '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
    with tempfile.TemporaryDirectory(prefix='awl-bits-') as td:
        work = Path(td)
        aw, c, exe = work / 'main.aw', work / 'main.c', work / 'main'
        aw.write_text(source(), encoding='utf-8')
        with c.open('wb') as output:
            subprocess.run([acc, 'emit-c', aw], stdout=output, check=True, timeout=30)
        for opt in ('0', '3'):
            subprocess.run([args.cc, f'-O{opt}', *flags, c, '-lm', '-o', exe], check=True, timeout=60)
            checked, traps = 0, 0
            for width in WIDTHS:
                cases = list(samples(width))
                for start in range(0, len(cases), 64):
                    batch = cases[start:start + 64]
                    argv = list(itertools.chain.from_iterable(packed(width, a, b, n) for a, b, n in batch))
                    values = itertools.chain.from_iterable(oracle(width, a, b, n) for a, b, n in batch)
                    execute(exe, ['0', *argv], ('128\n' + ''.join(f'{v}\n' for v in values)).encode(),
                            f'u{width} batch {start} at -O{opt}')
                    checked += len(batch)
                for op in range(6, 10):
                    for n in (-2**63, -1, width, width + 1, 2**63 - 1):
                        execute(exe, [str(op), *packed(width, (1 << width) - 1, 0, n)], b'',
                                f'u{width} {METHODS[op - 1]}({n}) at -O{opt}',
                                -signal.SIGABRT, b'Awl arithmetic trap\n')
                        traps += 1
            print(f'PASS {checked} input tuples across all 9 bit methods, {traps} count traps at -O{opt}'
                  + (' (ASan/UBSan)' if args.sanitize else ''), flush=True)

        for expression, helper in [('bits.xor(7u32, 1u32)', 'k_bits_xor_u32'), ('3', None)]:
            aw.write_text(f'func main {{ print({expression}); return 0; }};\n', encoding='utf-8')
            code = subprocess.check_output([acc, 'emit-c', aw], timeout=15).decode()
            used = set(re.findall(r'\bk_bits_[a-z0-9_]+(?=\()', code))
            assert used == ({helper} if helper else set()), used
            assert 'k_buffer_new' not in code and 'Awl_STRINGS_RUNTIME' not in code, 'unneeded platform/text runtime'

        rejections = {
            'bits.not(3)': 'requires a u8, u16, u32 or u64 first argument',
            'bits.and(1i8, 1i8)': 'requires a u8, u16, u32 or u64 first argument',
            'bits.popcount(true)': 'requires a u8, u16, u32 or u64 first argument',
            'bits.xor()': 'requires a u8, u16, u32 or u64 first argument',
            'bits.and(1u8, 1u16)': 'invalid platform arguments for bits.and',
            'bits.or(1u32, 2)': 'invalid platform arguments for bits.or',
            'bits.rotl(1u8, 2u8)': 'invalid platform arguments for bits.rotl',
            'bits.shl(1u64, 2.0)': 'invalid platform arguments for bits.shl',
            'bits.shr(1u64)': 'invalid platform arguments for bits.shr',
            'bits.not(1u16, 2u16)': 'invalid platform arguments for bits.not',
            'bits_popcount(0u8)': 'call builtins as namespace.method',
            'bits_xor_u8(0u8, 1u8)': 'call builtins as namespace.method',
        }
        for expression, diagnostic in rejections.items():
            aw.write_text(f'func main {{ print({expression}); return 0; }};\n', encoding='utf-8')
            result = subprocess.run([acc, 'check', aw], capture_output=True, timeout=15)
            assert result.returncode == 1 and diagnostic.encode() in result.stderr, (expression, result)
        print(f'PASS {len(rejections)} rejection cases and selective C emission')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Check emitted i64/u64 overflow helpers against exact Python arithmetic."""
import argparse
import itertools
import operator
import os
from pathlib import Path
import random
import resource
import shlex
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

SOURCE = '''func read_unsigned :: index:i64 {
    return u64.convert(arg.i64(index)) * 4294967296u64 + u64.convert(arg.i64(index + 1));
};
func main {
    @p op: arg.i64(0);
    if op < 3 {
        @p left: arg.i64(1);
        @p right: arg.i64(2);
        if op == 0 { print(left + right); }
        elseif op == 1 { print(left - right); }
        else { print(left * right); };
    } elseif op < 6 {
        @p left: read_unsigned(1);
        @p right: read_unsigned(3);
        if op == 3 { print(left + right); }
        elseif op == 4 { print(left - right); }
        else { print(left * right); };
    } else {
        print(-arg.i64(1));
    };
    return 0;
};
'''


def cases():
    rng = random.Random(83198)
    i_min, i_max, u_max = -(1 << 63), (1 << 63) - 1, (1 << 64) - 1
    signed = (i_min, i_min + 1, -3037000500, -3037000499, -2, -1, 0, 1, 2,
              3037000499, 3037000500, i_max - 1, i_max)
    unsigned = (0, 1, 2, (1 << 32) - 1, 1 << 32, (1 << 32) + 1, i_max, i_max + 1, u_max - 1, u_max)
    for base, low, high, edges in [(0, i_min, i_max, signed), (3, 0, u_max, unsigned)]:
        pairs = list(itertools.product(edges, repeat=2))
        pairs += [(rng.randint(low, high), rng.randint(low, high)) for _ in range(32)]
        for index, op in enumerate([operator.add, operator.sub, operator.mul], base):
            for a, b in pairs:
                values = (a, b) if base == 0 else (*divmod(a, 1 << 32), *divmod(b, 1 << 32))
                result = op(a, b)
                yield [str(x) for x in (index, *values)], result if low <= result <= high else None
    for x in signed:
        yield ['6', str(x)], None if x == i_min else -x


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    samples = list(cases())
    with tempfile.TemporaryDirectory(prefix='awl-checked-arithmetic-') as tmp:
        work = Path(tmp)
        source, generated, exe = [work / name for name in ('main.aw', 'main.c', 'program')]
        source.write_text(SOURCE, encoding='utf-8')
        with generated.open('wb') as out:
            subprocess.run([args.acc.resolve(), 'emit-c', source], stdout=out, check=True, timeout=30)
        for level, mode in itertools.product(('0', '3'), ('default', 'portable')):
            flags = ['-DAWL_PORTABLE_ARITHMETIC'] if mode == 'portable' else []
            subprocess.run([args.cc, '-std=c11', f'-O{level}', '-fsanitize=undefined',
                            '-fno-sanitize-recover=all', *flags, generated, '-lm', '-o', exe],
                           check=True, timeout=60)
            for argv, expected in samples:
                result = subprocess.run([exe, *argv], capture_output=True, text=True, timeout=5)
                want = (-signal.SIGABRT, '', 'Awl arithmetic trap\n') if expected is None else (0, f'{expected}\n', '')
                got = (result.returncode, result.stdout, result.stderr)
                if got != want:
                    raise AssertionError(f'O{level} {mode}, {shlex.join(argv)}: expected {want}, got {got}')
            print(f'PASS {len(samples)} checked arithmetic cases at -O{level} ({mode}, UBSan)', flush=True)


if __name__ == '__main__':
    main()

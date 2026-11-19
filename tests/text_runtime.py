#!/usr/bin/env python3
"""Check emitted UTF-8 slicing, scalar indexing and strict decimal parsing on Linux."""
import argparse
import json
import os
from pathlib import Path
import random
import re
import resource
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MINIMUM, MAXIMUM = -(2**63), 2**63 - 1
STRING_TRAP = b'Awl string trap: bounds, scalar, I/O, or allocation limit\n'
SLICE_SOURCE = '''func main {
    @p size: arg.i64(0);
    @p b: buffer.new(size);
    if b == 0 { return 2; };
    defer buffer.free(b);
    @p got: 0;
    while got < size {
        @p n: stdin.read(b, got, size - got);
        if n <= 0 { return 2; };
        got: got + n;
    };
    @p source: buffer.text(b, 0, size);
    @p index: arg.i64(1);
    if arg.count() == 2 { print(string.codepoint(source, index)); return 0; };
    @p count: arg.i64(2);
    @p part: string.slice(source, index, count);
    print(string.length(part));
    print(string.bytes(part));
    print(part);
    if count > 1 { print(string.slice(part, 1, count - 2)); };
    return 0;
};
'''
ARG_SOURCE = '''func main {
    if arg.i64valid(-1) or arg.i64valid(arg.count()) { return 2; };
    for i in 0..arg.count() {
        if arg.i64valid(i) { print(arg.i64(i)); } else { print(false); };
    };
    return 0;
};
'''


def literal(s):
    return json.dumps(s, ensure_ascii=False).replace('\\u0000', '\\0')


def expect(result, label, stdout=b'', stderr=b'', code=0):
    if (result.returncode, result.stdout, result.stderr) != (code, stdout, stderr):
        raise AssertionError(f'{label}: expected {code}, {stdout[:100]!r}, {stderr!r}; got '
                             f'{result.returncode}, {result.stdout[:100]!r}, {result.stderr!r}')


def slice_cases(exe):
    def run(source, *args):
        payload = source.encode('utf-8')
        return subprocess.run([exe, str(len(payload)), *map(str, args)], input=payload, capture_output=True, timeout=15)

    def check_slice(source, start, count):
        piece = source[start:start + count]
        payload = piece.encode('utf-8')
        expected = f'{count}\n{len(payload)}\n'.encode() + payload + b'\n'
        if count > 1:
            expected += piece[1:-1].encode('utf-8') + b'\n'
        expect(run(source, start, count), f'slice {start}, {count} of {source[:40]!r}', expected)

    checked = 0
    # Exhaust short inputs, including scalar-width transitions and U+0000.
    for source in ('', '\0abc\r\nxyz', 'A\x7f\x80\u07ff\u0800\ud7ff\ue000\uffff\U00010000\U0010ffffe\u0301\0'):
        for start in range(len(source) + 1):
            for count in range(len(source) - start + 1):
                check_slice(source, start, count)
                checked += 1
            if start < len(source):
                expect(run(source, start), f'codepoint {start} of {source!r}', f'{ord(source[start])}\n'.encode())
                checked += 1
    rng = random.Random(159)
    alphabet = 'Abé𐍈🙂\u0301\0雪\r\n'
    for i in range(160):
        source = ''.join(rng.choices(alphabet if i % 2 else 'abc\0\r\n', k=rng.randrange(1, 1025)))
        start = rng.randrange(len(source) + 1)
        check_slice(source, start, rng.randrange(len(source) - start + 1))
        index = rng.randrange(len(source))
        expect(run(source, index), f'seeded codepoint {i}', f'{ord(source[index])}\n'.encode())
        checked += 2
    for source, indices in [('abc', (3,)), ('é🙂', (-1,)), ('', (0,)), ('abc', (-1, 0)),
                            ('aλ🙂', (2, 2)), ('aλ🙂', (1, -1)), ('aλ🙂', (4, 0)),
                            ('aλ🙂', (1, MAXIMUM)), ('abc', (MAXIMUM, MAXIMUM)),
                            ('🙂', (MINIMUM, 0)), ('abc', (0, MINIMUM))]:
        expect(run(source, *indices), f'out of bounds {source!r}, {indices}', stderr=STRING_TRAP, code=-signal.SIGABRT)
        checked += 1
    return checked


def decimal_inputs():
    yield from ['', '+', '-', '0', '+0', '-0', '00', '0001', '+000010', '-00009',
                ' 12', '12 ', '\t3', '3\n', '12\0', '12\0' + '3', '\0' + '8', '1_000',
                '0x10', '1.0', '1e3', '--1', '+-3', '１', '١٢', '−1', '2🙂',
                '18446744073709551615', '18446744073709551616', '9' * 20, '9' * 32,
                '0' * 8192, '+' + '0' * 8192 + str(MAXIMUM), '-0' * 20,
                '-' + '0' * 8192 + str(-MINIMUM), '0' * 8192 + str(MAXIMUM + 1)]
    for edge in (MINIMUM, MAXIMUM, 0, 10**18, -(10**18)):
        for n in range(edge - 3, edge + 4):
            yield str(n)
            yield ('-' if n < 0 else '+') + '0' * 20 + str(abs(n))
    rng = random.Random(159)
    for i in range(500):
        n = rng.randrange(-(2**64), 2**64)
        yield ('-' if n < 0 else '+' if i % 3 == 0 else '') + '0' * rng.randrange(25) + str(abs(n))
        yield ''.join(rng.choices('01234567899+-x\t\n０\0', k=rng.randrange(1, 32)))


def parsed_line(value):
    if re.fullmatch(r'[+-]?[0-9]+', value):
        digits = value.lstrip('+-').lstrip('0') or '0'
        if len(digits) <= 19:
            n = int(digits) * (-1 if value.startswith('-') else 1)
            if MINIMUM <= n <= MAXIMUM:
                return f'{n}\n'.encode()
    return b'false\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    p.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    p.add_argument('--sanitize', action='store_true')
    a = p.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function']
    if a.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                  '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
    with tempfile.TemporaryDirectory(prefix='awl-text-runtime-') as temp:
        work = Path(temp)

        def build(name, source):
            aw, c, exe = (work / f'{name}{suffix}' for suffix in ('.aw', '.c', ''))
            aw.write_text(source, encoding='utf-8')
            with c.open('wb') as out:
                subprocess.run([a.acc.resolve(), 'emit-c', aw], stdout=out, check=True, timeout=30)
            subprocess.run([a.cc, *flags, c, '-lm', '-o', exe], check=True, timeout=90)
            return exe, c.read_text(encoding='utf-8')

        exe, _ = build('slice', SLICE_SOURCE)
        slices = slice_cases(exe)
        values = list(decimal_inputs())
        text = 'func show[unit] :: s:text { if string.i64valid(s) { print(string.toi64(s)); } else { print(false); }; };\nfunc main {\n'
        text += ''.join(f'    show(string.slice({literal("λ" + s + "!")}, 1, {len(s)}));\n' for s in values)
        exe, c = build('text', text + '    return 0;\n};\n')
        assert 'k_program_argc' not in c, 'text parsing must not pull in argv support'
        expect(subprocess.run([exe], capture_output=True, timeout=15), 'text decimal inputs', b''.join(map(parsed_line, values)))

        values_argv = [s for s in values if '\0' not in s]
        exe, c = build('argv', ARG_SOURCE)
        assert '#define Awl_STRINGS_RUNTIME' not in c, 'argv-only integers must not pull in the string runtime'
        expect(subprocess.run([exe, *values_argv], capture_output=True, timeout=15), 'argv decimal inputs',
               b''.join(map(parsed_line, values_argv)))
        exe, c = build('count', 'func main { return arg.count(); };')
        assert 'static inline bool k_decimal_i64(' not in c, 'arg.count should not emit the decimal parser'
        expect(subprocess.run([exe], capture_output=True, timeout=15), 'arg.count without decimal parser')

        traps = 0
        exe, _ = build('text_trap', r'func main { return string.toi64("12\0"); };')
        expect(subprocess.run([exe], capture_output=True, timeout=15), 'decimal text trap',
               stderr=b'Awl string trap: invalid signed integer\n', code=-signal.SIGABRT)
        traps += 1
        exe, _ = build('arg_trap', 'func main { return arg.i64(0); };')
        for argv in ([], ['-9223372036854775809'], ['0\n']):
            expect(subprocess.run([exe, *argv], capture_output=True, timeout=15), f'decimal arg trap {argv!r}',
                   stderr=b'Awl argument trap: index or signed integer\n', code=-signal.SIGABRT)
            traps += 1

        wrong = work / 'wrong.aw'
        for method, args in [('i64valid', ''), ('i64valid', '"1", "2"'), ('toi64', '12'), ('toi64', 'false')]:
            wrong.write_text(f'func main {{ print(string.{method}({args})); return 0; }};')
            result = subprocess.run([a.acc.resolve(), 'check', wrong], capture_output=True, timeout=15)
            assert result.returncode == 1 and f'invalid platform arguments for string.{method}'.encode() in result.stderr, result
    print(f'PASS {slices} slice/codepoint cases, {len(values)} text and {len(values_argv)} argv decimal cases, '
          f'{traps} decimal traps, 4 type rejections and runtime selection' + (' (ASan/UBSan)' if a.sanitize else ''))


if __name__ == '__main__':
    main()

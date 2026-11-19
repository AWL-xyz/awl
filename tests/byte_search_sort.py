#!/usr/bin/env python3
"""Check emitted byte search and the shipped sort utility on Linux x86-64."""
import argparse
import os
from pathlib import Path
import random
import resource
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SORT = ROOT / 'examples/apps/sort/main.aw'
MAX_INPUT = 1024 * 1024

PROBE = '''func main {
    @p size: arg.i64(0);
    @p b: buffer.new(size);
    if b == 0 { return 9; };
    @p offset: 0;
    while offset < size {
        @p n: stdin.read(b, offset, size - offset);
        if n <= 0 { return 2; };
        offset: offset + n;
    };
    @p stale: arg.count() == 5;
    if stale { buffer.free(b); };
    print(buffer.findbyte(b, arg.i64(1), arg.i64(2), u8.convert(arg.i64(3))));
    if not stale { buffer.free(b); };
    return 0;
};
'''

# Force successful short writes even on a blocking stdout. No changes to the
# emitted C or assertions about the kernel's pipe size are needed.
SHORT_WRITE = '''#include <unistd.h>
ssize_t __real_write(int fd, const void *data, size_t count);
ssize_t __wrap_write(int fd, const void *data, size_t count) {
    if (fd == STDOUT_FILENO && count > 4096) count = 4096;
    return __real_write(fd, data, count);
}
'''


def expect(label, result, code=0, stdout=b'', stderr=b''):
    if (result.returncode, result.stdout, result.stderr) != (code, stdout, stderr):
        raise AssertionError(f'{label}: expected exit {code}, {len(stdout)} stdout bytes '
                             f'{stdout[:100]!r}, stderr {stderr!r}; got {result.returncode}, '
                             f'{len(result.stdout)} stdout bytes {result.stdout[:100]!r}, {result.stderr!r}')


def check_search(executable):
    cases = [(b'', 0, 0, 0), (b'a', 1, 0, 97), (b'\x00\x00', 0, 2, 0),
             (b'aa\xff\xff', 2, 2, 255), (b'abca', 1, 2, 97), (b'abca', 1, 3, 97),
             (b'x' * MAX_INPUT, 1, MAX_INPUT - 1, 0)]
    rng = random.Random(9781)
    for i in range(128):
        data = rng.randbytes(rng.randrange(1, 1025))
        start = rng.randrange(len(data))
        count = rng.randrange(1, len(data) - start + 1)
        needle = data[start + rng.randrange(count)] if i % 2 else rng.randrange(256)
        cases.append((data, start, count, needle))

    def run(data, start, count, needle, *extra):
        return subprocess.run([executable, str(len(data)), str(start), str(count), str(needle), *extra],
                              input=data, capture_output=True, timeout=15)

    for i, (data, start, count, needle) in enumerate(cases):
        wanted = data.find(bytes([needle]), start, start + count)
        expect(f'byte-search case {i}', run(data, start, count, needle), stdout=f'{wanted}\n'.encode())
    invalid = [(-1, 0), (0, -1), (3, 0), (1, 2), (2, 1), (1, 2**63 - 1), (2**63 - 1, 2**63 - 1)]
    trap = b'Awl resource trap: invalid handle, bounds, or argument\n'
    for start, count in invalid:
        expect(f'invalid range {start}, {count}', run(b'xx', start, count, 0), -signal.SIGABRT, stderr=trap)
    expect('stale handle with empty range', run(b'xx', 0, 0, 0, 'stale'), -signal.SIGABRT, stderr=trap)
    return len(cases) + len(invalid) + 1


def check_sort(executable):
    fixtures = [b'', b'one', b'one\n', b'\n', b'\n\n', b'b\n\na\nb', b'a\r\nb\na\r\n',
                '雪\nJosé\ne\u0301\né\n\x00aa\n\x00aa\n🙂\n'.encode(),
                b'z\na\n\x00b\na\n' * 2048, b'\n' * 32768, 'é'.encode() * (MAX_INPUT // 2)]
    for i, data in enumerate(fixtures):
        # Split on LF only; no spurious row after a terminal LF.
        rows = data.split(b'\n')
        if rows[-1] == b'':
            rows.pop()
        for unique in (False, True):
            expected = b''.join(row + b'\n' for row in sorted(set(rows) if unique else rows))
            args = ['--unique'] if unique else []
            result = subprocess.run([executable, *args], input=data, capture_output=True, timeout=15)
            expect(f'ksort case {i}, unique={unique}', result, stdout=expected)
    invalid = [(b'good\n\xff\n', [], b'input must be utf-8'),
               (b'x' * (MAX_INPUT + 1), [], b'input exceeds 1 MiB'),
               (b'\n' * 32769, [], b'allocation failure or more than 32768 lines'),
               (b'', ['--wrong'], b'usage: ksort [--unique]')]
    for data, args, message in invalid:
        result = subprocess.run([executable, *args], input=data, capture_output=True, timeout=15)
        expect(message.decode(), result, 2, stderr=b'ksort: ' + message + b'\n')
    with open('/dev/full', 'wb') as output:
        result = subprocess.run([executable], input=b'newline', stdout=output, stderr=subprocess.PIPE, timeout=15)
    if (result.returncode, result.stderr) != (3, b''):
        raise AssertionError(f'ksort must fail on a write error, got {result.returncode}, {result.stderr!r}')
    return 2 * len(fixtures) + len(invalid) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    acc = args.acc.resolve()
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function']
    if args.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                  '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
    with tempfile.TemporaryDirectory(prefix='awl-byte-search-sort-') as tmp:
        work = Path(tmp)
        probe, wrapper = work / 'probe.aw', work / 'short_write.c'
        probe.write_text(PROBE, encoding='utf-8')
        wrapper.write_text(SHORT_WRITE, encoding='utf-8')
        sort = work / 'ksort'
        search = work / 'search'
        for source, binary, link in [(probe, search, []), (SORT, sort, [wrapper, '-Wl,--wrap=write'])]:
            generated = binary.with_suffix('.c')
            with generated.open('wb') as out:
                subprocess.run([acc, 'emit-c', source], stdout=out, check=True, timeout=30)
            subprocess.run([args.cc, *flags, generated, *link, '-lm', '-o', binary], check=True, timeout=60)
        bad = work / 'wrong-type.aw'
        bad.write_text('func main { return buffer.findbyte(0, 0, 0, 10u16); };', encoding='utf-8')
        rejected = subprocess.run([acc, 'check', bad], capture_output=True, timeout=15)
        if rejected.returncode != 1 or b"buffer.findbyte: expected ['i64', 'i64', 'i64', 'u8']" not in rejected.stderr:
            raise AssertionError(f'wrong needle type not diagnosed: {rejected!r}')
        print(f'PASS {check_search(search)} byte-search cases, 1 type rejection, and {check_sort(sort)} sort cases'
              + (' (ASan/UBSan)' if args.sanitize else ''))


if __name__ == '__main__':
    main()

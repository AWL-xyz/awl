#!/usr/bin/env python3
"""Install the CSV Package and check generated native programs against Python on Linux."""
import argparse
import csv
import io
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages/csv'
DEMO = ROOT / 'examples/csv-demo'
PROBE = '''use csv;

func main {
    @p size: arg.i64(0);
    @p b: buffer.new(size);
    if b == 0 { return 2; };
    defer buffer.free(b);
    @p offset: 0;
    while offset < size {
        @p got: stdin.read(b, offset, size - offset);
        if got <= 0 { return 2; };
        offset: offset + got;
    };
    @s fields vector<text>: vector.new<text>(0);
    @s rows vector<i64>: vector.new<i64>(0);
    @p result: csv.parse(buffer.text(b, 0, size), fields, rows);
    print(result.code);
    print(result.offset);
    print(vector.length(fields));
    print(vector.length(rows));
    if result.code != 0 or arg.count() > 1 { return 0; };
    -- The encoder's own limit must still apply with a larger output spool.
    @s output spool: spool.new(1048580);
    if not spool.valid(output) { return 4; };
    if not csv.encode(fields, rows, output) {
        if spool.bytes(output) != 0 { return 4; };
        return 3;
    };
    return spool.print(output);
};
'''


def encode(rows, quote=csv.QUOTE_ALL, newline='\n'):
    output = io.StringIO(newline='')
    csv.writer(output, quoting=quote, lineterminator=newline).writerows(rows)
    return output.getvalue()


def invoke(exe, *args, payload=b''):
    return subprocess.run([exe, *args], input=payload, capture_output=True, timeout=15)


def require(result, label, stdout=b'', stderr=b'', status=0):
    got = (result.returncode, result.stdout, result.stderr)
    if got != (status, stdout, stderr):
        raise AssertionError(f'{label}: expected status {status}, stdout {stdout[:120]!r}, stderr {stderr!r}; '
                             f'got {got[0]}, {got[1][:120]!r}, {got[2][:120]!r}')


def fixtures():
    yield 'empty document', '', []
    yield 'blank records', '\n\r\n', [[''], ['']]
    yield 'trailing empty fields', ',,\r\n,', [['', '', ''], ['', '']]
    yield 'just one quoted empty field', '""', [['']]
    yield 'spaces are significant, no header rules', ' a ,  b\n\t', [[' a ', '  b'], ['\t']]
    yield 'escape and CR/LF inside quotes', '"λ,""💡""\r\n\r\n",x', [['λ,"💡"\r\n\r\n', 'x']]
    yield 'CR and LF inside quotes', '"a\rb\nc"\r\n', [['a\rb\nc']]
    yield 'NUL and BOM retained', '\ufeffé\0,雪\n"𐍈\0"', [['\ufeffé\0', '雪'], ['𐍈\0']]
    rng = random.Random(159)
    alphabet = 'aλ🙂雪\u0301\r\n, "\t\0'
    for i in range(320):
        rows = [[''.join(rng.choices(alphabet, k=rng.randrange(24))) for _ in range(rng.randrange(1, 13))]
                for _ in range(rng.randrange(1, 9))]
        quote = csv.QUOTE_ALL if i % 2 else csv.QUOTE_MINIMAL
        # Generate each record using CRLF so QUOTE_MINIMAL also quotes bare CR.
        # Independently vary each record separator, including a final EOF.
        encoded = [encode([row], quote, '\r\n')[:-2] for row in rows]
        source = ''.join(value + (rng.choice(['\n', '\r\n']) if j + 1 < len(rows) or i % 3 else '')
                         for j, value in enumerate(encoded))
        expected = list(csv.reader(io.StringIO(source, newline=''), strict=True))
        assert expected == rows, (source, rows, expected)
        yield f'seeded table {i}', source, expected


def check_tables(exe):
    def probe(source, encode_result=True):
        payload = source.encode('utf-8')
        return invoke(exe, str(len(payload)), *([] if encode_result else ['parse-only']), payload=payload)

    def valid(label, source, rows):
        counts = f'0\n{len(source)}\n{sum(map(len, rows))}\n{len(rows)}\n'
        require(probe(source), label, (counts + encode(rows) + '\n').encode('utf-8'))

    good = 0
    for label, source, rows in fixtures():
        valid(label, source, rows)
        good += 1
    valid('8192 fields exactly', ',' * 8191, [[''] * 8192])
    valid('4096 rows exactly', '\n' * 4096, [['']] * 4096)
    require(probe('é' * 524288, False), '1 MiB input exactly', b'0\n524288\n1\n1\n')
    full = 'a' * (1048576 - 3)
    valid('1 MiB encoded output exactly', full, [[full]])
    require(probe(full + 'a'), 'encoder limit despite extra spool capacity', b'0\n1048574\n1\n1\n', status=3)
    good += 4
    failures = [
        ('unquoted quote', 'a"b', 1, 1),
        ('spaces before a quote', ' "b"', 1, 1),
        ('spaces after a quote', '"b" ', 1, 3),
        ('astral scalar after a quote', '"雪"🌞', 1, 3),
        ('unterminated quote', '"b', 1, 2),
        ('unterminated escaped quote', '"b""', 1, 4),
        ('unterminated quoted CR', '"\r', 1, 2),
        ('bare CR', 'a\rb', 1, 1),
        ('bare CR at end', '""\r', 1, 2),
        ('bare CR before comma', '"a"\r,\n', 1, 3),
        ('CRCRLF', 'x\r\r\n', 1, 1),
        ('late quote with rows to roll back', 'ok\nλ,abc"', 1, 8),
        ('more than 1 MiB', 'é' * 524288 + 'x', 2, -1),
        ('more than 8192 fields', ',' * 8192, 2, 8192),
        ('more than 4096 rows', '\n' * 4097, 2, 4096),
    ]
    for label, source, code, offset in failures:
        require(probe(source), label, f'{code}\n{offset}\n0\n0\n'.encode())
    return good, len(failures)


def check_demo(exe):
    source = (DEMO / 'orders.csv').read_bytes()
    require(invoke(exe, payload=source), 'shipped orders sample', b'Orders: 3\nTotal quantity: 15\n')
    require(invoke(exe, payload=b'item,quantity\r\n'), 'header only', b'Orders: 0\nTotal quantity: 0\n')
    require(invoke(exe, payload=b'item,quantity\nx,1000000000\ny,1000000000\nz,1000000000'), 'sum above i32',
            b'Orders: 3\nTotal quantity: 3000000000\n')
    failures = [
        (b'', 'expected item,quantity header'),
        (b'quantity,item\nx,1\n', 'expected item,quantity header'),
        (b'item,quantity\nx\n', 'each order must have two fields'),
        (b'item,quantity\nx,1,2', 'each order must have two fields'),
        (b'item,quantity\nx,1\0', 'quantity must be a signed decimal integer'),
        (b'item,quantity\nx,9223372036854775808', 'quantity must be a signed decimal integer'),
        (b'item,quantity\nx,-1\n', 'quantity must be 0..1000000000'),
        (b'item,quantity\nx,1000000001\n', 'quantity must be 0..1000000000'),
        (b'item,quantity\n"x', 'CSV error 1 at scalar offset 16'),
        (b'\xff', 'input must be UTF-8'),
        (b'x' * 1048577, 'input exceeds 1 MiB'),
    ]
    for source, message in failures:
        require(invoke(exe, payload=source), message, stderr=f'csv-demo: {message}\n'.encode(), status=2)
    return 3 + len(failures)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    p.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    p.add_argument('--sanitize', action='store_true')
    a = p.parse_args()
    acc, cc = a.acc.resolve(), shutil.which(a.cc)
    if not cc:
        p.error('a host C compiler is required')
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function']
    if a.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                  '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
    with tempfile.TemporaryDirectory(prefix='awl-csv-') as tmp:
        work = Path(tmp)
        awl = work / 'awl'
        awl.symlink_to(acc)
        target = work / 'Orders'
        target.mkdir()
        subprocess.run([awl, 'init', 'Orders'], cwd=target, stdout=subprocess.DEVNULL, check=True, timeout=15)
        subprocess.run([awl, 'add', PACKAGE / 'csv.awpkg'], cwd=target, stdout=subprocess.DEVNULL, check=True, timeout=15)
        installed = target / 'packages/csv'
        vendored = DEMO / 'packages/csv'
        assert sorted(p.name for p in installed.iterdir()) == ['csv.aw', 'csv.awpkg']
        for file in installed.iterdir():
            assert file.read_bytes() == (PACKAGE / file.name).read_bytes() == (vendored / file.name).read_bytes()
        for name in ('main.aw', 'Orders.test.aw'):
            shutil.copy2(DEMO / name, target / name)
        (target / 'probe.aw').write_text(PROBE)

        def build(name):
            generated, exe = work / f'{name}.c', work / name
            with generated.open('wb') as out:
                subprocess.run([acc, 'emit-c', target / f'{name}.aw'], stdout=out, check=True, timeout=30)
            subprocess.run([cc, *flags, generated, '-lm', '-o', exe], check=True, timeout=60)
            return exe

        good, bad = check_tables(build('probe'))
        demo = check_demo(build('main'))
        require(invoke(build('Orders.test')), 'shipped Awl CSV tests')
        selected = subprocess.run([awl, 'test', '--cc', str(Path(cc).absolute()), '--filter', 'Orders'],
                                  cwd=target, capture_output=True, timeout=60)
        require(selected, 'toolkit test of installed Package',
                b'Testing Orders.test.aw\nPASS Orders.test.aw\nTest result: 1 passed, 0 failed\n')
    print(f'PASS {good} CSV tables, {bad} grammar/limit rejections, {demo} CLI cases, '
          'Awl tests and local Package vendoring' + (' (ASan/UBSan emitted programs)' if a.sanitize else ''))


if __name__ == '__main__':
    main()

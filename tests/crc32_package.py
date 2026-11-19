#!/usr/bin/env python3
"""Verify the offline CRC-32 Package and streaming demo against Python zlib."""
import argparse
import os
from pathlib import Path
import random
import resource
import shutil
import signal
import subprocess
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages/crc32'
DEMO = ROOT / 'examples/crc32-demo'
RESOURCE_TRAP = b'Awl resource trap: invalid handle, bounds, or argument\n'
PROBE = '''use crc32 as crc;

func main {
    @p size: arg.i64(0);
    @p offset: arg.i64(1);
    @p count: arg.i64(2);
    @p step: arg.i64(3);
    @p initial: crc.start();
    if step < 0 {
        @p stale: buffer.new(0);
        if stale == 0 { return 2; };
        buffer.free(stale);
        print(crc.update(initial, stale, offset, count));
        return 0;
    };
    @p bytes: buffer.new(size);
    if bytes == 0 { return 2; };
    defer buffer.free(bytes);
    @p used: 0;
    while used < size {
        @p got: stdin.read(bytes, used, size - used);
        if got <= 0 { return 2; };
        used: used + got;
    };
    print(crc.finish(crc.update(initial, bytes, offset, count)));
    @p state: initial;
    @p until: offset + count;
    @p i: offset;
    while i < until {
        @p n: step;
        if n > until - i { n: until - i; };
        state: crc.update(state, bytes, i, n);
        i: i + n;
    };
    print(crc.finish(state));
    return 0;
};
'''


def require(result, label, stdout=b'', stderr=b'', status=0):
    actual = (result.returncode, result.stdout, result.stderr)
    expected = (status, stdout, stderr)
    assert actual == expected, (label, actual, expected)


def execute(exe, *argv, payload=b''):
    return subprocess.run([exe, *map(str, argv)], input=payload, capture_output=True, timeout=15)


def package_cases(exe):
    def compare(data, offset, count, chunk):
        expected = zlib.crc32(data[offset:offset + count])
        require(execute(exe, len(data), offset, count, chunk, payload=data),
                f'{len(data)}-byte buffer, range ({offset}, {count}), chunk {chunk}', f'{expected}\n{expected}\n'.encode())

    binary = bytes(range(256))
    good = 0
    for i in range(256):
        compare(binary, i, 1, 1)
        good += 1
    for data in (b'', b'123456789', b'\0\xff\xc0\x80', binary, binary[::-1] * 9):
        for offset, count in ((0, 0), (len(data), 0), (0, len(data))):
            compare(data, offset, count, 1)
            good += 1
    rng = random.Random(32026)
    for _ in range(96):
        data = rng.randbytes(rng.randrange(4097))
        offset = rng.randrange(len(data) + 1)
        compare(data, offset, rng.randrange(len(data) - offset + 1), rng.randrange(1, 65))
        good += 1

    invalid = [(-1, 0, 1), (4, 0, 1), (0, -1, 1), (3, 1, 1), (2, 2, 1),
               (1, 2**63 - 1, 1), (2**63 - 1, 2**63 - 1, 1), (-2**63, 0, 1),
               (0, -2**63, 1), (0, 0, -1)]  # last case uses a freed handle
    for offset, count, step in invalid:
        require(execute(exe, 3, offset, count, step, payload=b'abc'), f'invalid range or handle ({offset}, {count}, {step})',
                stderr=RESOURCE_TRAP, status=-signal.SIGABRT)
    return good, len(invalid)


def cli_cases(exe, work):
    block = bytes(range(256)) * 256
    payloads = [b'', b'123456789', b'123456789\r\n', b'\xff\0\xfe\xc0', block[:-1], block, block + b'\0',
                block * 3 + b'\xff\x80\xaa', block * 257]  # last input is larger than the runtime's max single buffer
    for data in payloads:
        require(execute(exe, payload=data), f'checksum of {len(data)} bytes', f'{zlib.crc32(data):08x}\n'.encode())
    require(execute(exe, 'FILE'), 'stdin-only usage', stderr=b'usage: crc32-demo < FILE\n', status=2)
    directory = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = subprocess.run([exe], stdin=directory, capture_output=True, timeout=15)
        require(result, 'read error', stderr=b'crc32-demo: input read failed\n', status=3)
    finally:
        os.close(directory)
    with open('/dev/full', 'wb') as full:
        result = subprocess.run([exe], input=b'123456789', stdout=full, stderr=subprocess.PIPE, timeout=15)
        assert (result.returncode, result.stderr) == (3, b'crc32-demo: output write failed\n'), result
    return len(payloads) + 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    acc, cc = args.acc.resolve(), shutil.which(args.cc)
    if not cc:
        parser.error('a host C compiler is required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function']
    if args.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                  '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
    with tempfile.TemporaryDirectory(prefix='awl-crc32-') as td:
        work = Path(td)
        awl, project = work / 'awl', work / 'CRCCheck'
        awl.symlink_to(acc)
        project.mkdir()
        subprocess.run([awl, 'init', 'CRCCheck'], cwd=project, stdout=subprocess.DEVNULL, check=True, timeout=15)
        subprocess.run([awl, 'add', PACKAGE / 'crc32.awpkg'], cwd=project, stdout=subprocess.DEVNULL, check=True, timeout=15)
        installed = project / 'packages/crc32'
        vendored = DEMO / 'packages/crc32'
        assert sorted(p.name for p in installed.iterdir()) == ['crc32.aw', 'crc32.awpkg']
        for file in installed.iterdir():
            assert file.read_bytes() == (PACKAGE / file.name).read_bytes() == (vendored / file.name).read_bytes(), file.name
        for name in ('main.aw', 'Checksum.test.aw'):
            shutil.copy2(DEMO / name, project / name)
        (project / 'probe.aw').write_text(PROBE, encoding='utf-8')

        def build(name):
            c_file, exe = work / f'{name}.c', work / name
            with c_file.open('wb') as out:
                subprocess.run([acc, 'emit-c', project / f'{name}.aw'], stdout=out, check=True, timeout=30)
            subprocess.run([cc, *flags, c_file, '-lm', '-o', exe], check=True, timeout=60)
            return exe

        good, bad = package_cases(build('probe'))
        cli = cli_cases(build('main'), work)
        require(execute(build('Checksum.test')), 'Awl checksum regressions')
        suite = subprocess.run([awl, 'test', '--cc', str(Path(cc).absolute())], cwd=project, capture_output=True, timeout=60)
        require(suite, 'toolkit test of installed Package',
                b'Testing Checksum.test.aw\nPASS Checksum.test.aw\nTest result: 1 passed, 0 failed\n')
        demo = subprocess.run([awl, 'run', 'crc32-demo', '--cc', str(Path(cc).absolute())], cwd=DEMO.parent,
                              input=b'123456789', capture_output=True, timeout=60)
        require(demo, 'toolkit run of shipped project', b'cbf43926\n')
    print(f'PASS {good} CRC-32 range/chunk cases against zlib, {bad} range/handle traps, {cli} CLI cases, '
          'Awl tests and local Package vendoring' + (' (ASan/UBSan emitted programs)' if args.sanitize else ''))


if __name__ == '__main__':
    main()

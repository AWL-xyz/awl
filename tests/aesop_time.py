#!/usr/bin/env python3
"""Awl local time Package: checked clocks, deadlines, sleeps and native execution."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time as host_time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROGRAM = '''use time;

func main[i64] {
    @p started: time.now();
    @p stamp: time.wall();
    @p ok: time.sleep(20);
    @p elapsed: time.elapsed(started);
    @p future: time.deadline(10000);
    print(time.now() >= 0);
    print(stamp);
    print(ok);
    print(elapsed >= 1);
    print(future > started);
    print(time.remaining(future) > 0);
    print(time.expired(started));
    print(time.sleep(-1) == false);
    print(time.sleep(600001) == false);
    print(time.remaining(-1) == 0);
    print(time.elapsed(-1) == 0);
    print(time.deadline(9223372036854775807) == 9223372036854775807);
    return 0;
};
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    acc = args.acc.resolve()
    records = []

    def run(argv, **kw):
        return subprocess.run([str(x) for x in argv], capture_output=True, text=True, timeout=60, **kw)

    def expect(ok, label, detail=None):
        assert ok, (label, detail)
        records.append({'case': label, 'status': 'PASS'})

    platform = (ROOT / 'compiler/native/platform.inc').read_text()
    wall_helper = (ROOT / 'compiler/native/wallclock.inc').read_text()
    expect('k_wall_clock_millis' not in platform and 'k_wall_clock_millis' in wall_helper,
           'new wall-clock helper is isolated from legacy generated C')
    expect('CLOCK_REALTIME' in wall_helper and 'GetSystemTimePreciseAsFileTime' in wall_helper,
           'wall-clock helper has POSIX/WASI and Windows source paths')

    with tempfile.TemporaryDirectory(prefix='aesop-time-', dir='/var/tmp') as td:
        stub = Path(td) / 'windows-syntax.c'
        source = (ROOT / 'compiler/native/wallclock.c').read_text()
        stub.write_text('''#include <stdint.h>
#include <stdlib.h>
typedef struct { unsigned int dwLowDateTime, dwHighDateTime; } FILETIME;
typedef union { struct { unsigned int LowPart, HighPart; }; uint64_t QuadPart; } ULARGE_INTEGER;
static void GetSystemTimePreciseAsFileTime(FILETIME *p) { p->dwLowDateTime=0; p->dwHighDateTime=0; }
static _Noreturn void k_resource_trap(void) { abort(); }
#define _WIN32 1
''' + source + '\nint main(void) { return (int)k_wall_clock_millis(); }\n')
        syntax = subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsyntax-only', stub],
                                capture_output=True, text=True, timeout=60)
        expect(syntax.returncode == 0,
               'Windows helper branch passes C11 source syntax with stubbed Win32 types', syntax.stderr)
        work = Path(td)
        package = work / 'packages/time'
        package.mkdir(parents=True)
        for name in ['time.aw', 'time.awpkg']:
            source = ROOT / 'packages/time' / name
            target = package / name
            shutil.copy2(source, target)
            expect(target.read_bytes() == source.read_bytes(), 'installed Package file is byte-identical: ' + name)
        (work / 'main.aw').write_text(PROGRAM)
        emitted = run([acc, 'emit-c', 'main.aw'], cwd=work)
        expect(emitted.returncode == 0, 'compiler checks and emits the Package program', emitted.stderr)
        c = work / 'main.c'
        c.write_text(emitted.stdout)
        generated_c = emitted.stdout
        expect('k_wall_clock_millis' in generated_c, 'wall-clock helper appears only in generated programs that use it')

        bad = work / 'bad.aw'
        bad.write_text('func main[i64] { @p x: clock.wall(1); return x; };\n')
        rejected = run([acc, 'check', 'bad.aw', '--diagnostic-format', 'json'], cwd=work)
        expect(rejected.returncode == 1 and json.loads(rejected.stderr)['diagnostics'],
               'wall-clock intrinsic rejects wrong arity with a diagnostic', rejected.stderr)

        def validate(output, label):
            lines = output.splitlines()
            expect(len(lines) == 12 and lines[0] == 'true', label + ': bool outputs', lines)
            wall = int(lines[1])
            delta = abs(wall - int(host_time.time() * 1000))
            expect(delta <= 5000, label + ': UTC wall clock agrees with host', delta)
            expect(all(line == 'true' for line in lines[2:]), label + ': monotonic, deadline and sleep checks', lines)
            return delta

        flags = []
        exe = work / 'program'
        compiled = run(['cc', '-std=c11', '-O2', c, '-lm', '-o', exe], cwd=work)
        expect(compiled.returncode == 0, 'generated native program compiles', compiled.stderr)
        result = run([exe], cwd=work)
        expect(result.returncode == 0, 'generated native program executes', result.stderr)
        normal_delta = validate(result.stdout, 'native')
        sanitized_delta = None
        if args.sanitize:
            flags = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
            sanitized = work / 'program-sanitized'
            compiled = run(['cc', '-std=c11', '-O2', *flags, c, '-lm', '-o', sanitized], cwd=work)
            expect(compiled.returncode == 0, 'generated program compiles with ASan/UBSan', compiled.stderr)
            result = run([sanitized], cwd=work)
            expect(result.returncode == 0, 'generated program executes with ASan/UBSan', result.stderr)
            sanitized_delta = validate(result.stdout, 'sanitized')

        demo = ROOT / 'examples/time-demo'
        demo_check = run([acc, 'check', 'main.aw'], cwd=demo)
        expect(demo_check.returncode == 0, 'shipped time-demo passes native compiler check', demo_check.stderr)

    sources = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'compiler/native').iterdir())
               if p.suffix in ('.cpp', '.h', '.inc', '.c')}
    report = {
        'status': 'PASS', 'syntax': 'Aesop', 'scope': __doc__,
        'acc_sha256': sha(acc), 'harness_sha256': sha(Path(__file__)),
        'native_sources_sha256': sources,
        'package_sources_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'packages/time').iterdir())},
        'demo_sources_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'examples/time-demo').rglob('*')) if p.is_file()},
        'generated_c_sha256': hashlib.sha256(generated_c.encode()).hexdigest(),
        'native_programs_executed': 1, 'sanitized_programs_executed': 1 if args.sanitize else 0,
        'sanitize': args.sanitize, 'wall_clock_delta_ms': normal_delta,
        'sanitized_wall_clock_delta_ms': sanitized_delta, 'records': records,
        'limits': 'Linux host-native generated C execution, wall-clock delta and source-level Windows helper only, not complete SDK or native Windows acceptance'
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS local time Package:', len(records), 'checks,', report['native_programs_executed'],
          'native program,', report['sanitized_programs_executed'], 'sanitized program')


if __name__ == '__main__':
    main()

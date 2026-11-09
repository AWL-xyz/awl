#!/usr/bin/env python3
"""Aesop-only declaration, CLI, starter and generated-native execution checks"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--sanitize-programs', action='store_true')
    args = parser.parse_args()
    acc = args.acc.resolve()
    records = []
    def run(argv, **kw):
        return subprocess.run([str(x) for x in argv], capture_output=True, text=True, timeout=30, **kw)
    with tempfile.TemporaryDirectory(prefix='aesop-') as td:
        work = Path(td)
        positives = {
            'inferred requested vector signature': ('func size :: @b values[i64], etc[i64] { return vector_length(values) + vector_length(etc); }; func main { @s a vector<i64>: vector.new<i64>(0); @p b vector<i64>: vector.new<i64>(0); vector.push(a,7); print(size(a,b)); vector.free(b); return 0; };', '1\n'),
            'inferred branch results': ('func choose :: flag:bool { if flag { return 7; } else { return 9; }; }; func main { print(choose(false)); return 0; };', '9\n'),
            'inferred argument-independent text and bool': ('func describe :: x:i64 { return "Awl"; }; func compare :: x:i64, y:i64 { return x<y; }; func main { print(describe(1)); print(compare(1,2)); return 0; };', 'Awl\ntrue\n'),
            'forward inferred call chain': ('func main { print(first()); return 0; }; func first { return second(); }; func second { return 42; };', '42\n'),
            'inferred local and nested result': ('func main { @p func helper :: n:i64 { @p result: n+2; return result; }; print(helper(40)); return 0; };', '42\n'),
            'inferred aggregate and f64': ('struct Pair { x:i64; }; func pair { return Pair(42); }; func fraction { return 1.5; }; func main { @p p: pair(); print(p.x); print(fraction()); return 0; };', '42\n1.5\n'),
            'annotated recursion breaks inference cycle': ('func even[bool] :: n:i64 { if n==0 { return true; }; return odd(n-1); }; func odd :: n:i64 { if n==0 { return false; }; return even(n-1); }; func main { print(even(4)); return 0; };', 'true\n'),
            'requested vector signature': ('func size[i64] :: @b values[i64], etc[i64] { return vector_length(values) + vector_length(etc); }; func main[i64] { @s a vector<i64>: vector.new<i64>(0); @p b vector<i64>: vector.new<i64>(0); vector.push(a, 7); print(size(a,b)); vector.free(b); return 0; };', '1\n'),
            'scalar and f64 result': ('func add[f64] :: x:f64, y:f64 { return x+y; }; func main[i64] { print(add(1.5,2)); return 0; };', '3.5\n'),
            'owned vector result': ('func make[@o vector<i64>] { @s v vector<i64>: vector.new<i64>(0); vector.push(v,42); return move v; }; func main[i64] { @s v vector<i64>: make(); print(vector.get(v,0)); return 0; };', '42\n'),
            'implicit and explicit unit': ('func one { print(1); return; }; func two[unit] { print(2); return; }; func main[i64] { one(); two(); return 0; };', '1\n2\n'),
            'fixed array result': ('func pair[[i64;2]] { return [3,4]; }; func main[i64] { @p a: pair(); print(a[1]); return 0; };', '4\n'),
            'nested helper': ('func main[i64] { @p func answer[i64] { return 42; }; print(answer()); return 0; };', '42\n'),
            'text and bool result': ('func text_value[text] { return "Awl"; }; func truth[bool] { return true; }; func main[i64] { print(text_value()); print(truth()); return 0; };', 'Awl\ntrue\n'),
        }
        for label, (source, expected) in positives.items():
            path = work / 'main.aw'; path.write_text(source)
            emitted = run([acc, 'emit-c', path]); assert emitted.returncode == 0, (label, emitted.stderr)
            c = work / 'main.c'; c.write_text(emitted.stdout)
            exe = work / 'program'
            flags = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie'] if args.sanitize_programs else []
            compiled = run(['cc', '-std=c11', '-O2', *flags, c, '-lm', '-o', exe]); assert compiled.returncode == 0, (label, compiled.stderr)
            result = run([exe]); assert result.returncode == 0 and result.stdout == expected, (label, result)
            records.append({'case': label, 'status': 'PASS', 'output': result.stdout})
        rejected = [
            'func main: i64 { return 0; };',
            'func f :: x:i64: i64 { return x; }; func main[i64] { return 0; };',
            'function main()->i64 return 0 end',
            'func main() -> i64 { return 0; };',
            'func main[i64] return 0; end;',
            'func main[] { return 0; };',
            'func main[i64 { return 0; };',
            'func main[i64]][bool] { return 0; };',
            'func main[@b i64] { return 0; };',
            'func main[@o i64] { return 0; };',
            'func main[unit] { return 0; };',
            'func main[i64] { local x:i64=0; return x; };',
            'func main[i64] { if true then return 0; end; return 1; };',
            'func main[i64] { @p x: 0; x=1; return x; };',
            'func main[i64] { return 0 };',
            'func main[i64] { return 0; }',
            'func main { if true { return 1; } else { return false; }; };',
            'func main { if true { return; } else { return 1; }; };',
            'func main { if true { return 1; }; };',
            'func main { return main(); };',
            'func first { return second(); }; func second { return first(); }; func main { return first(); };',
            'func value { if true { return 1; } else { return 1.5; }; }; func main { return 0; };',
            'func make { @s b spool: spool.new(4); return move b; }; func main { return 0; };',
            'func make { return spool.new(4); }; func main { return 0; };',
            'func f :: b:bool { if b { return 1; } else { return 1u64; }; }; func main { return 0; };',
            'func main { return false; };',
            'func main[i64] { return "wrong"; };',

        ]
        for source in rejected:
            path = work / 'main.aw'; path.write_text(source)
            result = run([acc, 'check', path, '--diagnostic-format', 'json'])
            assert result.returncode == 1, (source, result)
            assert json.loads(result.stderr)['diagnostics'], result.stderr
        records.append({'case': 'retired syntax, malformed headers and invalid results rejected', 'count': len(rejected), 'status': 'PASS'})
        path = work / 'main.aw'
        path.write_text('func main { return fn_0(); }; '+ ' '.join('func fn_'+str(i)+' { return '+('fn_'+str(i+1)+'()' if i<499 else '0')+'; };' for i in range(500)))
        result = run([acc, 'check', path]); assert result.returncode == 0, result.stderr
        records.append({'case': '500-function inferred forward chain without recursive dependency traversal', 'status': 'PASS'})
        (work / 'Library.aw').write_text('exports{@r func answer { return 42; };};')
        path.write_text('use Library.aw as lib; func main { print(lib.answer()); return 0; };')
        result = run([acc, 'emit-c', path]); assert result.returncode == 0, result.stderr
        records.append({'case': 'cross-module exported return inference', 'status': 'PASS'})
        path = work / 'main.aw'; path.write_text('func main[i64] { return 0; };')
        for syntax, code in [('aesop', 0), ('next', 2), ('legacy', 2)]:
            result = run([acc, 'check', path, '--syntax', syntax]); assert result.returncode == code, result
        records.append({'case': 'only --syntax aesop is accepted', 'status': 'PASS'})
        awl = work / 'awl'; awl.symlink_to(acc)
        project = work / 'project'; project.mkdir()
        result = run([awl, 'init', 'Demo'], cwd=project); assert result.returncode == 0, result.stderr
        assert 'syntax: aesop' in (project / 'Demo.awproj').read_text()
        result = run([acc, 'check', project / 'main.aw']); assert result.returncode == 0, result.stderr
        package = work / 'package'; package.mkdir()
        result = run([awl, 'init', '--pkg', 'Greeting'], cwd=package); assert result.returncode == 0, result.stderr
        assert 'func hello :: who:text' in (package / 'Greeting.aw').read_text()
        assert 'syntax: aesop' in (package / 'Greeting.awpkg').read_text()
        records.append({'case': 'project and local Package starters use Aesop', 'status': 'PASS'})
        for old in ['next', 'legacy']:
            manifest = project / 'Demo.awproj'
            manifest.write_text('format: 1\nentry: main.aw\nsyntax: '+old+'\n')
            result = run([awl, 'build'], cwd=project)
            assert result.returncode != 0 and 'manifest syntax must be aesop' in result.stderr, result
        records.append({'case': 'retired manifest syntaxes rejected before backend invocation', 'status': 'PASS'})
    library_path = acc.parent / 'Awllex.so'
    if library_path.is_file():
        lib = C.CDLL(str(library_path))
        assert lib.Awl_parse_abi_version() == 2 and lib.Awl_lex_abi_version() == 2
        lib.Awl_parse_source.argtypes = [C.c_char_p, C.c_size_t, C.POINTER(C.c_void_p)]
        lib.Awl_parse_free.argtypes = [C.c_void_p]
        lib.Awl_diagnostic_count.argtypes = [C.c_void_p]
        lib.Awl_check_unit.argtypes = [C.c_void_p]
        for source, good in [(b'func main[i64] { return 0; };', True),
                             (b'func main { return 0; };', True),
                             (b'func main: i64 { return 0; };', False),
                             (b'function main()->i64 return 0 end', False)]:
            unit = C.c_void_p()
            assert lib.Awl_parse_source(source, len(source), C.byref(unit)) == 0 and unit
            try:
                assert (lib.Awl_diagnostic_count(unit) == 0) == good
                if good:
                    assert lib.Awl_check_unit(unit) == 0
            finally:
                lib.Awl_parse_free(unit)
        for name in ['Awl_parse_file_next', 'Awl_lex_next', 'Awl_lex_project']:
            assert not hasattr(lib, name), 'retired dialect export remains'
        records.append({'case': 'Aesop-only byte-source ABI v2 and removed dialect exports', 'status': 'PASS'})
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((ROOT / 'compiler/native').iterdir()) if p.suffix in ('.cpp', '.h', '.inc', '.c')}
    report = {'status': 'PASS', 'syntax': 'Aesop', 'scope': __doc__, 'acc_sha256': hashlib.sha256(acc.read_bytes()).hexdigest(),
              'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'native_sources_sha256': sources, 'native_programs_executed': len(positives), 'generated_program_sanitizers': args.sanitize_programs, 'records': records}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    print('PASS Aesop declarations:', len(positives), 'executed native programs,', len(rejected), 'rejections, CLI and starters')
if __name__ == '__main__':
    main()

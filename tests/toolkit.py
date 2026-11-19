#!/usr/bin/env python3
"""End-to-end tests of the source-built toolkit on Linux x86-64, without an SDK."""
import argparse
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


def limit_file_size(size):
    def apply():
        # Let write() return an error after a short write rather than exiting on SIGXFSZ.
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (size, size))
    return apply


class ToolkitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prefix = tempfile.TemporaryDirectory(prefix='awl-toolkit-')
        cls.addClassCleanup(prefix.cleanup)
        bin_dir = Path(prefix.name) / 'bin'
        bin_dir.mkdir()
        # The default backend is discovered relative to the real executable.
        # Use a copy so this test works even if the supplied ACC has a full SDK.
        cls.driver = Path(shutil.copy2(cls.acc, bin_dir / 'acc'))
        cls.awl = bin_dir / 'AwL'
        cls.awl.symlink_to('acc')

    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix='awl-work-')
        self.addCleanup(work.cleanup)
        self.work = Path(work.name).resolve()
        self.project = self.work / 'owl project'
        self.project.mkdir()
        self.temp = self.work / 'private temp'
        self.temp.mkdir()
        self.env = {**os.environ, 'TMPDIR': str(self.temp), 'CC': self.cc}

    def invoke(self, *args, code=0, cwd=None, exe=None, stdin=None, preexec_fn=None):
        result = subprocess.run([exe or self.awl, *args], cwd=cwd or self.project,
                                env=self.env, input=stdin, capture_output=True,
                                text=True, encoding='utf-8', timeout=30,
                                preexec_fn=preexec_fn)
        self.assertEqual(result.returncode, code, (args, result.stdout, result.stderr))
        return result

    def init(self):
        self.invoke('InIt', 'Demo')
        return self.project / 'main.aw'

    def assert_no_temps(self):
        self.assertEqual(list(self.temp.iterdir()), [])
        self.assertEqual(list(self.work.rglob('.Awl-output-*')), [])

    def test_starter_check_run_and_build(self):
        help_text = self.invoke('--help').stdout
        self.assertIn('awl check', help_text)
        self.assertIn('awl run', help_text)
        self.init()
        self.assertIn('checked (native frontend)', self.invoke('ChEcK').stdout)
        self.assertEqual(self.invoke('RuN', '--cc', self.cc).stdout, 'Hello from Awl!\n')
        self.assertFalse((self.project / 'build').exists())
        out = self.project / 'build' / 'Demo'
        self.assertEqual(self.invoke('BuIlD', '--cc', self.cc, '-O', '0').stdout, f'{out}\n')
        self.assertEqual(self.invoke(exe=out).stdout, 'Hello from Awl!\n')
        self.assert_no_temps()

    def test_new_project_runs_and_never_overwrites(self):
        self.assertIn('awl new', self.invoke('--help').stdout)
        starter = self.project / 'Demo_2'
        self.assertIn('with a starter test', self.invoke('NeW', starter.name).stdout)
        before = {p.name: p.read_bytes() for p in starter.iterdir()}
        self.assertEqual(set(before), {'Demo_2.awproj', 'App.aw', 'main.aw', 'Smoke.test.aw', '.gitignore'})
        self.assertEqual(before['.gitignore'], b'/build/\n')
        self.invoke('check', starter.name)
        self.assertEqual(self.invoke('run', starter.name, '--cc', self.cc).stdout, 'Hello, Awl!\n')
        self.assertEqual(self.invoke('test', '--list', cwd=starter).stdout, 'Smoke.test.aw\n')
        self.assertIn('1 passed, 0 failed', self.invoke('test', starter.name, '--cc', self.cc).stdout)
        self.assertIn('refusing to overwrite', self.invoke('new', starter.name, code=2).stderr)
        self.assertEqual({p.name: p.read_bytes() for p in starter.iterdir()}, before)
        self.assert_no_temps()

    def test_new_rejects_unsafe_names_and_existing_paths(self):
        for name in ('', '../escape', 'foo.bar', '_hidden', 'Con', 'LPT9', 'a' * 65):
            with self.subTest(name=name):
                self.assertIn('usage: awl new', self.invoke('new', name, code=2).stderr)
        self.assertIn('usage: awl new', self.invoke('new', 'Demo', '--pkg', code=2).stderr)
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertFalse((self.work / 'escape').exists())
        outside = self.work / 'outside'
        outside.mkdir()
        file = self.project / 'file'
        file.write_bytes(b'keep')
        (self.project / 'link').symlink_to(outside, target_is_directory=True)
        (self.project / 'dangling').symlink_to(outside / 'missing', target_is_directory=True)
        for name in ('file', 'link', 'dangling'):
            self.assertIn('refusing to overwrite', self.invoke('new', name, code=2).stderr)
        self.assertEqual(file.read_bytes(), b'keep')
        self.assertEqual(list(outside.iterdir()), [])

    def test_new_rolls_back_after_partial_write(self):
        result = self.invoke('new', 'Demo', code=2, preexec_fn=limit_file_size(128))
        self.assertIn('cannot write', result.stderr)
        self.assertIn('Smoke.test.aw', result.stderr)
        self.assertEqual(list(self.project.iterdir()), [])
        self.invoke('new', 'Demo')
        self.invoke('test', 'Demo', '--check')

    def test_add_package_from_starter(self):
        source = self.init()
        package = self.work / 'greeting source λ'
        package.mkdir()
        self.invoke('init', 'Greeting', '--pkg', cwd=package)
        manifest = package / 'Greeting.awpkg'
        library = package / 'Greeting.aw'
        source.write_text('use Greeting; func main { print(Greeting.hello(arg.text(0))); return 0; };')
        self.assertIn('not installed', self.invoke('check', code=1).stderr)
        self.assertIn('awl add', self.invoke('--help').stdout)
        self.assertIn('Added Package Greeting', self.invoke('AdD', manifest).stdout)
        installed = self.project / 'packages' / 'Greeting'
        self.assertEqual((installed / manifest.name).read_bytes(), manifest.read_bytes())
        self.assertEqual((installed / library.name).read_bytes(), library.read_bytes())
        library.write_text('upstream changes must not touch the vendored copy')
        self.assertIn('refusing to overwrite', self.invoke('add', manifest, code=2).stderr)
        self.invoke('check')
        self.assertEqual(self.invoke('run', '--cc', self.cc, '--', 'Ada λ').stdout, 'Hello, Ada λ!\n')
        self.assert_no_temps()

    def test_add_package_with_nested_module_and_nested_project_entry(self):
        self.init()
        src = self.project / 'src'
        src.mkdir()
        (self.project / 'Demo.awproj').write_text('format: 1\nentry: src/main.aw\n')
        (src / 'main.aw').write_text('use test-tools as tools; func main { print(tools.answer()); return 0; };')
        package = self.work / 'tools'
        helper = package / 'support'
        helper.mkdir(parents=True)
        manifest = package / 'test-tools.awpkg'
        manifest.write_bytes(b'# local package\r\nformat : 1\r\nkind: package\r\nname: test-tools\r\nentry: API.aw\r\n')
        (package / 'API.aw').write_text('use support/Detail.aw as detail; exports { @r func answer { return detail.one(); }; };')
        (helper / 'Detail.aw').write_text('exports { @r func one { return 1; }; };')
        (helper / 'notes.txt').write_text('not source')
        (package / 'build').mkdir()
        (package / 'build' / 'generated.aw').write_text('not packaged')
        # Resolve a relative manifest path while still selecting the project here.
        self.invoke('add', Path('..') / 'tools' / manifest.name)
        installed = src / 'packages' / 'test-tools'
        self.assertEqual({p.relative_to(installed).as_posix() for p in installed.rglob('*') if p.is_file()},
                         {'test-tools.awpkg', 'API.aw', 'support/Detail.aw'})
        self.assertFalse((self.project / 'packages').exists())
        self.assertEqual(self.invoke('run', '--cc', self.cc).stdout, '1\n')
        # Package imports use the same manifest parser, including key validation.
        with (installed / manifest.name).open('ab') as out:
            out.write(b'format: 1\n')
        diagnostic = json.loads(self.invoke('check', '--diagnostic-format', 'json', code=1).stderr)['diagnostics'][0]
        self.assertEqual(diagnostic['code'], 'E300')
        self.assertIn('duplicate Package manifest key', diagnostic['message'])
        self.assert_no_temps()

    def test_add_package_rejects_invalid_manifests_and_source_preflight(self):
        self.init()
        package = self.work / 'local package'
        package.mkdir()
        manifest = package / 'Local.awpkg'
        source = package / 'Local.aw'
        source.write_text('exports { @r func answer { return 42; }; };')
        valid = 'format: 1\nkind: package\nname: Local\n'
        attempts = [
            (valid + 'name: Other\n', 'duplicate Package manifest key'),
            (valid.replace('name: Local', 'name: Other'), 'must declare'),
            (valid + 'entry: ../Local.aw\n', 'plain .aw file name'),
            (valid + 'entry: local.aw\n', 'missing or wrong-case Package entry'),
            (valid + 'entry: C:Local.aw\n', 'plain .aw file name'),
            (valid + 'entry: file?.aw\n', 'plain .aw file name'),
            (valid + 'entry: nul.extra.aw\n', 'plain .aw file name'),
            (valid + 'entry: LPT¹.aw\n', 'plain .aw file name'),
            (valid + '#\x00\n', 'NUL byte'),
            (valid + '#' * 16384, 'file exceeds the size budget'),
        ]
        for contents, message in attempts:
            with self.subTest(message=message):
                manifest.write_text(contents, encoding='utf-8')
                self.assertIn(message, self.invoke('add', manifest, code=2).stderr)
                self.assertFalse((self.project / 'packages').exists())
        manifest.write_text(valid)
        source.write_bytes(b'a' * (1024 * 1024 + 1))
        self.assertIn('file exceeds the size budget', self.invoke('add', manifest, code=2).stderr)
        self.assertFalse((self.project / 'packages').exists())
        source.unlink()
        os.mkfifo(source)
        self.assertIn('regular non-symlink file', self.invoke('add', manifest, code=2).stderr)
        self.assertFalse((self.project / 'packages').exists())

    def test_add_package_rolls_back_after_partial_write(self):
        self.init()
        package = self.work / 'rollback source'
        package.mkdir()
        self.invoke('init', 'Local', '--pkg', cwd=package)
        manifest = package / 'Local.awpkg'
        library = package / 'Local.aw'
        library.write_bytes(library.read_bytes() + b' ' * 2048)
        packages = self.project / 'packages'

        limited = limit_file_size(1024)
        result = self.invoke('add', manifest, code=2, preexec_fn=limited)
        self.assertIn('cannot write', result.stderr)
        self.assertFalse(packages.exists())

        packages.mkdir()
        previous = packages / 'Previous'
        previous.mkdir()
        sentinel = previous / 'Previous.aw'
        sentinel.write_text('previous source')
        result = self.invoke('add', manifest, code=2, preexec_fn=limited)
        self.assertIn('cannot write', result.stderr)
        self.assertEqual(list(packages.iterdir()), [previous])
        self.assertEqual(sentinel.read_text(), 'previous source')
        self.invoke('add', manifest)
        self.assertEqual((packages / 'Local' / library.name).read_bytes(), library.read_bytes())

    def test_add_package_does_not_follow_symlinks(self):
        source = self.init()
        package = self.work / 'link source'
        package.mkdir()
        self.invoke('init', 'Link', '--pkg', cwd=package)
        manifest = package / 'Link.awpkg'
        external = self.work / 'outside'
        external.mkdir()
        (external / 'do-not-touch').write_text('original')
        alternate = package / 'Sibling.aw'
        alternate.symlink_to(external / 'do-not-touch')
        self.assertIn('contains a symlink', self.invoke('add', manifest, code=2).stderr)
        alternate.unlink()
        packages = self.project / 'packages'
        packages.symlink_to(external, target_is_directory=True)
        self.assertIn('packages must be a real directory', self.invoke('add', manifest, code=2).stderr)
        packages.unlink()
        packages.mkdir()
        (packages / 'Link').symlink_to(external, target_is_directory=True)
        self.assertIn('refusing to overwrite', self.invoke('add', manifest, code=2).stderr)
        self.assertEqual(list(external.iterdir()), [external / 'do-not-touch'])
        self.assertEqual((external / 'do-not-touch').read_text(), 'original')
        # Manually created links do not allow the compiler to load a manifest
        # outside the entry's source tree either.
        shutil.copy2(manifest, external)
        shutil.copy2(package / 'Link.aw', external)
        source.write_text('use Link; func main { print(Link.hello("test")); return 0; };')
        self.assertIn('package manifest escapes project root', self.invoke('check', code=1).stderr)

    def test_named_project_and_imported_diagnostics(self):
        src = self.project / 'src'
        src.mkdir()
        (self.project / 'Demo.awproj').write_text('format: 1\nentry: src/start.aw\n')
        (src / 'start.aw').write_text('use Lib.aw as lib; func main { print(lib.answer()); return 0; };')
        lib = src / 'Lib.aw'
        lib.write_text('exports { @r func answer { return 42; }; };')
        self.invoke('check', 'Demo', cwd=self.work)
        self.assertEqual(self.invoke('run', 'Demo', '--cc', self.cc, cwd=self.work).stdout, '42\n')
        self.assertFalse((self.project / 'build').exists())
        self.invoke('check', 'demo', cwd=self.work, code=2)
        lib.write_text('exports { @r func answer[i64] { return false; }; };')
        rejected = self.invoke('check', 'Demo', '--diagnostic-format', 'json', cwd=self.work, code=1)
        self.assertEqual(rejected.stdout, '')
        self.assertEqual(Path(json.loads(rejected.stderr)['diagnostics'][0]['file']), lib)
        self.assert_no_temps()

    def test_project_tests_share_import_root_and_receive_eof(self):
        self.init()
        src = self.project / 'src'
        src.mkdir()
        # The project entry itself is not part of the suite, even with this name.
        (self.project / 'Demo.awproj').write_text('format: 1\nentry: src/main.test.aw\n')
        (src / 'main.test.aw').write_text('func main { return 99; };')
        (src / 'Measure.aw').write_text('exports { @r func length { return 7; }; };')
        (self.project / 'fixture.txt').write_bytes(b'fixture')
        package = self.work / 'library'
        package.mkdir()
        self.invoke('init', 'Greeting', '--pkg', cwd=package)
        self.invoke('add', package / 'Greeting.awpkg')

        (src / 'Z.test.aw').write_text('func main { print("last"); return 0; };')
        (src / '.ignored.test.aw').write_text('not parsed')
        (src / 'ignored.TEST.aw').write_text('not parsed')
        name = 'A with spaces λ.test.aw'
        (src / name).write_text('''use Measure.aw as measure;
            use Greeting;
            func main {
                @p f: file.open("fixture.txt",0);
                if f < 0 { return 3; };
                @p length: file.size(f);
                if file.close(f) != 0 or length != measure.length() { return 4; };
                @p b: buffer.new(1);
                if b == 0 { return 5; };
                defer buffer.free(b);
                if stdin.read(b,0,1) != 0 or arg.count() != 0 { return 6; };
                print(Greeting.hello("Awl"));
                return 0;
            };''', encoding='utf-8')
        host = self.work / 'cc with input check'
        host.write_text('#!/bin/sh\nif IFS= read -r line; then exit 99; fi\n'
                        f'exec {shlex.quote(self.cc)} "$@"\n')
        host.chmod(0o700)
        for directory, args in [(self.project, ()), (self.work, ('Demo',))]:
            with self.subTest(cwd=directory):
                result = self.invoke('TeSt', *args, '--cc', host, cwd=directory, stdin='unread\n')
                self.assertEqual(result.stderr, '')
                self.assertEqual(result.stdout.splitlines(), [
                    f'Testing {name}', 'Hello, Awl!', f'PASS {name}',
                    'Testing Z.test.aw', 'last', 'PASS Z.test.aw', 'Test result: 2 passed, 0 failed'])
        self.assertFalse((self.project / 'build').exists())
        self.assert_no_temps()

    def test_shipped_testing_example(self):
        result = self.invoke('test', 'testing', '--cc', self.cc, cwd=ROOT / 'examples')
        self.assertEqual(result.stdout.splitlines(), ['Testing Totals.test.aw', 'PASS Totals.test.aw',
                         'Test result: 1 passed, 0 failed'])
        self.assertEqual(result.stderr, '')
        self.assert_no_temps()

    def test_explicit_test_file_needs_no_project(self):
        (self.work / 'fixture.txt').write_text('relative to caller')
        source = self.project / 'one.aw'
        source.write_text('''func main {
            @p f: file.open("fixture.txt",0);
            if f < 0 { return 1; };
            return file.close(f);
        };''')
        result = self.invoke('test', source, '--cc', self.cc, cwd=self.work)
        self.assertEqual(result.stdout.splitlines(), ['Testing one.aw', 'PASS one.aw', 'Test result: 1 passed, 0 failed'])
        self.assertEqual(result.stderr, '')
        self.assert_no_temps()

    def test_tests_report_failures_and_continue(self):
        self.init()
        sources = {'A.test.aw': 'func main { return 124; };',
                   'B.test.aw': 'func main[i64] { return false; };',
                   'C.test.aw': 'func main { return 130; };',
                   'Z.test.aw': 'func main { return 0; };'}
        for name, text in sources.items():
            (self.project / name).write_text(text)
        result = self.invoke('test', '--cc', self.cc, '--diagnostic-format', 'json', code=1)
        self.assertEqual(result.stdout.splitlines(), [
            'Testing A.test.aw', 'FAIL A.test.aw (status 124)',
            'Testing B.test.aw', 'FAIL B.test.aw (status 1)',
            'Testing C.test.aw', 'FAIL C.test.aw (status 130)',
            'Testing Z.test.aw', 'PASS Z.test.aw', 'Test result: 1 passed, 3 failed'])
        report = json.loads(result.stderr)
        self.assertEqual(Path(report['file']), self.project / 'B.test.aw')
        self.assertTrue(report['diagnostics'])
        self.assert_no_temps()

    def test_list_and_filter_tests_without_loading_source(self):
        self.init()
        names = ['A smoke λ.test.aw', 'B smoke.test.aw', 'Z Smoke.test.aw']
        for name in reversed(names):
            (self.project / name).write_text('this cannot compile')
        (self.project / '.Hidden smoke.test.aw').touch()
        for cwd, args in [(self.project, ()), (self.work, ('Demo',))]:
            self.assertEqual(self.invoke('test', *args, '--list', cwd=cwd).stdout.splitlines(), names)
            listed = self.invoke('test', *args, '--filter', 'smoke', '--list', cwd=cwd)
            self.assertEqual(listed.stdout.splitlines(), names[:2])
            self.assertEqual(listed.stderr, '')
        (self.project / names[0]).write_text('func main { return 0; };')
        selected = self.invoke('test', '--filter', 'λ', '--cc', self.cc)
        self.assertEqual(selected.stdout.splitlines(), [f'Testing {names[0]}', f'PASS {names[0]}',
                                                        'Test result: 1 passed, 0 failed'])
        self.assertEqual(selected.stderr, '')
        self.assertEqual(self.invoke('test', names[1], '--list', '--filter', 'smoke').stdout, names[1] + '\n')
        none = self.invoke('test', '--filter', 'SMOKE', '--list', code=2)
        self.assertIn('no tests match --filter', none.stderr)
        self.assertEqual(none.stdout, '')
        self.assert_no_temps()

    def test_check_only_and_failure_cutoff(self):
        self.init()
        (self.project / 'A.test.aw').write_text('func main { print("must not run"); return 9; };')
        bad = self.project / 'B.test.aw'
        bad.write_text('func main[i64] { return false; };')
        (self.project / 'C.test.aw').write_text('func main { return 0; };')
        check = self.invoke('test', '--check', '--diagnostic-format', 'json', code=1)
        self.assertEqual([line for line in check.stdout.splitlines() if 'native frontend' not in line], [
            'Checking A.test.aw', 'PASS A.test.aw', 'Checking B.test.aw', 'FAIL B.test.aw (status 1)',
            'Checking C.test.aw', 'PASS C.test.aw', 'Test result: 2 passed, 1 failed'])
        self.assertEqual(Path(json.loads(check.stderr)['file']), bad)
        stopped = self.invoke('test', '--check', '--fail-fast', code=1)
        self.assertNotIn('C.test.aw', stopped.stdout)
        self.assertIn('Test result: 1 passed, 1 failed, 1 skipped', stopped.stdout)
        cutoff = self.invoke('test', '--cc', self.cc, '--fail-fast', code=1)
        self.assertEqual(cutoff.stdout.splitlines(), ['Testing A.test.aw', 'must not run',
                         'FAIL A.test.aw (status 9)', 'Test result: 0 passed, 1 failed, 2 skipped'])
        self.assertEqual(cutoff.stderr, '')
        self.assertFalse((self.project / 'build').exists())
        self.assert_no_temps()

    def test_test_mode_option_errors(self):
        self.init()
        (self.project / 'A.test.aw').touch()
        for opts, message in [
            (('--list', '--check'), 'cannot be combined'),
            (('--list', '--fail-fast'), 'cannot be combined'),
            (('--check', '--cc', self.cc), 'requires building and running tests'),
            (('--list', '-O', '0'), 'requires building and running tests'),
            (('--check', '--run-timeout', '5'), 'requires building and running tests'),
            (('--check', '--build-timeout', '5'), 'requires building and running tests'),
            (('--list', '--build-memory-mib', '512'), 'requires building and running tests'),
            (('--list', '--list'), 'duplicate option'),
            (('--filter', ''), 'nonempty filename substring'),
            (('--filter',), 'missing value'),
            (('--filter', 'A', '--filter', 'B'), 'duplicate option'),
        ]:
            with self.subTest(opts=opts):
                rejected = self.invoke('test', *opts, code=2)
                self.assertIn(message, rejected.stderr)
                self.assertEqual(rejected.stdout, '')
        for flag in ('--list', '--check', '--fail-fast', '--filter'):
            self.assertIn('unknown run option', self.invoke('run', flag, code=2).stderr)
        self.assert_no_temps()

    def test_test_discovery_errors_do_not_run_anything(self):
        self.init()
        self.assertIn('awl test', self.invoke('--help').stdout)
        empty = self.invoke('test', code=2)
        self.assertIn('no .test.aw files', empty.stderr)
        self.assertEqual(empty.stdout, '')

        good = self.project / 'A.test.aw'
        good.write_text('func main { print("must not run"); return 0; };')
        unsafe = self.project / 'Z.test.aw'
        for form in ('symlink', 'directory', 'FIFO'):
            with self.subTest(form=form):
                if form == 'symlink':
                    unsafe.symlink_to(good)
                elif form == 'directory':
                    unsafe.mkdir()
                else:
                    os.mkfifo(unsafe)
                rejected = self.invoke('test', '--cc', self.cc, code=2)
                self.assertIn('test must be a regular non-symlink file', rejected.stderr)
                self.assertIn(unsafe.name, rejected.stderr)
                self.assertEqual(rejected.stdout, '')
                filtered = self.invoke('test', '--filter', 'A', '--list', code=2)
                self.assertIn(unsafe.name, filtered.stderr)
                self.assertEqual(filtered.stdout, '')
                if form == 'directory':
                    unsafe.rmdir()
                else:
                    unsafe.unlink()
        for index in range(64):
            (self.project / f'file{index}.test.aw').touch()
        overflow = self.invoke('test', '--cc', self.cc, code=2)
        self.assertIn('test discovery exceeds 64', overflow.stderr)
        self.assertEqual(overflow.stdout, '')
        self.assert_no_temps()

    def test_test_timeout_does_not_stop_the_suite(self):
        self.init()
        slow = self.project / 'A.test.aw'
        slow.write_text('func main { clock.sleep(5000); return 0; };')
        (self.project / 'Z.test.aw').write_text('func main { return 0; };')
        result = self.invoke('test', '--cc', self.cc, '--run-timeout', '1', code=1)
        self.assertIn('program wall-time limit exceeded', result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['Testing A.test.aw', 'TIMEOUT A.test.aw',
                         'Testing Z.test.aw', 'PASS Z.test.aw', 'Test result: 1 passed, 1 failed'])
        stopped = self.invoke('test', '--cc', self.cc, '--run-timeout', '1', '--fail-fast', code=1)
        self.assertEqual(stopped.stdout.splitlines(), ['Testing A.test.aw', 'TIMEOUT A.test.aw',
                         'Test result: 0 passed, 1 failed, 1 skipped'])
        backend = self.work / 'sleeping backend'
        backend.write_text('#!/bin/sh\nexec /bin/sleep 5\n')
        backend.chmod(0o700)
        result = self.invoke('test', slow, '--cc', backend, '--build-timeout', '1', code=1)
        self.assertIn('backend wall-time limit exceeded', result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['Testing A.test.aw', 'TIMEOUT A.test.aw',
                         'Test result: 0 passed, 1 failed'])
        self.assert_no_temps()

    def test_test_cancellation_stops_suite_and_cleans_up(self):
        self.init()
        (self.project / 'A.test.aw').write_text('''func main {
            @p marker: file.open("ready",1);
            if marker < 0 { return 2; };
            if file.close(marker) != 0 { return 3; };
            clock.sleep(15000);
            return 0;
        };''')
        (self.project / 'Z.test.aw').write_text('func main { return 0; };')
        with subprocess.Popen([self.awl, 'test', '--cc', self.cc], cwd=self.project, env=self.env,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding='utf-8') as process:
            try:
                ready = self.project / 'ready'
                deadline = time.monotonic() + 10
                while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists(), 'first test did not start')
                process.send_signal(signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)
        self.assertEqual(process.returncode, 128 + signal.SIGTERM, (stdout, stderr))
        self.assertEqual(stdout.splitlines(), ['Testing A.test.aw', 'INTERRUPTED A.test.aw'])
        self.assertIn('run interrupted', stderr)
        self.assert_no_temps()

    def test_run_forwards_arguments_and_exit_code(self):
        source = self.project / 'with spaces λ.aw'
        source.write_text('''func main {
            print(arg.count());
            for i in 0..arg.count() { print(arg.text(i)); };
            print(sqrt(f64.convert(arg.i64(0))));
            return 7;
        };''', encoding='utf-8')
        args = ['--cc', self.cc, '--', '169', '--cc', 'with spaces λ', '', '--', 'a"b\\']
        expected = '6\n169\n--cc\nwith spaces λ\n\n--\na"b\\\n13\n'
        self.assertEqual(self.invoke('run', source.name, *args, code=7).stdout, expected)
        self.assertEqual(self.invoke('run', source.name, *args, code=7, exe=self.driver).stdout, expected)
        self.assert_no_temps()

    def test_run_shipped_sort_with_stdin(self):
        source = ROOT / 'examples/apps/sort/main.aw'
        result = self.invoke('run', source, '--cc', self.cc, '--', '--unique', stdin='owl\nant\nowl\n')
        self.assertEqual((result.stdout, result.stderr), ('ant\nowl\n', ''))
        self.assert_no_temps()

    def test_explicit_backend_and_option_validation(self):
        self.init()
        # Even with CC and a system compiler on PATH, the default is bundle-only.
        missing = self.invoke('run', code=2)
        self.assertIn('bundled toolchain missing', missing.stderr)
        self.assertIn('--cc /absolute/path/to/cc', missing.stderr)
        for value in ['cc', self.work / 'missing']:
            with self.subTest(value=value):
                self.assertIn('absolute path to an executable C compiler',
                              self.invoke('run', '--cc', value, code=2).stderr)
        for args in [('check', '--cc', self.cc), ('build', '--run-timeout', '1'),
                     ('run', '-o', 'out'), ('run', '--cc', '--'), ('run', '--cc', ''),
                     ('run', '--run-timeout', '86401'), ('run', '--build-timeout', '0'),
                     ('test', '--', 'arg'), ('test', '-o', 'out'), ('test', '--run-timeout', '86401'),
                     ('check', '--syntax', 'legacy'), ('check', '--', 'arg')]:
            with self.subTest(args=args):
                self.invoke(*args, code=2)
        self.assert_no_temps()

    def test_failures_preserve_previous_output(self):
        source = self.init()
        out = self.project / 'custom binary'
        self.invoke('build', '--cc', self.cc, '-o', out.name)
        original = out.read_bytes()
        for compiler, message in [('/bin/false', 'host C compiler failed'),
                                  ('/bin/true', 'not a supported x86-64 ELF executable')]:
            with self.subTest(compiler=compiler):
                failed = self.invoke('build', '--cc', compiler, '-o', out.name, code=2)
                self.assertIn(message, failed.stderr)
                self.assertEqual(out.read_bytes(), original)
        source.write_text('func main[i64] { return true; };')
        failed = self.invoke('build', '--cc', '/bin/false', '-o', out.name, code=1)
        self.assertNotIn('host C compiler failed', failed.stderr)
        self.assertEqual(out.read_bytes(), original)
        self.assert_no_temps()

    def test_output_protects_manifest_and_all_sources(self):
        source = self.init()
        source.write_text('use Lib.aw as lib; func main { return lib.answer(); };')
        lib = self.project / 'Lib.aw'
        lib.write_text('exports { @r func answer { return 0; }; };')
        for protected in [source, lib, self.project / 'Demo.awproj']:
            with self.subTest(protected=protected):
                before = protected.read_bytes()
                alias = self.project / 'alias'
                os.link(protected, alias)
                rejected = self.invoke('build', '--cc', self.cc, '-o', alias.name, code=2)
                self.assertIn('refusing to overwrite', rejected.stderr)
                self.assertEqual(protected.read_bytes(), before)
                self.assertTrue(alias.samefile(protected))
                alias.unlink()
        self.assert_no_temps()

    def test_output_protects_package_manifest_and_hardlink(self):
        source = self.init()
        package = self.work / 'library'
        package.mkdir()
        self.invoke('init', 'Local', '--pkg', cwd=package)
        self.invoke('add', package / 'Local.awpkg')
        source.write_text('use Wrapper.aw; func main { print(Wrapper.message()); return 0; };')
        (self.project / 'Wrapper.aw').write_text('use Local; exports { @r func message { return Local.hello("Awl"); }; };')
        manifest = self.project / 'packages' / 'Local' / 'Local.awpkg'
        original = manifest.read_bytes()
        alias = self.project / 'output'
        os.link(manifest, alias)
        for driver, args in [(self.awl, ()), (self.driver, (source.name,))]:
            for output in [manifest, alias]:
                with self.subTest(driver=driver.name, output=output.name):
                    result = self.invoke('build', *args, '--cc', '/bin/false', '-o', output,
                                         exe=driver, code=2)
                    self.assertIn('refusing to overwrite', result.stderr)
                    self.assertIn('Local.awpkg', result.stderr)
                    self.assertEqual(manifest.read_bytes(), original)
                    self.assertTrue(alias.samefile(manifest))
        self.assert_no_temps()

    def test_backend_and_program_timeouts(self):
        source = self.init()
        source.write_text('func main { clock.sleep(5000); return 0; };')
        self.assertIn('program wall-time limit exceeded', self.invoke(
            'run', '--cc', self.cc, '--run-timeout', '1', code=124).stderr)
        slow = self.work / 'slow compiler'
        slow.write_text('#!/bin/sh\nexec /bin/sleep 5\n')
        slow.chmod(0o700)
        self.assertIn('backend wall-time limit exceeded', self.invoke(
            'build', '--cc', slow, '--build-timeout', '1', '-o', 'unused', code=124).stderr)
        self.assertFalse((self.project / 'unused').exists())
        self.assert_no_temps()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    args = parser.parse_args()
    cc = shutil.which(args.cc)
    if not cc:
        parser.error('a host C compiler is required')
    ToolkitTests.cc = str(Path(cc).absolute())
    ToolkitTests.acc = args.acc.resolve()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ToolkitTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())

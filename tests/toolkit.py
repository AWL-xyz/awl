#!/usr/bin/env python3
"""End-to-end tests of the source-built toolkit on Linux x86-64, without an SDK."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


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

    def invoke(self, *args, code=0, cwd=None, exe=None, stdin=None):
        result = subprocess.run([exe or self.awl, *args], cwd=cwd or self.project,
                                env=self.env, input=stdin, capture_output=True,
                                text=True, encoding='utf-8', timeout=30)
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
            (valid + '#\x00\n', 'NUL byte'),
            (valid + '#' * 16384, 'file exceeds the size budget'),
        ]
        for contents, message in attempts:
            with self.subTest(message=message):
                manifest.write_text(contents)
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

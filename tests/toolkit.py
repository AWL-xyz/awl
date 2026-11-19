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

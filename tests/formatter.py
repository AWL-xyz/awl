#!/usr/bin/env python3
"""Exercise the source toolkit formatter, including token parity and safe writes."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NORMAL = '''use end/enum.aw as helper;

exports {
    @r enum Letter
        Value(number:i64);
        Empty();
    end;
};

func main {
    -- } ] case then enum end; literal words aren't delimiters here.
    @p line: "héllo -- { } [ ] ";
    @p pair [i64;2]: [
        1, 2
    ];
    match Letter.Value(pair[0]) then
        case Letter.Value(n) then
            if i64.match(n) {
                print(
                    "${n}: " + line
                );
            };
        case Letter.Empty() then return 1;
    end;
    return helper.zero();
};
'''.encode()
ROUGH = b'\r\n'.join(b'\t ' + line.lstrip(b' ') + b' \t' for line in NORMAL.splitlines())


class FormatterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='awl-fmt-')
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name)
        self.awl = self.work / 'AwL'
        self.awl.symlink_to(self.acc)
        self.file = self.work / 'with space λ.aw'
        self.file.write_bytes(ROUGH)

    def invoke(self, *args, result=0, payload=b'', preexec_fn=None):
        run = subprocess.run([self.awl, 'FmT', *args], cwd=self.work, input=payload,
                             capture_output=True, timeout=20, preexec_fn=preexec_fn)
        self.assertEqual(run.returncode, result, (args, run.stderr, run.stdout[:100]))
        return run

    def test_preview_and_parser_parity(self):
        preview = self.invoke(self.file.name)
        self.assertEqual(preview.stdout, NORMAL)
        self.assertEqual(preview.stderr, b'')
        self.assertEqual(self.file.read_bytes(), ROUGH)
        (self.work / 'end').mkdir()
        (self.work / 'end/enum.aw').write_text('exports { @r func zero { return 0; }; };\n')

        def emit():
            return subprocess.check_output([self.acc, 'emit-c', self.file], timeout=20)

        before = emit()
        self.assertEqual(self.invoke('--write', self.file.name).stdout,
                         f'Formatted {self.file.name}\n'.encode())
        self.assertEqual(self.file.read_bytes(), NORMAL)
        self.assertEqual(emit(), before)

    def test_stdin_and_unbracketed_spacing(self):
        self.assertEqual(self.invoke('-', payload=ROUGH).stdout, NORMAL)
        self.assertEqual(self.invoke('-', payload=b'').stdout, b'')
        sample = b' @p precise: 1.250; -- two  spaces\r  \n\r\r\n'
        expected = b'@p precise: 1.250; -- two  spaces\n\n'
        self.assertEqual(self.invoke('-', payload=sample).stdout, expected)
        self.assertEqual(self.invoke('-', payload=expected).stdout, expected)
        self.assertEqual(self.invoke('--check', '-', payload=expected).stdout, b'')
        self.assertEqual(self.invoke('--check', '-', result=1, payload=sample).stdout, b'Would reformat -\n')

    def test_check_list_and_noop(self):
        other = self.work / '-good.aw'
        other.write_bytes(NORMAL)
        result = self.invoke('--check', '--', other.name, self.file.name, result=1)
        self.assertEqual(result.stdout, f'Would reformat {self.file.name}\n'.encode())
        self.assertEqual(self.file.read_bytes(), ROUGH)
        self.file.chmod(0o640)
        previous = self.file.stat()
        self.invoke('--write', self.file.name)
        current = self.file.stat()
        self.assertNotEqual(current.st_ino, previous.st_ino, 'should stage and rename, not truncate the original')
        self.assertEqual(stat.S_IMODE(current.st_mode), 0o640)
        self.assertEqual(self.invoke('--write', self.file.name, '--', other.name).stdout, b'')
        self.assertEqual(self.file.stat().st_ino, current.st_ino)
        self.assertEqual(self.file.stat().st_mtime_ns, current.st_mtime_ns)
        self.assertEqual(list(self.work.glob('.Awl-fmt-*')), [])

    def test_invalid_input_is_not_modified(self):
        for payload, code in [(b'func main { return 0 };', 'E100'), (b'--\xff\n', 'E008'),
                              (b'func main { print("oops); };', 'E102')]:
            with self.subTest(payload=payload):
                self.file.write_bytes(payload)
                result = self.invoke(self.file.name, '--write', '--diagnostic-format', 'json', result=1)
                self.assertEqual(result.stdout, b'')
                report = json.loads(result.stderr)
                self.assertEqual(report['file'], self.file.name)
                self.assertEqual(report['diagnostics'][0]['code'], code)
                self.assertEqual(self.file.read_bytes(), payload)
                self.assertEqual(list(self.work.glob('.Awl-fmt-*')), [])

    def test_input_and_output_bounds(self):
        over = b'\n' * 1048577
        self.assertIn(b'input exceeds 1 MiB', self.invoke('-', result=2, payload=over).stderr)
        self.file.write_bytes(over)
        self.assertIn(b'size budget', self.invoke(self.file.name, result=2).stderr)
        expanding = b'func main {\n' + b'-- c\n' * 130000 + b'return 0;\n};'
        self.file.write_bytes(expanding)
        result = self.invoke('--write', self.file.name, result=2)
        self.assertIn(b'formatted source would exceed 1 MiB', result.stderr)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(self.file.read_bytes(), expanding)

    def test_write_refuses_links_special_files_and_read_only(self):
        link = self.work / 'link.aw'
        link.symlink_to(self.file)
        self.assertIn(b'regular non-symlink', self.invoke('--write', link.name, result=2).stderr)
        self.assertTrue(link.is_symlink())
        link.unlink()
        os.link(self.file, link)
        self.assertIn(b'hard-linked', self.invoke('--write', link.name, result=2).stderr)
        self.assertTrue(link.samefile(self.file))
        link.unlink()
        os.mkfifo(link)
        self.assertIn(b'regular non-symlink', self.invoke('--check', link.name, result=2).stderr)
        self.file.chmod(0o400)
        self.assertIn(b'owned, writable source', self.invoke('--write', self.file.name, result=2).stderr)
        self.assertEqual(self.file.read_bytes(), ROUGH)
        self.assertEqual(list(self.work.glob('.Awl-fmt-*')), [])

    def test_failed_partial_write_cleans_up(self):
        def limit():
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            resource.setrlimit(resource.RLIMIT_FSIZE, (128, 128))

        before = self.file.stat()
        result = self.invoke('--write', self.file.name, result=2, preexec_fn=limit)
        self.assertIn(b'cannot write staged source', result.stderr)
        self.assertEqual(self.file.read_bytes(), ROUGH)
        self.assertEqual(self.file.stat().st_ino, before.st_ino)
        self.assertEqual(list(self.work.glob('.Awl-fmt-*')), [])

    def test_command_errors(self):
        for args in [(), ('main.txt',), (self.file.name, self.file.name), ('--write', '-'),
                     ('--check', '-', self.file.name), ('--check', '--write', self.file.name),
                     ('--cc', '/bin/false', self.file.name), ('--diagnostic-format',),
                     ('--diagnostic-format', 'xml', self.file.name), ('--check', *([self.file.name] * 65))]:
            with self.subTest(args=args):
                self.assertEqual(self.invoke(*args, result=2).stdout, b'')
        self.assertEqual(self.file.read_bytes(), ROUGH)

    def test_shipped_sources_are_idempotent(self):
        files = sorted((ROOT / 'examples').rglob('*.aw')) + sorted((ROOT / 'packages').rglob('*.aw'))
        for file in files:
            with self.subTest(file=file.relative_to(ROOT)):
                first = self.invoke(file).stdout
                self.assertEqual(self.invoke('-', payload=first).stdout, first)
        print(f'Checked format idempotence on {len(files)} shipped sources')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acc', type=Path, default=ROOT / 'compiler/native/bin/acc')
    FormatterTests.acc = p.parse_args().acc.resolve()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FormatterTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())

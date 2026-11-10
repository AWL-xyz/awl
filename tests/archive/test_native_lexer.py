import concurrent.futures
import ctypes as C
import dataclasses as D
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_kcc import kcc, ROOT

@unittest.skipUnless(kcc.native_library_path().is_file(),'build optional C++20 lexer with compiler/build_native.py')
class NativeLexer(unittest.TestCase):
    def compare(self,text):
        def outcome(backend):
            try: return ('ok',[D.asdict(t) for t in kcc.lex(text,backend)])
            except kcc.Error as e: return ('error',[D.asdict(d) for d in e.diagnostics],str(e))
        self.assertEqual(outcome('python'),outcome('native'))
    def test_examples_and_ir(self):
        for p in sorted((ROOT/'examples').glob('*.aw')):
            with self.subTest(source=p.name):
                self.compare(p.read_text())
                self.assertEqual(kcc.compile_text(p.read_text(),'python'),kcc.compile_text(p.read_text(),'native'))
    def test_error_fixtures(self):
        for p in (ROOT/'tests/diagnostics').glob('*.aw'):
            self.compare(p.read_text()); results=[]
            for backend in ('python','native'):
                with self.assertRaises(kcc.Error) as caught: kcc.compile_text(p.read_text(),backend)
                results.append(kcc.render_diagnostics(caught.exception,p.read_text(),p.name,'json'))
            self.assertEqual(*results)
    def test_unicode_comments_and_offsets(self):
        self.compare('-- café 😀 汉\r\n\tlocal x:i64=7 -- '+chr(0)+' é\nprint(x)')
        for char in ['é','汉','😀',chr(0),chr(127),chr(12),chr(11),chr(0x2028),'²',chr(0x301)]:
            self.compare('-- 😀\n1'+char)
    def test_suffixes_and_operators(self):
        self.compare('0 1i8 65535u16 -> == != <= >= + - * / % . ( ) : , ; and or not')
        for text in ['1u128','1i8oops','1_u8','12é','12😀','9'*257+'é','9'*257+'😀','--123','- -1','1!']:
            self.compare(text)
    def test_empty_and_terminal_edges(self):
        for text in ['', ' ', '\r', '\n', '--', 'a', '8', '-', '->', '.', ':','1u','1i64', '-- 😀']:
            self.compare(text)
    def test_limits(self):
        for text in ['a'*129,'9'*257,'1 '*100001,'--'+'é'*524288,' '*1048577]: self.compare(text)
    def test_limit_error_priority(self):
        self.compare('1 '*100000+'a'*129); self.compare('1 '*100000+'9'*257)
    def test_randomized_parity(self):
        rng=random.Random(606); alphabet='abcXYZ_019+-*/%=!<>()[]:;,. \t\r\n'+'é😀汉²'+chr(0x301)+chr(0)+chr(12)
        for i in range(2000):
            text=''.join(rng.choice(alphabet) for _ in range(rng.randrange(200)))
            with self.subTest(case=i): self.compare(text)
    def test_abi_and_ownership(self):
        lib,Result=kcc.load_native_lexer(); out=Result()
        self.assertEqual(lib.Awl_lex_abi_version(),1)
        self.assertEqual(lib.Awl_lex(b'abc',3,C.byref(out)),0)
        self.assertEqual((out.count,out.tokens[0].start,out.tokens[0].end),(1,0,3))
        lib.Awl_lex_free(C.byref(out)); self.assertFalse(out.owner)
        lib.Awl_lex_free(C.byref(out)); lib.Awl_lex_free(None)
    def test_raw_invalid_utf8(self):
        lib,Result=kcc.load_native_lexer()
        for hexdata in ['80','c080','eda080','f4908080','e282','40ff']:
            data=bytes.fromhex(hexdata); out=Result()
            self.assertEqual(lib.Awl_lex(data,len(data),C.byref(out)),4); lib.Awl_lex_free(C.byref(out))
    def test_raw_argument_and_size_limits(self):
        lib,Result=kcc.load_native_lexer(); out=Result()
        self.assertEqual(lib.Awl_lex(None,1,C.byref(out)),5)
        self.assertEqual(lib.Awl_lex(b'x',1048577,C.byref(out)),3)
        self.assertEqual(lib.Awl_lex(b'',0,None),5)
    def test_concurrent_independent_results(self):
        texts=['-- 😀\nlocal v:i64='+str(i) for i in range(100)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(kcc.lex_native,texts))
        self.assertEqual(results,[kcc.lex_python(t) for t in texts])
    def test_cli_native_execution(self):
        p=subprocess.run([sys.executable,str(ROOT/'compiler/kcc.py'),'run',str(ROOT/'examples/integers.aw'),'--lexer','native'],capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0); self.assertEqual(p.stdout,'4097\n-128\n32767\n2147483647\n255\n')
    def test_environment_selection(self):
        with patch.dict(os.environ,{'KCC_LEXER':'native'}): self.assertEqual(kcc.lex('a'),kcc.lex_native('a'))
    def test_unavailable_library_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ,{'Awl_LEXER_LIBRARY':str(Path(td)/'missing')}):
                with self.assertRaisesRegex(kcc.Error,'build_native.py'): kcc.lex_native('a')
    def test_surrogate_api_errors(self): self.compare(chr(0xd800))
    def test_unknown_backend(self):
        with self.assertRaisesRegex(kcc.Error,'unknown lexer'): kcc.lex('a','not-a-backend')

if __name__=='__main__': unittest.main()

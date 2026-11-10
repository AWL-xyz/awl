import ctypes as C
import dataclasses as D
import os
import random
import subprocess
import sys
import unittest
from test_kcc import kcc, ROOT

@unittest.skipUnless(kcc.native_library_path().is_file(),'build native components first')
class NativeParser(unittest.TestCase):
    def compare(self,text):
        results=[]
        for backend in ('python','native'):
            try: results.append(('ok',kcc.parse_text(text,'python',backend)))
            except kcc.Error as e: results.append(('error',[D.asdict(d) for d in e.diagnostics]))
        self.assertEqual(*results)
    def test_examples(self):
        for file in (ROOT/'examples').glob('*.aw'):
            self.compare(file.read_text())
            self.assertEqual(kcc.compile_text(file.read_text(),'python','python'),kcc.compile_text(file.read_text(),'native','native'))
    def test_diagnostics(self):
        for file in (ROOT/'tests/diagnostics').glob('*.aw'): self.compare(file.read_text())
    def test_recovery(self):
        self.compare('function main()->i64\nlocal a bool=1;\nlocal b:i64=;\nreturn 0 end')
        self.compare('function bad(x bool)->i64 return 0 end function main()->i64 return 0 end')
    def test_limits(self):
        for body in ['('*100+'1'+')'*100,' + '.join(['1']*100)]:
            self.compare('function main()->i64 return '+body+' end')
        self.compare('function main()->i64\n'+'local a bool=1;\n'*100+'return 0 end')
    def test_precedence_and_minima(self):
        for expr in ['1+2*3','true or false and not true','-128i8','-000128i8','-9223372036854775808','i8(i16(12i8))']:
            self.compare('function main()->i64 print('+expr+') return 0 end')
    def test_bad_delimiters_no_hang(self):
        for text in ['struct P ) end','union U V( end','function main()->i64 return . end','function main()->i64 local p:i64=1 p. end']:
            self.compare(text)
    def test_arena_backward_references(self):
        arena,tokens=kcc.native_syntax_arena((ROOT/'examples/results.aw').read_text(),'native')
        for i,node in enumerate(arena['nodes']): self.assertTrue(all(child<i for child in node['children']))
        self.assertTrue(arena['roots']); self.assertFalse(arena['diagnostics'])
    def test_syntax_mutations(self):
        rng=random.Random(707); seeds=[p.read_text() for p in (ROOT/'examples').glob('*.aw')]
        for i in range(1500):
            text=rng.choice(seeds); lo=rng.randrange(len(text)); hi=min(len(text),lo+rng.randrange(1,15))
            text=text[:lo]+rng.choice(['','end','then','case','(',')','.',';','local','struct'])+text[hi:]
            with self.subTest(case=i): self.compare(text)
    def test_cli_execution(self):
        p=subprocess.run([sys.executable,str(ROOT/'compiler/kcc.py'),'run',str(ROOT/'examples/results.aw'),'--parser','native','--lexer','native'],capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0); self.assertEqual(p.stdout,'7\ntrue\n6\nfalse\nfalse\n-1\n')
    def test_raw_argument_validation(self):
        lib,Record=kcc.native_parser_api(); handle=C.c_void_p()
        self.assertEqual(lib.Awl_parse_tokens(None,1,None,0,C.byref(handle)),1)
        self.assertFalse(handle); lib.Awl_parse_free(None)
if __name__=='__main__': unittest.main()

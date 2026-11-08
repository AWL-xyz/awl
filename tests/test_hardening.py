import copy
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from test_kcc import kcc, ROOT

class Diagnostics(unittest.TestCase):
    def test_golden(self):
        for source in sorted((ROOT/'tests/diagnostics').glob('*.aw')):
            with self.subTest(source=source.name):
                with self.assertRaises(kcc.Error) as caught: kcc.compile_text(source.read_text())
                actual=kcc.render_diagnostics(caught.exception,source.read_text(),source.name)+'\n'
                self.assertEqual(actual,source.with_suffix('.expected.txt').read_text())
    def test_json(self):
        text='function main() -> i64 return true end'
        with self.assertRaises(kcc.Error) as caught: kcc.compile_text(text)
        data=json.loads(kcc.render_diagnostics(caught.exception,text,'input.aw','json'))
        d=data['diagnostics'][0]; self.assertEqual(d['code'],'E200')
        self.assertEqual(text[d['start']:d['end']],'return')
    def test_recovery_across_functions(self):
        text='function bad(x bool) -> i64 return 0 end\nfunction main() -> i64 local y bool = 1 return 0 end'
        with self.assertRaises(kcc.Error) as caught: kcc.compile_text(text)
        self.assertEqual(len(caught.exception.diagnostics),2)
    def test_error_limit(self):
        text='function main() -> i64\n'+('local a bool = 1;\n'*100)+'return 0 end'
        with self.assertRaises(kcc.Error) as caught: kcc.compile_text(text)
        self.assertEqual(len(caught.exception.diagnostics),kcc.MAX_DIAGNOSTICS)
    def test_tabs(self):
        text='function main() -> i64\n\treturn true\nend'
        with self.assertRaises(kcc.Error) as caught: kcc.compile_text(text)
        self.assertIn('\n      ^~~~~~',kcc.render_diagnostics(caught.exception,text,'tab.aw'))
    def test_cli_json(self):
        p=subprocess.run([sys.executable,str(ROOT/'compiler/kcc.py'),'check',str(ROOT/'tests/diagnostics/type.aw'),'--diagnostic-format','json'],capture_output=True,text=True)
        self.assertEqual(p.returncode,1); self.assertEqual(json.loads(p.stderr)['diagnostics'][0]['code'],'E200')
    def test_invalid_encoding(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.aw'; p.write_bytes(b'\xff')
            with self.assertRaisesRegex(kcc.Error,'UTF-8'): kcc.read_source(p)

class Limits(unittest.TestCase):
    def reject(self,text,code):
        with self.assertRaises(kcc.Error) as caught: kcc.compile_text(text)
        self.assertEqual(caught.exception.diagnostics[0].code,code)
    def test_source_budget(self): self.reject(' '* (kcc.MAX_SOURCE_BYTES+1),'E001')
    def test_utf8_budget(self): self.reject('--'+'é'*(kcc.MAX_SOURCE_BYTES//2),'E001')
    def test_identifier_budget(self): self.reject('function '+'a'*129+'() -> i64 return 0 end','E003')
    def test_integer_budget(self): self.reject('function main() -> i64 return '+'1'*257+' end','E004')
    def test_token_budget(self): self.reject('1 '* (kcc.MAX_TOKENS+1),'E005')
    def test_paren_budget(self): self.reject('function main() -> i64 return '+'('*100+'1'+')'*100+' end','E002')
    def test_block_budget(self): self.reject('function main() -> i64 '+'if true then '*100+'return 0 '+'end '*101,'E002')
    def test_left_deep_tree_budget(self): self.reject('function main() -> i64 return '+' + '.join(['1']*100)+' end','E006')
    def test_near_limit_serialization(self):
        fs=kcc.compile_text('function main() -> i64 return '+' + '.join(['1']*50)+' end')
        self.assertIn('binary',json.dumps([kcc.D.asdict(f) for f in fs]))
    def test_positive_min_magnitude_rejected(self):
        self.reject('function main() -> i64 return 9223372036854775808 end','E200')
    def test_below_min_rejected(self):
        self.reject('function main() -> i64 return -9223372036854775809 end','E200')
    def test_bounded_file(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'large.aw'; p.write_bytes(b' '*(kcc.MAX_SOURCE_BYTES+1))
            with self.assertRaisesRegex(kcc.Error,'source exceeds'): kcc.read_source(p)

class Verifier(unittest.TestCase):
    def setUp(self):
        self.fs=kcc.compile_text('function main() -> i64 local x: i64 = 1 print(x) return x + 2 end')
        self.body=self.fs[0].children[1]
    def rejects(self):
        with self.assertRaisesRegex(kcc.Error,'IR verification failed'): kcc.verify_ir(self.fs)
    def test_read_only(self):
        before=copy.deepcopy(self.fs); kcc.verify_ir(self.fs); self.assertEqual(before,self.fs)
    def test_annotation(self): self.body[2].children[0].type='bool'; self.rejects()
    def test_symbol(self): self.body[2].children[0].children[0].symbol='k_v999'; self.rejects()
    def test_operator(self): self.body[2].children[0].value='<<'; self.rejects()
    def test_literal(self): self.body[0].children[0].value=1<<63; self.rejects()
    def test_callee(self): self.body[1].children[0].value='printf'; self.rejects()
    def test_children(self): self.body[2].children[0].children.pop(); self.rejects()
    def test_missing_return(self): self.body.pop(); self.rejects()
    def test_injection(self): self.fs[0].value=('main;abort()', 'i64'); self.rejects()
    def test_emitter_gate(self):
        self.body[0].symbol='bad;'
        with self.assertRaisesRegex(kcc.Error,'IR verification failed'): kcc.Emitter(self.fs).emit()

class FuzzSmoke(unittest.TestCase):
    def test_malformed_mutations(self):
        rng=random.Random(20261105)
        seeds=[p.read_text() for p in (ROOT/'examples').glob('*.aw')]
        seeds+=['function main() -> i64 return -9223372036854775808 end']
        alphabet='abc012()=+-*/,:;\n@ end function true local'
        for i in range(1000):
            source=rng.choice(seeds)
            for _ in range(rng.randint(1,5)):
                pos=rng.randrange(len(source)+1); op=rng.randrange(3)
                if op==0: source=source[:pos]+rng.choice(alphabet)+source[pos:]
                elif op==1: source=source[:pos]+source[pos+1:]
                else: source=source[:pos]+source[pos:pos+5]+source[pos:]
            with self.subTest(case=i):
                try:
                    fs=kcc.compile_text(source); kcc.Emitter(fs).emit()
                except kcc.Error: pass
                # Any uncaught exception fails the test. This is not a soundness proof.

if __name__=='__main__': unittest.main()

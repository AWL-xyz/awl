import importlib.util
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('kcc',ROOT/'compiler/kcc.py')
kcc=importlib.util.module_from_spec(spec); sys.modules['kcc']=kcc; spec.loader.exec_module(kcc)

class Frontend(unittest.TestCase):
    def reject(self,body,part):
        with self.assertRaisesRegex(kcc.Error,part): kcc.compile_text(body)
    def test_wrong_return(self): self.reject('function main() -> i64 return true end','expected i64')
    def test_missing_return(self): self.reject('function main() -> i64 local a: i64 = 2 end','not every path')
    def test_unknown(self): self.reject('function main() -> i64 return x end','unknown local')
    def test_range(self): self.reject('function main() -> i64 return 9223372036854775808 end','outside i64')
    def test_scope(self): self.reject('function main() -> i64 if true then local x: i64 = 1 end return x end','unknown local')
    def test_bad_call(self): self.reject('function main() -> i64 print(1,2) return 0 end','print expects')
    def test_bad_condition(self): self.reject('function main() -> i64 if 1 then return 0 else return 1 end end','expected bool')
    def test_duplicate(self): self.reject('function main() -> i64 return 0 end function main() -> i64 return 1 end','duplicate')
    def test_unreachable(self): self.reject('function main() -> i64 return 0 print(1) end','unreachable')
    def test_missing_end(self): self.reject('function main() -> i64 return 0','unterminated')
    def test_unit_local(self): self.reject('function main() -> i64 local x: unit = print(1) return 0 end','unit locals')
    def test_argument(self): self.reject('function f(x: bool) -> i64 return 0 end function main() -> i64 return f(2) end','argument types')
    def test_character(self): self.reject('function main() -> i64 return @ end','unexpected character')
    def test_ir(self):
        fs=kcc.compile_text('function main() -> i64 return 1 + 2 end')
        self.assertEqual(fs[0].children[1][0].children[0].type,'i64')

@unittest.skipUnless(shutil.which(os.environ.get('CC','cc')),'native C compiler required')
class Native(unittest.TestCase):
    def run_k(self,text,opt='2'):
        with tempfile.TemporaryDirectory() as td:
            c=Path(td)/'a.c'; exe=Path(td)/('a.exe' if os.name=='nt' else 'a')
            c.write_text(kcc.Emitter(kcc.compile_text(text)).emit())
            subprocess.run([os.environ.get('CC','cc'),'-std=c11','-O'+opt,str(c),'-o',str(exe)],check=True,capture_output=True)
            return subprocess.run([str(exe)],capture_output=True,text=True)
    def test_examples(self):
        p=self.run_k((ROOT/'examples/hello.aw').read_text()); self.assertEqual(p.returncode,0); self.assertEqual(p.stdout.splitlines()[-1],'3628800')
    def test_logic(self): self.assertEqual(self.run_k((ROOT/'examples/logic.aw').read_text()).stdout,'true\n')
    def test_short_circuit(self):
        p=self.run_k('function fail() -> bool print(99) return true end function main() -> i64 print(false and fail()) print(true or fail()) return 0 end')
        self.assertEqual(p.stdout,'false\ntrue\n')
    def test_evaluation_order(self):
        p=self.run_k('function f(x: i64) -> i64 print(x) return x end function g(a: i64,b: i64) -> i64 return a+b end function main() -> i64 print(g(f(1),f(2))) return 0 end')
        self.assertEqual(p.stdout,'1\n2\n3\n')
    def test_loop_shadow(self):
        p=self.run_k('function main() -> i64 local x: i64 = 1 if true then local x: i64 = 2 print(x) end while x < 3 do x = x+1 end print(x) return 0 end')
        self.assertEqual(p.stdout,'2\n3\n')
    def test_traps(self):
        for expr in ['9223372036854775807 + 1','(-9223372036854775807 - 1) - 1','3037000500 * 3037000500','1 / 0','1 % 0','(-9223372036854775807 - 1) / -1','(-9223372036854775807 - 1) * -1','-(-9223372036854775807 - 1)']:
            with self.subTest(expr=expr):
                p=self.run_k('function main() -> i64 print('+expr+') return 0 end')
                self.assertNotEqual(p.returncode,0); self.assertIn('arithmetic trap',p.stderr)
    def test_signed_division(self): self.assertEqual(self.run_k('function main() -> i64 print(-7/3) print(-7%3) return 0 end').stdout,'-2\n-1\n')
    def test_random_arithmetic(self):
        rng=random.Random(17); exprs=[]; expected=[]
        for _ in range(100):
            a=rng.randint(-1000000,1000000); b=rng.randint(-1000000,1000000); op=rng.choice(['+','-','*'])
            exprs.append(f'print(({a}) {op} ({b}))'); expected.append(str({'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b}[op]()))
        p=self.run_k('function main() -> i64 '+' '.join(exprs)+' return 0 end')
        self.assertEqual(p.stdout.splitlines(),expected)
    def test_unit(self):
        p=self.run_k('function f() -> unit print(3) end function g() -> unit return f() end function main() -> i64 g() return 0 end')
        self.assertEqual(p.stdout,'3\n')
    def test_minimum_literal(self):
        for opt in ('0','3'):
            p=self.run_k('function main() -> i64 print(-9223372036854775808) print(-9223372036854775808 + 1) return 0 end',opt)
            self.assertEqual(p.returncode,0)
            self.assertEqual(p.stdout,'-9223372036854775808\n-9223372036854775807\n')
    def test_minimum_negation_traps(self):
        p=self.run_k('function main() -> i64 print(-(-9223372036854775808)) return 0 end')
        self.assertNotEqual(p.returncode,0); self.assertIn('arithmetic trap',p.stderr)
    def test_grammar_differential(self):
        from generators import integer, boolean
        rng=random.Random(20261106); expressions=[]; expected=[]
        for i in range(200):
            expr,value=(integer(rng,3) if i%2 else boolean(rng,3))
            expressions.append('print('+expr+')')
            expected.append(str(value).lower())
        source='function main() -> i64 '+' '.join(expressions)+' return 0 end'
        for opt in ('0','3'):
            with self.subTest(optimization=opt):
                p=self.run_k(source,opt)
                self.assertEqual(p.returncode,0)
                self.assertEqual(p.stdout.splitlines(),expected)
    def test_optimization_equivalence(self):
        source=(ROOT/'examples/hello.aw').read_text(); self.assertEqual(self.run_k(source,'0').stdout,self.run_k(source,'3').stdout)

if __name__=='__main__': unittest.main()

import copy
import os
import random
import shutil
import unittest
from test_kcc import kcc, ROOT
import test_kcc

class ValueFrontend(unittest.TestCase):
    def reject(self,source,fragment):
        with self.assertRaisesRegex(kcc.Error,fragment): kcc.compile_text(source)
    def program(self,decl='',body='return 0'): return decl+' function main() -> i64 '+body+' end'
    def test_uint_range(self): self.reject(self.program(body='print(18446744073709551616u64) return 0'),'outside u64')
    def test_mixed_arithmetic(self): self.reject(self.program(body='print(1 + 2u64) return 0'),'matching integer')
    def test_mixed_comparison(self): self.reject(self.program(body='print(1 < 2u64) return 0'),'matching integer')
    def test_mixed_equality(self): self.reject(self.program(body='print(1 == 2u64) return 0'),'matching scalar')
    def test_unsigned_negation(self): self.reject(self.program(body='print(-1u64) return 0'),'signed integer')
    def test_unknown_type(self): self.reject(self.program(body='local x: Missing = 1 return 0'),'invalid value type')
    def test_duplicate_struct(self): self.reject(self.program('struct P x:i64 end struct P y:i64 end'),'duplicate/reserved')
    def test_function_struct_collision(self): self.reject(self.program('struct P x:i64 end function P()->i64 return 0 end'),'duplicate/reserved')
    def test_empty_struct(self): self.reject(self.program('struct P end'),'empty structs')
    def test_duplicate_field(self): self.reject(self.program('struct P x:i64 x:bool end'),'duplicate field')
    def test_unit_field(self): self.reject(self.program('struct P x:unit end'),'invalid field type')
    def test_unknown_field_type(self): self.reject(self.program('struct P x:Missing end'),'invalid field type')
    def test_self_recursive(self): self.reject(self.program('struct P x:P end'),'recursive value')
    def test_mutually_recursive(self): self.reject(self.program('struct P x:Q end struct Q x:P end'),'recursive value')
    def test_constructor_count(self): self.reject(self.program('struct P x:i64 end','print(P(1,2).x) return 0'),'constructor argument')
    def test_constructor_type(self): self.reject(self.program('struct P x:u64 end','print(P(1).x) return 0'),'constructor argument')
    def test_missing_field(self): self.reject(self.program('struct P x:i64 end','print(P(1).y) return 0'),'unknown field')
    def test_scalar_field(self): self.reject(self.program(body='print((1).x) return 0'),'unknown field')
    def test_invalid_place(self): self.reject(self.program('struct P x:i64 end','P(1).x = 2 return 0'),'local-rooted place')
    def test_field_store_type(self): self.reject(self.program('struct P x:i64 end','local p:P=P(1) p.x=true return 0'),'expected i64')
    def test_struct_equality(self): self.reject(self.program('struct P x:i64 end','print(P(1)==P(1)) return 0'),'matching scalar')
    def test_struct_print(self): self.reject(self.program('struct P x:i64 end','print(P(1)) return 0'),'print expects')
    def test_nominal_types(self): self.reject(self.program('struct P x:i64 end struct Q x:i64 end','local p:P=Q(1) return 0'),'expected P')
    def test_value_size_limit(self):
        decl='struct S0 x:i64 end '
        for i in range(1,20): decl+=f'struct S{i} a:S{i-1} b:S{i-1} end '
        self.reject(self.program(decl),'size budget')
    def test_graph_depth_limit(self):
        decl='struct S0 x:i64 end '
        for i in range(1,70): decl+=f'struct S{i} x:S{i-1} end '
        self.reject(self.program(decl),'nesting limit')
    def test_field_count_limit(self):
        self.reject(self.program('struct P '+' '.join(f'x{i}:bool' for i in range(129))+' end'),'128 fields')
    def test_ir_uint_mutation(self):
        fs=kcc.compile_text(self.program(body='print(1u64) return 0'))
        fs[0].children[1][0].children[0].children[0].value=1<<64
        with self.assertRaisesRegex(kcc.Error,'IR verification failed'): kcc.verify_ir(fs)
    def test_ir_struct_mutation(self):
        fs=kcc.compile_text(self.program('struct P x:i64 end','local p:P=P(1) p.x=2 return 0'))
        fs[1].children[1][1].children[0].value='missing'
        with self.assertRaisesRegex(kcc.Error,'IR verification failed'): kcc.verify_ir(fs)
    def test_ir_constructor_mutation(self):
        fs=kcc.compile_text(self.program('struct P x:i64 end','local p:P=P(1) return 0'))
        fs[1].children[1][0].children[0].type='i64'
        with self.assertRaisesRegex(kcc.Error,'IR verification failed'): kcc.verify_ir(fs)
    def test_ir_metadata_readonly(self):
        fs=kcc.compile_text((ROOT/'examples/values.aw').read_text()); before=copy.deepcopy(fs)
        kcc.verify_ir(fs); self.assertEqual(fs,before)
    def test_new_syntax_mutations(self):
        rng=random.Random(303); source=(ROOT/'examples/values.aw').read_text()
        for i in range(500):
            lo=rng.randrange(len(source)); hi=min(len(source),lo+rng.randint(1,12))
            variant=source[:lo]+rng.choice(['', 'end', '.', 'u64', ';', 'struct'])+source[hi:]
            try: kcc.Emitter(kcc.compile_text(variant)).emit()
            except kcc.Error: pass

@unittest.skipUnless(shutil.which(os.environ.get('CC','cc')),'native C compiler required')
class ValueNative(unittest.TestCase):
    # Reuse only the native compile/run helper, not its entire test class.
    run_k=test_kcc.Native.run_k
    def test_example(self):
        for opt in ('0','3'):
            p=self.run_k((ROOT/'examples/values.aw').read_text(),opt)
            self.assertEqual(p.returncode,0); self.assertEqual(p.stdout,'10\n15\n1\ntrue\n18446744073709551615\n')
    def test_uint_boundaries(self):
        p=self.run_k('function main()->i64 print(0u64) print(18446744073709551615u64/1u64) print(18446744073709551615u64%2u64) return 0 end')
        self.assertEqual(p.returncode,0); self.assertEqual(p.stdout,'0\n18446744073709551615\n1\n')
    def test_uint_traps(self):
        for expr in ['18446744073709551615u64+1u64','0u64-1u64','18446744073709551615u64*2u64','1u64/0u64','1u64%0u64']:
            with self.subTest(expr=expr):
                p=self.run_k('function main()->i64 print('+expr+') return 0 end')
                self.assertNotEqual(p.returncode,0); self.assertIn('arithmetic trap',p.stderr)
    def test_uint_oracle(self):
        rng=random.Random(304); cases=[]; expected=[]
        for i in range(200):
            a=rng.randrange(1<<64); b=rng.randrange(1,1<<64); op=rng.choice(['+','-','*','/','%','<','=='])
            if op=='+' and a+b>=1<<64: a//=2; b//=2
            if op=='-' and a<b: a,b=b,a
            if op=='*': a>>=32; b>>=32
            v={'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a//b,'%':lambda:a%b,'<':lambda:a<b,'==':lambda:a==b}[op]()
            cases.append(f'print({a}u64 {op} {b}u64)'); expected.append(str(v).lower())
        source='function main()->i64 '+' '.join(cases)+' return 0 end'
        for opt in ('0','3'):
            p=self.run_k(source,opt); self.assertEqual(p.returncode,0); self.assertEqual(p.stdout.splitlines(),expected)
    def test_forward_struct_and_copy(self):
        source='''struct Outer inner:Inner end struct Inner x:i64 end
        function change(p:Outer)->Outer p.inner.x=99 return p end
        function main()->i64 local p:Outer=Outer(Inner(2)) local q:Outer=p
        q.inner.x=7 print(p.inner.x) print(q.inner.x) print(change(p).inner.x) print(p.inner.x) return 0 end'''
        p=self.run_k(source); self.assertEqual(p.stdout,'2\n7\n99\n2\n')
    def test_constructor_evaluation_order(self):
        source='''struct P x:i64 y:i64 end function f(x:i64)->i64 print(x) return x end
        function main()->i64 local p:P=P(f(1),f(2)) print(p.x+p.y) return 0 end'''
        self.assertEqual(self.run_k(source).stdout,'1\n2\n3\n')
    def test_whole_struct_assignment(self):
        source='struct P x:i64 end function main()->i64 local p:P=P(1) p=P(2) print(p.x) return 0 end'
        self.assertEqual(self.run_k(source).stdout,'2\n')
    def test_nested_whole_field_assignment(self):
        source='struct P x:i64 end struct Q p:P end function main()->i64 local q:Q=Q(P(1)) q.p=P(3) print(q.p.x) return 0 end'
        self.assertEqual(self.run_k(source).stdout,'3\n')

if __name__=='__main__': unittest.main()

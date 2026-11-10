import copy
import os
import random
from pathlib import Path
import subprocess
import tempfile
import shutil
import unittest
from test_kcc import kcc, ROOT
import test_kcc

DECL='union Outcome Value(value:i64) Empty() end '

def program(body='return 0',decl=DECL):
    return decl+' function main()->i64 '+body+' end'

def both(value='Outcome.Value(7)',yes='print(x)',no='print(0)'):
    return f'match {value} then case Outcome.Value(x) then {yes} case Outcome.Empty() then {no} end'

class UnionFrontend(unittest.TestCase):
    def reject(self,source,message):
        with self.assertRaisesRegex(kcc.Error,message): kcc.compile_text(source)
    def test_empty_union(self): self.reject(program(decl='union U end'),'empty unions')
    def test_duplicate_variant(self): self.reject(program(decl='union U A() A() end'),'duplicate variant')
    def test_duplicate_payload(self): self.reject(program(decl='union U A(x:i64,x:bool) end'),'duplicate field')
    def test_unit_payload(self): self.reject(program(decl='union U A(x:unit) end'),'invalid field type')
    def test_unknown_payload(self): self.reject(program(decl='union U A(x:Missing) end'),'invalid field type')
    def test_recursive_union(self): self.reject(program(decl='union U A(x:U) Empty() end'),'recursive value')
    def test_mutual_aggregate_cycle(self): self.reject(program(decl='union U A(x:S) end struct S u:U end'),'recursive value')
    def test_duplicate_namespace(self): self.reject(program(decl='union U A() end struct U x:i64 end'),'duplicate/reserved')
    def test_variant_limit(self): self.reject(program(decl='union U '+' '.join(f'V{i}()' for i in range(129))+' end'),'128 variants')
    def test_payload_field_limit(self): self.reject(program(decl='union U A('+','.join(f'x{i}:i64' for i in range(129))+') end'),'128 fields')
    def test_unknown_union_constructor(self): self.reject(program('local u:Outcome=Missing.Value(1) return 0'),'unknown union')
    def test_unknown_variant_constructor(self): self.reject(program('local u:Outcome=Outcome.Missing() return 0'),'unknown variant')
    def test_constructor_arity(self): self.reject(program('local u:Outcome=Outcome.Value() return 0'),'variant argument types')
    def test_constructor_type(self): self.reject(program('local u:Outcome=Outcome.Value(true) return 0'),'variant argument types')
    def test_bare_union_call(self): self.reject(program('local u:Outcome=Outcome(1) return 0'),'unknown function')
    def test_missing_case(self): self.reject(program('match Outcome.Value(1) then case Outcome.Value(x) then print(x) end return 0'),'non-exhaustive.*Empty')
    def test_no_cases(self): self.reject(program('match Outcome.Empty() then end return 0'),'non-exhaustive')
    def test_duplicate_case(self): self.reject(program(both()+' return 0').replace('case Outcome.Empty() then print(0)','case Outcome.Value(y) then print(y)'),'duplicate case')
    def test_case_wrong_owner(self): self.reject(program(both().replace('case Outcome.Empty()', 'case Other.Empty()')+' return 0'),'case type Other')
    def test_case_unknown_variant(self): self.reject(program(both().replace('case Outcome.Empty()', 'case Outcome.Other()')+' return 0'),'unknown variant')
    def test_binding_arity(self): self.reject(program(both().replace('Outcome.Value(x)', 'Outcome.Value()')+' return 0'),'pattern payload count')
    def test_duplicate_binding(self):
        self.reject(program('match U.Pair(1,2) then case U.Pair(x,x) then return x end', 'union U Pair(a:i64,b:i64) end'),'duplicate pattern binding')
    def test_binding_escape(self): self.reject(program(both()+' print(x) return 0'),'unknown local x')
    def test_binding_other_arm(self): self.reject(program(both(no='print(x)')+' return 0'),'unknown local x')
    def test_scalar_scrutinee(self): self.reject(program(both(value='42')+' return 0'),'match requires a tagged union')
    def test_struct_scrutinee(self): self.reject(program(both(value='P(1)')+' return 0',DECL+'struct P x:i64 end'),'match requires a tagged union')
    def test_union_equality(self): self.reject(program('print(Outcome.Empty()==Outcome.Empty()) return 0'),'matching scalar')
    def test_direct_payload_access(self): self.reject(program('print(Outcome.Value(1).value) return 0'),'unknown field')
    def test_direct_tag_access(self): self.reject(program('print(Outcome.Value(1).k_tag) return 0'),'unknown field')
    def test_partial_return(self): self.reject(program(both(yes='return x',no='print(0)')),'not every path')
    def test_unreachable_after_match(self): self.reject(program(both(yes='return x',no='return 0')+' return 0'),'unreachable')
    def test_union_assignment_nominal(self): self.reject(program('local x:Outcome=Other.Value(1) return 0',DECL+'union Other Value(x:i64) Empty() end'),'expected Outcome')
    def test_union_print(self): self.reject(program('print(Outcome.Empty()) return 0'),'print expects')
    def test_discard_not_binding(self): self.reject(program(both().replace('Value(x)', 'Value(_)')+' return 0'),'unknown local x')
    def test_nested_match_depth(self):
        source='match Outcome.Empty() then case Outcome.Empty() then '*100+'return 0 '+'end '*100
        self.reject(program(source),'nesting exceeds')
    def test_decl_depth_budget(self):
        decl='union U0 A() end '
        for i in range(1,70): decl+=f'union U{i} A(value:U{i-1}) end '
        self.reject(program(decl=decl),'nesting limit')
    def test_ir_read_only(self):
        fs=kcc.compile_text((ROOT/'examples/results.aw').read_text()); before=copy.deepcopy(fs)
        kcc.verify_ir(fs); self.assertEqual(before,fs)
    def test_source_mutations(self):
        rng=random.Random(404); source=(ROOT/'examples/results.aw').read_text()
        for i in range(750):
            lo=rng.randrange(len(source)); hi=min(len(source),lo+rng.randint(1,15))
            variant=source[:lo]+rng.choice(['','case','union','.','(',')','then','end'])+source[hi:]
            try: kcc.Emitter(kcc.compile_text(variant)).emit()
            except kcc.Error: pass

class UnionVerifier(unittest.TestCase):
    def setUp(self):
        self.fs=kcc.compile_text(program(both()+' return 0')); self.match=self.fs[1].children[1][0]
    def reject(self):
        with self.assertRaisesRegex(kcc.Error,'IR verification failed'): kcc.verify_ir(self.fs)
    def test_missing_arm(self): self.match.children[1].pop(); self.reject()
    def test_duplicate_arm(self): self.match.children[1].append(copy.deepcopy(self.match.children[1][0])); self.reject()
    def test_owner(self): self.match.children[1][0].value=('Unknown','Value'); self.reject()
    def test_binder_annotation(self): self.match.children[1][0].children[0][0].type='bool'; self.reject()
    def test_binder_symbol(self): self.match.children[1][0].children[0][0].symbol='bad'; self.reject()
    def test_free_payload(self): self.match.children[1][0].children[1][0].children[0].children[0].symbol='k_v999'; self.reject()
    def test_constructor_annotation(self): self.match.children[0].type='i64'; self.reject()
    def test_constructor_identity(self): self.match.children[0].value=('Outcome','Missing'); self.reject()
    def test_constructor_arguments(self): self.match.children[0].children=[]; self.reject()
    def test_variant_schema(self): self.fs[0].children[0].kind='field_decl'; self.reject()
    def test_discard_symbol(self):
        self.fs=kcc.compile_text(program(both(yes='print(1)').replace('Value(x)','Value(_)')+' return 0'))
        self.fs[1].children[1][0].children[1][0].children[0][0].symbol='k_v1'; self.reject()

@unittest.skipUnless(shutil.which(os.environ.get('CC','cc')),'native C compiler required')
class UnionNative(unittest.TestCase):
    run_k=test_kcc.Native.run_k
    def test_results_example(self):
        for opt in ('0','3'):
            p=self.run_k((ROOT/'examples/results.aw').read_text(),opt)
            self.assertEqual(p.returncode,0); self.assertEqual(p.stdout,'7\ntrue\n6\nfalse\nfalse\n-1\n')
    def test_exhaustive_returns(self):
        decl=DECL+'function read(r:Outcome)->i64 '+both('r','return x','return 9')+' end '
        p=self.run_k(program('print(read(Outcome.Value(5))) print(read(Outcome.Empty())) return 0',decl))
        self.assertEqual(p.stdout,'5\n9\n'); self.assertEqual(p.returncode,0)
    def test_scrutinee_once(self):
        decl=DECL+'function get()->Outcome print(99) return Outcome.Value(1) end '
        self.assertEqual(self.run_k(program(both('get()')+' return 0',decl)).stdout,'99\n1\n')
    def test_case_order(self):
        body='match Outcome.Value(4) then case Outcome.Empty() then print(0) case Outcome.Value(x) then print(x) end return 0'
        self.assertEqual(self.run_k(program(body)).stdout,'4\n')
    def test_snapshot_and_mutable_binding(self):
        body='local r:Outcome=Outcome.Value(5) '+both('r','r=Outcome.Empty() x=x+2 print(x)')+' '+both('r')+' return 0'
        self.assertEqual(self.run_k(program(body)).stdout,'7\n0\n')
    def test_shadowed_pattern(self):
        body='local x:i64=99 '+both('Outcome.Value(1)','x=x+1 print(x)')+' print(x) return 0'
        self.assertEqual(self.run_k(program(body)).stdout,'2\n99\n')
    def test_discard_multiple(self):
        decl='union U Pair(a:i64,b:i64) end '
        self.assertEqual(self.run_k(program('match U.Pair(1,2) then case U.Pair(_,_) then print(true) end return 0',decl)).stdout,'true\n')
    def test_nullary_only(self):
        decl='union Color Red() Blue() end '
        body='match Color.Blue() then case Color.Red() then print(1) case Color.Blue() then print(2) end return 0'
        self.assertEqual(self.run_k(program(body,decl)).stdout,'2\n')
    def test_union_in_struct(self):
        decl=DECL+'struct Box value:Outcome end '
        body='local b:Box=Box(Outcome.Empty()) b.value=Outcome.Value(8) '+both('b.value')+' return 0'
        self.assertEqual(self.run_k(program(body,decl)).stdout,'8\n')
    def test_nested_union_match(self):
        decl=DECL+'union Outer Item(value:Outcome) None() end '
        body='match Outer.Item(Outcome.Value(3)) then case Outer.Item(r) then '+both('r')+' case Outer.None() then print(-1) end return 0'
        self.assertEqual(self.run_k(program(body,decl)).stdout,'3\n')
    def test_constructor_evaluation_order(self):
        decl='union U Pair(a:i64,b:i64) end function f(x:i64)->i64 print(x) return x end '
        body='match U.Pair(f(1),f(2)) then case U.Pair(a,b) then print(a+b) end return 0'
        self.assertEqual(self.run_k(program(body,decl)).stdout,'1\n2\n3\n')
    def test_invalid_tag_defense(self):
        # This is a deliberately corrupted C object, not a constructible safe Awl
        # value. It checks the defensive default branch rather than type soundness.
        emitted=kcc.Emitter(kcc.compile_text(program(both()+' return 0'))).emit()
        self.assertIn('.k_tag = 0',emitted)
        emitted=emitted.replace('.k_tag = 0','.k_tag = 999',1)
        with tempfile.TemporaryDirectory() as td:
            c=Path(td)/'bad.c'; exe=Path(td)/('bad.exe' if os.name=='nt' else 'bad')
            c.write_text(emitted)
            subprocess.run([os.environ.get('CC','cc'),'-std=c11','-O2',str(c),'-o',str(exe)],check=True,capture_output=True,timeout=30)
            p=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(p.returncode,0); self.assertIn('invalid union tag',p.stderr)
    def test_generated_union_oracle(self):
        rng=random.Random(405); decl='union U Number(x:i64) Flag(x:bool) None() end '
        cases=[]; expected=[]
        for i in range(150):
            choice=rng.randrange(3); number=rng.randint(-1000000,1000000); flag=bool(rng.randrange(2))
            ctor=[f'U.Number({number})',f'U.Flag({str(flag).lower()})','U.None()'][choice]
            arms=['case U.Number(n) then print(n + 1)','case U.Flag(b) then print(not b)','case U.None() then print(0)']
            rng.shuffle(arms); cases.append('match '+ctor+' then '+' '.join(arms)+' end')
            expected.append(str([number+1,not flag,0][choice]).lower())
        source=program(' '.join(cases)+' return 0',decl)
        for opt in ('0','3'):
            p=self.run_k(source,opt); self.assertEqual(p.returncode,0); self.assertEqual(p.stdout.splitlines(),expected)

if __name__=='__main__': unittest.main()

import math
import os
import random
import shutil
import unittest
from test_kcc import kcc, ROOT
import test_kcc

TYPES=list(kcc.INTEGERS)
def literal(value,ty): return f'{value}{ty}'
def program(body): return 'function main()->i64 '+body+' end'

class IntegerFrontend(unittest.TestCase):
    def reject(self,text,message):
        with self.assertRaisesRegex(kcc.Error,message): kcc.compile_text(text)
    def test_positive_literal_bounds(self):
        for ty in TYPES:
            with self.subTest(type=ty):
                high=kcc.bounds(ty)[1]
                self.reject(program(f'print({high+1}{ty}) return 0'),f'outside {ty}')
    def test_negative_literal_bounds(self):
        for ty in kcc.SIGNED:
            with self.subTest(type=ty): self.reject(program(f'print({kcc.bounds(ty)[0]-1}{ty}) return 0'),f'outside {ty}')
    def test_mixed_width_arithmetic(self): self.reject(program('print(1i8 + 1i16) return 0'),'matching integer')
    def test_mixed_width_comparison(self): self.reject(program('print(1u16 < 2u32) return 0'),'matching integer')
    def test_mixed_width_equality(self): self.reject(program('print(1i16 == 2i32) return 0'),'matching scalar')
    def test_contextual_literal_rejected(self): self.reject(program('local x:u8=1 return 0'),'expected u8')
    def test_unsigned_negation(self):
        for ty in TYPES:
            if ty.startswith('u'): self.reject(program(f'print(-1{ty}) return 0'),'signed integer')
    def test_convert_arity(self):
        for text in ['u8()','i16(1,2)','i32(true)']:
            with self.subTest(expr=text): self.reject(program(f'print({text}) return 0'),'conversion')
    def test_convert_aggregate(self): self.reject('struct P x:i64 end '+program('print(i64(P(1))) return 0'),'conversion requires an integer')
    def test_convert_unit(self): self.reject(program('print(i8(print(1))) return 0'),'conversion requires an integer')
    def test_invalid_suffix(self):
        for text in ['1u128','1i24','1u640','1u8oops','1_u8','1i8u8']:
            with self.subTest(literal=text): self.reject(program('print('+text+') return 0'),'invalid integer suffix')
    def test_suffix_digit_budget(self): self.reject(program('print('+'0'*257+'u8) return 0'),'256 digits')
    def test_no_implicit_call_conversion(self): self.reject('function f(x:u8)->u8 return x end '+program('print(f(1u16)) return 0'),'argument types')
    def test_reserved_type_names(self): self.reject('function u8()->i64 return 0 end '+program('return 0'),'expected identifier')
    def test_bool_not_integer(self): self.reject(program('print(1i8 + true) return 0'),'matching integer')
    def test_layout_sizes(self):
        ds=kcc.compile_text('struct Packet a:u8 b:i16 c:u32 d:i64 end '+program('return 0'))
        order,sizes=kcc.layout_values(ds)
        self.assertEqual(sizes['u8'],(1,1)); self.assertEqual(sizes['i16'],(2,2)); self.assertEqual(sizes['u32'],(4,4)); self.assertEqual(sizes['Packet'],(16,8))
    def test_width_types_in_payloads(self):
        ds=kcc.compile_text('union U Tiny(x:i8) Wide(x:u32) end '+program('match U.Tiny(1i8) then case U.Tiny(v) then print(v) case U.Wide(v) then print(v) end return 0'))
        kcc.verify_ir(ds)
    def test_literal_metadata(self):
        ds=kcc.compile_text(program('print(-128i8) return 0')); n=ds[0].children[1][0].children[0].children[0]
        self.assertEqual((n.value,n.type,n.literal_type),(-128,'i8','i8'))
    def test_unused_helpers_omitted(self):
        emitted=kcc.Emitter(kcc.compile_text(program('return 0'))).emit()
        self.assertNotIn('k_i8_add',emitted); self.assertNotIn('k_convert_',emitted)
    def test_helper_dependencies(self):
        emitted=kcc.Emitter(kcc.compile_text(program('print(i16(1i8 + 2i8)) return 0'))).emit()
        for name in ['k_i8_add','k_convert_i8_i16','k_print_i16']: self.assertIn(name,emitted)
        self.assertNotIn('k_u64_mul',emitted); self.assertNotIn('k_convert_i16_i8',emitted)
    def test_source_mutations(self):
        source=(ROOT/'examples/integers.aw').read_text(); rng=random.Random(505)
        for _ in range(500):
            lo=rng.randrange(len(source)); hi=min(len(source),lo+rng.randint(1,14))
            variant=source[:lo]+rng.choice(['','u8','i16','255i8','(',')','unit'])+source[hi:]
            try: kcc.Emitter(kcc.compile_text(variant)).emit()
            except kcc.Error: pass

class IntegerVerifier(unittest.TestCase):
    def setUp(self):
        self.fs=kcc.compile_text(program('print(i16(12i8)) return 0'))
        self.convert=self.fs[0].children[1][0].children[0].children[0]
    def reject(self):
        with self.assertRaisesRegex(kcc.Error,'IR verification failed'): kcc.verify_ir(self.fs)
    def test_literal_type_metadata(self): self.convert.children[0].literal_type='u8'; self.reject()
    def test_literal_annotation(self): self.convert.children[0].type='i16'; self.reject()
    def test_literal_range(self): self.convert.children[0].value=128; self.reject()
    def test_conversion_target(self): self.convert.value='unit'; self.reject()
    def test_conversion_annotation(self): self.convert.type='u16'; self.reject()
    def test_conversion_children(self): self.convert.children=[]; self.reject()
    def test_unsigned_unary(self):
        self.fs=kcc.compile_text(program('print(-1i8) return 0'))
        unary=self.fs[0].children[1][0].children[0].children[0]; unary.children[0].kind='uint'; unary.children[0].literal_type='u8'; unary.children[0].type='u8'; self.reject()

@unittest.skipUnless(shutil.which(os.environ.get('CC','cc')),'native C compiler required')
class IntegerNative(unittest.TestCase):
    run_k=test_kcc.Native.run_k
    def test_example(self):
        for opt in ('0','3'):
            p=self.run_k((ROOT/'examples/integers.aw').read_text(),opt)
            self.assertEqual(p.returncode,0); self.assertEqual(p.stdout,'4097\n-128\n32767\n2147483647\n255\n')
    def test_all_literal_extrema(self):
        statements=[]; expected=[]
        for ty in TYPES:
            for value in kcc.bounds(ty): statements.append('print('+literal(value,ty)+')'); expected.append(str(value))
        for opt in ('0','3'):
            p=self.run_k(program(' '.join(statements)+' return 0'),opt)
            self.assertEqual(p.returncode,0); self.assertEqual(p.stdout.splitlines(),expected)
    def test_all_width_parameters(self):
        decl=''; calls=[]
        for ty in TYPES:
            decl+=f'function f_{ty}(x:{ty})->{ty} return x end '
            calls.append(f'print(f_{ty}(1{ty}))')
        self.assertEqual(self.run_k(decl+program(' '.join(calls)+' return 0')).stdout,'1\n'*8)
    def test_width_arithmetic_oracle(self):
        rng=random.Random(506); statements=[]; expected=[]
        for ty in TYPES:
            low,high=kcc.bounds(ty)
            for _ in range(64):
                a=rng.randint(low,high); b=rng.randint(low,high); op=rng.choice(['+','-','*','/','%','<','<=','==','!='])
                if op=='+': a//=2; b//=2
                if op=='-' and low==0 and a<b: a,b=b,a
                if op=='-' and low<0: a//=2; b//=2
                if op=='*':
                    bound=math.isqrt(high); a=rng.randint(-bound if low<0 else 0,bound); b=rng.randint(-bound if low<0 else 0,bound)
                if op in ('/','%') and (b==0 or (low<0 and a==low and b==-1)): b=1
                q=(abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1) if b else 0
                value={'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:q,'%':lambda:a-q*b,'<':lambda:a<b,'<=':lambda:a<=b,'==':lambda:a==b,'!=':lambda:a!=b}[op]()
                statements.append(f'print(({literal(a,ty)}) {op} ({literal(b,ty)}))'); expected.append(str(value).lower())
        for opt in ('0','3'):
            p=self.run_k(program(' '.join(statements)+' return 0'),opt)
            self.assertEqual(p.returncode,0); self.assertEqual(p.stdout.splitlines(),expected)
    def test_width_arithmetic_traps(self):
        for ty in TYPES:
            low,high=kcc.bounds(ty)
            exprs=[f'{high}{ty}+1{ty}',f'{low}{ty}-1{ty}',f'{high}{ty}*2{ty}',f'1{ty}/0{ty}',f'1{ty}%0{ty}']
            if low<0: exprs += [f'-({low}{ty})',f'({low}{ty})/(-1{ty})',f'({low}{ty})%(-1{ty})']
            for expr in exprs:
                for opt in ('0','3'):
                    with self.subTest(expr=expr,opt=opt):
                        p=self.run_k(program('print('+expr+') return 0'),opt)
                        self.assertNotEqual(p.returncode,0); self.assertIn('arithmetic trap',p.stderr)
    def test_all_conversion_pairs(self):
        statements=[]; expected=[]
        for src in TYPES:
            for dst in TYPES:
                lo=max(kcc.bounds(src)[0],kcc.bounds(dst)[0]); hi=min(kcc.bounds(src)[1],kcc.bounds(dst)[1])
                for value in sorted({lo,0,1,hi}):
                    statements.append(f'print({dst}({value}{src}))'); expected.append(str(value))
        for opt in ('0','3'):
            p=self.run_k(program(' '.join(statements)+' return 0'),opt)
            self.assertEqual(p.returncode,0); self.assertEqual(p.stdout.splitlines(),expected)
    def test_out_of_range_conversions(self):
        for src in TYPES:
            for dst in TYPES:
                sl,sh=kcc.bounds(src); dl,dh=kcc.bounds(dst)
                for value in sorted({sl,sh,dl-1,dh+1}):
                    if not sl<=value<=sh or dl<=value<=dh: continue
                    for opt in ('0','3'):
                        with self.subTest(src=src,dst=dst,value=value,opt=opt):
                            p=self.run_k(program(f'print({dst}({value}{src})) return 0'),opt)
                            self.assertNotEqual(p.returncode,0); self.assertIn('arithmetic trap',p.stderr)
    def test_conversion_evaluation_once(self):
        source='function make()->i8 print(1) return 2i8 end '+program('print(i64(make())) return 0')
        self.assertEqual(self.run_k(source).stdout,'1\n2\n')
    def test_literal_leading_zeroes(self): self.assertEqual(self.run_k(program('print(000255u8) print(-00128i8) return 0')).stdout,'255\n-128\n')
    def test_nested_conversions(self): self.assertEqual(self.run_k(program('print(i8(u16(i32(u64(127u8))))) return 0')).stdout,'127\n')

if __name__=='__main__': unittest.main()

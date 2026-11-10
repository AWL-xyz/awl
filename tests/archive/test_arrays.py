from native_features import supports_version
"""Native fixed arrays: structural types/value copies, checked places and ABI."""
import json,os,random,shutil,subprocess,unittest
from pathlib import Path
from test_builders import Builders,ROOT
KCC=Path(os.environ.get('Awl_ARRAY_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():return supports_version(KCC,(0, 9, 0))
@unittest.skipUnless(available(),'requires native0.9.0 arrays')
class Arrays(Builders):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def test_example_o0_o3(self):
        self.source((ROOT/'examples/arrays/main.aw').read_text(),True)
        for opt in ['0','3']:self.output('Typed arrays: original / doubled\n3\n6\n7\n14\n11\n22\n15\n30\nNested update\n42\nValue copies preserve the original\ntrue\n',opt)
    def test_all_integer_widths_and_bool(self):
        lines=[];expected=[]
        for ty in ['i8','i16','i32','i64','u8','u16','u32','u64']:
            lines+=['local a'+ty+':['+ty+';2]=[1'+ty+',2'+ty+']','a'+ty+'[1]=3'+ty,'print(a'+ty+'[0])','print(a'+ty+'[1])'];expected+=['1','3']
        lines+=['local b:[bool;2]=[true,false] b[1]=true print(b[0] and b[1])'];expected+=['true'];self.source(' '.join(lines));self.output('\n'.join(expected)+'\n')
    def test_nested_structs_and_union_arrays(self):
        self.source('struct P x:i64 end union U A(x:i64) B() end struct Row values:[P;2] end function main()->i64 local r:Row=Row([P(3),P(4)]) r.values[1].x=42 print(r.values[1].x) local us:[U;2]=[U.A(7),U.B()] match us[0] then case U.A(x) then print(x) case U.B() then return 1 end return 0 end',True);self.output('42\n7\n')
    def test_struct_array_layout_dependency_and_copy(self):
        self.source('struct Inner b:bool n:u64 end struct Outer a:[Inner;2] tail:u8 end function f(a:[Inner;2])->[Inner;2] a[0].n=99u64 return a end function main()->i64 local o:Outer=Outer([Inner(true,1u64),Inner(false,2u64)],3u8) local a:[Inner;2]=f(o.a) print(a[0].n) print(o.a[0].n) print(o.tail) return 0 end',True)
        for opt in ['0','3']:self.output('99\n1\n3\n',opt)
    def test_immutable_strings_and_resource_alias_elements(self):
        self.source('local a:[string;2]=["é","🚀"] local b:[string;2]=a b[0]="changed" print(a[0]) print(b[0]) local h:spool=spool.new(8) defer spool.free(h) local handles:[spool;2]=[h,h] spool.append(handles[0],"aliased") spool.print(handles[1])');self.output('é\nchanged\naliased\n')
    def test_unused_string_and_builder_array_parameter_types_compile(self):
        self.source('function unused(a:[[string;2];2],b:[spool;2])->i64 return 0 end function main()->i64 return 0 end',True);self.output('')
    def test_cross_module_nominal_elements_and_return(self):
        (self.root/'points.aw').write_text('struct P x:i64 end function make()->[P;2] return [P(1),P(2)] end')
        self.source('import points as p function f(a:[p.P;2])->[p.P;2] a[1].x=9 return a end function main()->i64 local a:[p.P;2]=p.make() local b:[p.P;2]=f(a) print(a[1].x) print(b[1].x) return 0 end',True);self.output('2\n9\n')
    def test_nested_index_store_evaluation_once_left_to_right(self):
        self.source('function row()->i64 print(1) return 1 end function col()->i64 print(2) return 0 end function value()->i64 print(3) return 42 end function main()->i64 local a:[[i64;2];2]=[[1,2],[3,4]] a[row()][col()]=value() print(a[1][0]) return 0 end',True);self.output('1\n2\n3\n42\n')
    def test_array_literal_and_length_preserve_effects(self):
        self.source('function n(x:i64)->i64 print(x) return x end function make()->[i64;2] return [n(1),n(2)] end function main()->i64 print(array.length(make())) print(make()[1]) return 0 end',True);self.output('1\n2\n2\n1\n2\n2\n')
    def test_bounds_reads_and_writes(self):
        for body in ['print(a[-1])','print(a[2])','print(a[9223372036854775807])','a[-1]=1','a[2]=1','a[9223372036854775807]=1']:
            with self.subTest(body=body):
                self.source('local a:[i64;2]=[1,2] '+body);r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl array bounds trap',r.stderr);self.assertNotIn('AddressSanitizer',r.stderr);self.assertNotIn('runtime error:',r.stderr)
    def test_bad_store_bounds_trap_before_rhs(self):
        self.source('function rhs()->i64 print("wrong") return 1 end function main()->i64 local a:[i64;1]=[0] a[1]=rhs() return 0 end',True);r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'');self.assertIn('Awl array bounds trap',r.stderr)
    def test_type_errors_and_no_array_equality(self):
        for body in ['local a:[i64;2]=[1,true]','local a:[i64;2]=[1]','local a:[i64;1]=[print(1)]','local a:[i64;2]=[1,2] print(a[0u64])','local a:[i64;2]=[1,2] a[0]=true','local a:[i64;2]=[1,2] print(a==a)','print(array.length(1))','print(array.length())','print([1,2])','print(1[0])','local x:i64=0; [1,2][0]=x','local a:[[i64;1];2]=[[1],[true]]']:
            with self.subTest(body=body):self.source(body);self.reject()
    def test_invalid_lengths_and_empty_literals(self):
        for text in ['local a:[i64;0]=[1]','local a:[i64;1025]=[1]','local a:[i64;-1]=[1]','local a:[i64;1u8]=[1]','local a:[i64;true]=[1]','local a:[i64;1]=[]','local a:[i64;2]=[1,2,]']:
            self.source(text);r=self.invoke('check');self.assertEqual(r.returncode,1,r.stderr)
    def test_max_count_and_value_budget(self):
        self.source('local a:[i64;1024]=['+','.join(str(i) for i in range(1024))+'] print(array.length(a)) print(a[1023])');self.output('1024\n1023\n')
        self.source('function oversized(a:[[i64;1024];1024])->i64 return 0 end function main()->i64 return 0 end',True);r=self.invoke('check');self.assertEqual(r.returncode,1);self.assertIn('E210',r.stderr)
        self.source('struct Bad x:[Bad;1] end function main()->i64 return 0 end',True);r=self.invoke('check');self.assertEqual(r.returncode,1);self.assertIn('E210',r.stderr)
        self.source('local a:[i64;1024]=['+','.join('1' for _ in range(1025))+']');r=self.invoke('check');self.assertEqual(r.returncode,1);self.assertIn('E007',r.stderr)
    def test_seeded_matrix_oracles_o0_o3(self):
        rng=random.Random(900);matrix=[[rng.randrange(-100,101) for _ in range(5)] for _ in range(4)]
        lines=['local a:[[i64;5];4]=['+','.join('['+','.join(map(str,row))+']' for row in matrix)+']'];expected=[]
        for _ in range(40):
            i=rng.randrange(4);j=rng.randrange(5);v=rng.randrange(-10000,10001);matrix[i][j]=v;lines.extend([f'a[{i}][{j}]={v}',f'print(a[{i}][{j}])']);expected.append(str(v))
        lines+=['print(array.length(a))','print(array.length(a[0]))'];expected+=['4','5'];self.source(' '.join(lines))
        for opt in ['0','3']:self.output('\n'.join(expected)+'\n',opt)
    def test_repeated_emission_and_reserved_intrinsic(self):
        self.source('local a:[i64;2]=[1,2] print(a[0])');r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,self.invoke('emit-c').stdout)
        self.source('function array.length()->i64 return 0 end function main()->i64 return 0 end',True);r=self.invoke('check');self.assertEqual(r.returncode,1);self.assertIn('E210',r.stderr)
for name in Builders.__dict__:
    if name.startswith('test_') and name not in Arrays.__dict__:setattr(Arrays,name,None)
del Builders
if __name__=='__main__':unittest.main()

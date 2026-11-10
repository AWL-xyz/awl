from native_features import supports_version
"""Repeated fixed arrays: compact syntax, once-only evaluation, value copies."""
import os,subprocess,unittest
from pathlib import Path
from test_builders import Builders,ROOT
KCC=Path(os.environ.get('Awl_REPEAT_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():return supports_version(KCC,(0, 9, 1))
@unittest.skipUnless(available(),'requires native0.9.1 repeated arrays')
class Repeats(Builders):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def test_once_not_per_element_and_length_evaluates(self):
        self.source('function seed()->i64 print("seed once") return 7 end function main()->i64 local a:[i64;1024]=[seed();1024] print(array.length(a)) print(a[1023]) print(array.length([seed();1])) return 0 end',True)
        for opt in ['0','3']:self.output('seed once\n1024\n7\nseed once\n1\n',opt)
    def test_nested_copy_independence_and_all_elements_initialized(self):
        self.source('local row:[i64;3]=[2;3] local grid:[[i64;3];4]=[row;4] grid[1][2]=99 print(row[2]) print(grid[0][2]) print(grid[1][2]) print(grid[3][2]) local i:i64=0 local sum:i64=0 while i<1024 do local a:[i64;1024]=[5;1024] sum=sum+a[i] i=i+1 end print(sum)')
        for opt in ['0','3']:self.output('2\n2\n99\n2\n5120\n',opt)
    def test_nominal_union_string_bool_and_integer_types(self):
        self.source('struct P x:i64 end union U A(x:i64) B() end function main()->i64 local ps:[P;2]=[P(7);2] ps[0].x=42 print(ps[1].x) local us:[U;2]=[U.A(9);2] match us[1] then case U.A(x) then print(x) case U.B() then return 1 end local s:[string;3]=["é🚀";3] print(s[2]) local bs:[bool;2]=[true;2] print(bs[1]) local ns:[u8;2]=[255u8;2] print(ns[1]) return 0 end',True);self.output('7\n9\né🚀\ntrue\n255\n')
    def test_resource_descriptor_copies_alias_one_creation(self):
        self.source('function make()->spool print("created once") return spool.new(16) end function main()->i64 local hs:[spool;64]=[make();64] defer spool.free(hs[0]) print(spool.append(hs[63],"shared")) spool.print(hs[1]) return 0 end',True);self.output('created once\n0\nshared\n')
    def test_modules_parameters_and_returns(self):
        (self.root/'p.aw').write_text('struct P x:i64 end function make()->[P;3] return [P(8);3] end')
        self.source('import p as p function f(a:[p.P;3])->[p.P;3] a[0].x=12 return a end function main()->i64 local a:[p.P;3]=p.make() local b:[p.P;3]=f(a) print(a[0].x) print(b[0].x) return 0 end',True);self.output('8\n12\n')
    def test_malformed_counts_and_type_mismatches(self):
        for body in ['local a:[i64;2]=[1;0]','local a:[i64;2]=[1;1025]','local a:[i64;2]=[1;-1]','local a:[i64;2]=[1;1u8]','local n:i64=2 local a:[i64;2]=[1;n]','local a:[i64;2]=[1;1+1]','local a:[i64;2]=[1;]','local a:[i64;2]=[1;2,]','local a:[i64;2]=[1,2;3]','local a:[i64;2]=[;3]','local a:[bool;2]=[1;2]','local a:[i64;2]=[print(1);2]']:
            with self.subTest(body=body):
                self.source(body);r=self.invoke('check');self.assertEqual(r.returncode,1,r.stderr)
        self.source('local a:[[i64;1024];1024]=[[0;1024];1024]');r=self.invoke('check');self.assertEqual(r.returncode,1);self.assertIn('E210',r.stderr)
    def test_count_spelling_postfix_and_short_c(self):
        self.source('print([7;0002][1]) print(array.length([[false;2];3])) local a:[i64;1024]=[0;1024] print(a[1023])');self.output('7\n3\n0\n')
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,self.invoke('emit-c').stdout);self.assertLess(len(r.stdout),50000);self.assertIn('for (uint32_t k_i',r.stdout)
    def test_example(self):
        self.source((ROOT/'examples/repeat/main.aw').read_text(),True);self.output('Compact fixed arrays\nSeed evaluated once\n1024\n7168\nIndependent rows after copy\n0\n42\n0\n')
for name in Builders.__dict__:
    if name.startswith('test_') and name not in Repeats.__dict__:setattr(Repeats,name,None)
del Builders
if __name__=='__main__':unittest.main()

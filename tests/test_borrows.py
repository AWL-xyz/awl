from native_features import supports_version
"""Nonescaping synchronous descriptor borrow parameters; not reference exclusivity."""
import json,os,shutil,subprocess,unittest
from pathlib import Path
from test_builders import Builders,ROOT
KCC=Path(os.environ.get('Awl_BORROWS_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():return supports_version(KCC,(0, 11, 0))
@unittest.skipUnless(available(),'requires native0.11.0 builder borrows')
class Borrows(Builders):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def reject_borrow(self,s,code='E220'):
        self.source(s,True);r=self.invoke('check','--diagnostic-format','json');self.assertEqual(r.returncode,1,r.stderr);self.assertEqual(json.loads(r.stderr)['diagnostics'][0]['code'],code,r.stderr)
    def test_module_example_o0_o3(self):
        shutil.copytree(ROOT/'examples/borrows',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.output('frame=99999\n100000 helper calls: one scoped builder\n1088890\ntrue\n',opt)
    def test_forward_call_and_recursive_borrow(self):
        self.source('function forward(borrow b:spool,n:i64)->i64 return append(b,n) end function append(borrow b:spool,n:i64)->i64 if n==0 then return spool_bytes(b) end spool_append(b,"x") return forward(b,n-1) end function main()->i64 scoped b:spool=spool_new(16) print(forward(b,8)) spool_print(b) print(spool_valid(b)) return 0 end',True);self.output('8\nxxxxxxxx\ntrue\n')
    def test_parameter_modes_at_each_argument_position(self):
        self.source('function f(x:i64,borrow a:spool,borrow b:spool,y:i64)->i64 spool_i64(a,x) spool_i64(b,y) return spool_bytes(a)+spool_bytes(b) end function main()->i64 scoped a:spool=spool_new(16) scoped b:spool=spool_new(16) print(f(12,a,b,34)) spool_print(a) spool_print(b) return 0 end',True);self.output('4\n12\n34\n')
    def test_duplicate_borrows_are_shared_not_exclusive(self):
        self.source('function f(borrow a:spool,borrow b:spool)->unit spool_append(a,"a") spool_append(b,"b") end function main()->i64 scoped b:spool=spool_new(8) f(b,b) spool_print(b) return 0 end',True);self.output('ab\n')
    def test_no_callee_release_and_manual_input_stays_manual(self):
        self.source('function f(borrow b:spool)->bool return spool_valid(b) end function main()->i64 local b:spool=spool_new(8) print(f(b)) print(spool_valid(b)) spool_free(b) print(spool_valid(b)) return 0 end',True);self.output('true\ntrue\nfalse\n')
    def test_snapshot_and_independent_fresh_return(self):
        self.source('function snapshot(borrow b:spool)->string return spool_snapshot(b) end function fresh(borrow b:spool)->spool return spool_new(spool_capacity(b)) end function main()->i64 scoped b:spool=spool_new(16) spool_append(b,"hé") local s:string=snapshot(b) spool_clear(b) print(s) local other:spool=fresh(b) print(spool_valid(other)) spool_free(other) return 0 end',True);self.output('hé\ntrue\n')
    def test_reject_copy_free_reassign_and_defer(self):
        for body in ['local alias:spool=b','spool_free(b)','defer spool_free(b)','b=spool_new(8)','local a:[spool;2]=[b,b]','local a:[spool;2]=[b;2]']:
            with self.subTest(body=body):self.reject_borrow('function bad(borrow b:spool)->i64 '+body+' return 0 end function main()->i64 return 0 end')
    def test_reject_return_and_aggregate_escape(self):
        self.reject_borrow('function bad(borrow b:spool)->spool return b end function main()->i64 return 0 end')
        for header,body in [('struct S b:spool end','local s:S=S(b)'),('union U A(b:spool) end','local u:U=U.A(b)'),('','local a:[spool;1]=[spool_new(8)] a[0]=b')]:
            self.reject_borrow(header+' function bad(borrow b:spool)->i64 '+body+' return 0 end function main()->i64 return 0 end')
    def test_reject_forward_to_by_value_and_wrong_parameter_slot(self):
        self.reject_borrow('function manual(b:spool)->i64 return 0 end function bad(borrow b:spool)->i64 return manual(b) end function main()->i64 return 0 end')
        self.reject_borrow('function f(borrow a:spool,b:spool)->i64 return 0 end function main()->i64 scoped b:spool=spool_new(8) return f(b,b) end')
    def test_borrow_type_and_parser_policy(self):
        for ty in ['i64','bool','string','[spool;1]']:
            self.reject_borrow('function bad(borrow b:'+ty+')->i64 return 0 end function main()->i64 return 0 end')
        self.reject_borrow('function bad(borrow b:unit)->i64 return 0 end function main()->i64 return 0 end','E200')
        self.reject_borrow('function bad(borrow borrow b:spool)->i64 return 0 end function main()->i64 return 0 end','E100')
    def test_module_modes_and_alias_conflicts(self):
        (self.root/'helper.aw').write_text('function f(borrow b:spool)->i64 return spool_capacity(b) end')
        self.source('import helper as h function main()->i64 scoped b:spool=spool_new(8) print(h.f(b)) return 0 end',True);self.output('8\n')
        self.reject_borrow('import helper as h function bad(borrow h:spool)->i64 return 0 end function main()->i64 return 0 end','E303')
        (self.root/'helper.aw').write_text('function f(b:spool)->i64 return spool_capacity(b) end')
        self.reject_borrow('import helper as h function main()->i64 scoped b:spool=spool_new(8) return h.f(b) end')
    def test_unavailable_descriptor_can_be_borrowed_for_validity(self):
        self.source('function available(borrow b:spool)->bool return spool_valid(b) end function main()->i64 scoped b:spool=spool_new(-1) print(available(b)) return 0 end',True);self.output('false\n')
    def test_nested_borrows_evaluate_arguments_left_to_right(self):
        self.source('function touch(borrow b:spool)->i64 spool_append(b,"x") print("arg") return 1 end function use(borrow b:spool,n:i64)->i64 print("body") return spool_bytes(b)+n end function main()->i64 scoped b:spool=spool_new(8) print(use(b,touch(b))) return 0 end',True);self.output('arg\nbody\n2\n')
    def test_shadowed_manual_binding_is_distinct(self):
        self.source('function f(borrow b:spool)->i64 if true then local b:spool=spool_new(8) spool_free(b) end return spool_capacity(b) end function main()->i64 scoped b:spool=spool_new(16) print(f(b)) return 0 end',True);self.output('16\n')
    def test_unused_borrow_param_still_emits_runtime_types(self):
        self.source('function unused(borrow b:spool)->i64 return 0 end function main()->i64 return 0 end',True);self.output('')
    def test_deterministic_c_and_borrow_has_no_cleanup(self):
        self.source('function f(borrow b:spool)->i64 return spool_bytes(b) end function main()->i64 scoped b:spool=spool_new(8) print(f(b)) return 0 end',True);r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,self.invoke('emit-c').stdout);self.output('0\n')
for name in Builders.__dict__:
    if name.startswith('test_') and name not in Borrows.__dict__:setattr(Borrows,name,None)
del Builders
if __name__=='__main__':unittest.main()

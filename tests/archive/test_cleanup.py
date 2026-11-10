from native_features import supports_version
"""Project-only scoped deferred releases; not ownership/alias checking."""
import json,os,shutil,subprocess,unittest
from pathlib import Path
from test_builders import Builders,ROOT
KCC=Path(os.environ.get('Awl_CLEANUP_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():return supports_version(KCC,(0, 8, 4))
@unittest.skipUnless(available(),'requires native0.8.4 scoped cleanup')
class Cleanup(Builders):
    # Reuse helpers, not inherited test cases; see bottom of module.
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def test_example_o0_o3(self):
        self.source((ROOT/'examples/cleanup/main.aw').read_text(),True)
        for opt in ['0','3']:self.output('frame=99999\n100000 calls: scoped cleanup on every return\ncafé\nInner scope released before this line\n',opt)
    def test_early_return_value_evaluated_before_cleanup(self):
        self.source('function test(b:spool)->bool defer spool.free(b) return spool.valid(b) end function main()->i64 local b:spool=spool.new(4) print(test(b)) print(spool.valid(b)) return 0 end',True)
        for opt in ['0','3']:self.output('true\nfalse\n',opt)
    def test_capture_once_at_registration_and_reverse_order(self):
        self.source('function make()->spool print("capture") return spool.new(8) end function main()->i64 defer spool.free(make()) local b:spool=spool.new(8) defer spool.free(b) print("body") return 0 end',True)
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr)
        code=r.stdout.replace('static void k_spool_free(KSpool b) {','static void k_spool_free(KSpool b) { fprintf(stderr,"release=%" PRIu64 "\\n",b.id);',1)
        c=self.root/'trace.c';c.write_text(code);exe=self.root/'trace'
        flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],check=True,capture_output=True)
        r=subprocess.run([str(exe)],capture_output=True,text=True,env=self.env)
        self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'capture\nbody\n','release=2\nrelease=1\n'))
    def test_reassignment_captures_original_not_future_value(self):
        self.source('function f(a:spool,b:spool)->unit defer spool.free(a) a=b end function main()->i64 local a:spool=spool.new(4) local b:spool=spool.new(4) f(a,b) print(spool.valid(a)) print(spool.valid(b)) spool.free(b) return 0 end',True)
        self.output('false\ntrue\n')
    def test_field_capture_and_nested_scope_cleanup(self):
        self.source('struct H value:spool end function main()->i64 local a:spool=spool.new(4) local b:spool=spool.new(4) local h:H=H(a) if true then defer spool.free(h.value) h.value=b end print(spool.valid(a)) print(spool.valid(b)) spool.free(b) return 0 end',True)
        self.output('false\ntrue\n')
    def test_nested_returns_release_all_active_scopes(self):
        self.source('function f(a:spool,b:spool,choose:bool)->i64 defer spool.free(a) if choose then defer spool.free(b) return 7 else defer spool.free(b) return 8 end end function main()->i64 local a:spool=spool.new(1) local b:spool=spool.new(1) print(f(a,b,true)) print(spool.valid(a)) print(spool.valid(b)) local c:spool=spool.new(1) local d:spool=spool.new(1) print(f(c,d,false)) print(spool.valid(c)) print(spool.valid(d)) return 0 end',True)
        self.output('7\nfalse\nfalse\n8\nfalse\nfalse\n')
    def test_loop_scope_released_each_iteration(self):
        self.source('local i:i64=0 while i<100000 do local b:spool=spool.new(1024) if not spool.valid(b) then return 1 end defer spool.free(b) spool.append(b,"loop") i=i+1 end print(i)')
        for opt in ['0','3']:self.output('100000\n',opt)
    def test_false_branch_does_not_register_or_evaluate(self):
        self.source('function make()->spool print("wrong") return spool.new(1) end function main()->i64 if false then defer spool.free(make()) end print("ok") return 0 end',True);self.output('ok\n')
    def test_unit_return_and_fallthrough(self):
        self.source('function fall(b:spool)->unit defer spool.free(b) end function early(b:spool)->unit defer spool.free(b) return print("unit") end function main()->i64 local a:spool=spool.new(1) local b:spool=spool.new(1) fall(a) early(b) print(spool.valid(a)) print(spool.valid(b)) return 0 end',True);self.output('unit\nfalse\nfalse\n')
    def test_match_arm_scope_and_return(self):
        self.source('union U A(value:spool) B(value:spool) end function f(x:U)->i64 match x then case U.A(b) then defer spool.free(b) return 1 case U.B(b) then defer spool.free(b) print("arm") end return 2 end function main()->i64 local a:spool=spool.new(1) local b:spool=spool.new(1) print(f(U.A(a))) print(f(U.B(b))) print(spool.valid(a)) print(spool.valid(b)) return 0 end',True);self.output('1\narm\n2\nfalse\nfalse\n')
    def test_byte_buffer_defer_reclaims_payload(self):
        self.source('local i:i64=0 while i<128 do local b:i64=buffer.new(16777216) if b==0 then return 1 end defer buffer.free(b) buffer.set(b,0,42u8) i=i+1 end print(i)');self.output('128\n')
    def test_deferred_builder_return_is_stale_not_ownership_transfer(self):
        self.source('function f()->spool local b:spool=spool.new(1) defer spool.free(b) return b end function main()->i64 print(spool.valid(f())) return 0 end',True);self.output('false\n')
    def test_invalid_releases_and_shapes_rejected(self):
        for expr in ['print(1)','spool.clear(spool.new(1))','string.length("a")','spool.free(1)','buffer.free(true)','window.close(spool.new(1))','1','spool.free(spool.new(1))+1']:
            with self.subTest(expr=expr):self.source('defer '+expr);self.reject()
    def test_scope_and_project_budgets(self):
        self.source(' '.join('defer buffer.free(1)' for _ in range(65)))
        r=self.invoke('check');self.assertEqual(r.returncode,1);self.assertIn('E210',r.stderr)
        scopes=' '.join('if false then '+' '.join('defer buffer.free(1)' for _ in range(64))+' end' for _ in range(4))
        self.source(scopes);r=self.invoke('check');self.assertEqual(r.returncode,0,r.stderr)
        self.source(scopes+' if false then defer buffer.free(1) end');r=self.invoke('check');self.assertEqual(r.returncode,1);self.assertIn('E210',r.stderr)
    def test_module_provenance_and_project_only_syntax(self):
        (self.root/'worker.aw').write_text('function f()->unit defer print(1) end')
        self.source('import worker function main()->i64 worker.f() return 0 end',True)
        r=self.invoke('check','--diagnostic-format','json');d=json.loads(r.stderr)['diagnostics'][0];self.assertEqual(d['code'],'E200');self.assertEqual(d['file'],str(self.root/'worker.aw'))
    def test_repeated_emission_is_deterministic(self):
        self.source('local b:spool=spool.new(4) defer spool.free(b)');a=self.invoke('emit-c');b=self.invoke('emit-c');self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(a.stdout,b.stdout)
for name in Builders.__dict__:
    if name.startswith('test_') and name not in Cleanup.__dict__:setattr(Cleanup,name,None)
# Don't rediscover imported parent class as a second test suite.
del Builders
if __name__=='__main__':unittest.main()

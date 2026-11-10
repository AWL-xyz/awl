from native_features import supports_version
"""Restricted scoped ownership: fresh builders, intrinsic-only borrows, no escapes."""
import json,os,shutil,subprocess,unittest
from pathlib import Path
from test_builders import Builders,ROOT
KCC=Path(os.environ.get('Awl_SCOPED_OWNER_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():return supports_version(KCC,(0, 10, 0))
@unittest.skipUnless(available(),'requires native0.10.0 scoped unique builders')
class ScopedOwners(Builders):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def reject_owner(self,s,full=False,code='E220'):
        self.source(s,full);r=self.invoke('check','--diagnostic-format','json');self.assertEqual(r.returncode,1,r.stderr);self.assertEqual(json.loads(r.stderr)['diagnostics'][0]['code'],code,r.stderr)
    def test_example_many_return_cleanups(self):
        self.source((ROOT/'examples/scoped-owner/main.aw').read_text(),True)
        for opt in ['0','3']:self.output('frame=99999\n100000 scoped builders: automatic release\n1088890\nUnavailable allocation is safe to leave scope\nfalse\n',opt)
    def test_every_borrow_operation_and_independent_snapshot_escape(self):
        self.source('function f()->string scoped b:spool=spool.new(32) print(spool.valid(b)) print(spool.capacity(b)) spool.clear(b) print(spool.append(b,"é")) print(spool.codepoint(b,65u32)) print(spool.i64(b,-7)) print(spool.u64(b,8u64)) print(spool.length(b)) print(spool.bytes(b)) spool.print(b) return spool.snapshot(b) end function main()->i64 print(f()) return 0 end',True);self.output('true\n32\n0\n0\n0\n0\n5\n6\néA-78\néA-78\n')
    def test_reject_copy_return_reassign_free_and_defer(self):
        prefix='scoped b:spool=spool.new(8) '
        for body in ['local alias:spool=b','local a:[spool;2]=[b,b]','local a:[spool;2]=[b;2]','b=spool.new(8)','spool.free(b)','defer spool.free(b)','local a:[spool;1]=[spool.new(1)] a[0]=b']:
            with self.subTest(body=body):self.reject_owner(prefix+body)
        self.reject_owner('function f()->spool scoped b:spool=spool.new(8) return b end function main()->i64 return 0 end',True)
    def test_reject_aggregate_union_and_function_escape(self):
        for header,body in [('struct S b:spool end','local s:S=S(b)'),('union U A(b:spool) end','local u:U=U.A(b)'),('function id(b:spool)->spool return b end','local x:spool=id(b)'),('function inspect(b:spool)->bool return spool.valid(b) end','print(inspect(b))')]:
            self.reject_owner(header+' function main()->i64 scoped b:spool=spool.new(8) '+body+' return 0 end',True)
    def test_fresh_creation_only_and_type_policy(self):
        for s in ['local a:spool=spool.new(8) scoped b:spool=a','scoped b:i64=7','scoped b:string="x"','scoped b:[spool;1]=[spool.new(8)]']:
            self.reject_owner(s)
        self.reject_owner('function make()->spool return spool.new(8) end function main()->i64 scoped b:spool=make() return 0 end',True)
    def test_unavailable_creation_and_slot_reclamation(self):
        self.source('local i:i64=0 while i<1000 do scoped b:spool=spool.new(8) if not spool.valid(b) then return 1 end i=i+1 end scoped a:spool=spool.new(-1) scoped c:spool=spool.new(16777217) print(spool.valid(a)) print(spool.valid(c))');self.output('false\nfalse\n')
    def test_nested_scope_shadowing_and_returns(self):
        self.source('function f(n:i64)->i64 scoped b:spool=spool.new(8) spool.append(b,"outer") if n==1 then scoped b:spool=spool.new(8) spool.append(b,"inner") spool.print(b) return spool.bytes(b) end spool.print(b) return spool.bytes(b) end function main()->i64 print(f(1)) print(f(0)) return 0 end',True);self.output('inner\n5\nouter\n5\n')
    def test_match_and_unit_fallthrough(self):
        self.source('union U A() B() end function f(u:U)->unit scoped b:spool=spool.new(8) match u then case U.A() then scoped c:spool=spool.new(8) spool.append(c,"A") spool.print(c) case U.B() then spool.append(b,"B") spool.print(b) end end function main()->i64 local i:i64=0 while i<100 do f(U.A()) f(U.B()) i=i+1 end return 0 end',True);self.output('A\nB\n'*100)
    def test_cleanup_interleaves_lifo_with_manual_defer(self):
        self.source('scoped a:spool=spool.new(8) defer spool.free(spool.new(8)) scoped c:spool=spool.new(8) print(spool.valid(a))')
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr)
        code=r.stdout.replace('static void k_spool_free(KSpool b) {','static void k_spool_free(KSpool b) { fprintf(stderr,"release=%" PRIu64 "\\n",b.id);',1)
        c=self.root/'trace.c';c.write_text(code);exe=self.root/'trace';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],check=True,capture_output=True)
        r=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'true\n','release=3\nrelease=2\nrelease=1\n'))
    def test_module_integration_and_import_alias_conflict(self):
        (self.root/'helper.aw').write_text('function f()->i64 scoped b:spool=spool.new(8) spool.i64(b,42) return spool.bytes(b) end')
        self.source('import helper as h function main()->i64 print(h.f()) return 0 end',True);self.output('2\n')
        self.reject_owner('import helper as h function main()->i64 scoped h:spool=spool.new(8) return 0 end',True,'E303')
    def test_mixed_cleanup_budgets(self):
        bindings=' '.join(f'scoped b{i}:spool=spool.new(1)' for i in range(64))
        self.source(bindings+' print(spool.valid(b63))');self.output('true\n')
        self.reject_owner(bindings+' defer spool.free(spool.new(1))',code='E210')
        funcs=' '.join('function f'+str(i)+'()->i64 '+bindings+' return 0 end' for i in range(4))
        self.reject_owner(funcs+' function main()->i64 scoped b:spool=spool.new(1) return 0 end',True,'E210')
    def test_scope_and_contextual_keyword(self):
        self.reject_owner('if true then scoped b:spool=spool.new(8) end print(spool.valid(b))',code='E200')
        self.source('local scoped:i64=1');r=self.invoke('check');self.assertEqual(r.returncode,1);self.assertIn('E100',r.stderr)
    def test_read_before_normal_cleanup_and_returned_value(self):
        self.source('function f()->bool scoped b:spool=spool.new(8) return spool.valid(b) end function main()->i64 print(f()) return 0 end',True);self.output('true\n')
    def test_seed_and_nested_arguments_cannot_hide_escape(self):
        for body in ['print(array.length([b;2]))','local c:spool=spool.new(spool.bytes(b)) local alias:spool=b','local a:[spool;1]=[b] print(spool.valid(a[0]))']:
            self.reject_owner('scoped b:spool=spool.new(8) '+body)
    def test_zero_capacity_is_valid_and_slot_exhaustion_is_recoverable(self):
        self.source('scoped z:spool=spool.new(0) print(spool.valid(z)) local i:i64=0 while i<100 do if true then '+ ' '.join(f'scoped b{k}:spool=spool.new(1)' for k in range(63))+' if true then scoped unavailable:spool=spool.new(1) if spool.valid(unavailable) then return 1 end end end i=i+1 end print(spool.valid(z))');self.output('true\ntrue\n')
    def test_deterministic_verified_c(self):
        self.source('scoped b:spool=spool.new(8) spool.append(b,"ok")');r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,self.invoke('emit-c').stdout);self.assertIn('if (k_spool_valid(k_v',r.stdout)
for name in Builders.__dict__:
    if name.startswith('test_') and name not in ScopedOwners.__dict__:setattr(ScopedOwners,name,None)
del Builders
if __name__=='__main__':unittest.main()

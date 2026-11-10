"""Restricted direct-call owning spool parameters with callee cleanup."""
import json,os,shutil,subprocess,unittest
from pathlib import Path
from native_features import supports_version
from test_builders import Builders,ROOT
KCC=Path(os.environ.get('Awl_OWN_PARAMS_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
@unittest.skipUnless(supports_version(KCC,(0,13,0)),'requires native0.13.0 owning parameters')
class OwnParams(Builders):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def reject_own(self,s,code='E222'):
        self.source(s,True);r=self.invoke('check','--diagnostic-format','json');self.assertEqual(r.returncode,1,r.stderr);self.assertEqual(json.loads(r.stderr)['diagnostics'][0]['code'],code,r.stderr)
    def test_example_o0_o3(self):
        shutil.copytree(ROOT/'examples/own-params',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.output('frame=99999\n100000 owning calls: callee releases builders\n1088890\nUnavailable handles transfer safely\nfalse\n',opt)
    def test_direct_unit_status_and_return_call(self):
        self.source('function finish(own b:spool)->i64 return spool.bytes(b) end function forward(own b:spool)->i64 return finish(move b) end function unit_finish(own b:spool)->unit spool.print(b) end function main()->i64 scoped a:spool=spool.new(8) spool.append(a,"abc") local n:i64=forward(move a) print(n) scoped b:spool=spool.new(8) spool.append(b,"taken") unit_finish(move b) return 0 end',True);self.output('3\ntaken\n')
    def test_recursive_forwarding_cleans_only_at_final_owner(self):
        self.source('function forward(own b:spool,n:i64)->i64 if n==0 then return spool.capacity(b) end return forward(move b,n-1) end function main()->i64 scoped b:spool=spool.new(16) local n:i64=forward(move b,8) print(n) return 0 end',True);self.output('16\n')
    def test_reject_use_after_call_double_move_and_assignment(self):
        for body in ['print(spool.valid(a))','take(move a)','scoped after:spool=move a']:
            self.reject_own('function take(own b:spool)->unit end function main()->i64 scoped a:spool=spool.new(8) take(move a) '+body+' return 0 end','E221')
    def test_explicit_move_and_unique_source_required(self):
        for binding,arg in [('scoped a:spool=spool.new(8)','a'),('local a:spool=spool.new(8)','move a'),('','spool.new(8)')]:
            self.reject_own('function take(own b:spool)->unit end function main()->i64 '+binding+' take('+arg+') return 0 end')
        self.reject_own('function take(own b:spool)->unit end function bad(borrow b:spool)->unit take(move b) end function main()->i64 return 0 end')
    def test_callee_cannot_copy_return_free_or_reassign_owned_formal(self):
        for body in ['spool.free(b)','defer spool.free(b)','local c:spool=b','b=spool.new(8)']:
            self.reject_own('function bad(own b:spool)->unit '+body+' end function main()->i64 return 0 end','E220')
        self.reject_own('function bad(own b:spool)->spool return b end function main()->i64 return 0 end','E220')
    def test_owned_formal_can_move_into_local_and_borrow(self):
        self.source('function bytes(borrow b:spool)->i64 return spool.bytes(b) end function f(own b:spool)->i64 scoped c:spool=move b spool.append(c,"xyz") return bytes(c) end function main()->i64 scoped a:spool=spool.new(8) local n:i64=f(move a) print(n) return 0 end',True);self.output('3\n')
    def test_reject_borrow_consume_alias_and_duplicate_consumption(self):
        self.reject_own('function f(borrow a:spool,own b:spool)->unit end function main()->i64 scoped b:spool=spool.new(8) f(b,move b) return 0 end')
        self.reject_own('function f(own a:spool,borrow b:spool)->unit end function main()->i64 scoped b:spool=spool.new(8) f(move b,b) return 0 end','E221')
        self.reject_own('function f(own a:spool,own b:spool)->unit end function main()->i64 scoped b:spool=spool.new(8) f(move b,move b) return 0 end','E221')
    def test_distinct_borrow_and_own_parameters_and_positions(self):
        self.source('function f(n:i64,borrow a:spool,own b:spool)->i64 spool.i64(a,n) return spool.capacity(b) end function main()->i64 scoped a:spool=spool.new(8) scoped b:spool=spool.new(16) local n:i64=f(42,a,move b) print(n) spool.print(a) return 0 end',True);self.output('16\n42\n')
    def test_no_hidden_transfers_or_outer_block_moves(self):
        header='function take(own b:spool)->i64 return 0 end function main()->i64 scoped a:spool=spool.new(8) '
        for body in ['if take(move a)==0 then end','while take(move a)==1 do end','print(take(move a))','local n:i64=1+take(move a)','while false do take(move a) end','while false do if true then local a:i64=take(move a) end end']:
            self.reject_own(header+body+' return 0 end','E225' if body.startswith('while false') else 'E222')
    def test_loop_local_handoffs_release_every_iteration(self):
        self.source('function take(own b:spool)->bool return spool.valid(b) end function main()->i64 local i:i64=0 while i<1000 do scoped b:spool=spool.new(8) local ok:bool=take(move b) if not ok then return 1 end i=i+1 end print(i) return 0 end',True);self.output('1000\n')
    def test_unavailable_descriptor_and_zero_capacity_are_handled(self):
        self.source('function available(own b:spool)->bool return spool.valid(b) end function main()->i64 scoped a:spool=spool.new(-1) local av:bool=available(move a) print(av) scoped b:spool=spool.new(0) local bv:bool=available(move b) print(bv) return 0 end',True);self.output('false\ntrue\n')
    def test_exact_release_order_and_no_double_release(self):
        self.source('function take(own a:spool,own b:spool)->unit scoped c:spool=spool.new(8) end function main()->i64 scoped a:spool=spool.new(8) scoped b:spool=spool.new(8) take(move a,move b) print("returned") return 0 end',True)
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);c=self.root/'trace.c';c.write_text(r.stdout.replace('static void k_spool_free(KSpool b) {','static void k_spool_free(KSpool b) { fprintf(stderr,"release=%" PRIu64 "\\n",b.id);',1));exe=self.root/'trace';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],capture_output=True,check=True);r=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'returned\n','release=3\nrelease=2\nrelease=1\n'))
    def test_module_alias_conflict_and_contextual_own_name(self):
        (self.root/'h.aw').write_text('function own(own b:spool)->i64 return spool.capacity(b) end')
        self.source('import h as h function own(own:i64)->i64 return own+1 end function main()->i64 scoped own:spool=spool.new(8) local n:i64=h.own(move own) print(n) print(own(41)) return 0 end',True);self.output('8\n42\n')
        self.reject_own('import h as h function bad(own h:spool)->unit end function main()->i64 return 0 end','E303')
    def test_type_and_cleanup_budget_policy(self):
        for ty in ['i64','bool','string','[spool;1]']:
            self.reject_own('function bad(own b:'+ty+')->unit end function main()->i64 return 0 end','E220')
        params=','.join('own b'+str(i)+':spool' for i in range(65))
        self.reject_own('function too_many('+params+')->unit end function main()->i64 return 0 end','E210')
        params=','.join('own b'+str(i)+':spool' for i in range(64))
        self.reject_own('function too_many('+params+')->unit scoped c:spool=spool.new(8) end function main()->i64 return 0 end','E210')
        functions=' '.join('function many'+str(i)+'('+params+')->unit end' for i in range(4))
        self.reject_own(functions+' function main()->i64 scoped extra:spool=spool.new(8) return 0 end','E210')
    def test_deterministic_c_for_unused_own_parameter(self):
        self.source('function unused(own b:spool)->unit end function main()->i64 return 0 end',True);r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,self.invoke('emit-c').stdout);self.assertIn('k_spool_valid',r.stdout);self.output('')
for name in Builders.__dict__:
    if name.startswith('test_') and name not in OwnParams.__dict__:setattr(OwnParams,name,None)
del Builders
if __name__=='__main__':unittest.main()

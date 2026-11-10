"""Exhaustive match ownership joins and symbol-safe arm patterns."""
import os,shutil,unittest,subprocess
from pathlib import Path
from native_features import supports_version
from test_owned_results import OwnedResults,ROOT
KCC=Path(os.environ.get('Awl_MATCH_JOINS_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
DECL='union Route First(n:i64) Second() Third() end '
def arms(a='',b='',c='',binder='n'):
    return 'match r then case Route.First('+binder+') then '+a+' case Route.Second() then '+b+' case Route.Third() then '+c+' end '
@unittest.skipUnless(supports_version(KCC,(0,16,0)),'requires native0.16 match ownership')
class MatchJoins(OwnedResults):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def program_source(self,body):return DECL+'function take(own b:spool)->i64 return spool.bytes(b) end function main()->i64 scoped a:spool=spool.new(8) local r:Route=Route.First(42) '+body+' return 0 end'
    def reject_join(self,body,code='E221'):self.reject_result(self.program_source(body),code)
    def test_example_o0_o3(self):
        shutil.copytree(ROOT/'examples/match-joins',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.output('frame=99999 / draw\n100000 match routes: moved or retained, one cleanup\n1555559\n',opt)
    def test_any_continuing_arm_blocks_later_use(self):
        for a,b,c in [('take(move a)','',''),('','scoped b:spool=move a',''),('','','take(move a)')]:
            for use in ['spool.print(a)','take(move a)','scoped b:spool=move a']:
                self.reject_join(arms(a,b,c)+use)
    def test_arm_order_never_changes_incoming_state(self):
        self.source(self.program_source(arms('take(move a)','take(move a)','take(move a)')),True);self.output('')
    def test_returning_arms_excluded_from_continuation(self):
        self.source(DECL+'function take(own b:spool)->unit end function f(r:Route)->i64 scoped a:spool=spool.new(8) spool.append(a,"kept") '+arms('take(move a) return 1','scoped b:spool=move a return 2','')+'spool.print(a) return 3 end function main()->i64 print(f(Route.First(0))) print(f(Route.Second())) print(f(Route.Third())) return 0 end',True);self.output('1\n2\nkept\n3\n')
    def test_pattern_shadow_is_not_outer_owner(self):
        self.source(self.program_source(arms('print(a)','','',binder='a')+'print(spool.capacity(a))'),True);self.output('42\n8\n')
        self.reject_join(arms('take(move a)','','',binder='a'),'E222')
    def test_arm_local_shadow_does_not_resurrect_consumed_outer(self):
        for b in ['take(move a) local a:i64=1','scoped a:spool=move a','scoped b:spool=move a scoped a:spool=spool.new(8)']:
            self.reject_join(arms(b)+'spool.print(a)')
    def test_fresh_arm_shadow_does_not_consume_outer(self):
        self.source(self.program_source(arms('scoped a:spool=spool.new(8) take(move a)')+'print(spool.capacity(a))'),True);self.output('8\n')
    def test_nested_if_match_states_compose(self):
        self.reject_join('if true then '+arms('take(move a)')+'end spool.print(a)')
        self.reject_join(arms('if true then take(move a) end')+'spool.print(a)')
        self.reject_join(arms(arms('take(move a)'))+'spool.print(a)')
    def test_loop_barrier_not_bypassed_by_match(self):
        self.reject_join('while false do '+arms('take(move a)')+'end','E225')
        self.reject_join(arms('while false do if true then take(move a) end end'),'E225')
    def test_loop_local_owners_can_dispatch_each_iteration(self):
        self.source(DECL+'function take(own b:spool)->unit end function main()->i64 local i:i64=0 while i<1000 do scoped a:spool=spool.new(8) local r:Route=Route.First(i) '+arms('take(move a)','scoped b:spool=move a','')+'i=i+1 end print(i) return 0 end',True);self.output('1000\n')
    def test_unavailable_owner_transfers_or_retains(self):
        self.source(DECL+'function take(own b:spool)->unit print(spool.valid(b)) end function f(r:Route)->unit scoped a:spool=spool.new(-1) '+arms('take(move a)','scoped b:spool=move a print(spool.valid(b))','print(spool.valid(a))')+'end function main()->i64 f(Route.First(0)) f(Route.Second()) f(Route.Third()) return 0 end',True);self.output('false\nfalse\nfalse\n')
    def test_exhaustiveness_and_duplicate_arms_still_checked(self):
        for match in ['match r then case Route.First(n) then take(move a) end',arms()[:-4]+'case Route.First(_) then end']:
            self.reject_join(match,'E200')
    def test_owned_result_forwarding_from_arms(self):
        self.source(DECL+'function make(r:Route)->own spool scoped a:spool=spool.new(8) '+arms('return move a','return move a','return move a')+'end function main()->i64 scoped a:spool=make(Route.First(0)) print(spool.capacity(a)) return 0 end',True);self.output('8\n')
    def test_exactly_one_release_on_every_route(self):
        self.source(DECL+'function take(own b:spool)->unit end function f(r:Route)->unit scoped a:spool=spool.new(8) '+arms('take(move a)','scoped b:spool=move a','')+'end function main()->i64 f(Route.First(0)) f(Route.Second()) f(Route.Third()) print("done") return 0 end',True)
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);c=self.root/'trace.c';c.write_text(r.stdout.replace('static void k_spool_free(KSpool b) {','static void k_spool_free(KSpool b) { fprintf(stderr,"release=%" PRIu64 "\\n",b.id);',1));exe=self.root/'trace';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],capture_output=True,check=True);r=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'done\n','release=1\nrelease=2\nrelease=3\n'))
for name in OwnedResults.__dict__:
    if name.startswith('test_') and name not in MatchJoins.__dict__:setattr(MatchJoins,name,None)
del OwnedResults
if __name__=='__main__':unittest.main()

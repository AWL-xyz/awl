"""Definitely-empty owner reinitialization; may-moved is not enough."""
import os,shutil,unittest,subprocess
from pathlib import Path
from native_features import supports_version
from test_owned_results import OwnedResults,ROOT
KCC=Path(os.environ.get('Awl_REINIT_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
H='function take(own a:spool)->unit end function make()->own spool scoped b:spool=spool_new(16) return move b end '
@unittest.skipUnless(supports_version(KCC,(0,17,0)),'requires native0.17 owner reinitialization')
class Reinit(OwnedResults):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def run_body(self,body,out=''):
        self.source(H+'function main()->i64 scoped a:spool=spool_new(8) '+body+' return 0 end',True);self.output(out)
    def bad(self,body,code='E224'):
        self.reject_result(H+'function main()->i64 scoped a:spool=spool_new(8) '+body+' return 0 end',code)
    def test_example_o0_o3(self):
        shutil.copytree(ROOT/'examples/reinit',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.output('restored=99999\n100000 owner reinitializations: original cleanup slot\n2477780\n',opt)
    def test_reinit_after_scoped_move_and_owning_call(self):
        self.run_body('scoped b:spool=move a a=make() print(spool_capacity(a)) take(move a) a=spool_new(0) print(spool_valid(a))','16\ntrue\n')
    def test_all_if_paths_empty_allow_reinit(self):
        self.run_body('if true then take(move a) else scoped b:spool=move a end a=make() print(spool_capacity(a))','16\n')
    def test_partial_if_move_not_definitely_empty(self):
        for body in ['if true then take(move a) end','if false then else take(move a) end']:
            self.bad(body+' a=make()')
    def test_returned_path_excluded_from_definite_join(self):
        self.run_body('if false then return 1 else take(move a) end a=make() print(spool_capacity(a))','16\n')
    def test_reinit_in_both_if_arms_restores_use_after_join(self):
        self.run_body('take(move a) if true then a=make() else a=spool_new(24) end print(spool_valid(a))','true\n')
    def test_one_refilled_arm_blocks_use_and_second_overwrite(self):
        self.bad('take(move a) if true then a=make() end a=make()')
        self.bad('take(move a) if true then a=make() end spool_print(a)','E221')
    def test_match_definite_empty_and_refill_joins(self):
        self.source('union R A(n:i64) B() end '+H+'function main()->i64 scoped a:spool=spool_new(8) match R.A(1) then case R.A(n) then take(move a) case R.B() then take(move a) end a=make() print(spool_capacity(a)) take(move a) match R.B() then case R.A(n) then a=make() case R.B() then a=spool_new(24) end print(spool_capacity(a)) return 0 end',True);self.output('16\n24\n')
    def test_match_pattern_shadow_preserves_hidden_empty_state(self):
        self.source('union R A(n:i64) B() end '+H+'function main()->i64 scoped a:spool=spool_new(8) take(move a) match R.A(42) then case R.A(a) then print(a) case R.B() then end a=make() print(spool_capacity(a)) return 0 end',True);self.output('42\n16\n')
    def test_moving_then_shadowing_preserves_definite_empty(self):
        self.run_body('if true then take(move a) local a:i64=1 else scoped a:spool=move a end a=make() print(spool_capacity(a))','16\n')
    def test_reject_live_or_borrowed_overwrite(self):
        self.bad('a=make()','E220')
        self.reject_result('function f(borrow a:spool)->unit a=spool_new(8) end function main()->i64 return 0 end','E220')
    def test_reject_alias_manual_or_move_rhs(self):
        for rhs in ['move a','a','spool_snapshot(a)']:
            self.bad('take(move a) a='+rhs)
        self.bad('local b:spool=spool_new(8) take(move a) a=b')
    def test_outer_empty_owner_cannot_refill_inside_loop(self):
        self.bad('take(move a) while false do a=make() end','E225')
        self.bad('take(move a) while false do if true then a=make() end end','E225')
    def test_unavailable_and_repeated_straight_line_refill(self):
        self.run_body('take(move a) a=spool_new(-1) print(spool_valid(a)) take(move a) a=make() print(spool_valid(a))','false\ntrue\n')
    def test_original_cleanup_slot_releases_latest_owner_once(self):
        self.source(H+'function main()->i64 scoped a:spool=spool_new(8) take(move a) a=make() take(move a) a=spool_new(0) print("done") return 0 end',True)
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);c=self.root/'trace.c';c.write_text(r.stdout.replace('static void k_spool_free(KSpool b) {','static void k_spool_free(KSpool b) { fprintf(stderr,"release=%" PRIu64 "\\n",b.id);',1));exe=self.root/'trace';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],capture_output=True,check=True);r=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'done\n','release=1\nrelease=2\nrelease=3\n'))
for name in OwnedResults.__dict__:
    if name.startswith('test_') and name not in Reinit.__dict__:setattr(Reinit,name,None)
del OwnedResults
if __name__=='__main__':unittest.main()

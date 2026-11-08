"""Entry-state-preserving ownership loops, not arbitrary fixed-point inference."""
import os,shutil,unittest,subprocess
from pathlib import Path
from native_features import supports_version
from test_owned_results import OwnedResults,ROOT
KCC=Path(os.environ.get('Awl_LOOP_OWNERS_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
H='function take(own a:spool)->unit end function make()->own spool scoped b:spool=spool_new(16) return move b end '
@unittest.skipUnless(supports_version(KCC,(0,18,0)),'requires native0.18 loop ownership')
class LoopOwners(OwnedResults):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def run_body(self,body,out=''):
        self.source(H+'function main()->i64 scoped a:spool=spool_new(8) '+body+' return 0 end',True);self.output(out)
    def bad(self,body,code='E225'):
        self.reject_result(H+'function main()->i64 scoped a:spool=spool_new(8) '+body+' return 0 end',code)
    def test_example_o0_o3(self):
        shutil.copytree(ROOT/'examples/loop-owners',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.output('frame=99999\n100000 loop-carried owners: state restored on every backedge\n1088890\nFinal owner remains live\nframe=100000\n',opt)
    def test_live_loop_consumes_and_refills(self):
        self.run_body('local i:i64=0 while i<1000 do take(move a) a=make() i=i+1 end print(spool_capacity(a))','16\n')
    def test_empty_entry_refill_consume_and_refill_after_loop(self):
        self.run_body('take(move a) local i:i64=0 while i<1000 do a=make() take(move a) i=i+1 end a=spool_new(24) print(spool_capacity(a))','24\n')
    def test_zero_iterations_preserve_entry(self):
        self.run_body('while false do take(move a) a=make() end print(spool_capacity(a))','8\n')
        self.run_body('take(move a) while false do a=make() take(move a) end a=spool_new(24) print(spool_capacity(a))','24\n')
    def test_unbalanced_backedge_rejected_even_false_condition(self):
        self.bad('while false do take(move a) end')
        self.bad('take(move a) while false do a=make() end')
    def test_partial_refill_rejected(self):
        self.bad('while false do take(move a) if true then a=make() end end')
        self.bad('while false do if true then take(move a) end end')
    def test_conditional_balanced_paths(self):
        self.run_body('local i:i64=0 while i<100 do if i%2==0 then take(move a) a=make() else scoped b:spool=move a a=spool_new(24) end i=i+1 end print(spool_capacity(a))','24\n')
    def test_match_balanced_paths(self):
        self.source('union R A(n:i64) B() end '+H+'function main()->i64 scoped a:spool=spool_new(8) local i:i64=0 while i<100 do match R.A(i) then case R.A(n) then take(move a) a=make() case R.B() then scoped b:spool=move a a=spool_new(24) end i=i+1 end print(spool_capacity(a)) return 0 end',True);self.output('16\n')
    def test_return_paths_do_not_require_backedge(self):
        self.source(H+'function f(flag:bool)->i64 scoped a:spool=spool_new(8) while flag do take(move a) return 3 end return spool_capacity(a) end function main()->i64 print(f(true)) print(f(false)) return 0 end',True);self.output('3\n8\n')
    def test_mixed_return_and_restored_backedge(self):
        self.source(H+'function f(flag:bool)->i64 scoped a:spool=spool_new(8) local i:i64=0 while i<2 do if flag then take(move a) return 3 else take(move a) a=make() end i=i+1 end return spool_capacity(a) end function main()->i64 print(f(true)) print(f(false)) return 0 end',True);self.output('3\n16\n')
    def test_nested_loops_each_restore_their_entry(self):
        self.run_body('local i:i64=0 while i<20 do local j:i64=0 while j<20 do take(move a) a=make() j=j+1 end i=i+1 end print(spool_capacity(a))','16\n')
        self.bad('while false do while false do take(move a) end a=make() end')
    def test_shadow_cannot_hide_unrestored_outer(self):
        self.bad('while false do take(move a) scoped a:spool=spool_new(8) end')
        self.run_body('while false do scoped a:spool=spool_new(8) take(move a) end print(spool_capacity(a))','8\n')
    def test_unavailable_descriptor_can_cycle(self):
        self.run_body('local i:i64=0 while i<100 do take(move a) a=spool_new(-1) i=i+1 end print(spool_valid(a))','false\n')
    def test_next_condition_can_borrow_restored_owner(self):
        self.run_body('local i:i64=0 while spool_valid(a) and i<5 do take(move a) a=make() i=i+1 end print(i)','5\n')
        self.bad('while spool_valid(a) do take(move a) end')
    def test_maybe_moved_entry_cannot_be_used(self):
        self.bad('if true then take(move a) end while false do take(move a) end','E221')
    def test_release_trace_includes_final_outer_owner(self):
        self.source(H+'function main()->i64 scoped a:spool=spool_new(8) local i:i64=0 while i<2 do take(move a) a=make() i=i+1 end print("done") return 0 end',True)
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);c=self.root/'trace.c';c.write_text(r.stdout.replace('static void k_spool_free(KSpool b) {','static void k_spool_free(KSpool b) { fprintf(stderr,"release=%" PRIu64 "\\n",b.id);',1));exe=self.root/'trace';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],capture_output=True,check=True);r=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'done\n','release=1\nrelease=2\nrelease=3\n'))
for name in OwnedResults.__dict__:
    if name.startswith('test_') and name not in LoopOwners.__dict__:setattr(LoopOwners,name,None)
del OwnedResults
if __name__=='__main__':unittest.main()

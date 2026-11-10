"""Path-sensitive if joins; lexical symbol identity and loop barriers."""
import os,shutil,unittest,json
from pathlib import Path
from native_features import supports_version
from test_owned_results import OwnedResults,ROOT
KCC=Path(os.environ.get('Awl_BRANCH_JOINS_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
@unittest.skipUnless(supports_version(KCC,(0,15,0)),'requires native0.15 conditional ownership')
class BranchJoins(OwnedResults):
    def invoke(self,command,*args):
        import subprocess
        return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def reject_join(self,body,code='E221'):
        self.reject_result('function take(own b:spool)->i64 return spool.bytes(b) end function main()->i64 scoped a:spool=spool.new(8) '+body+' return 0 end',code)
    def test_pipeline_o0_o3(self):
        shutil.copytree(ROOT/'examples/branch-joins',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.output('frame=99999 / odd\n100000 conditional handoffs: one owner per path\n1738890\n',opt)
    def test_either_branch_consumes_and_final_cleanup_skips_source(self):
        self.source('function take(own b:spool)->unit spool.print(b) end function f(flag:bool)->unit scoped a:spool=spool.new(8) spool.append(a,"owned") if flag then take(move a) else scoped b:spool=move a spool.print(b) end end function main()->i64 f(true) f(false) return 0 end',True);self.output('owned\nowned\n')
    def test_one_branch_move_makes_post_join_use_unavailable(self):
        for branch in ['if true then take(move a) end','if false then else take(move a) end','if true then scoped a:spool=move a end']:
            for later in ['spool.print(a)','take(move a)','scoped b:spool=move a']:
                self.reject_join(branch+' '+later)
    def test_shadow_after_consumption_does_not_erase_original_symbol_state(self):
        for inner in ['take(move a) local a:i64=7','scoped b:spool=move a scoped a:spool=spool.new(8)','if true then take(move a) end local a:i64=7']:
            self.reject_join('if true then '+inner+' end spool.print(a)')
    def test_fresh_inner_shadow_does_not_consume_outer(self):
        self.source('scoped a:spool=spool.new(8) spool.append(a,"outer") if true then scoped a:spool=spool.new(8) scoped b:spool=move a end spool.print(a)');self.output('outer\n')
    def test_returned_branch_not_in_continuing_join(self):
        self.source('function take(own b:spool)->unit end function f(flag:bool)->i64 scoped a:spool=spool.new(8) spool.append(a,"continue") if flag then take(move a) return 3 end spool.print(a) return 4 end function main()->i64 print(f(true)) print(f(false)) return 0 end',True);self.output('3\ncontinue\n4\n')
    def test_nested_conditional_joins_propagate(self):
        self.reject_join('if true then if false then else take(move a) end end spool.print(a)')
        self.reject_join('if true then take(move a) else if true then take(move a) end end take(move a)')
    def test_return_only_inner_path_leaves_other_path_live(self):
        self.source('function f(x:bool,y:bool)->i64 scoped a:spool=spool.new(8) if x then if y then scoped b:spool=move a return 1 end end return spool.capacity(a) end function main()->i64 print(f(true,true)) print(f(true,false)) print(f(false,true)) return 0 end',True);self.output('1\n8\n8\n')
    def test_loop_barrier_not_bypassed_by_nested_if(self):
        for body in ['while false do if true then take(move a) end end','while false do if true then scoped b:spool=move a end end','if true then while false do take(move a) end end']:
            self.reject_join(body,'E225')
    def test_loop_local_owner_can_branch_each_iteration(self):
        self.source('function take(own a:spool)->unit end function main()->i64 local i:i64=0 while i<1000 do scoped a:spool=spool.new(8) if i%2==0 then take(move a) else scoped b:spool=move a end i=i+1 end print(i) return 0 end',True);self.output('1000\n')
    def test_borrow_consume_overlap_still_rejected(self):
        self.reject_result('function f(borrow a:spool,own b:spool)->unit end function main()->i64 scoped a:spool=spool.new(8) if true then f(a,move a) end return 0 end','E222')
    def test_conditional_reassignment_remains_forbidden(self):
        self.reject_join('if true then take(move a) end a=spool.new(8)','E224')
for name in OwnedResults.__dict__:
    if name.startswith('test_') and name not in BranchJoins.__dict__:setattr(BranchJoins,name,None)
del OwnedResults
if __name__=='__main__':unittest.main()

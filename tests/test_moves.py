"""Restricted same-block scoped builder moves and use-after-move checking."""
import json,os,shutil,subprocess,unittest
from pathlib import Path
from native_features import supports_version
from test_builders import Builders,ROOT
KCC=Path(os.environ.get('Awl_MOVES_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
@unittest.skipUnless(supports_version(KCC,(0,12,0)),'requires native0.12.0 local moves')
class Moves(Builders):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def reject_move(self,s,full=False,code='E221'):
        self.source(s,full);r=self.invoke('check','--diagnostic-format','json');self.assertEqual(r.returncode,1,r.stderr);self.assertEqual(json.loads(r.stderr)['diagnostics'][0]['code'],code,r.stderr)
    def test_example_many_moves_o0_o3(self):
        self.source((ROOT/'examples/moves/main.aw').read_text(),True)
        for opt in ['0','3']:self.output('frame=99999 / moved\n100000 local moves: one release per owner\n1888890\nMoved unavailable descriptor remains unavailable\nfalse\n',opt)
    def test_transfer_and_chain_preserve_payload_and_identity(self):
        self.source('scoped a:spool=spool_new(16) spool_append(a,"hé") scoped b:spool=move a spool_append(b,"!") scoped c:spool=move b spool_print(c) print(spool_capacity(c))');self.output('hé!\n16\n')
    def test_borrow_after_move_and_before_move(self):
        self.source('function size(borrow b:spool)->i64 return spool_bytes(b) end function main()->i64 scoped a:spool=spool_new(8) spool_append(a,"abc") print(size(a)) scoped b:spool=move a print(size(b)) return 0 end',True);self.output('3\n3\n')
    def test_use_after_move_in_each_context(self):
        for body in ['print(spool_valid(a))','spool_append(a,"x")','local alias:spool=a','scoped c:spool=move a','scoped after:spool=move a','if true then print(spool_valid(a)) end','while false do print(spool_valid(a)) end']:
            with self.subTest(body=body):self.reject_move('scoped a:spool=spool_new(8) scoped b:spool=move a '+body)
    def test_reject_manual_and_borrowed_moves(self):
        self.reject_move('local a:spool=spool_new(8) scoped b:spool=move a')
        self.reject_move('function bad(borrow a:spool)->i64 scoped b:spool=move a return 0 end function main()->i64 return 0 end',True)
        self.reject_move('function bad(a:spool)->i64 scoped b:spool=move a return 0 end function main()->i64 return 0 end',True)
    def test_move_only_scoped_initializer(self):
        prefix='scoped a:spool=spool_new(8) '
        for body in ['local b:spool=move a','move a','spool_valid(move a)','local b:[spool;1]=[move a]']:
            with self.subTest(body=body):self.reject_move(prefix+body)
        self.reject_move('function bad()->spool scoped a:spool=spool_new(8) return move a end function main()->i64 return 0 end',True)
    def test_cross_block_moves_rejected_including_same_name_shadow(self):
        for body in ['while false do scoped b:spool=move a end','while false do if true then scoped a:spool=move a end end']:
            self.reject_move('scoped a:spool=spool_new(8) '+body,code='E225')
        self.reject_move('union U A() end function main()->i64 scoped a:spool=spool_new(8) while false do match U.A() then case U.A() then scoped b:spool=move a end end return 0 end',True,code='E225')
    def test_same_block_inside_loop_is_reinitialized(self):
        self.source('local i:i64=0 while i<1000 do scoped a:spool=spool_new(8) scoped b:spool=move a if not spool_valid(b) then return 1 end i=i+1 end print(i)');self.output('1000\n')
    def test_block_local_moves_do_not_change_outer_shadowed_owner(self):
        self.source('scoped a:spool=spool_new(8) spool_append(a,"outer") if true then scoped a:spool=spool_new(8) spool_append(a,"inner") scoped b:spool=move a spool_print(b) end spool_print(a)');self.output('inner\nouter\n')
    def test_unavailable_and_zero_capacity_moves(self):
        self.source('scoped a:spool=spool_new(-1) scoped b:spool=move a print(spool_valid(b)) scoped c:spool=spool_new(0) scoped d:spool=move c print(spool_valid(d))');self.output('false\ntrue\n')
    def test_trace_exactly_one_release_and_lifo(self):
        self.source('scoped a:spool=spool_new(8) scoped other:spool=spool_new(8) scoped b:spool=move a print(spool_valid(b))')
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);code=r.stdout.replace('static void k_spool_free(KSpool b) {','static void k_spool_free(KSpool b) { fprintf(stderr,"release=%" PRIu64 "\\n",b.id);',1)
        c=self.root/'trace.c';c.write_text(code);exe=self.root/'trace';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],check=True,capture_output=True);r=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'true\n','release=1\nrelease=2\n'))
    def test_move_then_early_return_and_unit_fallthrough(self):
        self.source('function f()->bool scoped a:spool=spool_new(8) scoped b:spool=move a return spool_valid(b) end function finish()->unit scoped a:spool=spool_new(8) scoped b:spool=move a spool_append(b,"x") end function main()->i64 local i:i64=0 while i<100 do finish() if not f() then return 1 end i=i+1 end print(i) return 0 end',True);self.output('100\n')
    def test_module_and_import_alias_conflict(self):
        (self.root/'helper.aw').write_text('function f()->i64 scoped a:spool=spool_new(8) scoped b:spool=move a return spool_capacity(b) end')
        self.source('import helper as h function main()->i64 print(h.f()) return 0 end',True);self.output('8\n')
        self.reject_move('import helper as h function main()->i64 scoped a:spool=spool_new(8) scoped h:spool=move a return 0 end',True,'E303')
    def test_cleanup_registration_limit_counts_move_destinations(self):
        source='scoped a0:spool=spool_new(1) '+' '.join(f'scoped a{i}:spool=move a{i-1}' for i in range(1,64))
        self.source(source+' print(spool_valid(a63))');self.output('true\n')
        self.reject_move(source+' scoped a64:spool=move a63',code='E210')
    def test_deterministic_c_zeroes_source_descriptor(self):
        self.source('scoped a:spool=spool_new(8) scoped b:spool=move a spool_print(b)');r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,self.invoke('emit-c').stdout);self.assertIn(' = (KSpool){0};',r.stdout);self.output('\n')
        self.source('function move(n:i64)->i64 return n+1 end function main()->i64 scoped move:spool=spool_new(8) scoped b:spool=move move print(spool_valid(b)) print(move(41)) return 0 end',True);self.output('true\n42\n')
    def test_pre_move_branch_does_not_consume_and_post_move_branch_checks(self):
        self.source('scoped a:spool=spool_new(8) if false then print(spool_valid(a)) end scoped b:spool=move a print(spool_valid(b))');self.output('true\n')
        self.reject_move('scoped a:spool=spool_new(8) scoped b:spool=move a if false then scoped c:spool=move a end')
for name in Builders.__dict__:
    if name.startswith('test_') and name not in Moves.__dict__:setattr(Moves,name,None)
del Builders
if __name__=='__main__':unittest.main()

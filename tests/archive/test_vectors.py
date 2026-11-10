"""Growable i64 vectors, owned resources, and native integer-argument CLI."""
import os,shutil,unittest,subprocess,random,json
try:import resource
except ImportError:resource=None
from pathlib import Path
from native_features import supports_version
from test_owned_results import OwnedResults,ROOT
KCC=Path(os.environ.get('Awl_VECTOR_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
@unittest.skipUnless(supports_version(KCC,(0,19,0)),'requires native0.19 growable vectors')
class Vectors(OwnedResults):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def run_args(self,exe,args):
        return subprocess.run([str(exe),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=30,preexec_fn=(lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0))) if resource is not None and os.name=='posix' else None)
    def test_growth_reserve_and_value_access_o0_o3(self):
        self.source('scoped v:int_vector=intvector.new(0) print(intvector.valid(v)) local i:i64=0 while i<10000 do if not intvector.push(v,i) then return 1 end i=i+1 end print(intvector.length(v)) print(intvector.capacity(v)) print(intvector.get(v,9999)) intvector.set(v,0,-42) print(intvector.get(v,0)) print(intvector.reserve(v,20000)) print(intvector.capacity(v))')
        for opt in ['0','3']:self.output('true\n10000\n16384\n9999\n-42\ntrue\n20000\n',opt)
    def test_insert_remove_pop_and_clear_reuses_capacity(self):
        self.source('scoped v:int_vector=intvector.new(0) print(intvector.insert(v,0,20)) print(intvector.insert(v,0,10)) print(intvector.insert(v,2,30)) print(intvector.insert(v,1,15)) print(intvector.remove(v,2)) print(intvector.pop(v)) print(intvector.get(v,1)) local cap:i64=intvector.capacity(v) intvector.clear(v) print(intvector.length(v)) print(intvector.capacity(v)==cap)');self.output('true\ntrue\ntrue\ntrue\n20\n30\n15\n0\ntrue\n')
    def test_seeded_mutation_oracle(self):
        rng=random.Random(1900);model=[];lines=['scoped v:int_vector=intvector.new(0)'];expected=[]
        for _ in range(1200):
            op=rng.choice(['push','insert','remove','pop','set','get']) if model else 'push';value=rng.randrange(-100000,100000)
            if op=='push':lines.append(f'if not intvector.push(v,{value}) then return 1 end');model.append(value)
            elif op=='insert':
                i=rng.randrange(len(model)+1);lines.append(f'if not intvector.insert(v,{i},{value}) then return 1 end');model.insert(i,value)
            elif op=='remove':
                i=rng.randrange(len(model));lines.append(f'print(intvector.remove(v,{i}))');expected.append(str(model.pop(i)))
            elif op=='pop':lines.append('print(intvector.pop(v))');expected.append(str(model.pop()))
            elif op=='set':
                i=rng.randrange(len(model));lines.append(f'intvector.set(v,{i},{value})');model[i]=value
            else:
                i=rng.randrange(len(model));lines.append(f'print(intvector.get(v,{i}))');expected.append(str(model[i]))
        lines.append('print(intvector.length(v))');expected.append(str(len(model)))
        for i,v in enumerate(model):lines.append(f'print(intvector.get(v,{i}))');expected.append(str(v))
        self.source(' '.join(lines));self.output('\n'.join(expected)+'\n')
    def test_cap_failure_atomic_and_existing_values_preserved(self):
        self.source('scoped v:int_vector=intvector.new(1) intvector.push(v,42) print(intvector.reserve(v,-1)) print(intvector.reserve(v,1048577)) print(intvector.capacity(v)) print(intvector.length(v)) print(intvector.get(v,0))');self.output('false\nfalse\n1\n1\n42\n')
    def test_growth_allocator_failure_injection_is_atomic(self):
        self.source('scoped v:int_vector=intvector.new(1) intvector.push(v,42) print(intvector.push(v,99)) print(intvector.insert(v,0,99)) print(intvector.length(v)) print(intvector.capacity(v)) print(intvector.get(v,0))')
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);old='int64_t *p=realloc(s->data,(size_t)capacity*sizeof(int64_t));';self.assertIn(old,r.stdout);c=self.root/'fail.c';c.write_text(r.stdout.replace(old,'int64_t *p=NULL;',1));exe=self.root/'fail';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],capture_output=True,check=True);r=self.run_args(exe,[]);self.assertEqual((r.returncode,r.stdout),(0,'false\nfalse\n1\n1\n42\n'),r.stderr)
    def test_element_limit_push_and_insert_fail_without_mutation(self):
        self.source('scoped v:int_vector=intvector.new(1048576) local i:i64=0 while i<1048576 do if not intvector.push(v,i) then return 1 end i=i+1 end print(intvector.push(v,7)) print(intvector.insert(v,0,7)) print(intvector.length(v)) print(intvector.get(v,1048575))');self.output('false\nfalse\n1048576\n1048575\n')
    def test_payload_budget_release_and_reallocation(self):
        lines=[f'local v{i}:int_vector=intvector.new(1048576)' for i in range(8)];lines+=['local missing:int_vector=intvector.new(1)','print(intvector.valid(missing))','intvector.free(v0)','local available:int_vector=intvector.new(1)','print(intvector.valid(available))','intvector.free(available)']+[f'intvector.free(v{i})' for i in range(1,8)];self.source(' '.join(lines));self.output('false\ntrue\n')
    def test_handle_table_cap_and_invalid_new(self):
        self.source(' '.join(f'scoped v{i}:int_vector=intvector.new(0)' for i in range(64))+' local missing:int_vector=intvector.new(0) print(intvector.valid(missing)) print(intvector.valid(intvector.new(-1))) print(intvector.valid(intvector.new(1048577)))');self.output('false\nfalse\nfalse\n')
    def test_bounds_empty_and_stale_traps(self):
        for body in ['intvector.get(v,0)','intvector.get(v,-1)','intvector.set(v,0,1)','intvector.pop(v)','intvector.remove(v,0)','intvector.insert(v,1,1)','intvector.insert(v,-1,1)','intvector.free(v) intvector.get(v,0)']:
            self.source('local v:int_vector=intvector.new(0) '+body);r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl int vector trap',r.stderr)
    def test_identity_survives_growth_but_never_reuses_released_id(self):
        self.source('local v:int_vector=intvector.new(1) local alias:int_vector=v intvector.push(v,7) intvector.push(v,8) print(intvector.get(alias,1)) intvector.free(v) print(intvector.valid(alias)) local other:int_vector=intvector.new(0) print(intvector.valid(alias)) intvector.free(other)');self.output('8\nfalse\nfalse\n')
    def test_owning_factory_transform_and_refill(self):
        self.source('function make()->own int_vector scoped v:int_vector=intvector.new(0) intvector.push(v,42) return move v end function transform(own v:int_vector)->own int_vector intvector.push(v,99) return move v end function main()->i64 scoped a:int_vector=make() scoped b:int_vector=transform(move a) a=make() print(intvector.get(b,1)) print(intvector.get(a,0)) return 0 end',True);self.output('99\n42\n')
    def test_borrowing_modules_and_mixed_resource_owned_parameters(self):
        (self.root/'help.aw').write_text('function append(borrow v:int_vector)->unit intvector.push(v,42) end function take(own v:int_vector,own b:spool)->i64 return intvector.length(v)+spool.bytes(b) end')
        self.source('import help as help function main()->i64 scoped v:int_vector=intvector.new(0) scoped b:spool=spool.new(8) help.append(v) spool.append(b,"abc") local n:i64=help.take(move v,move b) print(n) return 0 end',True);self.output('4\n')
    def test_reject_owner_copy_free_escape_and_manual_adoption(self):
        for body in ['local alias:int_vector=v','intvector.free(v)','defer intvector.free(v)','v=intvector.new(0)']:
            self.reject_result('function main()->i64 scoped v:int_vector=intvector.new(0) '+body+' return 0 end','E220')
        self.reject_result('function bad()->int_vector scoped v:int_vector=intvector.new(0) return v end function main()->i64 return 0 end','E220')
        self.reject_result('function main()->i64 local v:int_vector=intvector.new(0) scoped b:int_vector=move v return 0 end','E221')
    def test_reject_cross_resource_move_and_owned_calls(self):
        self.reject_result('function main()->i64 scoped v:int_vector=intvector.new(0) scoped b:spool=move v return 0 end','E200')
        self.reject_result('function take(own v:int_vector)->unit end function main()->i64 scoped b:spool=spool.new(0) take(move b) return 0 end','E200')
    def test_use_after_move_dropped_owned_result_and_alias_overlap(self):
        self.reject_result('function take(own v:int_vector)->unit end function main()->i64 scoped v:int_vector=intvector.new(0) take(move v) print(intvector.valid(v)) return 0 end','E221')
        self.reject_result('function make()->own int_vector scoped v:int_vector=intvector.new(0) return move v end function main()->i64 make() return 0 end','E223')
        self.reject_result('function f(borrow a:int_vector,own b:int_vector)->unit end function main()->i64 scoped v:int_vector=intvector.new(0) f(v,move v) return 0 end','E222')
    def test_loop_carried_vector_and_join_invariants(self):
        self.source('function take(own v:int_vector)->unit end function main()->i64 scoped v:int_vector=intvector.new(0) local i:i64=0 while i<10000 do intvector.push(v,i) if i%2==0 then take(move v) else scoped b:int_vector=move v end v=intvector.new(0) i=i+1 end print(intvector.valid(v)) return 0 end',True);self.output('true\n')
        self.reject_result('function take(own v:int_vector)->unit end function main()->i64 scoped v:int_vector=intvector.new(0) while false do take(move v) end return 0 end','E225')
    def test_normal_cleanup_and_deferred_manual_release(self):
        self.source('function take(own v:int_vector)->unit end function main()->i64 scoped a:int_vector=intvector.new(0) take(move a) a=intvector.new(0) local b:int_vector=intvector.new(0) defer intvector.free(b) print("done") return 0 end',True)
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);c=self.root/'trace.c';c.write_text(r.stdout.replace('static void k_int_vector_free(KIntVector v) {','static void k_int_vector_free(KIntVector v) { fprintf(stderr,"release=%" PRIu64 "\\n",v.id);',1).replace('return (KIntVector){s->id};','fprintf(stderr,"new=%" PRIu64 "\\n",s->id);return (KIntVector){s->id};',1));exe=self.root/'trace';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],capture_output=True,check=True);r=self.run_args(exe,[]);self.assertEqual((r.returncode,r.stdout),(0,'done\n'),r.stderr)
        events=[line.split('=') for line in r.stderr.splitlines()];self.assertEqual([event[0] for event in events],['new','release','new','new','release','release']);created=[events[i][1] for i in [0,2,3]];self.assertEqual(len(set(created)),3);self.assertEqual([events[i][1] for i in [1,4,5]],[created[0],created[2],created[1]])
    def test_manual_array_descriptors_and_legacy_nominal_name(self):
        self.source('local v:int_vector=intvector.new(0) local a:[int_vector;2]=[v,v] intvector.push(a[1],42) print(intvector.get(a[0],0)) intvector.free(v)');self.output('42\n')
        r=subprocess.run([str(ROOT/'compiler/native/bin/kcc'),'check',str(ROOT/'examples/hello.aw')],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
    def test_cli_sorts_external_integer_arguments(self):
        shutil.copytree(ROOT/'examples/apps/intstats',self.root,dirs_exist_ok=True);exe=self.program();args=[42,-7,19,0,42,-9223372036854775808,9223372036854775807];r=self.run_args(exe,args);self.assertEqual((r.returncode,r.stdout),(0,'count\n7\nminimum\n-9223372036854775808\nmaximum\n9223372036854775807\nsorted\n'+'\n'.join(map(str,sorted(args)))+'\n'),r.stderr)
    def test_cli_seeded_sort_oracle(self):
        shutil.copytree(ROOT/'examples/apps/intstats',self.root,dirs_exist_ok=True);exe=self.program();rng=random.Random(1901)
        for count in [1,2,31,1000]:
            values=[rng.randrange(-100000,100000) for _ in range(count)];r=self.run_args(exe,values);self.assertEqual((r.returncode,r.stdout),(0,f'count\n{count}\nminimum\n{min(values)}\nmaximum\n{max(values)}\nsorted\n'+'\n'.join(map(str,sorted(values)))+'\n'),r.stderr)
    def test_cli_usage_and_invalid_overflow_unicode_inputs(self):
        shutil.copytree(ROOT/'examples/apps/intstats',self.root,dirs_exist_ok=True);exe=self.program();r=self.run_args(exe,[]);self.assertEqual((r.returncode,r.stdout),(2,'usage: intstats INTEGER [INTEGER ...]\n'))
        for arg in ['', '+','--1',' 1','1x','9223372036854775808','-9223372036854775809','９']:
            r=self.run_args(exe,[arg]);self.assertEqual((r.returncode,r.stdout),(2,'invalid signed 64-bit integer argument\n'),r.stderr)
    def test_argument_validity_and_invalid_access_trap(self):
        self.source('print(arg.count()) print(arg.i64valid(-1)) print(arg.i64valid(0))');self.output('0\nfalse\nfalse\n')
        self.source('print(arg.i64(0))');r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl argument trap',r.stderr)
    def test_cli_accepts_signs_and_leading_zeroes(self):
        shutil.copytree(ROOT/'examples/apps/intstats',self.root,dirs_exist_ok=True);exe=self.program();r=self.run_args(exe,['+00042','-0','-00007']);self.assertEqual((r.returncode,r.stdout),(0,'count\n3\nminimum\n-7\nmaximum\n42\nsorted\n-7\n0\n42\n'),r.stderr)
    def test_deterministic_emission_and_project_keyword(self):
        self.source('scoped v:int_vector=intvector.new(0) intvector.push(v,42)');a=self.invoke('emit-c');self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(a.stdout,self.invoke('emit-c').stdout)
        self.source('function int_vector()->i64 return 0 end function main()->i64 return 0 end',True);r=self.invoke('check');self.assertNotEqual(r.returncode,0)
for name in OwnedResults.__dict__:
    if name.startswith('test_') and name not in Vectors.__dict__:setattr(Vectors,name,None)
del OwnedResults
if __name__=='__main__':unittest.main()

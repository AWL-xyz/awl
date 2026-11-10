from native_features import supports_version
"""Native typed text builders: reuse/reclamation, atomic errors and alias safety."""
import json,os,random,shutil,subprocess,tempfile,unittest
try:import resource
except ImportError:resource=None
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
KCC=Path(os.environ.get('Awl_BUILDER_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():return supports_version(KCC,(0, 8, 3))
def literal(s):return '"'+''.join('\\u{'+format(ord(c),'x')+'}' for c in s)+'"'

@unittest.skipUnless(available(),'requires native0.8.3 builder compiler')
class Builders(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix='Awl builders ');self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
        self.env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':os.environ.get('Awl_PLATFORM_TEST_CACHE',str(ROOT/'build/builders-cache'))}
    def source(self,s,full=False):
        (self.root/'main.aw').write_text(s if full else 'function main()->i64 '+s+' return 0 end')
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def program(self,opt='2'):
        out=self.root/'program'
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':
            r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);c=self.root/'out.c';c.write_text(r.stdout)
            r=subprocess.run([shutil.which('cc'),'-std=c11','-O'+opt,'-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-o',str(out)],capture_output=True,text=True,timeout=60)
        else:r=self.invoke('build','-o',out,'-O',opt)
        self.assertEqual(r.returncode,0,r.stderr);return out
    def run_program(self,opt='2'):
        exe=self.program(opt)
        def limits():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        return subprocess.run([str(exe)],env={**self.env,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'},capture_output=True,text=True,timeout=20,preexec_fn=limits)
    def output(self,expected,opt='2'):
        r=self.run_program(opt);self.assertEqual((r.returncode,r.stdout),(0,expected),r.stderr)
    def reject(self):
        r=self.invoke('check','--diagnostic-format','json');self.assertEqual(r.returncode,1,r.stderr);self.assertEqual(json.loads(r.stderr)['diagnostics'][0]['code'],'E200',r.stderr)
    def test_example_and_tagged_errors(self):
        shutil.copytree(ROOT/'examples/builders',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.output('Awl café | 42\n13\n14\nInvalid scalar: recovered\nframe=99999\n100000 updates, one reusable builder\n',opt)
    def test_fixed_capacity_and_atomic_failure(self):
        self.source('local b:spool=spool.new(4) print(spool.valid(b)) print(spool.capacity(b)) print(spool.append(b,"é")) print(spool.append(b,"🚀")) print(spool.codepoint(b,233u32)) print(spool.bytes(b)) print(spool.length(b)) spool.print(b) print(spool.append(b,"")) print(spool.append(b,"x")) spool.free(b)')
        self.output('true\n4\n0\n1\n0\n4\n2\néé\n0\n1\n')
    def test_invalid_scalar_is_recoverable_and_atomic(self):
        self.source('local b:spool=spool.new(4) spool.append(b,"x") print(spool.codepoint(b,55296u32)) print(spool.codepoint(b,1114112u32)) print(spool.codepoint(b,4294967295u32)) print(spool.length(b)) spool.print(b) spool.free(b)')
        self.output('2\n2\n2\n1\nx\n')
    def test_zero_capacity(self):
        self.source('local b:spool=spool.new(0) print(spool.valid(b)) print(spool.append(b,"")) print(spool.append(b,"x")) print(spool.codepoint(b,0u32)) print(spool.bytes(b)) spool.print(b) print(spool.snapshot(b)=="") spool.free(b)')
        self.output('true\n0\n1\n1\n0\n\ntrue\n')
    def test_snapshot_copies_and_survives_mutation_free_and_return(self):
        self.source('function make()->string local b:spool=spool.new(20) spool.append(b,"a\\0é🚀") local s:string=spool.snapshot(b) spool.clear(b) spool.append(b,"changed") spool.free(b) return string.slice(s,1,3) end function main()->i64 local s:string=make() print(s=="\\0é🚀") print(string.length(s)) print(string.bytes(s)) return 0 end',True)
        for opt in ['0','3']:self.output('true\n3\n7\n',opt)
    def test_copies_alias_not_ownership_and_valid_is_safe_on_stale(self):
        self.source('struct Holder item:spool end function pass(b:spool)->spool return b end function main()->i64 local b:spool=spool.new(8) local h:Holder=Holder(pass(b)) spool.append(h.item,"ok") spool.print(b) spool.free(h.item) print(spool.valid(b)) local c:spool=spool.new(8) print(spool.valid(b)) print(spool.valid(c)) spool.free(c) return 0 end',True)
        self.output('ok\nfalse\nfalse\ntrue\n')
    def test_released_handles_trap_without_memory_access(self):
        for op in ['spool.free(b)','spool.clear(b)','spool.append(b,"x")','spool.codepoint(b,65u32)','spool.i64(b,1)','spool.u64(b,1u64)','spool.print(b)','spool.snapshot(b)','spool.capacity(b)','spool.bytes(b)','spool.length(b)']:
            with self.subTest(op=op):
                self.source('local b:spool=spool.new(8) spool.free(b) '+op);r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl text builder trap',r.stderr);self.assertNotIn('AddressSanitizer',r.stderr);self.assertNotIn('runtime error:',r.stderr)
    def test_unavailable_handle_guard(self):
        self.source('print(spool.valid(spool.new(-1))) print(spool.valid(spool.new(16777217))) print(spool.valid(spool.new(9223372036854775807)))');self.output('false\nfalse\nfalse\n')
        self.source('local b:spool=spool.new(-1) spool.clear(b)');r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl text builder trap',r.stderr)
    def test_table_and_payload_caps_reclaimed(self):
        self.source('local i:i64=0 local first:spool=spool.new(0) while i<63 do if not spool.valid(spool.new(0)) then return 2 end i=i+1 end print(spool.valid(spool.new(0))) spool.free(first) local replacement:spool=spool.new(0) print(spool.valid(replacement)) print(spool.valid(first)) spool.free(replacement)')
        self.output('false\ntrue\nfalse\n')
        self.source('local a:spool=spool.new(16777216) local b:spool=spool.new(16777216) local c:spool=spool.new(16777216) local d:spool=spool.new(16777216) print(spool.valid(d)) print(spool.valid(spool.new(1))) spool.free(a) local e:spool=spool.new(16777216) print(spool.valid(e)) spool.free(b) spool.free(c) spool.free(d) spool.free(e)')
        self.output('true\nfalse\ntrue\n')
    def test_many_cycles_do_not_consume_string_region_or_handle_slots(self):
        self.source('local i:i64=0 while i<100000 do local b:spool=spool.new(128) if not spool.valid(b) then return 1 end if spool.append(b,"é frame=")!=0 then return 2 end if spool.i64(b,i)!=0 then return 3 end if spool.length(b)<9 then return 4 end spool.free(b) i=i+1 end print(i)')
        for opt in ['0','3']:self.output('100000\n',opt)
    def test_long_running_clear_reuse_without_string_allocations(self):
        self.source('local b:spool=spool.new(64) local i:i64=0 while i<1000000 do spool.clear(b) if spool.append(b,"count=")!=0 then return 1 end if spool.i64(b,i)!=0 then return 2 end i=i+1 end spool.print(b) spool.free(b)')
        for opt in ['0','3']:self.output('count=999999\n',opt)
    def test_decimal_boundaries_and_atomic_full(self):
        self.source('local b:spool=spool.new(64) spool.i64(b,-9223372036854775808) spool.append(b," ") spool.u64(b,18446744073709551615u64) spool.print(b) spool.clear(b) spool.i64(b,0) spool.u64(b,0u64) spool.print(b) spool.free(b) local tiny:spool=spool.new(1) print(spool.i64(tiny,-1)) print(spool.u64(tiny,10u64)) print(spool.bytes(tiny)) spool.free(tiny)')
        self.output('-9223372036854775808 18446744073709551615\n00\n1\n1\n0\n')
    def test_embedded_nul_exact_output(self):
        self.source('local b:spool=spool.new(10) spool.append(b,"a\\0b") spool.print(b) print(spool.length(b)) print(spool.bytes(b)) spool.free(b)');self.output('a\0b\n3\n3\n')
    def test_seeded_unicode_append_oracle(self):
        rng=random.Random(883);lines=['local b:spool=spool.new(256)'];expected=[]
        for _ in range(30):
            s=''.join(chr(rng.choice([0,65,233,769,0x4e16,0x1f680,0x10ffff])) for _ in range(rng.randrange(20)))
            cp=rng.choice([0,65,127,128,2047,2048,0xd7ff,0xe000,0xffff,0x10000,0x10ffff]);want=s+chr(cp)
            lines.extend(['spool.clear(b)',f'print(spool.append(b,{literal(s)}))',f'print(spool.codepoint(b,{cp}u32))','print(spool.bytes(b))','print(spool.length(b))',f'print(spool.snapshot(b)=={literal(want)})'])
            expected.extend(['0','0',str(len(want.encode())),str(len(want)),'true'])
        lines.append('spool.free(b)');self.source(' '.join(lines))
        for opt in ['0','3']:self.output('\n'.join(expected)+'\n',opt)
    def test_type_separation(self):
        for op in ['spool.free(1)','spool.free(buffer.new(1))','buffer.free(spool.new(1))','spool.append(spool.new(1),1)','spool.codepoint(spool.new(1),65)','print(spool.new(1))','i64(spool.new(1))','spool.new(1)+spool.new(1)','spool.new(1)==spool.new(1)','spool.new(true)']:
            with self.subTest(op=op):self.source(op);self.reject()
        self.source('local b:spool=0');self.reject()
    def test_no_platform_runtime_and_deterministic_emission(self):
        self.source('local b:spool=spool.new(4) spool.free(b)');r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);self.assertNotIn('sys/socket.h',r.stdout);self.assertIn('KSpool',r.stdout);self.assertEqual(r.stdout,self.invoke('emit-c').stdout)
        self.source('print(1)');r=self.invoke('emit-c');self.assertNotIn('KBuilderSlot',r.stdout)
    def test_private_runtime_accounting_failure_and_id_exhaustion(self):
        # Private emitted-C test TU, no exported compiler/runtime mutation API.
        self.source('local b:spool=spool.new(1) spool.free(b)')
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr)
        prefix='''#include <stdlib.h>
#include <assert.h>
static int fail_alloc,fail_registration;
static void *fixture_malloc(size_t n) {return fail_alloc?NULL:malloc(n);}
static int fixture_atexit(void (*f)(void)) {return fail_registration?-1:atexit(f);}
#define malloc fixture_malloc
#define atexit fixture_atexit
#define main fixture_program_main
'''
        suffix='''
#undef main
#undef malloc
#undef atexit
int main(void) {
    fail_registration=1;
    assert(!k_spool_valid(k_spool_new(32)));
    assert(!k_builder_cleanup_registered && k_builder_payload==0);
    fail_registration=0;fail_alloc=1;
    assert(!k_spool_valid(k_spool_new(32)));
    assert(k_builder_payload==0 && k_builder_next_id==1);
    fail_alloc=0;
    KSpool b=k_spool_new(32);
    assert(k_spool_valid(b) && k_builder_payload==32);
    for(int i=0;i<1000000;++i) {
        k_spool_clear(b);
        assert(k_spool_i64(b,i)==0);
    }
    assert(k_builder_payload==32 && k_string_heap_bytes==0 && k_string_heap_count==0);
    k_spool_free(b);
    assert(k_builder_payload==0 && !k_spool_valid(b));
    for(int i=0;i<100000;++i) {
        KSpool x=k_spool_new(32);assert(k_spool_valid(x));k_spool_free(x);
        assert(k_builder_payload==0);
    }
    k_builder_next_id=UINT64_MAX-1;
    KSpool last=k_spool_new(1);assert(k_spool_valid(last));
    assert(!k_spool_valid(k_spool_new(1)));
    k_spool_free(last);assert(!k_spool_valid(last));
    assert(k_builder_payload==0 && k_string_heap_count==0);
    puts("private runtime: allocator/atexit failures, accounting, reuse, ID exhaustion passed");
    return 0;
}
'''
        c=self.root/'private.c';c.write_text(prefix+r.stdout+suffix);exe=self.root/'private'
        flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],check=True,capture_output=True)
        r=subprocess.run([str(exe)],env=self.env,capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('accounting, reuse, ID exhaustion passed',r.stdout)
    def test_io_failure_recoverable(self):
        if not Path('/dev/full').exists():self.skipTest('/dev/full unavailable')
        self.source('function main()->i64 local b:spool=spool.new(4) spool.append(b,"x") local result:i64=spool.print(b) spool.free(b) return result end',True)
        exe=self.program()
        with open('/dev/full','wb') as sink:r=subprocess.run([str(exe)],stdout=sink,stderr=subprocess.PIPE,env=self.env,timeout=10)
        self.assertEqual((r.returncode,r.stderr),(3,b''))
if __name__=='__main__':unittest.main()

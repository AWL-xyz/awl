from native_features import supports_version
"""Native project UTF-8 strings. Python supplies independent scalar/byte oracles,
not compiler/runtime behavior. Product runs with no Python or host tool PATH."""
import json
import os
from pathlib import Path
import random
try:import resource
except ImportError:resource=None
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
KCC=Path(os.environ.get('Awl_STRING_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():return supports_version(KCC,(0, 8, 2))
def literal(s):return '"'+''.join('\\u{'+format(ord(c),'x')+'}' for c in s)+'"'

@unittest.skipUnless(available(),'requires native0.8.2 string compiler')
class Strings(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='Awl strings ');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':os.environ.get('Awl_PLATFORM_TEST_CACHE',str(ROOT/'build/strings-cache'))}
    def write(self,s,name='main.aw'):
        p=self.root/name;p.write_text(s);return p
    def invoke(self,command='check',*options):
        return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,options)],env=self.env,capture_output=True,text=True,timeout=120)
    def body(self,s):self.write('function main()->i64 '+s+' return 0 end')
    def run_program(self,opt='2'):
        exe=self.root/'program'
        if os.environ.get('Awl_STRING_SANITIZE')=='1':
            r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr)
            c=self.root/'out.c';c.write_text(r.stdout)
            r=subprocess.run([shutil.which('cc'),'-std=c11','-O'+opt,'-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-o',str(exe)],capture_output=True,text=True,timeout=60)
        else:r=self.invoke('build','-o',exe,'-O',opt)
        self.assertEqual(r.returncode,0,r.stderr)
        def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        return subprocess.run([str(exe)],env={**self.env,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'},capture_output=True,text=True,timeout=15,preexec_fn=no_core)
    def output(self,expected,opt='2'):
        r=self.run_program(opt);self.assertEqual((r.returncode,r.stdout),(0,expected),r.stderr)
    def reject(self,code):
        r=self.invoke('check','--diagnostic-format','json');self.assertEqual(r.returncode,1,r.stderr)
        d=json.loads(r.stderr)['diagnostics'][0];self.assertEqual(d['code'],code,r.stderr);return d
    def test_example_o0_o3(self):
        self.write((ROOT/'examples/strings/main.aw').read_text())
        for opt in ['0','3']:self.output('Hello, Awl 🚀!\n5\n8\n🚀\ntrue\nAnswer: 42\n',opt)
    def test_escapes_embedded_nul_and_exact_bytes(self):
        text='"\\\n\r\t\b\f\0é🚀'
        self.body('print("\\\"\\\\\\n\\r\\t\\b\\f\\0é\\u{1F680}") print(string.length('+literal(text)+')) print(string.bytes('+literal(text)+'))')
        # subprocess text=True normalizes CR; compare raw bytes separately.
        exe=self.root/'program';self.run_program()
        r=subprocess.run([str(exe)],env=self.env,capture_output=True)
        self.assertEqual((r.returncode,r.stdout),(0,text.encode()+b'\n'+str(len(text)).encode()+b'\n'+str(len(text.encode())).encode()+b'\n'))
    def test_scalar_not_grapheme_or_normalization(self):
        self.body('print(string.length("e\\u{301}")) print(string.bytes("e\\u{301}")) print("é"=="e\\u{301}") print(string.slice("aé🚀z",1,2))')
        self.output('2\n3\nfalse\né🚀\n')
    def test_empty_and_slice_boundaries(self):
        self.body('print("") print(string.length("")) print(string.bytes("")) print(""+"x") print("x"+"") print(string.slice("",0,0)=="") print(string.slice("é🚀",2,0)=="") print(string.slice("é🚀",0,2)) print(string.compare("","")==0)')
        self.output('\n0\n0\nx\nx\ntrue\ntrue\né🚀\ntrue\n')
    def test_equality_handles_nul_length_and_non_ascii(self):
        self.body('print("a\\0b"=="a\\0b") print("a\\0b"!="a\\0c") print("a"!="a\\0") print("🚀"==string.fromcodepoint(128640u32)) print(string.compare("a\\0b","a\\0c")) print(string.compare("é","e"))')
        self.output('true\ntrue\ntrue\ntrue\n-1\n1\n')
    def test_value_copy_struct_union_return_and_view_lifetime(self):
        self.write('''struct Box value:string size:u8 end
union Text Some(value:string) Empty() end
function make()->string local x:string="a"+"é🚀" return string.slice(x,1,2) end
function get(t:Text)->string match t then case Text.Some(v) then return v case Text.Empty() then return "" end end
function main()->i64 local a:string=make() local b:Box=Box(a,3u8) a="changed" local c:Box=b c.value=c.value+"!" print(b.value) print(c.value) print(get(Text.Some(b.value))) print(get(Text.Empty())) print(b.size) return 0 end''')
        for opt in ['0','3']:self.output('é🚀\né🚀!\né🚀\n\n3\n',opt)
    def test_cross_module_strings(self):
        self.write('struct Message text:string end function greet(s:string)->Message return Message("Hi "+s) end','greet.aw')
        self.write('import greet as g function main()->i64 local m:g.Message=g.greet("世界") print(m.text) return 0 end')
        self.output('Hi 世界\n')
    def test_left_to_right_single_evaluation(self):
        self.write('function left()->string print(1) return "a" end function right()->string print(2) return "b" end function main()->i64 print(left()+right()) print(left()==right()) return 0 end')
        self.output('1\n2\nab\n1\n2\nfalse\n')
    def test_integer_formatting_boundaries(self):
        self.body('print(string.fromi64(-9223372036854775808)) print(string.fromi64(9223372036854775807)) print(string.fromi64(0)) print(string.fromu64(18446744073709551615u64)) print(string.fromu64(0u64))')
        self.output('-9223372036854775808\n9223372036854775807\n0\n18446744073709551615\n0\n')
    def test_scalar_boundary_roundtrips(self):
        values=[0,1,127,128,2047,2048,0xd7ff,0xe000,0xffff,0x10000,0x10ffff]
        self.body(' '.join('local s'+str(i)+':string=string.fromcodepoint('+str(v)+'u32) print(string.length(s'+str(i)+')) print(string.bytes(s'+str(i)+')) print(string.codepoint(s'+str(i)+',0))' for i,v in enumerate(values)))
        self.output(''.join('1\n'+str(len(chr(v).encode()))+'\n'+str(v)+'\n' for v in values))
    def test_seeded_unicode_oracles(self):
        rng=random.Random(882);lines=[];expected=[]
        for _ in range(40):
            chars=[]
            for _ in range(rng.randrange(1,14)):
                while True:
                    cp=rng.randrange(0x110000)
                    if not 0xd800<=cp<=0xdfff:break
                chars.append(chr(cp))
            s=''.join(chars);data=s.encode();a=rng.randrange(len(s)+1);n=rng.randrange(len(s)-a+1);index=rng.randrange(len(s));byte=rng.randrange(len(data))
            lines.extend([f'print(string.length({literal(s)}))',f'print(string.bytes({literal(s)}))',f'print(string.codepoint({literal(s)},{index}))',f'print(string.byteat({literal(s)},{byte}))',f'print(string.slice({literal(s)},{a},{n})=={literal(s[a:a+n])})',f'print(({literal(s[:a])}+{literal(s[a:])})=={literal(s)})'])
            expected.extend([str(len(s)),str(len(data)),str(ord(s[index])),str(data[byte]),'true','true'])
        self.body(' '.join(lines))
        for opt in ['0','3']:self.output('\n'.join(expected)+'\n',opt)
    def test_bad_escapes_and_unterminated_literals(self):
        for text in ['"\\q"','"\\u1234"','"\\u{}"','"\\u{g}"','"\\u{0000000}"','"\\u{d800}"','"\\u{dfff}"','"\\u{110000}"','"missing','"line\nbreak"','"line\rbreak"','"escaped\\']:
            with self.subTest(text=text):self.body('print('+text+')');self.reject('E102')
    def test_invalid_source_utf8_rejected(self):
        for value in [b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\x80',b'\xe2\x82']:
            (self.root/'main.aw').write_bytes(b'function main()->i64 print("'+value+b'") return 0 end')
            self.reject('E008')
    def test_literal_budget(self):
        self.body('print(string.bytes("'+'a'*65536+'"))');self.output('65536\n')
        self.body('print("'+'a'*65537+'")');self.reject('E103')
        self.body('print("'+'é'*32769+'")');self.reject('E103')
    def test_type_and_operator_errors(self):
        for expression in ['"x"+1','1+"x"','"x"-"y"','"x"<"y"','"x"==1','i64("1")','string.length(1)','string.bytes()','string.byteat("x",0u64)','string.codepoint("x",true)','string.fromcodepoint(65)','string.slice("x",0,1u8)','string.compare("x",1)','string.fromi64(1u64)','string.fromu64(-1)','window.title(0,1)','"x".bytes']:
            with self.subTest(expression=expression):self.body('print('+expression+')');self.reject('E200')
    def test_checked_bounds_and_scalar_traps(self):
        for expression in ['string.byteat("",0)','string.byteat("é",-1)','string.byteat("é",2)','string.codepoint("",0)','string.codepoint("é",1)','string.codepoint("x",-1)','string.slice("x",-1,0)','string.slice("x",0,-1)','string.slice("x",2,0)','string.slice("x",1,1)','string.slice("x",0,9223372036854775807)','string.slice("x",9223372036854775807,1)','string.fromcodepoint(55296u32)','string.fromcodepoint(57343u32)','string.fromcodepoint(1114112u32)','string.fromcodepoint(4294967295u32)']:
            with self.subTest(expression=expression):
                self.body('print('+expression+')');r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl string trap',r.stderr);self.assertNotIn('AddressSanitizer',r.stderr);self.assertNotIn('runtime error:',r.stderr)
    def test_region_allocation_and_payload_caps(self):
        for code in ['local i:i64=0 while i<65537 do string.fromcodepoint(65u32) i=i+1 end','local s:string="x" local i:i64=0 while i<27 do s=s+s i=i+1 end']:
            self.body(code);r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl string trap',r.stderr);self.assertNotIn('AddressSanitizer',r.stderr);self.assertNotIn('runtime error:',r.stderr)
    def test_builtin_name_collisions(self):
        for name in ['string.length','string.fromcodepoint','window.title']:
            self.write('function '+name+'()->i64 return 0 end function main()->i64 return 0 end');self.reject('E210')
    def test_provenance_and_unicode_columns(self):
        code='function f()->i64 local s:string="é🚀" return true end'
        self.write(code,'unicode.aw');self.write('import unicode function main()->i64 return unicode.f() end')
        d=self.reject('E200');self.assertEqual(d['file'],str(self.root/'unicode.aw'));self.assertEqual(d['column'],code.index('return')+1)
    def test_string_only_runtime_has_no_platform_dependency(self):
        self.body('print("hi"+string.fromi64(2))');r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('Awl_STRINGS_RUNTIME',r.stdout);self.assertNotIn('sys/socket.h',r.stdout);self.assertNotIn('KStringAllocation',self.write_no_string_emit())
    def write_no_string_emit(self):
        self.body('print(42)');r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);return r.stdout
if __name__=='__main__':unittest.main()

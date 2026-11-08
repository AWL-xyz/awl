"""Regular-file I/O and external UTF-8 text. Contributor OS/fault oracles only."""
import os,json,shutil,subprocess,unittest,random
try:import resource
except ImportError:resource=None
from pathlib import Path
from native_features import supports_version
from test_builders import Builders,ROOT,literal
KCC=Path(os.environ.get('Awl_FILE_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
@unittest.skipUnless(supports_version(KCC,(0,22,0)),'requires native0.22 regular files')
class Files(Builders):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def args(self,exe,args):
        return subprocess.run([str(exe),*args],env=self.env,capture_output=True,text=True,timeout=30,preexec_fn=(lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0))) if resource else None)
    def path(self,name='data é🙂.bin'):return self.root/name
    def test_ignored_call_results_strict_c_single_evaluation(self):
        self.source('function side()->i64 print("side effect") return 7 end function main()->i64 scoped v:int_vector=int_vector_new(1) int_vector_push(v,side()) print(int_vector_get(v,0)) side() string_length("é") return 0 end',True)
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);c=self.root/'strict.c';c.write_text(r.stdout);exe=self.root/'strict'
        zig=ROOT/'build/Awl-linux-x86_64/libexec/zig/zig'
        r=subprocess.run([str(zig),'cc','-std=c11','-target','x86_64-linux-musl','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',str(c),'-o',str(exe)],capture_output=True,text=True,timeout=120);self.assertEqual(r.returncode,0,r.stderr)
        r=self.args(exe,[]);self.assertEqual((r.returncode,r.stdout),(0,'side effect\n7\nside effect\n'),r.stderr)
    def test_ignored_call_preserves_arithmetic_trap(self):
        self.source('function bad(n:i64)->i64 return 1/n end function main()->i64 bad(0) return 0 end',True)
        r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('trap',r.stderr)
    def test_utf8_arguments_and_scalar_counts(self):
        values=['','space here','café🙂','"quote"','back\\slash\\','+42','零']
        self.source('print(arg_count()) print(arg_text_valid(-1)) print(arg_text_valid(100)) local i:i64=0 while i<arg_count() do print(arg_text_valid(i)) print(arg_text(i)) print(string_length(arg_text(i))) i=i+1 end')
        r=self.args(self.program(),values);expected=str(len(values))+'\nfalse\nfalse\n'+''.join('true\n'+s+'\n'+str(len(s))+'\n' for s in values);self.assertEqual((r.returncode,r.stdout),(0,expected),r.stderr)
    def test_invalid_posix_argument_utf8_probe(self):
        self.source('print(arg_text_valid(0))');r=self.args(self.program(),[b'\xff']);self.assertEqual((r.returncode,r.stdout),(0,'false\n'),r.stderr)
    def test_roundtrip_binary_seek_flush_and_close(self):
        path=self.path();self.source('local f:i64=file_open('+literal(str(path))+',1) print(file_valid(f)) local b:i64=buffer_new(4) buffer_set(b,0,0u8) buffer_set(b,1,255u8) buffer_set(b,2,13u8) buffer_set(b,3,10u8) print(file_write(f,b,0,4)) print(file_size(f)) print(file_flush(f)) print(file_close(f)) print(file_valid(f)) f=file_open('+literal(str(path))+',0) print(file_size(f)) print(file_read(f,b,0,4)) print(file_read(f,b,0,4)) print(file_seek(f,1)) print(file_read(f,b,0,1)) print(buffer_get(b,0)) print(file_seek(f,-1)) print(file_close(f)) buffer_free(b)')
        self.output('true\n4\n4\n0\n0\nfalse\n4\n4\n0\n0\n1\n255\n-5\n0\n');self.assertEqual(path.read_bytes(),b'\0\xff\r\n')
    def test_exclusive_create_does_not_overwrite(self):
        path=self.path();path.write_bytes(b'keep me');self.source('print(file_open('+literal(str(path))+',1))');self.output('-3\n');self.assertEqual(path.read_bytes(),b'keep me')
    def test_explicit_truncate_mode(self):
        path=self.path();path.write_bytes(b'old contents');self.source('local f:i64=file_open('+literal(str(path))+',2) print(file_size(f)) print(file_close(f))');self.output('0\n0\n');self.assertEqual(path.read_bytes(),b'')
    def test_path_mode_and_missing_errors(self):
        self.source('print(file_open('+literal(str(self.path()))+',0)) print(file_open("",0)) print(file_open("x\\0y",0)) print(file_open("x",3)) print(file_valid(-1)) print(file_valid(0)) print(file_valid(buffer_new(0)))');self.output('-2\n-5\n-5\n-5\nfalse\nfalse\nfalse\n')
    def test_final_symlink_and_nonregular_rejected(self):
        original=self.path();original.write_bytes(b'kept');link=self.path('link');link.symlink_to(original);fifo=self.path('fifo');os.mkfifo(fifo)
        self.source('print(file_open('+literal(str(link))+',2)) print(file_open('+literal(str(fifo))+',0)) print(file_open('+literal(str(self.root))+',0))');self.output('-6\n-6\n-6\n');self.assertEqual(original.read_bytes(),b'kept')
    def test_32_slots_release_and_generation(self):
        path=self.path();path.write_bytes(b'');self.source('scoped ids:int_vector=int_vector_new(32) local i:i64=0 while i<32 do local f:i64=file_open('+literal(str(path))+',0) if f<0 then return 3 end int_vector_push(ids,f) i=i+1 end print(file_open('+literal(str(path))+',0)) local old:i64=int_vector_pop(ids) print(file_close(old)) print(file_valid(old)) local fresh:i64=file_open('+literal(str(path))+',0) print(fresh>old) print(file_valid(old)) file_close(fresh) while int_vector_length(ids)>0 do file_close(int_vector_pop(ids)) end');self.output('-7\n0\nfalse\ntrue\nfalse\n')
    def test_deferred_close_on_return_and_loop(self):
        path=self.path();path.write_bytes(b'');self.source('function once(path:string)->i64 local f:i64=file_open(path,0) if f<0 then return f end defer file_close(f) return f end function main()->i64 local i:i64=0 while i<100 do local old:i64=once('+literal(str(path))+') if old<0 or file_valid(old) then return 5 end i=i+1 end print("100 files released") return 0 end',True);self.output('100 files released\n')
    def test_wrong_access_mode_and_zero_count(self):
        path=self.path();path.write_bytes(b'xyz');self.source('local b:i64=buffer_new(0) defer buffer_free(b) local f:i64=file_open('+literal(str(path))+',0) print(file_read(f,b,0,0)) print(file_write(f,b,0,0)) print(file_flush(f)) file_close(f) f=file_open('+literal(str(path))+',2) print(file_write(f,b,0,0)) print(file_read(f,b,0,0)) print(file_close(f))');self.output('0\n-5\n-5\n0\n-5\n0\n')
    def test_file_buffer_offset_and_partial_eof(self):
        path=self.path();path.write_bytes(b'ABC');self.source('local f:i64=file_open('+literal(str(path))+',0) defer file_close(f) local b:i64=buffer_new(8) defer buffer_free(b) buffer_set(b,0,99u8) buffer_set(b,7,77u8) print(file_read(f,b,2,5)) print(buffer_get(b,0)) print(buffer_get(b,2)) print(buffer_get(b,4)) print(buffer_get(b,7))');self.output('3\n99\n65\n67\n77\n')
    def test_sparse_64bit_offset(self):
        path=self.path();self.source('local f:i64=file_open('+literal(str(path))+',1) defer file_close(f) local b:i64=buffer_new(1) defer buffer_free(b) buffer_set(b,0,42u8) print(file_seek(f,4294967296)) print(file_write(f,b,0,1)) print(file_size(f))');self.output('0\n1\n4294967297\n');self.assertEqual(path.stat().st_size,4294967297)
    def test_invalid_handles_and_ranges_trap(self):
        path=self.path();path.write_bytes(b'xyz')
        for body in ['file_size(0)','file_close(f) file_size(f)','file_read(f,b,-1,1)','file_read(f,b,0,-1)','file_read(f,b,4,1)','file_read(f,b,3,2)','file_read(f,0,0,0)']:
            self.source('local f:i64=file_open('+literal(str(path))+',0) local b:i64=buffer_new(4) '+body);r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl resource trap',r.stderr)
    def test_buffer_text_snapshot_and_capacity_failure(self):
        self.source('local b:i64=buffer_new(8) print(buffer_write_text(b,0,"é🙂")) print(buffer_text_valid(b,0,6)) local s:string=buffer_text(b,0,6) print(string_length(s)) print(buffer_write_text(b,7,"xx")) buffer_set(b,0,255u8) print(buffer_text_valid(b,0,6)) buffer_free(b) print(s)');self.output('6\ntrue\n2\n-5\nfalse\né🙂\n')
    def test_utf8_strict_invalid_sequences(self):
        sequences=[b'\x80',b'\xc0\x80',b'\xc1\xbf',b'\xc2',b'\xe0\x80\x80',b'\xed\xa0\x80',b'\xf0\x80\x80\x80',b'\xf4\x90\x80\x80',b'\xf5\x80\x80\x80',b'\xff',b'\xe2x\x80',b'\xf0\x9f\x99']
        lines=['local b:i64=buffer_new(4) defer buffer_free(b)']
        for seq in sequences:
            lines += [f'buffer_set(b,{i},{v}u8)' for i,v in enumerate(seq)];lines.append(f'print(buffer_text_valid(b,0,{len(seq)}))')
        self.source(' '.join(lines));self.output('false\n'*len(sequences))
    def test_buffer_text_invalid_data_and_bounds_trap(self):
        for body in ['buffer_set(b,0,255u8) buffer_text(b,0,1)','buffer_text_valid(b,1,1)','buffer_text(b,-1,0)','buffer_write_text(b,2,"")']:
            self.source('local b:i64=buffer_new(1) '+body);r=self.run_program();self.assertNotEqual(r.returncode,0);self.assertIn('Awl resource trap',r.stderr)
    def test_kcopy_application_random_binary_and_unicode_paths(self):
        shutil.copytree(ROOT/'examples/apps/kcopy',self.root,dirs_exist_ok=True);exe=self.program();data=random.Random(22).randbytes(200003);src=self.path();dst=self.path('copy 世界.bin');src.write_bytes(data);r=self.args(exe,[str(src),str(dst)]);self.assertEqual((r.returncode,r.stdout),(0,'bytes copied\n200003\n'),r.stderr);self.assertEqual(dst.read_bytes(),data);r=self.args(exe,[str(src),str(dst)]);self.assertEqual(r.returncode,4);self.assertEqual(dst.read_bytes(),data);r=self.args(exe,[str(src),str(src)]);self.assertEqual(r.returncode,4);self.assertEqual(src.read_bytes(),data)
    def test_textinfo_application_utf8_invalid_empty_oversize(self):
        shutil.copytree(ROOT/'examples/apps/textinfo',self.root,dirs_exist_ok=True);exe=self.program();path=self.path()
        for data,out,code in [('café🙂\0'.encode(),'bytes\n10\nUnicode scalars\n6\n',0),(b'','bytes\n0\nUnicode scalars\n0\n',0),(b'\xff','invalid UTF-8\n',5)]:
            path.write_bytes(data);r=self.args(exe,[str(path)]);self.assertEqual((r.returncode,r.stdout),(code,out),r.stderr)
        with path.open('wb') as f:f.truncate(8388609)
        r=self.args(exe,[str(path)]);self.assertEqual(r.returncode,4)
    def test_type_errors_and_release_whitelist(self):
        for body in ['file_open(1,0)','file_read(1,2,3)','buffer_write_text(1,0,2)','defer file_size(1)','defer file_read(1,2,3,4)']:
            self.source(body);r=self.invoke('check');self.assertEqual(r.returncode,1,r.stderr)
    def test_emission_dependencies_and_determinism(self):
        self.source('print("no file IO")');r=self.invoke('emit-c');self.assertNotIn('typedef struct {\n    int64_t id;int mode;',r.stdout)
        self.source('print(file_valid(0))');a=self.invoke('emit-c');self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(a.stdout,self.invoke('emit-c').stdout);self.assertIn('KFile',a.stdout)
for name in Builders.__dict__:
    if name.startswith('test_') and name not in Files.__dict__:setattr(Files,name,None)
del Builders
if __name__=='__main__':unittest.main()

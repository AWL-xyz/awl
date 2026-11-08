"""Actual Awl Pixelboard storage modules; Python is only an independent oracle."""
import os,random,shutil,subprocess,unittest,zlib
from pathlib import Path
from native_features import supports_version
from test_builders import Builders,ROOT,literal
KCC=Path(os.environ.get('Awl_PERSISTENCE_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def encode(colors):
 data=b'KPBOARD1'+b''.join(n.to_bytes(3,'big') for n in colors)
 return data+zlib.adler32(data).to_bytes(4,'big')
@unittest.skipUnless(supports_version(KCC,(0,23,0)),'requires native0.23 Pixelboard persistence')
class Persistence(Builders):
    def setUp(self):
        super().setUp();shutil.copy2(ROOT/'examples/apps/pixelboard/storage.aw',self.root/'storage.aw')
    def source(self,s,full=False):
        (self.root/'main.aw').write_text('import storage\n'+(s if full else 'function main()->i64 '+s+' return 0 end'))
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def seed(self,value='i*1234567%16777216'):
        return 'scoped cells:int_vector=int_vector_new(384) local i:i64=0 while i<384 do int_vector_push(cells,'+value+') i=i+1 end '
    def execute(self,exe,*args):return subprocess.run([str(exe),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=30)
    def test_native_platform_family_and_types(self):
        self.source('print(platform_kind())');self.output('1\n');self.source('platform_kind(1)');self.assertEqual(self.invoke('check').returncode,1)
    def test_save_roundtrip_matches_independent_adler_and_big_endian_rgb(self):
        path=self.root/'drawing é🙂.kpb';p=literal(str(path));self.source(self.seed()+'print(storage.save_new(cells,'+p+')) int_vector_set(cells,0,42) int_vector_set(cells,383,42) print(storage.load(cells,'+p+')) print(int_vector_get(cells,0)) print(int_vector_get(cells,383))')
        self.output('0\n0\n0\n'+str(383*1234567%16777216)+'\n');self.assertEqual(path.read_bytes(),encode([i*1234567%16777216 for i in range(384)]))
    def test_exclusive_refusal_preserves_existing_file_and_canvas(self):
        path=self.root/'keep.kpb';path.write_bytes(b'important');self.source(self.seed('7')+'print(storage.save_new(cells,'+literal(str(path))+')) print(int_vector_get(cells,0))');self.output('-3\n7\n');self.assertEqual(path.read_bytes(),b'important')
    def test_invalid_model_does_not_create_output(self):
        path=self.root/'invalid.kpb'
        for color in [-1,16777216]:
            self.source(self.seed('7')+f'int_vector_set(cells,383,{color}) print(storage.save_new(cells,'+literal(str(path))+'))');self.output('-5\n');self.assertFalse(path.exists())
        self.source('scoped cells:int_vector=int_vector_new(0) print(storage.save_new(cells,'+literal(str(path))+'))');self.output('-5\n');self.assertFalse(path.exists())
    def loader(self):
        self.source(self.seed('66051')+'local status:i64=storage.load(cells,arg_text(0)) print(status) local same:bool=true i=0 while i<384 do if int_vector_get(cells,i)!=66051 then same=false end i=i+1 end print(same)');return self.program()
    def test_invalid_files_leave_every_cell_unchanged(self):
        exe=self.loader();path=self.root/'bad.kpb';good=encode([0]*384);wrongmagic=b'XXXXXXXX'+good[8:1160];wrongversion=b'KPBOARD2'+good[8:1160];badpayload=bytearray(good);badpayload[500]^=128
        cases=[b'',good[:7],good[:8],good[:1160],good[:-1],good+b'x',good+b'x'*1024,bytes(badpayload),good[:-1]+bytes([good[-1]^1]),wrongmagic+zlib.adler32(wrongmagic).to_bytes(4,'big'),wrongversion+zlib.adler32(wrongversion).to_bytes(4,'big'),bytes(1164)]
        for data in cases:
            path.write_bytes(data);r=self.execute(exe,path);self.assertEqual((r.returncode,r.stdout),(0,'-5\ntrue\n'),r.stderr)
    def test_missing_and_symlink_fail_without_canvas_mutation(self):
        exe=self.loader();path=self.root/'missing';r=self.execute(exe,path);self.assertEqual((r.returncode,r.stdout),(0,'-2\ntrue\n'),r.stderr);target=self.root/'target';target.write_bytes(encode([0]*384));path.symlink_to(target);r=self.execute(exe,path);self.assertEqual((r.returncode,r.stdout),(0,'-6\ntrue\n'),r.stderr)
    def test_valid_random_rgb_files_and_checksum_oracle(self):
        self.source(self.seed('0')+'print(storage.load(cells,arg_text(0))) i=0 while i<384 do print(int_vector_get(cells,i)) i=i+1 end');exe=self.program();rng=random.Random(2300);path=self.root/'oracle.kpb'
        for colors in [[0]*384,[16777215]*384]+[[rng.randrange(16777216) for _ in range(384)] for _ in range(16)]:
            path.write_bytes(encode(colors));r=self.execute(exe,path);self.assertEqual((r.returncode,r.stdout),(0,'0\n'+''.join(str(n)+'\n' for n in colors)),r.stderr)
    def test_repeated_loads_release_file_and_buffer_slots(self):
        path=self.root/'repeat.kpb';path.write_bytes(encode([42]*384));self.source(self.seed('0')+'i=0 while i<500 do if storage.load(cells,'+literal(str(path))+')!=0 then return 4 end i=i+1 end print(int_vector_get(cells,383))');self.output('42\n')
    def test_shorter_model_load_fails_before_mutation(self):
        path=self.root/'valid.kpb';path.write_bytes(encode([0]*384));self.source('scoped cells:int_vector=int_vector_new(1) int_vector_push(cells,42) print(storage.load(cells,'+literal(str(path))+')) print(int_vector_get(cells,0))');self.output('-5\n42\n')
    def test_deterministic_module_emission(self):
        self.source(self.seed('0')+'print(storage.save_new(cells,"new.kpb"))');a=self.invoke('emit-c');self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(a.stdout,self.invoke('emit-c').stdout)
for name in Builders.__dict__:
    if name.startswith('test_') and name not in Persistence.__dict__:setattr(Persistence,name,None)
del Builders
if __name__=='__main__':unittest.main()

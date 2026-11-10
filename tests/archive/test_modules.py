from native_features import supports_version
"""Native project modules; not Python reference compiler functionality."""
import ctypes as C
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
KCC=Path(os.environ.get('Awl_MODULE_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():return supports_version(KCC,(0, 8, 1))
@unittest.skipUnless(available(),'requires native0.8.1 project compiler')
class Modules(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='Awl modules ');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':os.environ.get('Awl_PLATFORM_TEST_CACHE',str(ROOT/'build/modules-cache'))}
    def write(self,name,text):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
    def invoke(self,command='check',name='main.aw',*options):
        return subprocess.run([str(KCC),command,str(self.root/name),*map(str,options)],cwd=self.root.parent,env=self.env,capture_output=True,text=True,timeout=120)
    def run_main(self,expected,opt='2'):
        if os.environ.get('Awl_MODULE_SANITIZE')=='1':
            r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr)
            c=self.root/'out.c';c.write_text(r.stdout);exe=self.root/'out'
            subprocess.run([shutil.which('cc'),'-std=c11','-O'+opt,'-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-o',str(exe)],check=True,capture_output=True)
            r=subprocess.run([str(exe)],capture_output=True,text=True)
        else:r=self.invoke('run','main.aw','-O',opt)
        self.assertEqual((r.returncode,r.stdout),(0,expected),r.stderr)
    def reject(self,code,part='',command='check',*options):
        r=self.invoke(command,'main.aw','--diagnostic-format','json',*options)
        self.assertEqual(r.returncode,1,r.stderr)
        d=json.loads(r.stderr)['diagnostics'][0]
        self.assertEqual(d['code'],code,r.stderr);self.assertIn(part,d['message']);return d
    def test_alias_types_unions_and_native_codegen(self):
        shutil.copytree(ROOT/'examples/modules',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.run_main('10\n15\n3\n',opt)
        arena=json.loads(self.invoke('emit-checked-ast').stdout)
        self.assertEqual(len(arena['sources']),3)
        declarations=[n for n in arena['nodes'] if n['kind'] in ['struct','union','function']]
        self.assertEqual(len({n['value'] for n in declarations}),len(declarations))
        for n in arena['nodes']:
            self.assertLess(n['token'],len(arena['origins']))
    def test_default_alias_nested_path_and_cross_module_parameters(self):
        self.write('geometry/points.aw','struct P x:i64 end function move(p:P)->P return P(p.x+2) end')
        self.write('main.aw','import geometry.points function pass(p:points.P)->points.P return points.move(p) end function main()->i64 print(pass(points.P(40)).x) return 0 end')
        self.run_main('42\n')
    def test_global_names_are_isolated_and_missing_import_not_visible(self):
        self.write('a.aw','struct P x:i64 end function f()->i64 return 10 end')
        self.write('b.aw','struct P x:bool end function f()->i64 return 20 end')
        self.write('main.aw','import a import b function f()->i64 return 3 end function main()->i64 print(a.f()+b.f()+f()) return 0 end')
        self.run_main('33\n')
        self.write('main.aw','import a import b function main()->i64 return f() end')
        self.reject('E302','unknown module declaration f')
        self.write('main.aw','import a import b function main()->i64 return km_1_1() end')
        self.reject('E302','unknown module declaration km_1_1')
    def test_diamond_import_aliases_and_file_identity(self):
        self.write('common.aw','function value()->i64 return 7 end')
        self.write('a.aw','import common function value()->i64 return common.value() end')
        self.write('b.aw','import common function value()->i64 return common.value()+1 end')
        self.write('main.aw','import a import b import common as c import common as d function main()->i64 print(a.value()+b.value()+c.value()+d.value()) return 0 end')
        self.run_main('29\n')
        self.assertEqual(len(json.loads(self.invoke('emit-ast').stdout)['sources']),4)
        os.link(self.root/'common.aw',self.root/'same.aw')
        self.write('main.aw','import common import same function main()->i64 print(common.value()+same.value()) return 0 end')
        self.run_main('14\n');self.assertEqual(len(json.loads(self.invoke('emit-ast').stdout)['sources']),2)
    def test_direct_and_indirect_cycles(self):
        self.write('main.aw','import main function main()->i64 return 0 end')
        self.reject('E301','cyclic')
        self.write('main.aw','import a function main()->i64 return 0 end');self.write('a.aw','import b');self.write('b.aw','import a')
        d=self.reject('E301','cyclic');self.assertEqual(d['file'],str(self.root/'b.aw'))
        self.write('a.aw','import main')
        self.reject('E301','cyclic')
    def test_missing_file_nonregular_and_symlink_escape(self):
        self.write('main.aw','import absent function main()->i64 return 0 end')
        self.reject('E300','cannot resolve')
        (self.root/'absent.aw').mkdir();self.reject('E300','not a regular file')
        (self.root/'absent.aw').rmdir()
        with tempfile.TemporaryDirectory() as external:
            p=Path(external)/'outside.aw';p.write_text('function f()->i64 return 1 end')
            (self.root/'absent.aw').symlink_to(p)
            self.reject('E300','escapes project root')
    def test_alias_collisions_and_import_position(self):
        self.write('a.aw','function f()->i64 return 1 end')
        cases=[('import a import a','function main()->i64 return 0 end','E303'),
               ('import a as print','function main()->i64 return 0 end','E303'),
               ('import a','function a()->i64 return 1 end function main()->i64 return 0 end','E303'),
               ('import a','function main()->i64 local a:i64=1 return a end','E303'),
               ('import a','function f(a:i64)->i64 return a end function main()->i64 return 0 end','E303'),
               ('','function main()->i64 return 0 end import a','E300')]
        for imports,body,code in cases:
            with self.subTest(body=imports+body):self.write('main.aw',imports+' '+body);self.reject(code)
    def test_bad_members_types_and_arity(self):
        self.write('a.aw','struct P x:i64 end union U Yes(value:i64) No() end function f()->i64 return 1 end')
        for body,code in [('return a.absent()','E302'),('local p:a.f=a.P(1) return 0','E302'),('print(a.f(1)) return 0','E200'),('print(a.P(true).x) return 0','E200'),('print(a.U()) return 0','E302')]:
            self.write('main.aw','import a function main()->i64 '+body+' end');self.reject(code)
        self.write('b.aw','struct P x:i64 end')
        self.write('main.aw','import a import b function main()->i64 local p:a.P=b.P(1) return 0 end')
        d=self.reject('E200');self.assertIn('a.aw:P',d['message']);self.assertIn('b.aw:P',d['message']);self.assertNotIn('km_',d['message'])
    def test_imported_semantic_lexical_and_parse_diagnostics(self):
        self.write('main.aw','import bad function main()->i64 return bad.f() end')
        for source,code in [('-- Unicode comment: λ\nfunction f()->i64\n return true\nend','E200'),('function f()->i64 return @ end','E101'),('function f()->i64 return 1','E100')]:
            self.write('bad.aw',source);d=self.reject(code)
            self.assertEqual(d['file'],str(self.root/'bad.aw'))
            self.assertLessEqual(d['end'],len(source))
            if code=='E200':self.assertEqual(d['line'],3);self.assertEqual(d['column'],2)
    def test_duplicate_reserved_and_entry(self):
        self.write('a.aw','function f()->i64 return 1 end function f()->i64 return 2 end')
        self.write('main.aw','import a function main()->i64 return 0 end');self.reject('E210')
        self.write('a.aw','function print()->i64 return 1 end');self.reject('E210')
        self.write('a.aw','function f()->i64 return 1 end');self.write('main.aw','import a function other()->i64 return 0 end');self.reject('E201')
        self.write('a.aw','function main()->i64 return 3 end');self.write('main.aw','import a function main()->i64 print(a.main()) return 0 end');self.run_main('3\n')
    def test_protect_every_imported_source_and_preserve_old_output(self):
        p=self.write('a.aw','function value()->i64 return 9 end');before=p.read_bytes()
        self.write('main.aw','import a function main()->i64 print(a.value()) return 0 end')
        alias=self.root/'hardlink';os.link(p,alias)
        sym=self.root/'symlink';sym.symlink_to(p)
        for out in [p,alias,sym]:
            r=self.invoke('build','main.aw','-o',out);self.assertEqual(r.returncode,2,r.stderr);self.assertIn('refusing to overwrite source',r.stderr);self.assertEqual(p.read_bytes(),before)
        out=self.root/'old';out.write_bytes(b'old executable')
        self.write('a.aw','function value()->i64 return true end')
        self.reject('E200','', 'build','-o',out);self.assertEqual(out.read_bytes(),b'old executable')
    def test_depth_count_edges_and_aggregate_budgets(self):
        self.write('main.aw','import m0 function main()->i64 return 0 end')
        for i in range(33):self.write(f'm{i}.aw',f'import m{i+1}' if i<32 else '')
        self.reject('E300','depth')
        self.write('main.aw',' '.join(f'import m{i}' for i in range(64))+' function main()->i64 return 0 end')
        for i in range(64):self.write(f'm{i}.aw','')
        self.reject('E300','module count')
        self.write('main.aw','import a function main()->i64 return 0 end')
        self.write('a.aw','--'+'x'*1048575);self.reject('E001')
        self.write('a.aw','--'+'x'*600000);self.write('main.aw','import a\n--'+'y'*500000+'\nfunction main()->i64 return 0 end');self.reject('E300','aggregate')
        # 64 aliases to the same empty leaf are valid; five such modules exceed
        # the graph edge budget without exhausting the file budget.
        self.write('leaf.aw','')
        for i in range(5):self.write(f'e{i}.aw',' '.join(f'import leaf as n{j}' for j in range(64)))
        self.write('main.aw',' '.join(f'import e{i}' for i in range(5))+' function main()->i64 return 0 end');self.reject('E300','edge')
    def test_deterministic_emission_relocation_and_changed_dependency(self):
        self.write('a.aw','function f()->i64 return 4 end');self.write('main.aw','import a function main()->i64 print(a.f()) return 0 end')
        first=self.invoke('emit-c');self.assertEqual(first.returncode,0,first.stderr);self.assertEqual(first.stdout,self.invoke('emit-c').stdout)
        moved=self.root/'relocated project';shutil.copytree(self.root,moved,ignore=shutil.ignore_patterns('relocated project'))
        r=subprocess.run([str(KCC),'emit-c',str(moved/'main.aw')],capture_output=True,text=True);self.assertEqual(first.stdout,r.stdout)
        self.run_main('4\n');self.write('a.aw','function f()->i64 return 8 end');self.run_main('8\n')
    def test_seeded_graph_oracles(self):
        rng=random.Random(8101)
        for trial in range(15):
            values=[rng.randrange(-1000,1000) for _ in range(8)]
            for i,v in enumerate(values):self.write(f'n{i}.aw',f'function f()->i64 return {v} end')
            self.write('main.aw',' '.join(f'import n{i} as a{i}' for i in range(8))+' function main()->i64 print('+'+'.join(f'a{i}.f()' for i in range(8))+') return 0 end')
            self.run_main(str(sum(values))+'\n',rng.choice(['0','3']))
    def test_byte_source_api_does_not_read_files(self):
        libpath=ROOT/'compiler/native/bin'/('Awllex.dll' if os.name=='nt' else 'Awllex.so')
        if not libpath.exists():self.skipTest('contributor shared frontend unavailable')
        lib=C.CDLL(str(libpath));lib.Awl_parse_source.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(C.c_void_p)];lib.Awl_check_unit.argtypes=[C.c_void_p];lib.Awl_parse_free.argtypes=[C.c_void_p]
        text=b'import a function main()->i64 return 0 end';p=C.c_void_p()
        self.assertEqual(lib.Awl_parse_source(text,len(text),C.byref(p)),0)
        try:self.assertEqual(lib.Awl_check_unit(p),1)
        finally:lib.Awl_parse_free(p)
if __name__=='__main__':unittest.main()

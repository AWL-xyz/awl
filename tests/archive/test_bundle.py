"""Packaged Linux-native compiler tests, distinct from bootstrap/compiler-library tests."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_kcc import ROOT
PACKAGE=ROOT/'build/Awl-linux-x86_64'
KCC=PACKAGE/'bin/kcc'

@unittest.skipUnless(os.name=='posix' and KCC.is_file(),'build Linux engineering bundle first')
class BundledCompiler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared=tempfile.TemporaryDirectory(prefix='Awl-bundle-test-cache-');cls.cache=Path(cls.shared.name)
    @classmethod
    def tearDownClass(cls):cls.shared.cleanup()
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='Awl bundle test ');self.addCleanup(self.directory.cleanup)
        self.dir=Path(self.directory.name);(self.dir/'tmp').mkdir()
        self.env={**os.environ,'PATH':'/no-host-development-tools','XDG_CACHE_HOME':str(self.cache),'TMPDIR':str(self.dir/'tmp')}
    def source(self,body='print(42) return 0'):
        p=self.dir/'source with spaces.aw';p.write_text('function main()->i64 '+body+' end');return p
    def invoke(self,*args,**kw):return subprocess.run([str(KCC),*map(str,args)],env=self.env,cwd=self.dir,capture_output=True,text=True,timeout=120,**kw)
    def test_examples_tool_free_path(self):
        expected=json.loads((ROOT/'tests/example-outputs.json').read_text())
        for p in (ROOT/'examples').glob('*.aw'):
            r=self.invoke('run',p);self.assertEqual((r.returncode,r.stdout),(0,expected[p.name]),r.stderr)
    def test_build_paths_with_spaces_and_static_output(self):
        source=self.source();out=self.dir/'executable with spaces';r=self.invoke('build',source,'-o',out,'-O','3')
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,str(out)+'\n')
        self.assertTrue(os.access(out,os.X_OK))
        result=subprocess.run([str(out)],env=self.env,capture_output=True,text=True)
        self.assertEqual((result.returncode,result.stdout),(0,'42\n'))
        self.assertEqual(list((self.dir/'tmp').iterdir()),[])
        self.assertEqual(list(self.dir.glob('.Awl-output-*')),[])
    def test_default_output(self):
        source=self.source();r=self.invoke('build',source)
        self.assertEqual(r.returncode,0,r.stderr);self.assertTrue((self.dir/source.stem).is_file())
    def test_return_and_trap_status(self):
        r=self.invoke('run',self.source('return 37'));self.assertEqual(r.returncode,37,r.stderr)
        r=self.invoke('run',self.source('print(127i8+1i8) return 0'));self.assertEqual(r.returncode,134);self.assertIn('Awl arithmetic trap',r.stderr)
    def test_bad_source_preserves_old_output(self):
        p=self.source('return true');out=self.dir/'existing';out.write_bytes(b'keep this artifact')
        r=self.invoke('build',p,'-o',out,'--diagnostic-format','json');self.assertEqual(r.returncode,1)
        self.assertEqual(json.loads(r.stderr)['diagnostics'][0]['code'],'E200');self.assertEqual(out.read_bytes(),b'keep this artifact')
    def test_refuses_source_overwrite_and_invalid_host_options(self):
        p=self.source();before=p.read_bytes();r=self.invoke('build',p,'-o',p)
        self.assertEqual(r.returncode,2);self.assertIn('refusing to overwrite source',r.stderr);self.assertEqual(p.read_bytes(),before)
        r=self.invoke('build',p,'--cc','/usr/bin/gcc');self.assertEqual(r.returncode,2)
    def test_ignores_host_compiler_resource_environment(self):
        self.env.update({'CC':'/no-cc','CPATH':'/no-headers','C_INCLUDE_PATH':'/no-headers','LIBRARY_PATH':'/no-libs','ZIG_LIB_DIR':'/no-zig-libs','ZIG_GLOBAL_CACHE_DIR':'/no-cache'})
        r=self.invoke('run',self.source());self.assertEqual((r.returncode,r.stdout),(0,'42\n'),r.stderr)
    def test_codegen_failure_is_atomic(self):
        fake=self.dir/'fake';(fake/'bin').mkdir(parents=True);(fake/'libexec/zig/lib').mkdir(parents=True)
        shutil.copy2(KCC,fake/'bin/kcc');shutil.copy2('/bin/false',fake/'libexec/zig/zig')
        p=self.source();out=self.dir/'existing';out.write_bytes(b'previous')
        r=subprocess.run([str(fake/'bin/kcc'),'build',str(p),'-o',str(out)],env=self.env,capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,2);self.assertIn('bundled code generation/linking failed',r.stderr)
        self.assertEqual(out.read_bytes(),b'previous');self.assertEqual(list(self.dir.glob('.Awl-output-*')),[])
    def test_output_io_failure_is_not_success(self):
        if not Path('/dev/full').exists():self.skipTest('/dev/full unavailable')
        with open('/dev/full','wb') as full:
            r=subprocess.run([str(KCC),'emit-c',str(self.source())],stdout=full,stderr=subprocess.PIPE,env=self.env,text=True,timeout=10)
        self.assertEqual(r.returncode,2);self.assertIn('cannot write output',r.stderr)
if __name__=='__main__':unittest.main()

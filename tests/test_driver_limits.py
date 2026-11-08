"""Failure injection for native driver. Probe replaces the trusted tool only in fixtures."""
try:
    import fcntl
except ImportError:
    fcntl=None
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import struct
import subprocess
import tempfile
import time
import unittest
from test_kcc import ROOT
PACKAGE=ROOT/'build/Awl-linux-x86_64'
KCC=PACKAGE/'bin/kcc'
DRIVER=Path(os.environ.get('Awl_DRIVER_TEST_BINARY',str(KCC)))

@unittest.skipUnless(sys.platform=='linux' and fcntl is not None and KCC.is_file() and shutil.which('cc'),'Linux bundle and contributor C toolchain required')
class DriverLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared=tempfile.TemporaryDirectory(prefix='Awl-driver-probe-');cls.probe=Path(cls.shared.name)/'probe'
        subprocess.run(['cc','-std=c11','-O2','-static',str(ROOT/'tests/driver_probe.c'),'-o',str(cls.probe)],check=True,capture_output=True,timeout=60)
    @classmethod
    def tearDownClass(cls):cls.shared.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='Awl-driver-limits-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'bin').mkdir();self.tool=self.root/'libexec/zig';(self.tool/'lib').mkdir(parents=True)
        shutil.copy2(DRIVER,self.root/'bin/kcc');shutil.copy2(self.probe,self.tool/'zig');shutil.copy2(KCC,self.tool/'image')
        self.source=self.root/'input.aw';self.source.write_text('function main()->i64 return 0 end');self.out=self.root/'output';self.out.write_bytes(b'previous executable')
        (self.root/'tmp').mkdir();self.env={**os.environ,'PATH':'/no-tools','TMPDIR':str(self.root/'tmp'),'XDG_CACHE_HOME':str(self.root/'cache')}
        self.mode('image')
    def mode(self,name):(self.tool/'mode').write_text(name)
    def command(self,*args):return [str(self.root/'bin/kcc'),'build',str(self.source),'-o',str(self.out),*args]
    def invoke(self,*args,**kwargs):return subprocess.run(self.command(*args),env=self.env,capture_output=True,text=True,timeout=10,**kwargs)
    def assert_clean(self):
        self.assertEqual(self.out.read_bytes(),b'previous executable')
        self.assertEqual(list((self.root/'tmp').iterdir()),[]);self.assertEqual(list(self.root.glob('.Awl-output-*')),[])
    def pids(self):return list(map(int,(self.tool/'pids').read_text().splitlines()))
    def assert_dead(self):
        for pid in self.pids():
            with self.assertRaises(ProcessLookupError):os.kill(pid,0)
    def wait_ready(self,p):
        end=time.monotonic()+5
        while time.monotonic()<end:
            if (self.tool/'pids').exists() and len(self.pids())>=3:return
            if p.poll() is not None:self.fail('probe exited before setup')
            time.sleep(.01)
        p.kill();self.fail('probe never reached ready state')
    def test_timeout_kills_and_reaps_process_tree(self):
        self.mode('hang');start=time.monotonic();r=self.invoke('--build-timeout','1')
        self.assertEqual(r.returncode,124,r.stderr);self.assertIn('wall-time limit',r.stderr)
        self.assertLess(time.monotonic()-start,8);self.assertGreaterEqual(len(self.pids()),3);self.assert_dead();self.assert_clean()
    def test_interrupt_signals_kill_and_reap_process_tree(self):
        self.mode('hang')
        for sig in [signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT]:
            with self.subTest(signal=sig):
                if (self.tool/'pids').exists():(self.tool/'pids').unlink()
                p=subprocess.Popen(self.command(),env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                self.wait_ready(p);p.send_signal(sig);stdout,stderr=p.communicate(timeout=10)
                self.assertEqual(p.returncode,128+sig,stderr);self.assertIn('interrupted',stderr);self.assert_dead();self.assert_clean()
    def test_root_exit_does_not_leave_descendants(self):
        self.mode('exit-tree');r=self.invoke();self.assertEqual(r.returncode,2,r.stderr)
        self.assertEqual(len(self.pids()),3);self.assert_dead();self.assert_clean()
    def test_limits_and_descriptor_closure_are_real(self):
        self.mode('limits')
        with open(self.source,'rb') as stream:
            fd=fcntl.fcntl(stream.fileno(),fcntl.F_DUPFD,200)
            try:r=self.invoke('--build-memory-mib','512',pass_fds=(fd,))
            finally:os.close(fd)
        self.assertEqual(r.returncode,0,r.stderr);limits=json.loads((self.tool/'limits.json').read_text())
        self.assertEqual(limits,{'as':512*1024*1024,'file':256*1024*1024,'core':0,'fd_hard':32768,'memory_enforced':1,'fd_closed':1})
    def test_empty_or_symlinked_output_rejected(self):
        for mode in ['no-output','symlink']:
            self.mode(mode);r=self.invoke();self.assertEqual(r.returncode,2);self.assert_clean()
    def test_malformed_elf_metadata_rejected(self):
        original=KCC.read_bytes()
        corruptions=[(4,b'\x01'),(16,struct.pack('<H',3)),(18,struct.pack('<H',183)),(24,bytes(8)),(32,b'\xff'*8),(56,struct.pack('<H',129))]
        offset=struct.unpack_from('<Q',original,32)[0];corruptions.append((offset,struct.pack('<I',3)))
        for at,data in corruptions:
            image=bytearray(original);image[at:at+len(data)]=data;(self.tool/'image').write_bytes(image)
            r=self.invoke();self.assertEqual(r.returncode,2,r.stderr);self.assertIn('static x86-64 ELF',r.stderr);self.assert_clean()
    def test_umask_is_respected(self):
        r=self.invoke(preexec_fn=lambda:os.umask(0o077));self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(self.out.stat().st_mode&0o777,0o700)
    def test_invalid_limit_options_rejected(self):
        for flag,value in [('--build-timeout','0'),('--build-timeout','3601'),('--build-timeout','-1'),('--build-timeout','1.5'),('--build-timeout','99999999999999999'),('--build-memory-mib','511'),('--build-memory-mib','16385'),('--run-timeout','1')]:
            r=self.invoke(flag,value);self.assertEqual(r.returncode,2);self.assertIn('invalid option',r.stderr);self.assert_clean()
    def test_real_generated_program_timeout(self):
        self.source.write_text('function main()->i64 while true do end return 0 end')
        env={**self.env,'XDG_CACHE_HOME':str(ROOT/'.cache/hardening-integration')}
        r=subprocess.run([str(DRIVER),'run',str(self.source),'--run-timeout','1'],env=env,capture_output=True,text=True,timeout=90)
        self.assertEqual(r.returncode,124,r.stderr);self.assertIn('program wall-time limit',r.stderr)
        self.assertEqual(list((self.root/'tmp').iterdir()),[])
if __name__=='__main__':unittest.main()

"""Native-only experimental resource/window APIs. No Python reference emulation.
Xvfb/python-xlib are optional contributor test dependencies, never product ones.
"""
import contextlib
import os
from pathlib import Path
try:
    import resource
except ImportError:
    resource=None
import select
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from native_features import supports_version

ROOT=Path(__file__).resolve().parents[1]
KCC=Path(os.environ.get('Awl_PLATFORM_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
def available():
    return os.name=='posix' and supports_version(KCC,(0,8,0))

@unittest.skipUnless(available(),'requires experimental native 0.8.0 bundle')
class Platform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared=tempfile.TemporaryDirectory(prefix='Awl-platform-')
        cls.base=Path(cls.shared.name)
    @classmethod
    def tearDownClass(cls): cls.shared.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='Awl-platform-case-');self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        self.env={**os.environ,'XDG_CACHE_HOME':os.environ.get('Awl_PLATFORM_TEST_CACHE',str(self.base/'cache')),'PATH':'/no-host-tools'}
        self.env.pop('DISPLAY',None)
    def compile(self,body,opt='2',full=False):
        p=self.dir/'test.aw';p.write_text(body if full else 'function main()->i64 '+body+' return 0 end')
        exe=self.dir/'program'
        if os.environ.get('Awl_PLATFORM_SANITIZE')=='1':
            emitted=subprocess.run([str(KCC),'emit-c',str(p)],capture_output=True,text=True,timeout=15)
            self.assertEqual(emitted.returncode,0,emitted.stderr)
            c=self.dir/'test.c';c.write_text(emitted.stdout)
            r=subprocess.run([shutil.which('cc'),'-std=c11','-O'+opt,'-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-o',str(exe)],capture_output=True,text=True,timeout=60)
            self.env['ASAN_OPTIONS']='detect_leaks=1:abort_on_error=1'
        else:
            r=subprocess.run([str(KCC),'build',str(p),'-o',str(exe),'-O',opt],env=self.env,capture_output=True,text=True,timeout=120)
        self.assertEqual(r.returncode,0,r.stderr)
        return exe
    def run_body(self,body,opt='2'):
        exe=self.compile(body,opt)
        def no_core(): resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        return subprocess.run([str(exe)],env=self.env,capture_output=True,text=True,timeout=10,preexec_fn=no_core)
    def test_buffers_roundtrip_o0_o3(self):
        body=(ROOT/'examples/platform/buffers.aw').read_text()
        for opt in ['0','3']:
            exe=self.compile(body,opt,True);r=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout),(0,'4\n0\n255\n42\n0\n'))
    def test_bounds_and_invalid_handles_trap(self):
        for body in ['print(buffer.get(0,0))','local b:i64=buffer.new(4) print(buffer.get(b,-1))',
                     'local b:i64=buffer.new(4) buffer.set(b,4,1u8)',
                     'local b:i64=buffer.new(0) print(buffer.get(b,0))',
                     'local b:i64=buffer.new(2) buffer.free(b) print(buffer.get(b,0))',
                     'local b:i64=buffer.new(2) buffer.free(b) buffer.free(b)',
                     'print(window.width(0))','window.pixel(1,0,0,0)','clock.sleep(-1)','clock.sleep(60001)']:
            with self.subTest(body=body):
                r=self.run_body(body);self.assertNotEqual(r.returncode,0);self.assertIn('Awl resource trap',r.stderr)
    def test_stale_handle_not_reused(self):
        r=self.run_body('local a:i64=buffer.new(2) buffer.free(a) local b:i64=buffer.new(2) print(a != b) buffer.free(b)')
        self.assertEqual((r.returncode,r.stdout),(0,'true\n'))
    def test_allocation_and_table_caps(self):
        r=self.run_body('print(buffer.new(-1)) print(buffer.new(16777217)) local i:i64=0 local b:i64=0 while i<64 do b=buffer.new(0) if b==0 then return 1 end i=i+1 end print(buffer.new(0)) local j:i64=1 while j<=b do buffer.free(j) j=j+1 end')
        self.assertEqual((r.returncode,r.stdout),(0,'0\n0\n0\n'))
        r=self.run_body('local a:i64=buffer.new(16777216) local b:i64=buffer.new(16777216) local c:i64=buffer.new(16777216) local d:i64=buffer.new(16777216) print(buffer.new(1)) buffer.free(a) buffer.free(b) buffer.free(c) buffer.free(d)')
        self.assertEqual((r.returncode,r.stdout),(0,'0\n'))
    def test_monotonic_clock_and_sleep(self):
        r=self.run_body('local t:i64=clock.millis() clock.sleep(20) print(clock.millis()-t >= 15)')
        self.assertEqual((r.returncode,r.stdout),(0,'true\n'))
    def test_absent_unsupported_display_and_dimensions(self):
        exe=self.compile('print(window.open(64,64)) print(window.open(0,5)) print(window.open(2049,5))')
        for display in [None,':4096',':',':93.1','remote:0','unix:bad']:
            env=self.env.copy()
            if display is not None:env['DISPLAY']=display
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=5)
            self.assertEqual((r.returncode,r.stdout),(0,'0\n0\n0\n'))
    def test_checker_rejects_invalid_intrinsics(self):
        for body in ['print(buffer.get(1,0u64))','buffer.set(1,0,255)','window.open(true,20)','local x:i64=window.present(1)']:
            p=self.dir/'bad.aw';p.write_text('function main()->i64 '+body+' return 0 end')
            r=subprocess.run([str(KCC),'check',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,1);self.assertIn('E200',r.stderr)
        for declaration in ['function buffer.new()->i64 return 0 end','struct window.open x:i64 end']:
            p=self.dir/'bad.aw';p.write_text(declaration+' function main()->i64 return 0 end')
            r=subprocess.run([str(KCC),'check',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,1);self.assertIn('E210',r.stderr)
    def test_malformed_display_setup(self):
        folder=Path('/tmp/.X11-unix')
        if not folder.exists():self.skipTest('local X socket directory absent')
        exe=self.compile('print(window.open(32,32))')
        packets=[b'',b'\0'*8,b'\1\0\x0b\0\0\0\0\0',b'\1\0\x0b\0\0\0\x08\0'+b'\0'*32,
                 b'\1\0\x0b\0\0\0\xff\xff'+b'\0'*64]
        for packet in packets:
            with socket.socket(socket.AF_UNIX) as server:
                for n in range(3000,4096):
                    path=folder/f'X{n}'
                    try:server.bind(str(path));break
                    except OSError:continue
                else:self.skipTest('no unused test display path')
                try:
                    server.listen(1)
                    def serve():
                        conn,_=server.accept()
                        with conn:conn.recv(128);conn.sendall(packet)
                    thread=threading.Thread(target=serve,daemon=True);thread.start()
                    env={**self.env,'DISPLAY':f':{n}','XAUTHORITY':str(self.dir/'absent')}
                    r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=5)
                    thread.join(2);self.assertFalse(thread.is_alive())
                    self.assertEqual((r.returncode,r.stdout),(0,'0\n'))
                finally:path.unlink(missing_ok=True)

# The desktop suite creates an authenticated private display, not -ac. Products
# connect to its local Unix socket without any Xlib/SDL shared-library linkage.
@unittest.skipUnless(available() and shutil.which('Xvfb'),'requires Xvfb contributor fixture')
class Desktop(Platform):
    # Do not repeat all inherited resource tests under the desktop fixture.
    __unittest_skip__ = False
    @contextlib.contextmanager
    def desktop(self):
        try:from Xlib import display
        except ImportError:self.skipTest('python-xlib contributor fixture missing')
        cookie=os.urandom(16)
        number=None;reservation=None
        for n in range(100,500):
            if Path(f'/tmp/.X11-unix/X{n}').exists():continue
            lock=Path(f'/tmp/Awl-x11-test-{n}.lock')
            try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            except FileExistsError:continue
            os.close(fd);number=n;reservation=lock;break
        self.assertIsNotNone(number)
        def field(b):return struct.pack('>H',len(b))+b
        auth=self.dir/'auth';auth.write_bytes(struct.pack('>H',256)+field(socket.gethostname().encode())+field(str(number).encode())+field(b'MIT-MAGIC-COOKIE-1')+field(cookie));auth.chmod(0o600)
        env={**self.env,'DISPLAY':f':{number}','XAUTHORITY':str(auth)}
        log=open(self.dir/'xvfb.log','wb')
        ready_r,ready_w=os.pipe()
        server=subprocess.Popen([shutil.which('Xvfb'),f':{number}','-screen','0','640x640x24','-nolisten','tcp','-auth',str(auth),'-noreset','-displayfd',str(ready_w)],stdout=log,stderr=log,pass_fds=(ready_w,))
        os.close(ready_w)
        connection=None;last_error=''
        try:
            self.assertTrue(select.select([ready_r],[],[],5)[0],'Xvfb readiness timeout')
            self.assertTrue(os.read(ready_r,32).strip())
            for _ in range(1):
                try:
                    with patch.dict(os.environ,env):connection=display.Display(env['DISPLAY'])
                    break
                except Exception as exc:
                    last_error=str(exc)
                    if server.poll() is not None:break
                    time.sleep(.02)
            self.assertIsNotNone(connection,last_error+(self.dir/'xvfb.log').read_text())
            yield connection,env
        finally:
            if connection:connection.close()
            server.terminate();server.wait(timeout=5);log.close();os.close(ready_r);reservation.unlink(missing_ok=True)
    def wait_window(self,d):
        for _ in range(150):
            children=d.screen().root.query_tree().children
            if children:return children[0]
            time.sleep(.02)
        self.fail('native window not created')
    def test_real_pixels_resize_input_close(self):
        from Xlib import X, protocol
        body='''function main()->i64
local w:i64=window.open(96,64)
if w==0 then return 3 end
local active:bool=true
while active do
local e:i64=window.poll(w)
while e!=0 and active do
if e==1 then active=false end
if e==3 then print(3) print(window.width(w)) print(window.height(w)) end
if e>=4 then print(e) print(window.key(w)) print(window.mousex(w)) print(window.mousey(w)) end
e=window.poll(w)
end
if active then
local y:i64=0
while y<window.height(w) do
local x:i64=0
while x<window.width(w) do window.pixel(w,x,y,1193046) x=x+1 end
y=y+1
end
active=window.present(w)
clock.sleep(5)
end
end
window.close(w)
return 0 end'''
        exe=self.compile(body,full=True)
        with self.desktop() as (d,env):
            p=subprocess.Popen([str(exe)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                w=self.wait_window(d)
                for _ in range(100):
                    image=w.get_image(0,0,1,1,X.ZPixmap,0xffffffff)
                    if image.data[:3]==b'\x56\x34\x12':break
                    time.sleep(.02)
                self.assertEqual(image.data[:3],b'\x56\x34\x12')
                w.configure(width=80,height=72);d.sync()
                for _ in range(100):
                    image=w.get_image(79,71,1,1,X.ZPixmap,0xffffffff)
                    if image.data[:3]==b'\x56\x34\x12':break
                    time.sleep(.02)
                self.assertEqual(image.data[:3],b'\x56\x34\x12')
                fields=dict(time=0,root=d.screen().root,window=w,child=0,root_x=7,root_y=9,event_x=7,event_y=9,state=0,same_screen=1)
                for event,mask,detail in [(protocol.event.KeyPress,X.KeyPressMask,38),(protocol.event.KeyRelease,X.KeyReleaseMask,38),(protocol.event.MotionNotify,X.PointerMotionMask,0),(protocol.event.ButtonPress,X.ButtonPressMask,1),(protocol.event.ButtonRelease,X.ButtonReleaseMask,1)]:
                    w.send_event(event(detail=detail,**fields),event_mask=mask)
                d.sync();time.sleep(.05)
                w.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('WM_PROTOCOLS'),data=(32,[d.intern_atom('WM_DELETE_WINDOW'),0,0,0,0])),event_mask=0);d.flush()
                out,err=p.communicate(timeout=5)
                self.assertEqual(p.returncode,0,err)
                self.assertIn('3\n80\n72\n',out)
                for text in ['4\n38\n7\n9\n','5\n38\n7\n9\n','6\n0\n7\n9\n','7\n1\n7\n9\n','8\n1\n7\n9\n']:self.assertIn(text,out)
            finally:
                if p.poll() is None:p.kill();p.communicate()
    def test_modular_pyramid_window(self):
        if not supports_version(KCC,(0,8,1)):self.skipTest('requires native0.8.1 feature')
        from Xlib import X, protocol
        shutil.copytree(ROOT/'examples/apps/pyramid',self.dir,dirs_exist_ok=True)
        exe=self.compile((self.dir/'main.aw').read_text(),opt='3',full=True)
        with self.desktop() as (d,env):
            p=subprocess.Popen([str(exe)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                w=self.wait_window(d)
                for _ in range(100):
                    raw=w.get_image(0,0,480,480,X.ZPixmap,0xffffffff).data
                    if any(raw[i+2]>100 and raw[i+1]>50 for i in range(0,len(raw),4)):break
                    time.sleep(.02)
                else:self.fail('modular pyramid did not render')
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    if raw!=w.get_image(0,0,480,480,X.ZPixmap,0xffffffff).data:break
                    time.sleep(.02)
                else:self.fail("modular pyramid produced no changed frame within 5 seconds")
                w.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('WM_PROTOCOLS'),data=(32,[d.intern_atom('WM_DELETE_WINDOW'),0,0,0,0])),event_mask=0);d.flush()
                out,err=p.communicate(timeout=5)
                self.assertEqual((p.returncode,out),(0,''),err)
            finally:
                if p.poll() is None:p.kill();p.communicate()
    def test_pixelboard_paint_resize_clear(self):
        from Xlib import X,protocol
        shutil.copytree(ROOT/'examples/apps/pixelboard',self.dir,dirs_exist_ok=True)
        exe=self.compile((self.dir/'main.aw').read_text(),full=True)
        with self.desktop() as (d,env):
            p=subprocess.Popen([str(exe)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                w=self.wait_window(d)
                def wait_pixel(x,y,color):
                    for _ in range(200):
                        if w.get_image(x,y,1,1,X.ZPixmap,0xffffffff).data[:3]==color.to_bytes(3,'little'):return
                        time.sleep(.02)
                    self.fail('Pixelboard pixel mismatch')
                wait_pixel(15,135,1056816+263688)
                fields=dict(time=0,root=d.screen().root,window=w,child=0,root_x=15,root_y=135,event_x=15,event_y=135,state=0,same_screen=1)
                for kind,mask in [(protocol.event.ButtonPress,X.ButtonPressMask),(protocol.event.ButtonRelease,X.ButtonReleaseMask)]:w.send_event(kind(detail=1,**fields),event_mask=mask)
                d.flush();wait_pixel(15,135,2217134)
                w.configure(width=480,height=320);d.flush();wait_pixel(10,90,2217134)
                w.send_event(protocol.event.KeyPress(detail=38,**fields),event_mask=X.KeyPressMask);d.flush();wait_pixel(10,90,1056816+263688)
                w.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('WM_PROTOCOLS'),data=(32,[d.intern_atom('WM_DELETE_WINDOW'),0,0,0,0])),event_mask=0);d.flush()
                out,err=p.communicate(timeout=5);self.assertEqual((p.returncode,out),(0,''),err)
            finally:
                if p.poll() is None:p.kill();p.communicate()
    def test_pixelboard_save_load_restart_and_invalid_file_rollback(self):
        if not supports_version(KCC,(0,23,0)):self.skipTest('requires native0.23 persistence')
        from Xlib import X,protocol
        import zlib
        shutil.copytree(ROOT/'examples/apps/pixelboard',self.dir,dirs_exist_ok=True)
        exe=self.compile((self.dir/'main.aw').read_text(),full=True);saved=self.dir/'drawing é.kpb';second=self.dir/'second.kpb'
        with self.desktop() as (d,env):
            def wait_pixel(w,color):
                for _ in range(250):
                    if w.get_image(15,135,1,1,X.ZPixmap,0xffffffff).data[:3]==color.to_bytes(3,'little'):return
                    time.sleep(.02)
                self.fail('persistence pixel mismatch')
            def key(w,code):
                fields=dict(time=0,root=d.screen().root,window=w,child=0,root_x=15,root_y=135,event_x=15,event_y=135,state=0,same_screen=1)
                w.send_event(protocol.event.KeyPress(detail=code,**fields),event_mask=X.KeyPressMask);d.flush()
            def title(w,text):
                for _ in range(250):
                    if text in str(w.get_wm_name()):return
                    time.sleep(.02)
                self.fail('persistence status missing: '+str(w.get_wm_name()))
            def close(w,p):
                w.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('WM_PROTOCOLS'),data=(32,[d.intern_atom('WM_DELETE_WINDOW'),0,0,0,0])),event_mask=0);d.flush();out,err=p.communicate(timeout=10);self.assertEqual((p.returncode,out),(0,''),err)
            p=subprocess.Popen([str(exe),str(saved)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                w=self.wait_window(d);wait_pixel(w,1320504)
                fields=dict(time=0,root=d.screen().root,window=w,child=0,root_x=15,root_y=135,event_x=15,event_y=135,state=0,same_screen=1)
                for kind,mask in [(protocol.event.ButtonPress,X.ButtonPressMask),(protocol.event.ButtonRelease,X.ButtonReleaseMask)]:w.send_event(kind(detail=1,**fields),event_mask=mask)
                d.flush();wait_pixel(w,2217134);key(w,39);title(w,'Saved new file');original=saved.read_bytes();self.assertEqual(len(original),1164);self.assertEqual(zlib.adler32(original[:-4]),int.from_bytes(original[-4:],'big'))
                key(w,38);wait_pixel(w,1320504);key(w,46);title(w,'Loaded file');wait_pixel(w,2217134)
                key(w,39);title(w,'Save refused');self.assertEqual(saved.read_bytes(),original)
                corrupt=bytearray(original);corrupt[99]^=1;saved.write_bytes(corrupt);key(w,46);title(w,'Load failed');wait_pixel(w,2217134);saved.write_bytes(original);close(w,p)
            finally:
                if p.poll() is None:p.kill();p.communicate()
            p=subprocess.Popen([str(exe),str(second),str(saved)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                w=self.wait_window(d);wait_pixel(w,1320504);key(w,46);title(w,'Loaded file');wait_pixel(w,2217134);key(w,39);title(w,'Saved new file');self.assertEqual(second.read_bytes(),original);close(w,p)
            finally:
                if p.poll() is None:p.kill();p.communicate()
    def test_utf8_title_and_rejection_limits(self):
        if not supports_version(KCC,(0,8,2)):self.skipTest('requires native0.8.2 feature')
        from Xlib import protocol
        r=self.run_body('window.title(0,"x")');self.assertNotEqual(r.returncode,0);self.assertIn('Awl resource trap',r.stderr)
        title='Awl 世界 🚀'
        body='''function main()->i64
local w:i64=window.open(64,64) if w==0 then return 3 end
print(window.title(w,""))
local long:string="a" local i:i64=0 while i<10 do long=long+long i=i+1 end
print(window.title(w,long))
print(window.title(w,"Awl 世界 🚀"))
print(window.title(w,"bad\\0title"))
print(window.title(w,long+"a"))
local active:bool=true while active do if window.poll(w)==1 then active=false end clock.sleep(5) end
print(window.title(w,"")) window.close(w) return 0 end'''
        exe=self.compile(body,full=True)
        with self.desktop() as (d,env):
            p=subprocess.Popen([str(exe)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                w=self.wait_window(d)
                for _ in range(150):
                    prop=w.get_full_property(d.intern_atom('_NET_WM_NAME'),d.intern_atom('UTF8_STRING'))
                    if prop and prop.value==title.encode():break
                    time.sleep(.02)
                self.assertIsNotNone(prop);self.assertEqual(prop.value,title.encode())
                # Failed updates must leave the original title unchanged.
                time.sleep(.05);self.assertEqual(w.get_full_property(d.intern_atom('_NET_WM_NAME'),d.intern_atom('UTF8_STRING')).value,title.encode())
                w.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('WM_PROTOCOLS'),data=(32,[d.intern_atom('WM_DELETE_WINDOW'),0,0,0,0])),event_mask=0);d.flush()
                out,err=p.communicate(timeout=5)
                self.assertEqual((p.returncode,out),(0,'true\ntrue\ntrue\nfalse\nfalse\nfalse\n'),err)
            finally:
                if p.poll() is None:p.kill();p.communicate()
    def test_scoped_window_release(self):
        if not supports_version(KCC,(0,8,4)):self.skipTest('requires native0.8.4 feature')
        exe=self.compile('local i:i64=0 while i<100 do if true then local w:i64=window.open(32,32) if w==0 then return 3 end defer window.close(w) if window.width(w)!=32 then return 4 end end i=i+1 end print("100 windows closed at scope exit")')
        with self.desktop() as (d,env):
            r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual((r.returncode,r.stdout),(0,'100 windows closed at scope exit\n'),r.stderr)
            d.sync();self.assertEqual(d.screen().root.query_tree().children,[])
    def test_cookie_rejection_and_pixel_bounds(self):
        exe=self.compile('print(window.open(32,32))')
        with self.desktop() as (_,env):
            wrong=self.dir/'wrong-auth';wrong.write_bytes(b'')
            r=subprocess.run([str(exe)],env={**env,'XAUTHORITY':str(wrong)},capture_output=True,text=True,timeout=5)
            self.assertEqual((r.returncode,r.stdout),(0,'0\n'))
            for call in ['window.pixel(w,32,0,1)','window.pixel(w,-1,0,1)','window.pixel(w,0,0,16777216)','window.close(w) window.present(w)','local b:i64=buffer.new(1) window.width(b)','buffer.get(w,0)']:
                exe=self.compile('local w:i64=window.open(32,32) if w==0 then return 3 end '+call)
                def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
                r=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=5,preexec_fn=no_core)
                self.assertNotEqual(r.returncode,0);self.assertIn('resource trap',r.stderr)

# Avoid inherited tests duplicating counts in unittest discovery.
for _name in list(Platform.__dict__):
    if _name.startswith('test_') and _name not in Desktop.__dict__:
        setattr(Desktop,_name,None)
if __name__=='__main__':unittest.main()

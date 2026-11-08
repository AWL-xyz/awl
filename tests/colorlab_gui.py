#!/usr/bin/python3
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
from PIL import Image
from Xlib import X,display,protocol
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--sanitized',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);a=p.parse_args();records=[];server=subprocess.Popen(['Xvfb',':96','-screen','0','900x600x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
time.sleep(.4)
try:
 d=display.Display(':96')
 for mode,exe in [('native',a.native),('sanitized',a.sanitized)]:
  proc=subprocess.Popen([str(exe.resolve())],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'DISPLAY':':96','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'});start=time.monotonic();window=None;checks=[];draw_times=[]
  def wait(predicate,label):
   until=time.monotonic()+6
   while time.monotonic()<until:
    if proc.poll() is not None:raise AssertionError((mode,label,proc.returncode,proc.communicate()))
    if predicate():return
    time.sleep(.01)
   raise AssertionError((mode,label,'timeout'))
  def locate():
   global window
   for child in d.screen().root.query_tree().children:
    if child.get_wm_name()=='Awl Color Lab | native source graphics':window=child;return True
   return False
  def pixel(x,y):return int.from_bytes(window.get_image(x,y,1,1,X.ZPixmap,0xffffffff).data[:4],'little')&0xffffff
  def sample(color,label):
   begin=time.perf_counter_ns();wait(lambda:pixel(500,140)==color,label);draw_times.append((time.perf_counter_ns()-begin)/1e6);checks.append(label)
  def event(kind,x,y,button=1):
   common=dict(time=X.CurrentTime,root=d.screen().root,window=window,child=X.NONE,root_x=x,root_y=y,event_x=x,event_y=y,state=0,same_screen=1)
   if kind=='move':e=protocol.event.MotionNotify(detail=0,**common);mask=X.PointerMotionMask
   elif kind=='down':e=protocol.event.ButtonPress(detail=button,**common);mask=X.ButtonPressMask
   else:e=protocol.event.ButtonRelease(detail=button,**common);mask=X.ButtonReleaseMask
   window.send_event(e,event_mask=mask);d.flush()
  def click(x,y):event('down',x,y);event('up',x,y)
  try:
   wait(locate,'native window mapped');sample(0x4ea6e0,'initial RGB preview');ready=(time.monotonic()-start)*1000
   assert pixel(24,68)==1646897 and pixel(0,0)==1119522;checks.append('panel and background pixels')
   # An authored A fixture verifies real native text rather than only shape colors.
   assert pixel(244,24)==1119522 and pixel(247,24)==14215151;checks.append('native font raster pixels')
   event('move',431,120);time.sleep(.04);assert pixel(500,140)==0x4ea6e0;checks.append('hover does not edit')
   click(431,120);sample(0xffa6e0,'red endpoint click')
   click(48,180);sample(0xff00e0,'green endpoint click')
   click(240,250);sample(0xff0080,'blue midpoint click')
   event('down',48,120);sample(0x000080,'drag press');event('move',240,120);sample(0x800080,'drag motion');event('up',240,120)
   event('move',431,120);time.sleep(.04);assert pixel(500,140)==0x800080;checks.append('release ends drag')
   click(348,350);sample(0x808080,'grayscale selection')
   click(165,120);sample(0x4e8080,'red restore');click(297,180);sample(0x4ea680,'green restore');click(384,250);sample(0x4ea6e0,'blue restore')
   window.configure(width=800,height=480);d.sync();wait(lambda:window.get_geometry().width==800 and pixel(799,479)==1119522,'resize redraw');checks.append('resize redraw')
   window.configure(width=720,height=440);d.sync();time.sleep(.08);sample(0x4ea6e0,'resize restores layout')
   if mode=='native':
    raw=window.get_image(0,0,720,440,X.ZPixmap,0xffffffff);a.capture.parent.mkdir(parents=True,exist_ok=True);Image.frombytes('RGB',(720,440),raw.data,'raw','BGRX').save(a.capture,optimize=True)
   close=protocol.event.ClientMessage(window=window,client_type=d.intern_atom('WM_PROTOCOLS'),data=(32,[d.intern_atom('WM_DELETE_WINDOW'),X.CurrentTime,0,0,0]));window.send_event(close,event_mask=0);d.flush();out,err=proc.communicate(timeout=6);assert (proc.returncode,out,err)==(0,b'78 166 224\n',b''),(mode,proc.returncode,out,err);checks.append('normal close, RGB stdout and clean resource shutdown')
   records.append({'mode':mode,'checks':checks,'startup_to_observed_preview_ms':ready,'observed_draw_waits_ms':draw_times,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()})
  finally:
   if proc.poll() is None:proc.kill();proc.communicate(timeout=5)
 d.close()
finally:
 server.terminate();server.communicate(timeout=5)
result={'status':'PASS','runs':records,'capture_sha256':hashlib.sha256(a.capture.read_bytes()).hexdigest(),'capture_method':'actual native X11 window XGetImage, no mock/generated image','qualification':'synthetic mouse events against real native processes on Xvfb, observed waits include polling and X server, not UI latency benchmark or physical input acceptance','source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'examples-next/apps/colorlab').iterdir() if f.is_file()}}
a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',[(r['mode'],len(r['checks'])) for r in records])

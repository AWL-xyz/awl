"""Real native Linux/X11 Pixelboard pixels; external controller, never a renderer."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,time,zlib
from pathlib import Path
from PIL import Image
from Xlib import X,display,protocol
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--app',type=Path,required=True);a=p.parse_args();folder=Path(__file__).resolve().parent;drawing=folder/'native-drawing.kpb';assert not drawing.exists(),'exclusive capture fixture already exists';env={**os.environ,'DISPLAY':':93'}
 with tempfile.TemporaryDirectory(prefix='Awl-real-display-',dir=ROOT/'build') as td:
  work=Path(td);log=(work/'display.log').open('w');server=subprocess.Popen(['Xvfb',':93','-screen','0','1000x700x24','-nolisten','tcp'],stdout=log,stderr=log);wm=None;app=None;d=None
  try:
   for _ in range(250):
    try:d=display.Display(':93');break
    except Exception:time.sleep(.02)
   assert d is not None
   config=work/'twmrc';config.write_text('RandomPlacement\nNoGrabServer\nBorderWidth 2\nTitleFont "fixed"\nIconFont "fixed"\nMenuFont "fixed"\nResizeFont "fixed"\nIconManagerFont "fixed"\n');wm=subprocess.Popen(['twm','-f',str(config)],env={**env,'LC_ALL':'C'},stdout=log,stderr=log);time.sleep(.5);assert wm.poll() is None,'window manager exited'
   def window():
    def descendants(w):
     for c in w.query_tree().children:
      if str(c.get_wm_name()).startswith('Awl Pixelboard |'):return c
      found=descendants(c)
      if found:return found
    for _ in range(250):
     found=descendants(d.screen().root)
     if found:return found
     assert app.poll() is None;time.sleep(.02)
    raise AssertionError('actual application window missing')
   def fields(w):return dict(time=0,root=d.screen().root,window=w,child=0,root_x=15,root_y=135,event_x=15,event_y=135,state=0,same_screen=1)
   def button(w,detail,x,y):
    f=fields(w);f.update(event_x=x,event_y=y,root_x=x,root_y=y)
    for kind,mask in [(protocol.event.ButtonPress,X.ButtonPressMask),(protocol.event.ButtonRelease,X.ButtonReleaseMask)]:w.send_event(kind(detail=detail,**f),event_mask=mask)
    d.flush();time.sleep(.015)
   def key(w,code):w.send_event(protocol.event.KeyPress(detail=code,**fields(w)),event_mask=X.KeyPressMask);d.flush()
   def title(w,text):
    for _ in range(250):
     if text in str(w.get_wm_name()):return
     time.sleep(.02)
    raise AssertionError('status: '+str(w.get_wm_name()))
   def pixel(w,x,y,color):
    for _ in range(250):
     if w.get_image(x,y,1,1,X.ZPixmap,0xffffffff).data[:3]==color.to_bytes(3,'little'):return
     time.sleep(.02)
    raise AssertionError('native framebuffer pixel mismatch')
   def close(w):
    w.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('WM_PROTOCOLS'),data=(32,[d.intern_atom('WM_DELETE_WINDOW'),0,0,0,0])),event_mask=0);d.flush();out,err=app.communicate(timeout=10);assert (app.returncode,out,err)==(0,'','')
   app=subprocess.Popen([str(a.app.resolve()),str(drawing)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);w=window();pixel(w,15,135,1320504)
   letters=[['10001','10010','10100','11000','10100','10010','10001'],['11111','10000','10000','11110','10000','10000','11111'],['11110','10001','10001','11110','10100','10010','10001'],['10001','11001','11001','10101','10011','10011','10001']];colors=[2217134,7695615,16217750,16764784]
   for letter,rows in enumerate(letters):
    if letter:button(w,3,15,15)
    for row,bits in enumerate(rows):
     for col,on in enumerate(bits):
      if on=='1':button(w,1,(letter*6+col)*30+15,(row+4)*30+15)
    pixel(w,letter*180+15,135,colors[letter])
   key(w,39);title(w,'Saved new file');payload=drawing.read_bytes();assert len(payload)==1164 and zlib.adler32(payload[:-4])==int.from_bytes(payload[-4:],'big');close(w)
   # New native process starts checkerboard; only the saved file restores artwork.
   app=subprocess.Popen([str(a.app.resolve()),str(drawing)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);w=window();pixel(w,15,135,1320504);key(w,46);title(w,'Loaded file')
   for i,color in enumerate(colors):pixel(w,i*180+15,135,color)
   frame=w
   while frame.query_tree().parent.id!=d.screen().root.id:frame=frame.query_tree().parent
   assert frame.id!=w.id,'window manager failed to decorate client';geometry=frame.get_geometry();time.sleep(.2);d.sync();raw=d.screen().root.get_image(geometry.x,geometry.y,geometry.width,geometry.height,X.ZPixmap,0xffffffff);image=Image.frombytes('RGB',(geometry.width,geometry.height),raw.data,'raw','BGRX');output=folder/'native-pixelboard.png';image.save(output)
   report={'status':'passed','capture':'real Xvfb93 screen rectangle including twm native window decorations; original pixels, lossless PNG; no generated or Python-rendered GUI','input':'programmatic X11 messages','title':w.get_wm_name(),'workflow':'paint four colors in native Awl app, S exclusive save, exit, new process, L load, verify actual pixels','application_sha256':hashlib.sha256(a.app.read_bytes()).hexdigest(),'drawing_sha256':hashlib.sha256(payload).hexdigest(),'drawing_bytes':len(payload),'png_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'size':[geometry.width,geometry.height]};(folder/'capture.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));close(w)
  finally:
   if app and app.poll() is None:app.kill();app.communicate()
   if d:d.close()
   if wm:wm.terminate();wm.wait(timeout=10)
   server.terminate();server.wait(timeout=10);log.close();shutil.copy2(work/'display.log',folder/'display.log')
if __name__=='__main__':main()

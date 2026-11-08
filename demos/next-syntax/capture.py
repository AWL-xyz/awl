"""Capture the real Xterm process running the native prototype and actual commands."""
import hashlib,json,os,subprocess,time
from pathlib import Path
from PIL import Image
from Xlib import display,X
ROOT=Path(__file__).resolve().parents[2];folder=Path(__file__).resolve().parent
server=subprocess.Popen(['Xvfb',':95','-screen','0','1100x800x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);terminal=None;d=None
try:
 for _ in range(200):
  try:d=display.Display(':95');break
  except Exception:time.sleep(.02)
 assert d is not None
 ready=ROOT/'build/next/window-ready';ready.unlink(missing_ok=True)
 terminal=subprocess.Popen(['xterm','-geometry','115x45+0+0','-fn','7x13','-bg','#101a26','-fg','#d8e5ef','-title','Awl next syntax prototype (not code generation)','-e','/bin/bash',str(folder/'run-demo.sh')],env={**os.environ,'DISPLAY':':95'})
 for _ in range(300):
  if ready.exists():break
  assert terminal.poll() is None;time.sleep(.02)
 assert ready.exists();time.sleep(.2);d.sync();windows=[w for w in d.screen().root.query_tree().children if w.get_wm_name()];assert len(windows)==1;w=windows[0];g=w.get_geometry();raw=w.get_image(0,0,g.width,g.height,X.ZPixmap,0xffffffff);out=folder/'native-checker.png';Image.frombytes('RGB',(g.width,g.height),raw.data,'raw','BGRX').save(out)
 (folder/'capture.json').write_text(json.dumps({'capture':'actual Xterm/Xvfb95 pixels, native structural checker run via bash; no generated UI or text-to-image transcript','prototype_only':True,'not_type_checking_codegen_or_runtime_acceptance':True,'binary_sha256':hashlib.sha256((ROOT/'compiler/next/bin/Awl-next-syntax').read_bytes()).hexdigest(),'png_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'size':[g.width,g.height]},indent=2)+'\n')
finally:
 if d:d.close()
 if terminal:terminal.terminate();terminal.wait(timeout=10)
 server.terminate();server.wait(timeout=10)

"""Capture the real Xterm process running the native production compiler candidate and actual commands."""
import hashlib,json,os,subprocess,time
from pathlib import Path
from PIL import Image
from Xlib import display,X
ROOT=Path(__file__).resolve().parents[2];folder=Path(__file__).resolve().parent
server=subprocess.Popen(['Xvfb',':95','-screen','0','1200x1000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);terminal=None;d=None
try:
 for _ in range(200):
  try:d=display.Display(':95');break
  except Exception:time.sleep(.02)
 assert d is not None
 ready=ROOT/'build/module-numeric/window-ready';ready.unlink(missing_ok=True)
 terminal=subprocess.Popen(['xterm','-geometry','135x72+0+0','-fn','7x13','-bg','#101a26','-fg','#d8e5ef','-title','Awl module state, decimal literals and math','-e','/bin/bash',str(folder/'run-demo.sh')],env={**os.environ,'DISPLAY':':95'})
 for _ in range(2250):
  if ready.exists():break
  assert terminal.poll() is None;time.sleep(.02)
 assert ready.exists();time.sleep(.2);d.sync();windows=[w for w in d.screen().root.query_tree().children if w.get_wm_name()];assert len(windows)==1;w=windows[0];g=w.get_geometry();raw=w.get_image(0,0,g.width,g.height,X.ZPixmap,0xffffffff);out=folder/'module-numeric.png';Image.frombytes('RGB',(g.width,g.height),raw.data,'raw','BGRX').save(out)
 (folder/'capture.json').write_text(json.dumps({'capture':'actual Xterm/Xvfb95 pixels, production native check and installed driver execution via bash; no generated UI or text-to-image transcript','development_candidate_not_release_acceptance':True,'binary_sha256':hashlib.sha256((ROOT/'compiler/native/bin/kcc').read_bytes()).hexdigest(),'png_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'size':[g.width,g.height]},indent=2)+'\n')
finally:
 if d:d.close()
 if terminal:terminal.terminate();terminal.wait(timeout=10)
 server.terminate();server.wait(timeout=10)

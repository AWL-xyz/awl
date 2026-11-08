#!/usr/bin/python3
"""Actual Xterm screen capture. Contributor-only Xvfb/Xlib/Pillow fixtures."""
import hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
from PIL import Image
from Xlib import display,X
ROOT=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent
binary=Path(os.environ.get('ASDK_CAPTURE_BINARY','/tmp/Awl-ASDK-bundle/Awl/bin/Awl'))
with tempfile.TemporaryDirectory(prefix='Awl-ASDK-photo-') as td:
 work=Path(td);script=work/'demo.sh';transcript=work/'transcript.txt'
 script.write_text('''#!/bin/sh
export PATH="'''+str(binary.parent)+'''":/usr/bin:/bin
export XDG_CACHE_HOME=/tmp/Awl-ASDK-cache
cd "'''+td+'''"
{
printf '$ awl --version\\n'
awl --version
printf '\\n$ awl init Signal\\n'
awl init Signal
printf '\\n$ cat Signal.awproj\\n'
cat Signal.awproj
printf '\\n$ cat main.aw\\n'
cat main.aw
printf '\\n$ awl build\\n'
awl build
printf '\\n$ ./build/Signal\\n'
./build/Signal
printf '\\nNative ASDK beta: initialization + compilation.\\nNo host compiler on backend PATH; no Python runtime dependency.\\nWindows work deferred; language development first.\\n'
} > "'''+str(transcript)+'''" 2>&1
cat "'''+str(transcript)+'''"
touch "'''+td+'''/done"
''')
 xvfb=subprocess.Popen(['Xvfb',':93','-screen','0','1100x780x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 term=None
 try:
  time.sleep(.5);env={**os.environ,'DISPLAY':':93'}
  term=subprocess.Popen(['xterm','-hold','-geometry','112x38+0+0','-fa','Monospace','-fs','12','-bg','#10151d','-fg','#d8f2e6','-title','Awl Software Development Kit [Beta] - actual terminal','-e','/bin/sh',str(script)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  until=time.monotonic()+45
  while not(work/'done').exists():
   if time.monotonic()>until:raise RuntimeError('capture demo timeout')
   time.sleep(.1)
  time.sleep(.4);d=display.Display(':93');root=d.screen().root;raw=root.get_image(0,0,1100,780,X.ZPixmap,0xffffffff)
  image=Image.frombytes('RGB',(1100,780),raw.data,'raw','BGRX');image.quantize(colors=96).save(out/'ASDK-beta.png',optimize=True);d.close()
  (out/'transcript.txt').write_bytes(transcript.read_bytes())
  assert 'Hello from Awl!' in transcript.read_text()
  (out/'capture.json').write_text(json.dumps({'method':'actual Xvfb/Xterm root screenshot using XGetImage; opened for inspection','binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'image_sha256':hashlib.sha256((out/'ASDK-beta.png').read_bytes()).hexdigest(),'transcript_sha256':hashlib.sha256((out/'transcript.txt').read_bytes()).hexdigest()},indent=2)+'\n')
 finally:
  if term:term.terminate();term.wait(timeout=5)
  xvfb.terminate();xvfb.wait(timeout=5)
print(out/'ASDK-beta.png')

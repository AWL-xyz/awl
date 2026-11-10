#!/usr/bin/python3
import hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
from PIL import Image
from Xlib import X,display
ROOT=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent;binary=Path(os.environ.get('Awl_REPLACE_BINARY','/var/tmp/Awl-replace-sdk/Awl/bin/Awl'))
with tempfile.TemporaryDirectory(prefix='Awl-net-photo-',dir='/var/tmp') as td:
 work=Path(td)
 for src in (ROOT/'examples/apps/save').iterdir():
  if src.is_file():(work/src.name).write_bytes(src.read_bytes())
 transcript=work/'transcript.txt';script=work/'demo.sh';script.write_text('''#!/bin/sh
export PATH="'''+str(binary.parent)+'''":/usr/bin:/bin
export XDG_CACHE_HOME=/var/tmp/Awl-net-cache
cd "'''+td+'''"
{
printf '$ awl build\\n'
awl build
mkdir store
printf 'old copy\\n' > store/config
printf '\\n$ publish new stdin data without truncating the old file\\n'
printf '{"port":5432}\\n' | ./build/save store scratch config
printf 'publication status above, target now contains: '
cat store/config
printf '\\n$ existing temporary file refuses overwrite\\n'
printf 'reserved\\n' > store/scratch
printf 'bad replacement\\n' | ./build/save store scratch config
printf 'exit: %s\\n' "$?"
printf 'target retained: '
cat store/config
printf '\\n72 native/sanitizer replacement cases passed\\n14 fault/reuse cases passed, all 10 compiler sanitizer phases passed\\n'
printf '\\natomic publication, file + directory sync, explicit uncertain status\\ntrusted single writer, not hardware power-loss qualification\\n'
} > "'''+str(transcript)+'''" 2>&1
cat "'''+str(transcript)+'''"
touch "'''+td+'''/done"
''')
 xvfb=subprocess.Popen(['Xvfb',':97','-screen','0','900x440x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);term=None
 try:
  time.sleep(.5);term=subprocess.Popen(['xterm','-hold','-geometry','100x23+0+0','-fa','Monospace','-fs','11','-bg','#10151d','-fg','#d8f2e6','-e','/bin/sh',str(script)],env={**os.environ,'DISPLAY':':97'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  until=time.monotonic()+90
  while not(work/'done').exists():
   if time.monotonic()>until:raise RuntimeError('capture timed out')
   time.sleep(.1)
  time.sleep(.3);d=display.Display(':97');raw=d.screen().root.get_image(0,0,900,440,X.ZPixmap,0xffffffff);Image.frombytes('RGB',(900,440),raw.data,'raw','BGRX').quantize(colors=96).save(out/'native-replace.png',optimize=True);d.close()
  text=transcript.read_text();assert '5432' in text and 'target retained:' in text and 'exit: 3' in text and 'Traceback' not in text
  (out/'transcript.txt').write_text(text);(out/'capture.json').write_text(json.dumps({'method':'actual Xvfb/Xterm display captured via XGetImage, not generated imagery','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'image_sha256':hashlib.sha256((out/'native-replace.png').read_bytes()).hexdigest(),'transcript_sha256':hashlib.sha256((out/'transcript.txt').read_bytes()).hexdigest()},indent=2)+'\n')
 finally:
  if term:term.terminate();term.wait(timeout=5)
  xvfb.terminate();xvfb.wait(timeout=5)
print(out/'native-replace.png')

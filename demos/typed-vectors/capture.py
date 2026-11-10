#!/usr/bin/python3
import hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
from PIL import Image
from Xlib import display,X
ROOT=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent;binary=Path(os.environ.get('Awl_VECTOR_BINARY','/var/tmp/Awl-vectors-sdk/Awl/bin/Awl'))
with tempfile.TemporaryDirectory(prefix='Awl-vectors-photo-',dir='/var/tmp') as td:
 work=Path(td)
 for src in (ROOT/'examples/apps/sort').iterdir():
  if src.is_file():(work/src.name).write_bytes(src.read_bytes())
 transcript=work/'transcript.txt';script=work/'demo.sh'
 script.write_text('''#!/bin/sh
export PATH="'''+str(binary.parent)+'''":/usr/bin:/bin
export XDG_CACHE_HOME=/var/tmp/Awl-vectors-cache
cd "'''+td+'''"
{
printf '$ awl build\\n'
awl build
printf '\\n$ printf "pear\\\\napple\\\\npear\\\\nbanana\\\\n" | ./build/sort --unique\\n'
printf 'pear\\napple\\npear\\nbanana\\n' | ./build/sort --unique
printf '\\n$ printf "3\\\\n1\\\\n2\\\\n" | ./build/sort\\n'
printf '3\\n1\\n2\\n' | ./build/sort
printf '\\n$ invalid utf-8 input\\n'
printf '\\377' | ./build/sort
printf 'exit code: %s\\n' "$?"
printf '\\n$ current validation reports\\n'
/usr/bin/python3 -c 'import json; from pathlib import Path; r=Path("'''+str(ROOT)+'''"); print("bundled backend:",json.loads((r/"tests/typed-vectors-linux.json").read_text())["cases"],"passed"); print("generated-c ASan/UBSan:",json.loads((r/"tests/typed-vectors-sanitized.json").read_text())["cases"],"passed"); print((r/"tests/typed-vectors-verifier.txt").read_text().strip())'
printf '\\nscalar/text vectors, owned cleanup, independent slice copies\\nlinux development checkpoint, no new archive, windows deferred\\n'
} > "'''+str(transcript)+'''" 2>&1
cat "'''+str(transcript)+'''"
touch "'''+td+'''/done"
''')
 xvfb=subprocess.Popen(['Xvfb',':95','-screen','0','1000x600x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);term=None
 try:
  time.sleep(.5);term=subprocess.Popen(['xterm','-hold','-geometry','110x30+0+0','-fa','Monospace','-fs','11','-bg','#10151d','-fg','#d8f2e6','-title','Awl typed vectors','-e','/bin/sh',str(script)],env={**os.environ,'DISPLAY':':95'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  until=time.monotonic()+60
  while not(work/'done').exists():
   if time.monotonic()>until:raise RuntimeError('capture timed out')
   time.sleep(.1)
  time.sleep(.4);d=display.Display(':95');raw=d.screen().root.get_image(0,0,1000,600,X.ZPixmap,0xffffffff)
  Image.frombytes('RGB',(1000,600),raw.data,'raw','BGRX').quantize(colors=96).save(out/'native-sort.png',optimize=True);d.close()
  text=transcript.read_text();assert 'apple\nbanana\npear\n' in text and 'exit code: 2' in text
  (out/'transcript.txt').write_text(text)
  (out/'capture.json').write_text(json.dumps({'method':'actual Xvfb/Xterm display, XGetImage capture, not generated imagery','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'image_sha256':hashlib.sha256((out/'native-sort.png').read_bytes()).hexdigest(),'transcript_sha256':hashlib.sha256((out/'transcript.txt').read_bytes()).hexdigest()},indent=2)+'\n')
 finally:
  if term:term.terminate();term.wait(timeout=5)
  xvfb.terminate();xvfb.wait(timeout=5)
print(out/'native-sort.png')

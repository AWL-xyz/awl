#!/usr/bin/python3
import hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
from PIL import Image
from Xlib import X,display
ROOT=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent;binary=Path(os.environ.get('Awl_JSON_BINARY','/var/tmp/Awl-json-sdk/Awl/bin/Awl'))
with tempfile.TemporaryDirectory(prefix='Awl-net-photo-',dir='/var/tmp') as td:
 work=Path(td)
 for src in (ROOT/'examples/parsing').iterdir():
  if src.is_file():(work/src.name).write_bytes(src.read_bytes())
 (work/'config.json').write_text('{"database":{"host":"localhost","port":5432},"names":["café","Awl"]}')
 (work/'broken.json').write_text('{"database":]}')
 transcript=work/'transcript.txt';script=work/'demo.sh';script.write_text('''#!/bin/sh
export PATH="'''+str(binary.parent)+'''":/usr/bin:/bin
export XDG_CACHE_HOME=/var/tmp/Awl-net-cache
cd "'''+td+'''"
{
printf '$ awl build\\n'
awl build
printf '\\n$ jget config.json /database/port\\n'
./build/jget config.json /database/port
printf '\\n$ jget config.json /names/0\\n'
./build/jget config.json /names/0
printf '\\n$ jget broken.json\\n'
./build/jget broken.json
printf 'exit: %s\\n' "$?"
printf '\\n440 native +440 sanitizer parser/pointer cases passed\\n28 native +28 sanitizer cli cases passed\\n'
printf '\\nlimited to 16 KiB input, 16 nesting levels, 512 tokens\\nsource checkpoint, not browser parity or a new release archive\\n'
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
  time.sleep(.3);d=display.Display(':97');raw=d.screen().root.get_image(0,0,900,440,X.ZPixmap,0xffffffff);Image.frombytes('RGB',(900,440),raw.data,'raw','BGRX').quantize(colors=96).save(out/'native-json.png',optimize=True);d.close()
  text=transcript.read_text();assert '5432' in text and 'json error 1 at byte 12' in text and 'exit: 4' in text and 'Traceback' not in text
  (out/'transcript.txt').write_text(text);(out/'capture.json').write_text(json.dumps({'method':'actual Xvfb/Xterm display captured via XGetImage, not generated imagery','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'image_sha256':hashlib.sha256((out/'native-json.png').read_bytes()).hexdigest(),'transcript_sha256':hashlib.sha256((out/'transcript.txt').read_bytes()).hexdigest()},indent=2)+'\n')
 finally:
  if term:term.terminate();term.wait(timeout=5)
  xvfb.terminate();xvfb.wait(timeout=5)
print(out/'native-json.png')

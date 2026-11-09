#!/usr/bin/python3
import hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
from PIL import Image
from Xlib import display,X
ROOT=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent
binary=Path(os.environ.get('Awl_STREAMS_BINARY','/tmp/Awl-streams-bundle/Awl/bin/Awl'))
with tempfile.TemporaryDirectory(prefix='Awl-stream-photo-',dir='/var/tmp') as td:
 work=Path(td)
 for name in ['main.aw','kpipe.awproj']:(work/name).write_bytes((ROOT/'examples/apps/kpipe'/name).read_bytes())
 transcript=work/'transcript.txt';script=work/'demo.sh';oracle=work/'oracle.py'
 oracle.write_text('''import hashlib,os,subprocess
payload=bytes(range(256))*1024
r=subprocess.run(['./build/kpipe'],input=payload,capture_output=True,env={**os.environ,'KPIPE_MODE':'copy'})
assert r.returncode==0 and r.stdout==payload and not r.stderr
print('binary roundtrip:',len(payload),'bytes, sha256 matches')
print(hashlib.sha256(r.stdout).hexdigest())
''')
 script.write_text('''#!/bin/sh
export PATH="'''+str(binary.parent)+'''":/usr/bin:/bin
export XDG_CACHE_HOME=/tmp/Awl-streams-cache
unset KPIPE_MODE KPIPE_REPORT
cd "'''+td+'''"
{
printf '$ awl build\\n'
awl build
printf '\\n$ printf "hello, Awl!\\\\n" | KPIPE_MODE=upper KPIPE_REPORT=1 ./build/kpipe\\n'
printf 'hello, Awl!\\n' | KPIPE_MODE=upper KPIPE_REPORT=1 ./build/kpipe 2>report.txt
printf '\\n$ cat report.txt  # separate stderr report\\n'
cat report.txt
printf '\\n$ printf "AbC 123\\\\n" | KPIPE_MODE=lower ./build/kpipe\\n'
printf 'AbC 123\\n' | KPIPE_MODE=lower ./build/kpipe
printf '\\n$ KPIPE_MODE=invalid ./build/kpipe < /dev/null\\n'
KPIPE_MODE=invalid ./build/kpipe < /dev/null
printf 'exit code: %s\\n' "$?"
printf '\\n$ binary roundtrip oracle, all 256 byte values\\n'
/usr/bin/python3 "'''+str(oracle)+'''"
printf '\\n$ current validation reports\\n'
/usr/bin/python3 -c 'import json; from pathlib import Path; r=Path("'''+str(ROOT)+'''"); print("native cases:",json.loads((r/"tests/streams-linux.json").read_text())["cases"]); print("generated-c sanitizer cases:",json.loads((r/"tests/streams-sanitized.json").read_text())["cases"]); print("fault/real pipe cases:",json.loads((r/"tests/streams-faults.json").read_text())["cases"]); print("native sanitizer phases:",len(json.loads((r/"tests/streams-native-sanitized.json").read_text())["phases"]))'
printf '\\nlinux native source checkpoint, no new release archive\\nwindows deferred, language development first\\n'
} > "'''+str(transcript)+'''" 2>&1
cat "'''+str(transcript)+'''"
touch "'''+td+'''/done"
''')
 xvfb=subprocess.Popen(['Xvfb',':94','-screen','0','1100x820x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);term=None
 try:
  time.sleep(.5);term=subprocess.Popen(['xterm','-hold','-geometry','112x40+0+0','-fa','Monospace','-fs','12','-bg','#10151d','-fg','#d8f2e6','-title','Awl native pipelines','-e','/bin/sh',str(script)],env={**os.environ,'DISPLAY':':94'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  until=time.monotonic()+45
  while not(work/'done').exists():
   if time.monotonic()>until:raise RuntimeError('capture timed out')
   time.sleep(.1)
  time.sleep(.4);d=display.Display(':94');root=d.screen().root;raw=root.get_image(0,0,1100,820,X.ZPixmap,0xffffffff)
  Image.frombytes('RGB',(1100,820),raw.data,'raw','BGRX').quantize(colors=96).save(out/'native-pipelines.png',optimize=True);d.close()
  text=transcript.read_text();assert 'sha256 matches' in text and 'HELLO, Awl!' in text and 'exit code: 2' in text
  (out/'transcript.txt').write_text(text)
  (out/'capture.json').write_text(json.dumps({'method':'actual Xvfb/Xterm display captured with XGetImage, not generated text imagery','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'image_sha256':hashlib.sha256((out/'native-pipelines.png').read_bytes()).hexdigest(),'transcript_sha256':hashlib.sha256((out/'transcript.txt').read_bytes()).hexdigest()},indent=2)+'\n')
 finally:
  if term:term.terminate();term.wait(timeout=5)
  xvfb.terminate();xvfb.wait(timeout=5)
print(out/'native-pipelines.png')

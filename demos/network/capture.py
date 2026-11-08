#!/usr/bin/python3
import hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
from PIL import Image
from Xlib import X,display
ROOT=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent;binary=Path(os.environ.get('Awl_NET_BINARY','/var/tmp/Awl-net-sdk/Awl/bin/Awl'))
with tempfile.TemporaryDirectory(prefix='Awl-net-photo-',dir='/var/tmp') as td:
 work=Path(td)
 for src in (ROOT/'examples-next/apps/kserve').iterdir():
  if src.is_file():(work/src.name).write_bytes(src.read_bytes())
 oracle=work/'client.py';oracle.write_text('''import http.client,subprocess
p=subprocess.Popen(['./build/kserve','0','5'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 port=int(p.stdout.readline());print('native server bound to 127.0.0.1:'+str(port))
 for method,path,status in [('GET','/health',200),('GET','/counter',200),('POST','/counter',200),('GET','/counter',200),('GET','/missing',404)]:
  c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);c.request(method,path);r=c.getresponse();body=r.read().decode().strip();assert r.status==status;print(method,path,'->',r.status,body);c.close()
 assert p.wait(timeout=5)==0 and not p.stderr.read()
finally:
 if p.poll() is None:p.kill();p.wait()
''')
 transcript=work/'transcript.txt';script=work/'demo.sh';script.write_text('''#!/bin/sh
export PATH="'''+str(binary.parent)+'''":/usr/bin:/bin
export XDG_CACHE_HOME=/var/tmp/Awl-net-cache
cd "'''+td+'''"
{
printf '$ awl build\\n'
awl build
printf '\\n$ real http requests against the native Awl service\\n'
/usr/bin/python3 client.py
printf '\\n$ network validation reports\\n'
/usr/bin/python3 -c 'import json; from pathlib import Path; r=Path("'''+str(ROOT)+'''"); print("native network cases:",json.loads((r/"tests/net-linux.json").read_text())["cases"]); print("strict ASan/UBSan cases:",json.loads((r/"tests/net-sanitized.json").read_text())["cases"]); print((r/"tests/net-faults.txt").read_text().strip())'
printf '\\nloopback only, bounded synchronous foundation, not a production server\\nno tls, authentication, concurrency or complete http implementation\\nlinux source checkpoint, no new release archive, windows deferred\\n'
} > "'''+str(transcript)+'''" 2>&1
cat "'''+str(transcript)+'''"
touch "'''+td+'''/done"
''')
 xvfb=subprocess.Popen(['Xvfb',':97','-screen','0','1000x550x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);term=None
 try:
  time.sleep(.5);term=subprocess.Popen(['xterm','-hold','-geometry','110x28+0+0','-fa','Monospace','-fs','11','-bg','#10151d','-fg','#d8f2e6','-e','/bin/sh',str(script)],env={**os.environ,'DISPLAY':':97'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  until=time.monotonic()+90
  while not(work/'done').exists():
   if time.monotonic()>until:raise RuntimeError('capture timed out')
   time.sleep(.1)
  time.sleep(.3);d=display.Display(':97');raw=d.screen().root.get_image(0,0,1000,550,X.ZPixmap,0xffffffff);Image.frombytes('RGB',(1000,550),raw.data,'raw','BGRX').quantize(colors=96).save(out/'native-http.png',optimize=True);d.close()
  text=transcript.read_text();assert '-> 200 {"counter":1}' in text and '-> 404' in text and 'Traceback' not in text
  (out/'transcript.txt').write_text(text);(out/'capture.json').write_text(json.dumps({'method':'actual Xvfb/Xterm display captured via XGetImage, not generated imagery','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'image_sha256':hashlib.sha256((out/'native-http.png').read_bytes()).hexdigest(),'transcript_sha256':hashlib.sha256((out/'transcript.txt').read_bytes()).hexdigest()},indent=2)+'\n')
 finally:
  if term:term.terminate();term.wait(timeout=5)
  xvfb.terminate();xvfb.wait(timeout=5)
print(out/'native-http.png')

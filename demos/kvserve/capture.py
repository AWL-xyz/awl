#!/usr/bin/python3
import hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
from PIL import Image
from Xlib import X,display
ROOT=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent;binary=Path(os.environ.get('Awl_KV_BINARY','/var/tmp/Awl-kv-sdk/Awl/bin/Awl'))
with tempfile.TemporaryDirectory(prefix='Awl-net-photo-',dir='/var/tmp') as td:
 work=Path(td)
 for src in (ROOT/'examples/apps/kvserve').iterdir():
  if src.is_file():(work/src.name).write_bytes(src.read_bytes())
 oracle=work/'client.py';oracle.write_text('''import http.client,json,subprocess
for methods in [[('PUT','/kv/note','hello Awl'),('GET','/kv/note',None)],[('GET','/kv/note',None),('DELETE','/kv/note',None),('GET','/kv/note',None)]]:
 p=subprocess.Popen(['./build/kvserve','./store','0',str(len(methods))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  port=int(p.stdout.readline());print('native service ready, '+('restart from storage' if methods[0][0]=='GET' else 'new storage'))
  for method,path,value in methods:
   c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);c.request(method,path,value);r=c.getresponse();body=r.read().decode().strip();print(method,path,'->',r.status,body);c.close()
   assert r.status in [200,201,404] and json.loads(body)
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
printf '\\n$ store, read, restart, delete, read through actual http\\n'
/usr/bin/python3 client.py
printf '\\n$ network validation reports\\n'
/usr/bin/python3 -c 'import json; from pathlib import Path; r=Path("'''+str(ROOT)+'''"); print("native service cases:",json.loads((r/"tests/kv-linux.json").read_text())["cases"]); print("strict ASan/UBSan cases:",json.loads((r/"tests/kv-sanitized.json").read_text())["cases"]); print("storage fault checks:",json.loads((r/"tests/kv-faults.json").read_text())["cases"])'
printf '\\nbounded local key/value tool, 128 keys and 256 journal records\\nno tls/auth/concurrency, no power-loss durability guarantee\\nlinux source checkpoint, no new release archive, windows deferred\\n'
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
  time.sleep(.3);d=display.Display(':97');raw=d.screen().root.get_image(0,0,1000,550,X.ZPixmap,0xffffffff);Image.frombytes('RGB',(1000,550),raw.data,'raw','BGRX').quantize(colors=96).save(out/'native-kv.png',optimize=True);d.close()
  text=transcript.read_text();assert 'restart from storage' in text and '-> 201' in text and '-> 404' in text and 'Traceback' not in text
  (out/'transcript.txt').write_text(text);(out/'capture.json').write_text(json.dumps({'method':'actual Xvfb/Xterm display captured via XGetImage, not generated imagery','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'image_sha256':hashlib.sha256((out/'native-kv.png').read_bytes()).hexdigest(),'transcript_sha256':hashlib.sha256((out/'transcript.txt').read_bytes()).hexdigest()},indent=2)+'\n')
 finally:
  if term:term.terminate();term.wait(timeout=5)
  xvfb.terminate();xvfb.wait(timeout=5)
print(out/'native-kv.png')

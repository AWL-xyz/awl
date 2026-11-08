#!/usr/bin/env python3
import hashlib,http.client,json,os,subprocess,sys,tempfile
from pathlib import Path
from kvserve import record
exe=Path(sys.argv[1]).resolve();cases=[]
with tempfile.TemporaryDirectory(prefix='Awl-kv-faults-',dir='/var/tmp') as td:
 for mode in ['short','zero','partial','fsync','close']:
  prefix=Path(td)/mode;env={**os.environ,'KV_FAULT':mode,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'}
  p=subprocess.Popen([str(exe),str(prefix),'0','1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
  try:
   port=int(p.stdout.readline());c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);c.request('PUT','/kv/key',b'value');r=c.getresponse();r.read();c.close();out,err=p.communicate(timeout=5)
   assert (r.status,p.returncode,out,err)==((201,0,b'',b'') if mode=='short' else (503,5,b'',b'')),(mode,r.status,p.returncode,err)
   cases.append(mode+' write result and fail-stop');data=Path(str(prefix)+'.1.kvs').read_bytes()
   assert data==(b'' if mode=='zero' else b'KVS' if mode=='partial' else record(1,1,'key',b'value'))
   cases.append(mode+' exact record oracle')
  finally:
   if p.poll() is None:p.kill();p.communicate()
  env['KV_FAULT']='short';p=subprocess.Popen([str(exe),str(prefix),'0','1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
  try:
   line=p.stdout.readline()
   if mode in ['zero','partial']:
    out,err=p.communicate(timeout=5);assert (line,out,err,p.returncode)==(b'-5\n',b'',b'',4)
   else:
    port=int(line);c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);c.request('GET','/kv/key');r=c.getresponse();body=json.loads(r.read());c.close();out,err=p.communicate(timeout=5)
    assert r.status==200 and body=={'key':'key','value':'value','revision':1} and (out,err,p.returncode)==(b'',b'',0),(mode,body,err)
   cases.append(mode+' restart with short reads and EINTR')
  finally:
   if p.poll() is None:p.kill();p.communicate()
report={'status':'PASS','cases':len(cases),'records':cases,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'qualification':'linker syscall wrappers on strict generated-C ASan/UBSan service, not power-loss or filesystem hardware fault testing'}
Path(sys.argv[2]).write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(cases),'fault checks')

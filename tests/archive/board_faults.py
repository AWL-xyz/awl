#!/usr/bin/env python3
import hashlib,http.client,json,os,subprocess,sys,tempfile
from pathlib import Path
exe=Path(sys.argv[1]).resolve();records=[]
old={'version':1,'revision':1,'next_id':2,'tasks':[{'id':1,'title':'old','note':'','status':'todo'}]}
with tempfile.TemporaryDirectory(prefix='Awl-board-faults-',dir='/var/tmp') as td:
 for mode in ['zero','partial','file-sync','file-close','rename','dir-sync','dir-close','short']:
  d=Path(td)/mode;d.mkdir();raw=json.dumps(old).encode();(d/'board.json').write_bytes(raw);env={**os.environ,'BOARD_FAULT':mode,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'};p=subprocess.Popen([str(exe),str(d),'0','2'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
  try:
   port=int(p.stdout.readline());c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);headers={'Origin':f'http://127.0.0.1:{port}','If-Match':'"v1"','Content-Type':'application/json'};c.request('PUT','/api/tasks/1',json.dumps({'title':'new','note':'','status':'done'}),headers);r=c.getresponse();body=json.loads(r.read());h=dict(r.getheaders());c.close();published=mode in ['dir-sync','dir-close','short'];uncertain=mode.startswith('dir-');assert r.status==(202 if uncertain else 200 if published else 503),(mode,r.status,body)
   if published:
    data=json.loads((d/'board.json').read_bytes());assert data==body and data['revision']==2 and data['tasks'][0]['title']=='new';assert h['X-Awl-Durability']==('uncertain' if uncertain else 'confirmed')
   else:assert (d/'board.json').read_bytes()==raw
   records.append(mode+' exact publication and HTTP outcome')
   if uncertain:
    out,err=p.communicate(timeout=5);assert p.returncode==6 and not out and not err;records.append(mode+' explicit uncertain acknowledgement then fail-stop')
   else:
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);c.request('GET','/api/tasks');r=c.getresponse();data=json.loads(r.read());c.close();out,err=p.communicate(timeout=5);assert p.returncode==0 and not out and not err and data['revision']==(2 if published else 1);records.append(mode+' live state matches publication')
  finally:
   if p.poll() is None:p.kill();p.communicate()
  p=subprocess.Popen([str(exe),str(d),'0','1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'});port=int(p.stdout.readline());c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);c.request('GET','/api/tasks');r=c.getresponse();data=json.loads(r.read());c.close();out,err=p.communicate(timeout=5);assert p.returncode==0 and not out and not err and data['revision']==(2 if published else 1);records.append(mode+' restart agrees with published data')
report={'status':'PASS','cases':len(records),'records':records,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'qualification':'ASan/UBSan strict generated C plus deterministic syscall wrappers, not hardware power-loss, hostile directory races or multiwriter acceptance'};Path(sys.argv[2]).write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(records),'fault checks')

#!/usr/bin/env python3
import contextlib,hashlib,http.client,json,os,random,socket,subprocess,sys,tempfile,time
from pathlib import Path
EXE=Path(sys.argv[1]).resolve();REPORT=Path(sys.argv[2]);cases=[]
def check(name,condition=True):
 assert condition,name
 cases.append(name)
@contextlib.contextmanager
def server(directory,maximum=256,extra_env=None):
 p=subprocess.Popen([str(EXE),str(directory),'0',str(maximum)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,**(extra_env or {})})
 try:
  line=p.stdout.readline();assert line.strip().isdigit(),(line,p.communicate(timeout=5));port=int(line)
  yield p,port
 finally:
  if p.poll() is None:p.terminate()
  out,err=p.communicate(timeout=5);assert not out and not err,(out,err)
def request(port,method='GET',path='/api/tasks',body=None,tag=None,headers=None):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);h={'Origin':f'http://127.0.0.1:{port}'}
 if tag is not None:h['If-Match']=tag
 if body is not None:h['Content-Type']='application/json'
 if headers:h.update(headers)
 if isinstance(body,dict):body=json.dumps(body,ensure_ascii=False).encode()
 c.request(method,path,body,headers=h);r=c.getresponse();data=r.read();result=(r.status,dict(r.getheaders()),data);c.close();return result
def raw(port,payload):
 with socket.create_connection(('127.0.0.1',port),timeout=5) as s:
  s.sendall(payload);s.shutdown(socket.SHUT_WR);out=b''
  while True:
   part=s.recv(131072)
   if not part:break
   out+=part
 return int(out.split(b' ',2)[1]),out
TASK={'title':'ship the owl 🦉','note':'notes\n日本語\t"\\','status':'todo'}
with tempfile.TemporaryDirectory(prefix='Awl-board-test-',dir='/var/tmp') as td:
 d=Path(td)
 with server(d) as (p,port):
  code,h,b=request(port);state=json.loads(b);check('empty snapshot and strong ETag',(code,h['ETag'],state)==(200,'"v0"',{'version':1,'revision':0,'next_id':1,'tasks':[]}))
  code,h,b=request(port,path='/');check('embedded app and defensive CSP',code==200 and b'Awl Board' in b and 'frame-ancestors' in h['Content-Security-Policy'] and h['Cache-Control']=='no-store')
  check('missing precondition',request(port,'PUT','/api/tasks/1',TASK)[0]==428)
  check('weak etag not accepted',request(port,'PUT','/api/tasks/1',TASK,'W/"v0"')[0]==412)
  check('wildcard not accepted',request(port,'PUT','/api/tasks/1',TASK,'*')[0]==412)
  check('cross origin rejected',request(port,'PUT','/api/tasks/1',TASK,'"v0"',{'Origin':'https://evil.invalid'})[0]==403)
  check('DNS rebinding host rejected',request(port,headers={'Host':'evil.invalid'})[0]==403)
  check('cross-site fetch rejected',request(port,'PUT','/api/tasks/1',TASK,'"v0"',{'Sec-Fetch-Site':'cross-site'})[0]==403)
  code,h,b=request(port,'PUT','/api/tasks/1',TASK,'"v0"');state=json.loads(b);tag=h['ETag'];check('create returns canonical UTF-8 snapshot',code==201 and state['tasks']==[{'id':1,**TASK}] and tag=='"v1"')
  disk=(d/'board.json').read_bytes();check('API matches published snapshot',disk==b)
  check('stale tab cannot overwrite',request(port,'PUT','/api/tasks/1',{**TASK,'title':'stale'},'"v0"')[0]==412)
  check('retry cannot duplicate create',request(port,'PUT','/api/tasks/1',TASK,'"v0"')[0]==412)
  code,h,b=request(port,'PUT','/api/tasks/1',TASK,tag);check('identical PUT is a no-op',code==200 and h['ETag']==tag and (d/'board.json').read_bytes()==disk)
  for name,body in [('empty title',{**TASK,'title':''}),('spaces',{**TASK,'title':'  '}),('control title',{**TASK,'title':'x\n'}),('title bytes',{**TASK,'title':'🦉'*41}),('note bytes',{**TASK,'note':'🦉'*65}),('note control',{**TASK,'note':'\0'}),('status',{**TASK,'status':'other'}),('extra field',{**TASK,'extra':1}),('wrong type',{**TASK,'title':3}),('duplicate',b'{"title":"a","title":"b","note":"","status":"todo"}'),('invalid JSON',b'{'),('wrong root',b'[]')]:
   check('reject '+name,request(port,'PUT','/api/tasks/1',body,tag)[0]==422)
  check('failed validations preserve disk',(d/'board.json').read_bytes()==disk)
  check('wrong media type',request(port,'PUT','/api/tasks/1',TASK,tag,{'Content-Type':'text/plain'})[0]==415)
  for name,path,status in [('unknown','/missing',404),('query','/api/tasks?x=1',404),('leading zero','/api/tasks/01',400),('non-id','/api/tasks/a',400),('future-id','/api/tasks/10',404)]:
   check(name,request(port,'PUT',path,TASK,tag)[0]==status)
  check('missing delete',request(port,'DELETE','/api/tasks/2',tag=tag)[0]==404)
  payloads=[('duplicate host',b'GET / HTTP/1.1\r\nHost: x\r\nHost: y\r\n\r\n',400),('missing host',b'GET / HTTP/1.1\r\n\r\n',400),('transfer encoding',b'GET / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n',400),('duplicate length',b'PUT / HTTP/1.1\r\nHost: x\r\nContent-Length: 0\r\nContent-Length: 0\r\n\r\n',400),('oversized body',b'PUT / HTTP/1.1\r\nHost: x\r\nContent-Length: 1025\r\n\r\n',413),('bad version',b'GET / HTTP/1.0\r\nHost: x\r\n\r\n',400),('unsupported method',b'POST / HTTP/1.1\r\nHost: x\r\n\r\n',405),('folded header',b'GET / HTTP/1.1\r\nHost: x\r\n x: y\r\n\r\n',400),('bare newline',b'GET / HTTP/1.1\r\nHost: x\nx\r\n\r\n',400)]
  for name,payload,status in payloads:check(name,raw(port,payload)[0]==status)
  for header in ['Origin','If-Match','Sec-Fetch-Site']:
   payload=f'PUT / HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n{header}: x\r\n{header}: y\r\nContent-Length: 0\r\n\r\n'.encode();check('duplicate '+header,raw(port,payload)[0]==400)
  code,h,b=request(port,'PUT','/api/tasks/1',{**TASK,'status':'doing'},tag);tag=h['ETag'];check('status update',code==200 and json.loads(b)['tasks'][0]['status']=='doing')
  code,h,b=request(port,path='/api/export');check('download matches disk',code==200 and b==(d/'board.json').read_bytes() and 'attachment' in h['Content-Disposition'])
 with server(d) as (p,port):
  code,h,b=request(port);check('restart restores complete state',json.loads(b)['tasks']==[{'id':1,**TASK,'status':'doing'}] and h['ETag']=='"v2"')
  code,h,b=request(port,'DELETE','/api/tasks/1',tag=h['ETag']);check('delete persisted',code==200 and json.loads(b)['tasks']==[])
 with server(d) as (p,port):
  code,h,b=request(port);check('delete survives restart and IDs not reused',json.loads(b)=={'version':1,'revision':3,'next_id':2,'tasks':[]})
  code,h,b=request(port,'PUT','/api/tasks/2',TASK,h['ETag']);check('next creation remains monotonic',code==201 and json.loads(b)['next_id']==3)
 valid=(d/'board.json').read_bytes()
 corrupt=[b'',b'{',b'\xff',b'{}',b'{"version":2,"revision":0,"next_id":1,"tasks":[]}',valid.replace(b'"revision":4',b'"revision":-1'),valid.replace(b'"id":2',b'"id":3'),valid.replace(b'"status":"todo"',b'"status":"bad"'),valid.replace(b'"next_id":3',b'"next_id":2'),valid.replace(b'"version":1',b'"extra":1,"version":1')]
 for n,data in enumerate(corrupt):
  (d/'board.json').write_bytes(data);r=subprocess.run([str(EXE),str(d)],capture_output=True,timeout=5);check('fail closed corrupt snapshot '+str(n),r.returncode==4 and not r.stderr and (d/'board.json').read_bytes()==data)
 (d/'board.json').write_bytes(valid)
 # Single-server independent state-machine oracle, including restart checkpoints
 rng=random.Random(1729);oracle=json.loads(valid)
 for epoch in range(3):
  with server(d) as (p,port):
   for n in range(45):
    tag=f'"v{oracle["revision"]}"';existing=oracle['tasks'];op=rng.choice(['create','update','delete']) if existing else 'create'
    if op=='create' and len(existing)==32:op='delete'
    if op=='create':
     id=oracle['next_id'];task={'title':f'task {epoch}-{n} 🦉','note':rng.choice(['','a\nb','café','quotes " \\']),'status':rng.choice(['todo','doing','done'])};code,h,b=request(port,'PUT',f'/api/tasks/{id}',task,tag);assert code==201;(existing.append({'id':id,**task}));oracle['next_id']+=1
    else:
     task=rng.choice(existing);id=task['id']
     if op=='delete':code,h,b=request(port,'DELETE',f'/api/tasks/{id}',tag=tag);assert code==200;existing.remove(task)
     else:
      update={k:v for k,v in task.items() if k!='id'};update['note']=f'updated {epoch}-{n}';code,h,b=request(port,'PUT',f'/api/tasks/{id}',update,tag);assert code==200;task.update(update)
    oracle['revision']+=1;check('model operation '+str(epoch*45+n),json.loads(b)==oracle and json.loads((d/'board.json').read_bytes())==oracle and h['ETag']==f'"v{oracle["revision"]}"')
 # Real storage refusal, followed by a successful retry, no false acknowledgement
 with server(d) as (p,port):
  old=(d/'board.json').read_bytes();(d/'.board.tmp').mkdir();tag=f'"v{oracle["revision"]}"';id=oracle['next_id'];code,h,b=request(port,'PUT',f'/api/tasks/{id}',TASK,tag);check('write-open failure preserves published state',code==503 and (d/'board.json').read_bytes()==old);(d/'.board.tmp').rmdir();check('retry after storage repair',request(port,'PUT',f'/api/tasks/{id}',TASK,tag)[0]==201)
report={'status':'PASS','cases':len(cases),'records':cases,'executable_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'qualification':'independent HTTP/disk/state-machine oracle on Linux, no multiwriter, hardware power-loss or native Windows claim'};REPORT.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(cases),'native board checks')

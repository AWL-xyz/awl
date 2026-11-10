#!/usr/bin/env python3
import hashlib,http.client,json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
exe=Path(sys.argv[1]).resolve();records=[]
def req(port,method='GET',path='/api/tasks',body=None,tag=None):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);h={'Origin':f'http://127.0.0.1:{port}','Content-Type':'application/json'}
 if tag:h['If-Match']=tag
 c.request(method,path,json.dumps(body).encode() if body else None,h);r=c.getresponse();data=r.read();status=r.status;c.close();return status,json.loads(data)
with tempfile.TemporaryDirectory(prefix='Awl-board-limits-',dir='/var/tmp') as td:
 d=Path(td);state={'version':1,'revision':32,'next_id':33,'tasks':[{'id':i,'title':'"'*160,'note':'\n'*256,'status':'doing'} for i in range(1,33)]};(d/'board.json').write_text(json.dumps(state));p=subprocess.Popen([str(exe),td,'0','256'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  line=p.stdout.readline();assert line.strip().isdigit(),(line,p.communicate());port=int(line);hwm=0
  for n in range(256):
   body={'title':'"'*159+('A' if n%2==0 else 'B'),'note':'\n'*256,'status':'doing'};code,data=req(port,'PUT','/api/tasks/1',body,f'"v{32+n}"');assert code==200 and data['revision']==33+n and len(data['tasks'])==32,(n,code,data);assert json.loads((d/'board.json').read_bytes())==data
   if n==254:
    status=Path(f'/proc/{p.pid}/status').read_text();hwm=int(next(x.split()[1] for x in status.splitlines() if x.startswith('VmHWM:')))
  out,err=p.communicate(timeout=5);assert p.returncode==0 and not out and not err;records.append('all 256 maximum-size 32-task mutations persist and exhaust session cleanly');assert (d/'board.json').stat().st_size>60000;records.append('worst-case escaped snapshot above 60kB roundtrips')
 finally:
  if p.poll() is None:p.kill();p.communicate()
 p=subprocess.Popen([str(exe),td,'0','4'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);port=int(p.stdout.readline())
 try:
  code,data=req(port);assert code==200 and data['revision']==288;records.append('restart reloads maximum escaped snapshot')
  code,data=req(port,'PUT','/api/tasks/33',{'title':'overflow','note':'','status':'todo'},'"v288"');assert code==507;records.append('33rd task refused without publication')
  started=time.monotonic()
  with socket.create_connection(('127.0.0.1',port),timeout=5) as s:
   s.sendall(b'GET / HTTP/1.1\r\nHost:');raw=s.recv(4096);assert raw.startswith(b'HTTP/1.1 408 ') and time.monotonic()-started<4
  records.append('incomplete client has bounded total request deadline');code,data=req(port);assert code==200 and data['revision']==288;records.append('server remains usable after timeout and capacity failure');out,err=p.communicate(timeout=5);assert p.returncode==0 and not out and not err
 finally:
  if p.poll() is None:p.kill();p.communicate()
report={'status':'PASS','cases':len(records),'records':records,'peak_rss_kib_near_session_limit':hwm,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'qualification':'single local server, 256 worst-size serialized updates, observed RSS not a performance comparison or concurrency test'};Path(sys.argv[2]).write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(records),'limit checks',hwm,'KiB peak RSS')

#!/usr/bin/env python3
import argparse,hashlib,json,os,random,resource,shutil,socket,struct,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--sanitize-c',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args();binary=a.kcc.resolve();records=[]
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-net-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'}
 with tempfile.TemporaryDirectory(prefix='Awl-net-tests-',dir='/var/tmp') as td:
  work=Path(td);serial=0
  def build(name,body=None,source=None,files=None,error=None):
   nonlocal serial
   serial+=1;folder=work/str(serial);folder.mkdir();src=folder/'main.aw';src.write_text(source if source is not None else 'func main()->i64 '+body+' return 0; end;')
   for name,text in (files or {}).items():(folder/name).write_text(text)
   exe=folder/'app';command='check' if error else 'emit-c' if a.sanitize_c else 'build';r=subprocess.run([str(binary),command,str(src),'--syntax','next']+(['-o',str(exe)] if command=='build' else []),capture_output=True,text=True,env=env,timeout=180)
   if error:assert r.returncode==1 and error in r.stderr,(name,r.stderr);records.append([name,'diagnosed']);return
   assert r.returncode==0,(name,r.stderr)
   if a.sanitize_c:
    c=folder/'app.c';c.write_text(r.stdout);subprocess.run([shutil.which('cc'),'-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(c),'-lm','-o',str(exe)],check=True,timeout=90)
   return exe
  def plain(name,body,expected=None,trap=False):
   exe=build(name,body);r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=10)
   if trap:assert r.returncode!=0 and b'resource trap' in r.stderr,(name,r.returncode,r.stderr)
   else:assert (r.returncode,r.stdout,r.stderr)==(0,expected,b''),(name,r.returncode,r.stdout,r.stderr)
   assert b'AddressSanitizer' not in r.stderr and b'runtime error:' not in r.stderr;records.append([name,'passed'])
  plain('arguments','print(tcp.listenloopback(-1,1)); print(tcp.listenloopback(65536,1)); print(tcp.listenloopback(0,0)); print(tcp.listenloopback(0,129));',b'-5\n'*4)
  plain('listen deadline and port collision','@p s: tcp.listenloopback(0,8); defer tcp.close(s); print(tcp.valid(s)); print(tcp.port(s)>0); print(tcp.listenloopback(tcp.port(s),1)); print(tcp.accept(s,0)); print(tcp.accept(s,20)); print(tcp.accept(s,-1)); print(tcp.accept(s,3600001));',b'true\ntrue\n-3\n-10\n-10\n-5\n-5\n')
  plain('slots cleanup and ids','@p ids [i64;32]: [0;32]; @p i: 0; while i<32 do ids[i]: tcp.listenloopback(0,1); if ids[i]<0 then return 9; end; i: i+1; end; print(tcp.listenloopback(0,1)); @p old: ids[0]; tcp.close(old); @p fresh: tcp.listenloopback(0,1); print(fresh!=old); print(tcp.valid(old)); tcp.close(fresh); i: 1; while i<32 do tcp.close(ids[i]); i: i+1; end;',b'-7\ntrue\nfalse\n')
  for name,tail in [('stale','tcp.close(s); tcp.port(s);'),('double close','tcp.close(s); tcp.close(s);'),('range','@p b: buffer.new(1); tcp.read(s,b,2,0,0);'),('negative count','@p b: buffer.new(1); tcp.write(s,b,0,-1,0);'),('buffer handle','tcp.read(s,999,0,0,0);')]:plain(name,'@p s: tcp.listenloopback(0,1); '+tail,trap=True)
  plain('wrong resource family','tcp.port(1);',trap=True)
  plain('wrong socket kind','@p s: tcp.listenloopback(0,1); defer tcp.close(s); @p b: buffer.new(0); defer buffer.free(b); print(tcp.read(s,b,0,0,0));',b'-5\n')
  for name,body in [('arity','tcp.read(1,2,3,4);'),('type','tcp.accept("x",1);'),('defer type','defer tcp.close("x");')]:build(name,body,error='argument')
  prefix='@p s: tcp.listenloopback(0,8); defer tcp.close(s); print(tcp.port(s)); stdout.flush(); @p c: tcp.accept(s,2000); if c<0 then return 8; end; defer tcp.close(c); @p b: buffer.new(65536); defer buffer.free(b); '
  echo=build('echo',prefix+'@p done: false; while not done do @p n: tcp.read(c,b,0,65536,1000); if n<0 then return 9; end; if n==0 then done: true; else @p offset: 0; while offset<n do @p sent: tcp.write(c,b,offset,n-offset,1000); if sent<=0 then return 7; end; offset: offset+sent; end; end; end;')
  def start(exe,args=()):
   proc=subprocess.Popen([str(exe),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env);line=proc.stdout.readline();assert line and line.strip().isdigit(),(line,proc.stderr.read());return proc,int(line)
  def finish(proc,expected=b''):
   out,err=proc.communicate(timeout=10);assert (proc.returncode,out,err)==(0,expected,b''),(proc.returncode,out,err)
  proc,port=start(echo)
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=3) as client:
    data=random.Random(20261106).randbytes(200003);client.sendall(data);client.shutdown(socket.SHUT_WR);received=b''
    while True:
     part=client.recv(65536)
     if not part:break
     received+=part
    assert received==data
   finish(proc);records.append(['binary tcp echo and eof','passed'])
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
  probe=build('probe',prefix+'print(tcp.read(c,b,65536,0,0)); print(tcp.write(c,b,65536,0,0)); print(tcp.read(c,b,0,0,-1)); print(tcp.port(c)); print(tcp.accept(c,0)); print(tcp.read(c,b,0,1,20));')
  proc,port=start(probe)
  with socket.create_connection(('127.0.0.1',port),timeout=3):finish(proc,b'0\n0\n-5\n-5\n-5\n-10\n')
  records.append(['zero operations, connected kinds, read timeout','passed'])
  source=(ROOT/'examples/apps/serve/main.aw').read_text();files={'Http.aw':(ROOT/'examples/apps/serve/Http.aw').read_text()};service=build('serve',source=source,files=files)
  tests=[]
  def request(method,path='/health',headers=b'Host: localhost\r\n'):return method+b' '+path.encode()+b' HTTP/1.1\r\n'+headers+b'\r\n'
  tests += [('health',request(b'GET'),200,{'status':'ok'}),('counter start',request(b'GET','/counter'),200,{'counter':0}),('increment',request(b'POST','/counter'),200,{'counter':1}),('counter retained',request(b'GET','/counter'),200,{'counter':1}),('missing',request(b'GET','/missing'),404,{'error':404}),('method',request(b'DELETE','/counter'),405,{'error':405}),('health post',request(b'POST'),405,{'error':405}),('case folded headers',request(b'GET',headers=b'hOsT: localhost\r\ncontent-length: 0\r\n'),200,{'status':'ok'})]
  for label,data in [('no host',request(b'GET',headers=b'')),('duplicate host',request(b'GET',headers=b'Host: a\r\nHost: b\r\n')),('empty host',request(b'GET',headers=b'Host: \r\n')),('chunked',request(b'POST','/counter',b'Host: a\r\nTransfer-Encoding: chunked\r\n')),('body rejected',request(b'POST','/counter',b'Host: a\r\nContent-Length: 1\r\n')),('duplicate lengths',request(b'GET',headers=b'Host: a\r\nContent-Length: 0\r\nContent-Length: 0\r\n')),('bad version',b'GET /health HTTP/1.0\r\nHost: a\r\n\r\n'),('bad spacing',b'GET  /health HTTP/1.1\r\nHost: a\r\n\r\n'),('folded header',request(b'GET',headers=b'Host: a\r\n bad: x\r\n')),('nul',request(b'GET',headers=b'Host: a\0b\r\n')),('invalid utf8',request(b'GET',headers=b'Host: \xff\r\n'))]:tests.append((label,data,400,{'error':400}))
  tests += [('many headers',request(b'GET',headers=b'Host: a\r\n'+b'X: y\r\n'*32),431,{'error':431}),('large header',b'GET /health HTTP/1.1\r\nHost: a\r\nX: '+b'x'*8192,431,{'error':431}),('fragmented',request(b'GET'),200,{'status':'ok'}),('timeout',b'GET /health',408,{'error':408}),('truncated',b'GET /health',400,{'error':400})]
  proc,port=start(service,('0',str(len(tests)+3)))
  try:
   for label,data,status,body in tests:
    with socket.create_connection(('127.0.0.1',port),timeout=3) as client:
     if label=='fragmented':
      for byte in data:client.sendall(bytes([byte]));time.sleep(.001)
     else:client.sendall(data)
     if label=='truncated':client.shutdown(socket.SHUT_WR)
     output=b''
     while True:
      try:part=client.recv(16384)
      except ConnectionResetError:break
      if not part:break
      output+=part
    header,payload=output.split(b'\r\n\r\n',1);lines=header.split(b'\r\n');assert int(lines[0].split()[1])==status,(label,output)
    fields=dict(line.split(b': ',1) for line in lines[1:]);assert fields[b'Content-Length']==str(len(payload)).encode() and fields[b'Connection']==b'close' and json.loads(payload)==body,(label,output)
    if status==405:assert fields[b'Allow']==(b'GET' if label=='health post' else b'GET, POST')
    records.append(['http '+label,'passed'])
   with socket.create_connection(('127.0.0.1',port),timeout=3) as client:client.sendall(request(b'GET')+request(b'POST','/counter'));output=client.recv(8192);assert output.count(b'HTTP/1.1')==1
   records.append(['one request per connection, no pipelined mutation','passed'])
   with socket.create_connection(('127.0.0.1',port),timeout=3) as client:client.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0));client.sendall(request(b'GET'))
   time.sleep(.02)
   with socket.create_connection(('127.0.0.1',port),timeout=3) as client:
    client.sendall(request(b'GET','/counter'));out=b''
    while True:
     part=client.recv(8192)
     if not part:break
     out+=part
    assert json.loads(out.split(b'\r\n\r\n',1)[1])=={'counter':1}
   finish(proc);records.append(['peer reset survival and state retained','passed'])
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
  for args in [('0','0'),('0','257'),('bad',),('0','1','extra')]:
   r=subprocess.run([str(service),*args],env=env,capture_output=True,timeout=5);assert r.returncode==2 and not r.stderr;records.append(['service argument rejection','passed'])
 report={'status':'PASS','mode':'strict generated-C ASan/UBSan' if a.sanitize_c else 'bundled linux backend, host tools absent from PATH','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'cases':len(records),'records':records};a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(records),report['mode'])
if __name__=='__main__':main()

#!/usr/bin/env python3
import argparse,hashlib,json,os,random,socket,struct,subprocess,tempfile,time,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(seq,op,key,value=b''):
 key=key.encode();data=b'KVS1'+bytes([op,len(key)])+struct.pack('>HHH',len(value),seq,0)+key+value
 return data+struct.pack('>I',zlib.adler32(data))
def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();exe=a.exe.resolve();cases=[];latencies=[]
 env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'}
 def check(label,truth):
  assert truth,label
  cases.append(label)
 with tempfile.TemporaryDirectory(prefix='Awl-kv-tests-',dir='/var/tmp') as td:
  root=Path(td);serial=0;active=[]
  def directory():
   nonlocal serial
   serial+=1;folder=root/str(serial);folder.mkdir();return folder/'store'
  def start(prefix,maximum=256):
   proc=subprocess.Popen([str(exe),str(prefix),'0',str(maximum)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env);active.append(proc)
   line=proc.stdout.readline();assert line.strip().isdigit(),(line,proc.communicate(timeout=5));return proc,int(line)
  def stop(proc,code=None,kill=False):
   if kill:proc.kill()
   elif code is None:proc.terminate()
   out,err=proc.communicate(timeout=5);assert not out and not err,(out,err)
   if code is not None:assert proc.returncode==code,proc.returncode
  def wire(port,data,fragment=False,shutdown=False):
   begin=time.perf_counter_ns()
   with socket.create_connection(('127.0.0.1',port),timeout=3) as s:
    if fragment:
     for at in range(0,len(data),7):s.sendall(data[at:at+7]);time.sleep(.0001)
    else:s.sendall(data)
    if shutdown:s.shutdown(socket.SHUT_WR)
    out=b''
    while True:
     try:chunk=s.recv(16384)
     except ConnectionResetError:break
     if not chunk:break
     out+=chunk
   latencies.append((time.perf_counter_ns()-begin)/1e6)
   header,body=out.split(b'\r\n\r\n',1);lines=header.split(b'\r\n');fields=dict(x.split(b': ',1) for x in lines[1:]);assert fields[b'Content-Length']==str(len(body)).encode() and fields[b'Connection']==b'close' and fields[b'Content-Type']==b'application/json'
   return int(lines[0].split()[1]),json.loads(body)
  def request(port,method,path,value=b'',**options):
   return wire(port,method.encode()+b' '+path.encode()+b' HTTP/1.1\r\nHost: localhost\r\nContent-Length: '+str(len(value)).encode()+b'\r\n\r\n'+value,**options)
  try:
   prefix=directory();proc,port=start(prefix);oracle={};revision=0
   check('empty health',request(port,'GET','/health')==(200,{'status':'ok','keys':0,'revision':0}))
   values=['','hello','quote " slash \\','\x00\x01\b\t\n\r\x1f','café 日本語 😀','x'*1024,'\x00'*1024]
   for i,value in enumerate(values):
    key='k'+str(i);status,body=request(port,'PUT','/kv/'+key,value.encode(),fragment=i==4);revision+=1;oracle[key]=value
    check('put '+str(i),status==201 and body['revision']==revision)
    check('json roundtrip '+str(i),request(port,'GET','/kv/'+key)==(200,{'key':key,'value':value,'revision':revision}))
   rng=random.Random(673)
   for i in range(65):
    key='key'+str(rng.randrange(12));value=str(rng.randrange(10000))+' λ';created=key not in oracle
    status,body=request(port,'PUT','/kv/'+key,value.encode());revision+=1;oracle[key]=value
    check('random replacement '+str(i),status==(201 if created else 200) and body['revision']==revision)
   check('delete',request(port,'DELETE','/kv/k0')[0]==200);revision+=1;del oracle['k0']
   check('missing delete',request(port,'DELETE','/kv/k0')[0]==404)
   for method,path,value,status in [('GET','/kv/no',b'',404),('PUT','/kv/bad.key',b'v',400),('PUT','/kv/'+'a'*65,b'',400),('PUT','/kv/a',b'x'*1025,413),('PUT','/kv/a',b'\xff',422),('GET','/kv/a',b'x',400),('POST','/kv/a',b'',405),('PUT','/health',b'',405),('GET','/other',b'',404)]:
    check('http '+method+path[:15]+str(status),request(port,method,path,value)[0]==status)
   header=b'PUT /kv/a HTTP/1.1\r\nHost: a\r\n'
   for label,extra,status in [('missing length',b'',411),('duplicate length',b'Content-Length: 0\r\nContent-Length: 0\r\n',400),('transfer encoding',b'Transfer-Encoding: chunked\r\n',400),('negative length',b'Content-Length: -1\r\n',400),('nondecimal length',b'Content-Length: 1x\r\n',400),('media type',b'Content-Length: 0\r\nContent-Type: application/json\r\n',415),('empty host',b'Host: \r\nContent-Length: 0\r\n',400)]:
    check(label,wire(port,header+extra+b'\r\n')[0]==status)
   check('truncated body',wire(port,header+b'Content-Length: 9\r\n\r\nx',shutdown=True)[0]==400)
   check('body timeout',wire(port,header+b'Content-Length: 9\r\n\r\nx')[0]==408)
   stop(proc,kill=True)
   check('independent record oracle',all(Path(str(prefix)+'.'+str(seq)+'.kvs').read_bytes()==record(seq,1,'k'+str(seq-1),values[seq-1].encode()) for seq in range(1,8)))
   proc,port=start(prefix,len(oracle)+1)
   for key,value in sorted(oracle.items()):check('restart '+key,request(port,'GET','/kv/'+key)==(200,{'key':key,'value':value,'revision':revision}))
   check('restart deletion retained',request(port,'GET','/kv/k0')[0]==404);stop(proc,0)
   baseline=record(1,1,'key',b'value');corrupt=[('truncated '+str(n),baseline[:n]) for n in range(len(baseline))]
   corrupt += [('flipped '+str(n),baseline[:n]+bytes([baseline[n]^1])+baseline[n+1:]) for n in range(len(baseline))]
   for offset,value in [(4,0),(4,3),(5,0),(5,65),(6,5),(8,1),(9,2),(10,1),(12,47),(15,255)]:
    data=bytearray(baseline[:-4]);data[offset]=value;corrupt.append(('semantic '+str(offset)+' '+str(value),bytes(data)+struct.pack('>I',zlib.adler32(data))))
   corrupt += [('delete unknown',record(1,2,'key')),('delete payload',record(1,2,'key',b'x')),('oversize',baseline+b'x'*1105)]
   for label,data in corrupt:
    prefix=directory();Path(str(prefix)+'.1.kvs').write_bytes(data);r=subprocess.run([str(exe),str(prefix)],capture_output=True,env=env,timeout=5)
    check('recovery rejects '+label,r.returncode==4 and r.stdout==b'-5\n' and not r.stderr and Path(str(prefix)+'.1.kvs').read_bytes()==data)
   for seq in [2,257]:
    prefix=directory();Path(str(prefix)+'.'+str(seq)+'.kvs').write_bytes(record(seq,1,'key'));r=subprocess.run([str(exe),str(prefix)],capture_output=True,env=env,timeout=5);check('gap or overflow '+str(seq),r.returncode==4 and not r.stderr)
   prefix=directory();proc,port=start(prefix);collision=Path(str(prefix)+'.1.kvs');collision.write_bytes(b'untouched')
   check('exclusive create failure',request(port,'PUT','/kv/a',b'v')[0]==503);stop(proc,5);check('collision not overwritten',collision.read_bytes()==b'untouched')
   prefix=directory();proc,port=start(prefix.parent/'absent'/'store');check('missing parent write',request(port,'PUT','/kv/a',b'v')[0]==503);stop(proc,5)
   prefix=directory()
   for seq in range(1,129):Path(str(prefix)+'.'+str(seq)+'.kvs').write_bytes(record(seq,1,'k'+str(seq),b'v'))
   proc,port=start(prefix,4)
   check('key cap',request(port,'PUT','/kv/new',b'x')[0]==507)
   check('replace at key cap',request(port,'PUT','/kv/k1',b'x')[0]==200)
   check('delete at key cap',request(port,'DELETE','/kv/k2')[0]==200)
   check('insert after delete',request(port,'PUT','/kv/new',b'x')[0]==201);stop(proc,0)
   prefix=directory()
   for seq in range(1,257):Path(str(prefix)+'.'+str(seq)+'.kvs').write_bytes(record(seq,1,'key',str(seq).encode()))
   proc,port=start(prefix,2);check('mutation cap',request(port,'PUT','/kv/key',b'new')[0]==507);check('read at mutation cap',request(port,'GET','/kv/key')[1]['value']=='256');stop(proc,0)
  finally:
   for proc in active:
    if proc.poll() is None:proc.kill();proc.communicate(timeout=5)
 report={'status':'PASS','executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'examples/apps/kvserve').glob('*'))},'cases':len(cases),'records':cases,'benchmark':{'requests':len(latencies),'median_ms':sorted(latencies)[len(latencies)//2],'max_ms':max(latencies),'qualification':'sequential local clients, includes deliberately fragmented requests and 500ms timeout, not throughput or production load'}}
 a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(cases),'cases')
if __name__=='__main__':main()

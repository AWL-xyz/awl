#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();kcc=a.kcc.resolve();reports=[]
with tempfile.TemporaryDirectory(prefix='Awl-jget-tests-',dir='/var/tmp') as td:
 folder=Path(td);src=ROOT/'examples/parsing/jget.aw';env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-json-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'}
 for mode in ['bundled','sanitized']:
  exe=folder/mode;cmd='build' if mode=='bundled' else 'emit-c';start=time.perf_counter_ns();r=subprocess.run([str(kcc),cmd,str(src),'--syntax','next']+(['-o',str(exe)] if mode=='bundled' else []),capture_output=True,text=True,env=env,timeout=180);assert r.returncode==0,r.stderr;build=(time.perf_counter_ns()-start)/1e6
  if mode=='sanitized':
   c=folder/'main.c';c.write_text(r.stdout);subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)],check=True,timeout=90)
  passed=0
  tests=[(br'{"database":{"host":"localhost","port":5432},"enabled":true,"names":["caf\u00e9","\ud83d\ude00"],"empty":"","nil":null}',pointer,0,want) for pointer,want in [('/database/host',b'localhost\n'),('/database/port',b'5432\n'),('/enabled',b'true\n'),('/names/0','café\n'.encode()),('/names/1','😀\n'.encode()),('/empty',b'\n'),('/nil',b'null\n')]]
  tests += [(source.encode(),pointer,code,want) for source,pointer,code,want in [('123456789012345678901234567890','',0,b'123456789012345678901234567890\n'),('1e9999','',0,b'1e9999\n'),('"a\\nb\\u0000"','',0,b'a\nb\x00\n'),('{}','',6,b''),('[]','',6,b''),('{}','/missing',5,b''),('{"a":1,"a":2}','/a',5,b''),('[]','/01',2,b''),('{}','/~2',2,b''),('{}','#',2,b''),('[1,]','',4,b''),('{"é":]','',4,b''),('"'+('x'*4097)+'"','',4,b'')]]
  tests += [(b'\xff','',4,b''),(b'"\x00"','',4,b''),(b'0'+b' '*16384,'',4,b'')]
  for source,pointer,code,want in tests:
   file=folder/'input.json';file.write_bytes(source);r=subprocess.run([str(exe),str(file),pointer],capture_output=True,env=env,timeout=5)
   assert r.returncode==code and r.stdout==want,(mode,source[:80],pointer,r.returncode,r.stdout,r.stderr)
   assert bool(r.stderr)==(code!=0) and b'AddressSanitizer' not in r.stderr and b'runtime error:' not in r.stderr
   assert file.read_bytes()==source;passed+=1
  for args,code in [([],2),([str(folder/'missing')],3),([str(folder)],3),(['a','b','c'],2)]:
   r=subprocess.run([str(exe),*args],capture_output=True,env=env,timeout=5);assert r.returncode==code and not r.stdout and b'AddressSanitizer' not in r.stderr;passed+=1
  file=folder/'input.json';file.write_text('42')
  with open('/dev/full','wb') as full:
   r=subprocess.run([str(exe),str(file)],stdout=full,stderr=subprocess.PIPE,env=env,timeout=5);assert r.returncode==3 and not r.stderr;passed+=1
  reports.append({'mode':mode,'cases':passed,'build_or_emit_ms':build,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()})
report={'status':'PASS','compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'sources_sha256':{name:hashlib.sha256((ROOT/'examples/parsing'/name).read_bytes()).hexdigest() for name in ['Json.aw','jget.aw','jget.awproj']},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'runs':reports};a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print(report)

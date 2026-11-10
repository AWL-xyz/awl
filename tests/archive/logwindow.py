#!/usr/bin/env python3
import argparse,hashlib,json,os,random,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-view-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'};records=[];rng=random.Random(247)
 with tempfile.TemporaryDirectory(prefix='Awl-logwindow-',dir='/var/tmp') as td:
  td=Path(td);entry=ROOT/'apps/logwindow/main.aw';c=td/'main.c';c.write_bytes(subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(entry)],check=True,capture_output=True).stdout)
  for mode in ['native','sanitized']:
   exe=td/mode
   if mode=='native':subprocess.run([str(sdk/'bin/awl'),'build',str(entry),'-o',str(exe)],check=True,capture_output=True,env={**env,'PATH':'/no-host-tools'})
   else:subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)],check=True)
   data=td/'log.txt'
   def run(name,raw,args,code,out):
    if raw is None:
     if data.exists():data.unlink()
    else:data.write_bytes(raw)
    r=subprocess.run([str(exe),str(data),*map(str,args)],capture_output=True,env=env);assert (r.returncode,r.stdout,r.stderr)==(code,out,b''),(name,mode,r.returncode,r.stdout,r.stderr);records.append(mode+' '+name)
   for i in range(40):
    lines=[rng.choice(['','café 🦉','日本語','alpha\tbeta','warning: recovered','an ordinary line']) for _ in range(rng.randrange(1,50))];ending=rng.choice(['\n','\r\n','\r']);raw=(ending.join(lines)+ending).encode();start=rng.randrange(1,len(lines)+2);count=rng.randrange(len(lines)-start+2);want=''.join(str(j+1)+': '+lines[j]+'\n' for j in range(start-1,start-1+count)).encode();run('seeded line-range '+str(i),raw,[start,count],0,want)
   run('UTF8 exact4096byte line',('🦉'*1024).encode(),[1,1],0,('1: '+'🦉'*1024+'\n').encode())
   run('UTF84097byte line',('🦉'*1024+'x').encode(),[1,1],4,b'line exceeds 4096 bytes\n')
   for raw,args,code,out in [(b'',(1,0),0,b''),(b'x',(1,1),0,b'1: x\n'),(b'x\n',(2,0),0,b''),(b'x\n',(0,1),2,b'invalid range\n'),(b'x\n',(1,-1),2,b'invalid range\n'),(b'x\n',(1,2),2,b'invalid range\n'),(b'a\0b',(1,1),4,b'unsupported control character\n'),(b'\x1b[31m',(1,1),4,b'unsupported control character\n'),(b'x'*4097,(1,1),4,b'line exceeds 4096 bytes\n'),(b'\n'*4097,(1,1),4,b'too many lines\n'),(b'x'*16385,(1,1),3,b'file exceeds 16384 bytes\n16385\n'),(None,(1,1),3,b'missing file\n')]:run('boundary '+str(len(records)),raw,args,code,out)
 result={'status':'PASS','cases':len(records),'records':records,'compiler_sha256':hashlib.sha256((sdk/'bin/kcc').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'qualification':'real native Awl file reader/line index/cross-module view renderer, bounded local CLI, no Python processing in application, not a new workload stage'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'native/sanitized logwindow checks')
if __name__=='__main__':main()

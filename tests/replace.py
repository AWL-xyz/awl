#!/usr/bin/env python3
import argparse,hashlib,json,os,random,resource,shutil,subprocess,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--sanitized',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();kcc=a.kcc.resolve();records=[];env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1','XDG_CACHE_HOME':'/var/tmp/Awl-replace-cache'}
 with tempfile.TemporaryDirectory(prefix='Awl-replace-tests-',dir='/var/tmp') as td:
  work=Path(td);source=work/'main.aw';source.write_text('func main()->i64 print(file_replace(arg_text(0),arg_text(1),arg_text(2))); return 0; end;');executables=[]
  for mode in ['bundled','sanitized','unsupported']:
   exe=work/mode;cmd='build' if mode=='bundled' else 'emit-c';r=subprocess.run([str(kcc),cmd,str(source),'--syntax','next']+(['-o',str(exe)] if mode=='bundled' else []),capture_output=True,text=True,env={**env,'PATH':'/no-host-tools'},timeout=180);assert r.returncode==0,r.stderr
   if mode!='bundled':
    c=work/(mode+'.c');c.write_text(r.stdout);subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',*(['-DK_REPLACE_UNSUPPORTED'] if mode=='unsupported' else []),str(c),'-lm','-o',str(exe)],check=True,timeout=90)
   executables.append(exe)
  serial=0
  def folder():
   nonlocal serial
   serial+=1;f=work/str(serial);f.mkdir();return f
  def api(exe,directory,temp='temp',target='target'):
   r=subprocess.run([str(exe),str(directory),temp,target],capture_output=True,env=env,timeout=10);assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr);return int(r.stdout)
  for exe in executables:
   mode=exe.name
   if mode=='unsupported':
    f=folder();(f/'temp').write_bytes(b'new');(f/'target').write_bytes(b'old');assert api(exe,f)==-6 and (f/'target').read_bytes()==b'old' and (f/'temp').read_bytes()==b'new';records.append([mode,'no mutation']);continue
   for data in [b'',b'hello',bytes(range(256))*1025,'café 日本語'.encode()]:
    f=folder();(f/'temp').write_bytes(data);(f/'target').write_bytes(b'old')
    with (f/'target').open('rb') as old:
     assert api(exe,f)==0 and (f/'target').read_bytes()==data and not (f/'temp').exists() and old.read()==b'old'
    records.append([mode,'replace and old open descriptor '+str(len(data))])
   f=folder();(f/'temp').write_bytes(b'new');assert api(exe,f)==0 and (f/'target').read_bytes()==b'new';records.append([mode,'create absent target'])
   for temp,target in [('', 'target'),('temp',''),('.','target'),('..','target'),('a/b','target'),('temp','a/b'),('temp','temp'),('x'*256,'target'),('temp','x'*256)]:
    f=folder();(f/'temp').write_bytes(b'new');(f/'target').write_bytes(b'old');assert api(exe,f,temp,target)==-5 and (f/'target').read_bytes()==b'old' and (f/'temp').read_bytes()==b'new';records.append([mode,'invalid names '+str(len(temp))+' '+str(len(target))])
   for label in ['missing source','source directory','target directory','source symlink','target symlink','hardlink alias','FIFO','missing directory','directory symlink']:
    f=folder();(f/'old').write_bytes(b'old');(f/'temp').write_bytes(b'new');(f/'target').write_bytes(b'old');directory=f
    if label=='missing source':(f/'temp').unlink()
    if label=='source directory':(f/'temp').unlink();(f/'temp').mkdir()
    if label=='target directory':(f/'target').unlink();(f/'target').mkdir()
    if label=='source symlink':(f/'temp').unlink();(f/'temp').symlink_to('old')
    if label=='target symlink':(f/'target').unlink();(f/'target').symlink_to('old')
    if label=='hardlink alias':(f/'target').unlink();os.link(f/'temp',f/'target')
    if label=='FIFO':(f/'temp').unlink();os.mkfifo(f/'temp')
    if label=='missing directory':directory=f/'absent'
    if label=='directory symlink':directory=f/'alias';directory.symlink_to(f,target_is_directory=True)
    assert api(exe,directory)<0 and (f/'old').read_bytes()==b'old',label;records.append([mode,label])
   f=folder();(f/'é.tmp').write_bytes(b'new');assert api(exe,f,'é.tmp','日本語')==0 and (f/'日本語').read_bytes()==b'new';records.append([mode,'UTF-8 names'])
  for mode,exe in [('bundled',a.native.resolve()),('sanitized',a.sanitized.resolve())]:
   for data in [b'',b'hello',random.Random(429).randbytes(200003)]:
    f=folder();(f/'target').write_bytes(b'old');r=subprocess.run([str(exe),str(f),'temp','target'],input=data,capture_output=True,env=env,timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,b'0\n',b'') and (f/'target').read_bytes()==data and not (f/'temp').exists();records.append([mode,'ksave binary stdin '+str(len(data))])
   for args,code in [([],2),(['x','same','same'],2),(['x','../temp','target'],2),(['x','','target'],2)]:
    r=subprocess.run([str(exe),*args],input=b'data',capture_output=True,env=env);assert r.returncode==code and not r.stderr;records.append([mode,'ksave arguments'])
   f=folder();(f/'temp').write_bytes(b'untouched');(f/'target').write_bytes(b'old');r=subprocess.run([str(exe),str(f),'temp','target'],input=b'new',capture_output=True,env=env);assert r.returncode==3 and (f/'target').read_bytes()==b'old' and (f/'temp').read_bytes()==b'untouched';records.append([mode,'ksave exclusive creation'])
   f=folder();(f/'target').mkdir();r=subprocess.run([str(exe),str(f),'temp','target'],input=b'new',capture_output=True,env=env);assert r.returncode==5 and (f/'target').is_dir() and (f/'temp').read_bytes()==b'new';records.append([mode,'ksave failed publish retains temporary'])
   f=folder();old=b'a'*262144;new=b'b'*262144;(f/'target').write_bytes(old);stop=threading.Event();seen=[];errors=[]
   def reader():
    while not stop.is_set():
     try:
      data=(f/'target').read_bytes()
      if data not in [old,new]:errors.append(('partial',len(data)))
      seen.append(len(data))
     except Exception as e:errors.append(str(e))
   t=threading.Thread(target=reader);t.start()
   try:
    for i in range(12):
     data=new if i%2==0 else old;r=subprocess.run([str(exe),str(f),'temp','target'],input=data,capture_output=True,env=env,timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,b'0\n',b'')
   finally:stop.set();t.join()
   assert seen and not errors,(seen,errors);records.append([mode,'12 replacements with concurrent old-or-new observer'])
  for body in ['file_replace(1,"a","b");','file_replace(".","a");','defer file_replace(".","a","b");']:
   source.write_text('func main()->i64 '+body+' return 0; end;');r=subprocess.run([str(kcc),'check',str(source),'--syntax','next'],capture_output=True);assert r.returncode==1;records.append(['checker','invalid type/arity/defer'])
 report={'status':'PASS','compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'cases':len(records),'records':records,'ksave_sha256':{'bundled':hashlib.sha256(a.native.read_bytes()).hexdigest(),'sanitized':hashlib.sha256(a.sanitized.read_bytes()).hexdigest()},'qualification':'native local filesystem and strict generated-C sanitizers, observer test demonstrates old-or-new visibility during these runs, no hardware power-loss or hostile directory-race qualification'}
 a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(records),'replace cases')
if __name__=='__main__':main()

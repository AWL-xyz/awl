#!/usr/bin/env python3
import argparse,hashlib,json,os,random,resource,shutil,signal,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--sanitize-c',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args();binary=a.kcc.resolve();records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-stream-tests-') as td:
  work=Path(td);env={k:v for k,v in os.environ.items() if not k.startswith('KPIPE_')};env.update(PATH='/no-host-tools',XDG_CACHE_HOME='/tmp/Awl-streams-cache',ASAN_OPTIONS='detect_leaks=1:abort_on_error=1')
  def build(name,body=None,source=None,expected=None):
   src=work/(name+'.aw');src.write_text(source if source is not None else 'func main()->i64 '+body+' return 0; end;')
   exe=work/name
   if expected:
    r=subprocess.run([str(binary),'check',str(src),'--syntax','next'],capture_output=True,text=True,env=env,timeout=30);assert r.returncode==1 and expected in r.stderr,(name,r.returncode,r.stderr);records.append({'case':name,'kind':'compile diagnostic','exit':1});return
   command='emit-c' if a.sanitize_c else 'build';args=[str(binary),command,str(src),'--syntax','next']+([] if a.sanitize_c else ['-o',str(exe)])
   r=subprocess.run(args,capture_output=True,text=True,env=env,timeout=180);assert r.returncode==0,(name,r.stderr)
   if a.sanitize_c:
    c=work/(name+'.c');c.write_text(r.stdout);subprocess.run([shutil.which('cc'),'-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-lm','-o',str(exe)],check=True,timeout=60)
   return exe
  def run(name,exe,data=b'',out=b'',err=b'',code=0,extra=None,trap=False):
   r=subprocess.run([str(exe)],input=data,capture_output=True,env={**env,**(extra or {})},timeout=30)
   if trap:assert r.returncode!=0 and b'resource trap' in r.stderr,(name,r.returncode,r.stderr)
   else:assert (r.returncode,r.stdout,r.stderr)==(code,out,err),(name,r.returncode,r.stdout[:300],r.stderr[:300])
   assert b'AddressSanitizer' not in r.stderr and b'runtime error:' not in r.stderr,(name,r.stderr)
   records.append({'case':name,'kind':'runtime','exit':r.returncode,'input_bytes':len(data),'output_bytes':len(r.stdout)})
  echo=build('echo','@p b: buffer_new(8); @p n: stdin_read(b,2,4); print(n); print(buffer_get(b,2)); print(buffer_get(b,3)); buffer_free(b);')
  run('read offsets and partial input',echo,b'ab',b'2\n97\n98\n')
  eof=build('eof','@p b: buffer_new(1); print(stdin_read(b,0,1)); print(stdin_read(b,0,1)); print(stdin_read(b,1,0)); buffer_free(b);');run('repeated EOF and zero read',eof,out=b'0\n0\n0\n')
  zero=build('zero','@p b: buffer_new(0); print(stdin_read(b,0,0)); print(stdout_write(b,0,0)); print(stderr_write(b,0,0)); print(stdout_flush()); print(stderr_flush()); buffer_free(b);');run('zero buffer operations',zero,out=b'0\n0\n0\n0\n0\n')
  raw=build('raw','@p b: buffer_new(4); buffer_set(b,0,0u8); buffer_set(b,1,255u8); buffer_set(b,2,13u8); buffer_set(b,3,10u8); stdout_write(b,0,4); stderr_write(b,1,2); buffer_free(b);');run('raw binary stdout stderr separation',raw,out=b'\0\xff\r\n',err=b'\xff\r')
  order=build('order','@p b: buffer_new(1); buffer_set(b,0,120u8); print("before"); stdout_write(b,0,1); print("after"); stdout_flush(); buffer_free(b);');run('print and raw write preserve order',order,out=b'before\nxafter\n')
  envsrc='@p b: buffer_new(32); @p n: env_read("Awl_ENV",b,2,30); print(env_size("Awl_ENV")); print(n); if n>=0 then print(buffer_text_valid(b,2,n)); if buffer_text_valid(b,2,n) then print(buffer_text(b,2,n)); end; end; buffer_free(b);'
  environ=build('environment',envsrc)
  for label,value,expected in [('missing',None,b'-2\n-2\n'),('empty','',b'0\n0\ntrue\n\n'),('unicode','caf\u00e9\U0001f642',b'9\n9\ntrue\ncaf\xc3\xa9\xf0\x9f\x99\x82\n'),('raw bytes',b'\xff',b'1\n1\nfalse\n')]:
   clean=dict(env);clean.pop('Awl_ENV',None)
   if value is not None:clean['Awl_ENV']=value
   r=subprocess.run([str(environ)],capture_output=True,env=clean,timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,expected,b''),(label,r.stdout,r.stderr);records.append({'case':'environment '+label,'exit':r.returncode})
  atomic=build('atomic','@p b: buffer_new(4); buffer_set(b,0,77u8); print(env_read("Awl_ENV",b,0,4)); print(buffer_get(b,0)); print(env_read("Awl_ENV",b,4,0)); print(buffer_get(b,0)); buffer_free(b);');run('environment capacity errors do not modify buffer',atomic,out=b'-5\n77\n-5\n77\n',extra={'Awl_ENV':'12345'})
  names=build('names','@p b: buffer_new(1); print(env_size("")); print(env_size("a=b")); print(env_size("a\\0b")); print(env_read("",b,0,1)); print(env_size("'+('x'*4096)+'")); buffer_free(b);');run('invalid environment names',names,out=b'-5\n-5\n-5\n-5\n-5\n')
  exact=build('exact','@p b: buffer_new(3); print(env_read("Awl_ENV",b,0,3)); print(buffer_text(b,0,3)); buffer_free(b);');run('environment exact fit',exact,out=b'3\nabc\n',extra={'Awl_ENV':'abc'})
  utf=build('key','print(env_size("Awl_\u00e9")); print(env_size("Awl_\u00e9"));');run('unicode keys and case sensitivity',utf,out=b'2\n-2\n',extra={'Awl_\u00e9':'ok'})
  for name,call in [('stdin-negative','stdin_read(b,-1,1)'),('stdout-overflow','stdout_write(b,0,2)'),('stderr-negative-count','stderr_write(b,0,-1)'),('env-invalid-range','env_read("missing",b,2,0)')]:
   exe=build(name,'@p b: buffer_new(1); '+call+'; buffer_free(b);');run(name,exe,trap=True)
  bad=build('bad-handle','stdin_read(999,0,0);');run('zero count still validates handle',bad,trap=True)
  stale=build('stale','@p b: buffer_new(1); buffer_free(b); stdout_write(b,0,0);');run('stale buffer rejected',stale,trap=True)
  for name,body,error in [('arity','stdin_read(1,2);','argument'),('type','stdout_write("bad",0,1);','i64'),('env-type','env_size(1);','string'),('flush-arity','stdout_flush(1);','argument')]:build(name,body,expected=error)
  build('global-effect',source='@p n: env_size("x"); func main()->i64 return 0; end;',expected='initializer')
  app=build('kpipe',source=(ROOT/'examples/apps/kpipe/main.aw').read_text())
  data=random.Random(20261106).randbytes(200003)+b'\0\xff\r\nhello WORLD\n'
  for mode in ['copy','upper','lower']:
   expected=data if mode=='copy' else data.upper() if mode=='upper' else data.lower()
   run('kpipe binary oracle '+mode,app,data,expected,extra={'KPIPE_MODE':mode})
  run('kpipe default copy',app,data,data)
  run('kpipe empty input report',app,err=b'bytes processed: 0\n',extra={'KPIPE_REPORT':'1'})
  run('kpipe report goes only to stderr',app,b'a\0b',b'A\0B',b'bytes processed: 3\n',extra={'KPIPE_MODE':'upper','KPIPE_REPORT':'1'})
  for label,extra in [('unknown mode',{'KPIPE_MODE':'unicode'}),('empty mode',{'KPIPE_MODE':''}),('oversized mode',{'KPIPE_MODE':'x'*17}),('invalid utf8 mode',{'KPIPE_MODE':b'\xff'}),('oversized report',{'KPIPE_REPORT':'11'}),('invalid report',{'KPIPE_REPORT':'0'})]:
   r=subprocess.run([str(app)],input=b'kept out of stdout',capture_output=True,env={**env,**extra},timeout=10);assert r.returncode==2 and r.stdout==b'' and b'kpipe:' in r.stderr,(label,r.returncode,r.stdout,r.stderr);records.append({'case':'kpipe '+label,'exit':2})
  large=bytes(range(256))*4096;run('kpipe one MiB byte-exact bounded streaming',app,large,large)
  report={'status':'PASS','cases':len(records),'records':records,'compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'mode':'generated C ASan/UBSan' if a.sanitize_c else 'real bundled Linux backend; no host tools on PATH','windows_tested':False}
  a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
if __name__=='__main__':main()

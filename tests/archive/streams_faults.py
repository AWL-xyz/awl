#!/usr/bin/env python3
import argparse,hashlib,json,os,resource,shutil,signal,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);a=p.parse_args();binary=a.kcc.resolve();records=[]
 original=(ROOT/'compiler/native/streams.c').read_text()
 env={k:v for k,v in os.environ.items() if not k.startswith('KPIPE_')};env['ASAN_OPTIONS']='detect_leaks=1:abort_on_error=1'
 def emitted(source):
  r=subprocess.run([str(binary),'emit-c',str(source),'--syntax','next'],capture_output=True,text=True,check=True);assert original in r.stdout;return r.stdout
 app=emitted(ROOT/'examples/apps/pipe/main.aw')
 prefix='''#include <sys/auxv.h>
static unsigned fault_reads,fault_writes;
static ssize_t fault_read(int fd,void *p,size_t n){READ}
static ssize_t fault_write(int fd,const void *p,size_t n){WRITE}
static int fault_flush(FILE *f){FLUSH}
static unsigned long fault_auxval(unsigned long type){AUX}
static char *fault_getenv(const char *key){ENV}
#define read fault_read
#define write fault_write
#define fflush fault_flush
#define getauxval fault_auxval
#define getenv fault_getenv
'''
 normal={'READ':'return read(fd,p,n>3?3:n);','WRITE':'return write(fd,p,n>7?7:n);','FLUSH':'return fflush(f);','AUX':'return getauxval(type);','ENV':'return getenv(key);'}
 modes={
 'short-counts':({},0,b''),
 'EINTR-before-transfer':({'READ':'if(fault_reads++<2){errno=EINTR;return -1;}return read(fd,p,n>3?3:n);','WRITE':'if(fd==1&&fault_writes++<2){errno=EINTR;return -1;}return write(fd,p,n>7?7:n);'},0,b''),
 'zero-write':({'WRITE':'if(fd==1)return 0;return write(fd,p,n);'},4,b'pipe: stdout write failed\n'),
 'read-EIO':({'READ':'(void)fd;(void)p;(void)n;errno=EIO;return -1;'},3,b'pipe: stdin read failed\n'),
 'read-EAGAIN':({'READ':'(void)fd;(void)p;(void)n;errno=EAGAIN;return -1;'},3,b'pipe: stdin read failed\n'),
 'write-EAGAIN':({'WRITE':'if(fd==1){errno=EAGAIN;return -1;}return write(fd,p,n);'},4,b'pipe: stdout write failed\n'),
 'write-ENOSPC':({'WRITE':'if(fd==1){errno=ENOSPC;return -1;}return write(fd,p,n);'},4,b'pipe: stdout write failed\n'),
 'flush-ENOSPC':({'FLUSH':'if(f==stdout){errno=ENOSPC;return EOF;}return fflush(f);'},4,b'pipe: stdout write failed\n'),
 'secure-execution-refuses-environment':({'AUX':'if(type==AT_SECURE)return 1;return getauxval(type);'},2,b'pipe: cannot read mode configuration\n'),
 'oversized-environment':({'ENV':'if(strcmp(key,"KPIPE_MODE")==0){static char v[1048578];memset(v,120,sizeof(v)-1);return v;}return getenv(key);'},2,b'pipe: cannot read mode configuration\n')}
 with tempfile.TemporaryDirectory(prefix='Awl-stream-faults-') as td:
  work=Path(td)
  def compile(name,code):
   c=work/(name+'.c');exe=work/name;c.write_text(code);subprocess.run([shutil.which('cc'),'-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-lm','-o',str(exe)],check=True,timeout=60);return exe
  data=bytes(range(256))*4
  for name,(changes,code,err) in modes.items():
   wrapper=prefix
   for k,v in {**normal,**changes}.items():wrapper=wrapper.replace(k,v)
   altered=app.replace(original,wrapper+original+'\n#undef read\n#undef write\n#undef fflush\n#undef getauxval\n#undef getenv\n')
   exe=compile(name,altered);r=subprocess.run([str(exe)],input=data,capture_output=True,env=env,timeout=20)
   assert (r.returncode,r.stdout,r.stderr)==(code,data if code==0 else b'',err),(name,r.returncode,r.stdout[:100],r.stderr)
   records.append({'case':name,'exit':r.returncode,'method':'syscall/libc fault injection into actual emitted runtime; ASan/UBSan'})
  src=work/'probe.aw';src.write_text('func main()->i64 @p b:buffer.new(1); print(stdin.read(b,0,1)); buffer.free(b); return 0; end;')
  probe=compile('probe',emitted(src))
  r=subprocess.run([str(probe)],capture_output=True,env=env,preexec_fn=lambda:os.close(0),timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,b'-1\n',b''),(r.returncode,r.stdout,r.stderr);records.append({'case':'genuine closed stdin','exit':0})
  reader,writer=os.pipe();os.set_blocking(reader,False)
  try:
   r=subprocess.run([str(probe)],stdin=reader,capture_output=True,env=env,timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,b'-10\n',b''),(r.returncode,r.stdout,r.stderr);records.append({'case':'genuine nonblocking empty pipe returns would-block','exit':0})
  finally:os.close(reader);os.close(writer)
  src.write_text('func main()->i64 @p b:buffer.new(1); buffer.set(b,0,120u8); @p n:stdout.write(b,0,1); buffer.free(b); if n == -11 then return 0; end; return 9; end;')
  pipeprobe=compile('pipe-probe',emitted(src))
  for ignored in [False,True]:
   reader,writer=os.pipe();os.close(reader)
   try:r=subprocess.run([str(pipeprobe)],stdout=writer,stderr=subprocess.PIPE,env=env,timeout=10,preexec_fn=(lambda:signal.signal(signal.SIGPIPE,signal.SIG_IGN)) if ignored else None)
   finally:os.close(writer)
   assert r.returncode==(0 if ignored else -signal.SIGPIPE) and r.stderr==b'',(ignored,r.returncode,r.stderr)
   records.append({'case':'genuine broken pipe, '+('inherited ignored SIGPIPE returns -11' if ignored else 'default SIGPIPE preserved'),'exit':r.returncode})
 report={'status':'PASS','sanitized':True,'cases':len(records),'records':records,'compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'runtime_sha256':hashlib.sha256(original.encode()).hexdigest(),'scope':'injected short/EINTR/error paths and genuine Linux descriptor/pipe behavior, not disk-failure or Windows proof'}
 (ROOT/'tests/streams-faults.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

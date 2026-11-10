"""Inject short/error syscalls only into emitted file runtime, execute real kcopy.
Linux contributor instrumentation, not a host dependency or disk-failure proof."""
import hashlib,json,os,random,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 kcc=ROOT/'build/Awl-linux-x86_64/bin/kcc';r=subprocess.run([str(kcc),'emit-c',str(ROOT/'examples/apps/kcopy/main.aw')],capture_output=True,text=True,check=True);original=(ROOT/'compiler/native/files.c').read_text();assert original in r.stdout
 prefix='''static int fault_closes;
static ssize_t fault_read(int fd,void *p,size_t n){READ}
static ssize_t fault_write(int fd,const void *p,size_t n){WRITE}
static int fault_flush(int fd){FLUSH}
static int fault_close(int fd){CLOSE}
#define read fault_read
#define write fault_write
#define fsync fault_flush
#define close fault_close
'''
 normal={'READ':'return read(fd,p,n>3?3:n);','WRITE':'return write(fd,p,n>7?7:n);','FLUSH':'return fsync(fd);','CLOSE':'++fault_closes;return close(fd);'}
 modes={'short':{},'zero-write':{'WRITE':'(void)fd;(void)p;(void)n;return 0;'},'read-error':{'READ':'(void)fd;(void)p;(void)n;errno=EIO;return -1;'},'flush-error':{'FLUSH':'(void)fd;errno=ENOSPC;return -1;'},'close-error':{'CLOSE':'int r=close(fd);if(++fault_closes==1){errno=EIO;return -1;}return r;'}};records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-copy-faults-') as td:
  work=Path(td);src=work/'source';data=random.Random(22).randbytes(31003);src.write_bytes(data)
  for mode,changes in modes.items():
   wrapper=prefix
   for key,value in {**normal,**changes}.items():wrapper=wrapper.replace(key,value)
   code=r.stdout.replace(original,wrapper+original+'\n#undef read\n#undef write\n#undef fsync\n#undef close\n');c=work/(mode+'.c');c.write_text(code);exe=work/mode;dest=work/(mode+'.bin')
   subprocess.run([shutil.which('cc'),'-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-o',str(exe)],check=True,timeout=60)
   out=subprocess.run([str(exe),str(src),str(dest)],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'},timeout=30);assert out.returncode==(0 if mode=='short' else 5),(mode,out.returncode,out.stdout,out.stderr);assert out.stderr=='',out.stderr;assert src.read_bytes()==data
   if mode in ['short','flush-error','close-error']:assert dest.read_bytes()==data
   else:assert dest.read_bytes()==b''
   records.append({'mode':mode,'exit':out.returncode,'stdout':out.stdout,'destination_bytes':dest.stat().st_size})
 report={'status':'passed','scope':__doc__,'sanitized':True,'source_sha256':hashlib.sha256(data).hexdigest(),'records':records};(ROOT/'tests/files-copy-faults.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

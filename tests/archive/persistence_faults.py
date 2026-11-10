"""Contributor syscall fault injection around actual Awl drawing storage.
Not real disk-failure/race proof. Product codec and commit logic remain Awl.
"""
import json,os,shutil,subprocess,tempfile,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 kcc=ROOT/'build/Awl-linux-x86_64/bin/kcc';runtime=(ROOT/'compiler/native/files.c').read_text();records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-persistence-fault-',dir=ROOT/'build') as td:
  work=Path(td);shutil.copy2(ROOT/'examples/apps/pixelboard/storage.aw',work/'storage.aw');main=work/'main.aw';main.write_text('import storage function main()->i64 scoped cells:int_vector=intvector.new(384) local i:i64=0 while i<384 do intvector.push(cells,i*1234567%16777216) i=i+1 end print(storage.save_new(cells,arg.text(0))) i=0 while i<384 do intvector.set(cells,i,7) i=i+1 end local loaded:i64=storage.load(cells,arg.text(0)) print(loaded) local same:bool=true i=0 while i<384 do local expected:i64=7 if loaded==0 then expected=i*1234567%16777216 end if intvector.get(cells,i)!=expected then same=false end i=i+1 end print(same) return 0 end')
  emitted=subprocess.check_output([str(kcc),'emit-c',str(main)],text=True);assert runtime in emitted
  normal={'READ':'return read(fd,p,n>3?3:n);','WRITE':'return write(fd,p,n>7?7:n);','FLUSH':'return fsync(fd);','CLOSE':'++closes;return close(fd);'}
  variants={'short':({},'0\n0\ntrue\n'),'zero-write':({'WRITE':'(void)fd;(void)p;(void)n;return 0;'},'-1\n-5\ntrue\n'),'write-error':({'WRITE':'(void)fd;(void)p;(void)n;errno=ENOSPC;return -1;'},'-8\n-5\ntrue\n'),'read-error':({'READ':'(void)fd;(void)p;(void)n;errno=EIO;return -1;'},'0\n-1\ntrue\n'),'flush-error':({'FLUSH':'(void)fd;errno=EIO;return -1;'},'-1\n0\ntrue\n'),'close-error':({'CLOSE':'int r=close(fd);if(++closes==1){errno=EIO;return -1;}return r;'},'-1\n0\ntrue\n'),'early-eof':({'READ':'if(total_read>=500)return 0;ssize_t r=read(fd,p,n>3?3:n);if(r>0)total_read+=r;return r;'},'0\n-5\ntrue\n'),'extra-byte':({'READ':'ssize_t r=read(fd,p,n>3?3:n);if(!r && !extra){extra=1;((unsigned char*)p)[0]=0;return 1;}return r;'},'0\n-5\ntrue\n')}
  template='''static int closes,extra;static ssize_t total_read;
static ssize_t test_read(int fd,void *p,size_t n){READ}
static ssize_t test_write(int fd,const void *p,size_t n){WRITE}
static int test_flush(int fd){FLUSH}
static int test_close(int fd){CLOSE}
#define read test_read
#define write test_write
#define fsync test_flush
#define close test_close
'''
  expected=b'KPBOARD1'+b''.join((i*1234567%16777216).to_bytes(3,'big') for i in range(384));expected+=zlib.adler32(expected).to_bytes(4,'big')
  for name,(changes,out) in variants.items():
   prefix=template
   for key,value in {**normal,**changes}.items():prefix=prefix.replace(key,value)
   c=work/(name+'.c');c.write_text(emitted.replace(runtime,prefix+runtime+'\n#undef read\n#undef write\n#undef fsync\n#undef close\n'));exe=work/name;path=work/(name+'.kpb');subprocess.run([shutil.which('cc'),'-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-o',str(exe)],check=True,timeout=60)
   r=subprocess.run([str(exe),str(path)],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'},timeout=30);assert (r.returncode,r.stdout,r.stderr)==(0,out,''),(name,r.returncode,r.stdout,r.stderr)
   if name not in ['zero-write','write-error']:assert path.read_bytes()==expected
   records.append({'mode':name,'exit':r.returncode,'stdout':r.stdout,'destination_bytes':path.stat().st_size})
 report={'status':'passed','scope':__doc__,'sanitized':True,'records':records};(ROOT/'tests/persistence-faults.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

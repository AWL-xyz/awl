"""Windows file/UTF-8 application gate. Wine requires separate contributor cross-link;
only native Windows mode uses the installed compiler backend. No silent skips."""
import argparse,hashlib,json,os,random,subprocess,tempfile,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def literal(s):return '"'+''.join('\\u{'+format(ord(c),'x')+'}' for c in s)+'"'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--compiler',type=Path);p.add_argument('--examples',type=Path,default=ROOT/'examples');p.add_argument('--wine');p.add_argument('--report',type=Path,default=ROOT/'tests/files-windows.json');a=p.parse_args();records=[];env={**os.environ,'WINEDEBUG':'-all'}
 def win(path):return 'Z:'+str(Path(path).resolve()).replace('/','\\') if a.wine else str(Path(path).resolve())
 def run(exe,args,code=0):
  r=subprocess.run(([a.wine] if a.wine else [])+[win(exe),*args],env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
  records.append({'argv':[win(exe),*args],'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==code,records[-1];return r.stdout
 with tempfile.TemporaryDirectory(prefix='Awl-files-') as td:
  work=Path(td)
  def build(label,source=None,example=None):
   folder=work/label;folder.mkdir()
   if example:
    import shutil
    shutil.copytree(a.examples/'apps'/example,folder,dirs_exist_ok=True)
   if source is not None:(folder/'main.aw').write_text(source,encoding='utf-8')
   src=folder/'main.aw';exe=folder/'app.exe'
   if a.wine:
    assert a.compiler,'Wine gate requires --compiler Linux contributor Zig'
    r=subprocess.run([a.wine,win(a.frontend),'emit-c',win(src)],env=env,capture_output=True,text=True,encoding='utf-8',timeout=120);assert r.returncode==0,r.stderr
    c=folder/'app.c';c.write_text(r.stdout,encoding='utf-8');records.append({'frontend':label,'exit':r.returncode,'emitted_c_sha256':hashlib.sha256(r.stdout.encode()).hexdigest()})
    subprocess.run([str(a.compiler),'cc','-target','x86_64-windows-gnu','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',str(c),'-luser32','-lgdi32','-lshell32','-o',str(exe)],check=True,timeout=180)
   else:run(a.frontend,['build',str(src),'-o',str(exe)])
   return exe
  ignored=build('ignored','function side()->i64 print(7) return 3 end function main()->i64 scoped v:int_vector=int_vector_new(1) int_vector_push(v,9) side() print(int_vector_get(v,0)) return 0 end');assert run(ignored,[])=='7\n9\n'
  argv=build('argv','function main()->i64 print(arg_count()) local i:i64=0 while i<arg_count() do print(arg_text_valid(i)) print(arg_text(i)) print(string_length(arg_text(i))) i=i+1 end return 0 end')
  values=['','space here','café🙂','"quote"','back\\slash\\','零'];assert run(argv,values)==str(len(values))+'\n'+''.join('true\n'+s+'\n'+str(len(s))+'\n' for s in values)
  path=work/'data café🙂.bin';q=literal(win(path));path.write_bytes(b'old')
  io=build('io','function main()->i64 print(file_open('+q+',1)) local f:i64=file_open('+q+',2) print(file_size(f)) local b:i64=buffer_new(6) defer buffer_free(b) print(buffer_write_text(b,0,"é🙂")) print(file_write(f,b,0,6)) print(file_flush(f)) print(file_close(f)) print(file_valid(f)) f=file_open('+q+',0) defer file_close(f) print(file_size(f)) print(file_seek(f,2)) print(file_read(f,b,0,6)) print(file_read(f,b,0,1)) print(buffer_text_valid(b,0,4)) print(buffer_text(b,0,4)) print(file_open("x:y:z",0)) return 0 end')
  assert run(io,[])=='-3\n0\n6\n6\n0\n0\nfalse\n6\n0\n4\n0\ntrue\n🙂\n-5\n';assert path.read_bytes()=='é🙂'.encode()
  slots=build('slots','function main()->i64 scoped ids:int_vector=int_vector_new(32) local i:i64=0 while i<32 do local f:i64=file_open('+q+',0) if f<0 then return 3 end if not int_vector_push(ids,f) then return 4 end i=i+1 end print(file_open('+q+',0)) while int_vector_length(ids)>0 do if file_close(int_vector_pop(ids))!=0 then return 5 end end print("released") return 0 end');assert run(slots,[])=='-7\nreleased\n'
  copy=build('copy',example='kcopy');dest=work/'copy 世界.bin';data=random.Random(22).randbytes(200003);path.write_bytes(data);assert run(copy,[win(path),win(dest)])=='bytes copied\n200003\n';assert dest.read_bytes()==data;run(copy,[win(path),win(dest)],4);assert dest.read_bytes()==data
  info=build('info',example='textinfo');path.write_bytes('café🙂\0'.encode());assert run(info,[win(path)])=='bytes\n10\nUnicode scalars\n6\n';path.write_bytes(b'\xed\xa0\x80');assert run(info,[win(path)],5)=='invalid UTF-8\n';path.write_bytes(b'');assert run(info,[win(path)])=='bytes\n0\nUnicode scalars\n0\n'
  painting=work/'painting 世界.kpb';qp=literal(win(painting))
  persistence=build('persistence',example='pixelboard',source='import storage function main()->i64 print(platform_kind()) scoped cells:int_vector=int_vector_new(384) local i:i64=0 while i<384 do int_vector_push(cells,i*1234567%16777216) i=i+1 end if arg_count()>0 then print(storage.load(cells,'+qp+')) local same:bool=true i=0 while i<384 do if int_vector_get(cells,i)!=i*1234567%16777216 then same=false end i=i+1 end print(same) return 0 end print(storage.save_new(cells,'+qp+')) print(storage.save_new(cells,'+qp+')) int_vector_set(cells,0,42) print(storage.load(cells,'+qp+')) print(int_vector_get(cells,0)) print(int_vector_get(cells,383)) return 0 end')
  assert run(persistence,[])=='2\n0\n-3\n0\n0\n'+str(383*1234567%16777216)+'\n'
  expected=b'KPBOARD1'+b''.join((i*1234567%16777216).to_bytes(3,'big') for i in range(384));expected+=zlib.adler32(expected).to_bytes(4,'big');assert painting.read_bytes()==expected
  damaged=bytearray(expected);damaged[99]^=1;painting.write_bytes(damaged);assert run(persistence,['invalid'])=='2\n-5\ntrue\n'
  trap=build('trap','function main()->i64 local f:i64=file_open('+q+',0) if file_close(f)!=0 then return 2 end print(file_size(f)) return 0 end');r=subprocess.run(([a.wine] if a.wine else [])+[win(trap)],env={**env,'WINEDLLOVERRIDES':'winedbg.exe=d'},capture_output=True,text=True,encoding='utf-8',timeout=60);assert r.returncode!=0 and 'Awl resource trap' in r.stderr,(r.returncode,r.stdout,r.stderr);records.append({'probe':'stale handle trap','exit':r.returncode,'stderr':r.stderr})
 report={'status':'passed','execution':'Windows PE under Wine, not native Windows' if a.wine else 'native Windows','installed_Windows_backend_used':not bool(a.wine),'skips':0,'frontend_sha256':hashlib.sha256(a.frontend.read_bytes()).hexdigest(),'records':records};a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
if __name__=='__main__':main()

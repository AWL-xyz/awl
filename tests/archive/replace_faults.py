#!/usr/bin/env python3
import argparse,hashlib,json,os,resource,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='func main()->i64\n if arg.count()==0 then\n  print(file.replace("", "a", "b"));\n  print(file.replace(".", "a" + string.fromcodepoint(0u32), "b"));\n  print(file.replace("." + string.fromcodepoint(0u32), "a", "b"));\n  return 0;\n end;\n if arg.count()==1 then\n  @p i: 0;\n  while i<200 do\n   if file.replace(arg.text(0),"temp","target")!=0 then return 3; end;\n   if file.replace(arg.text(0),"target","temp")!=0 then return 3; end;\n   i: i+1;\n  end;\n  print(0); return 0;\n end;\n print(file.replace(arg.text(0),arg.text(1),arg.text(2)));\n return 0;\nend;\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'};records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-replace-faults-',dir='/var/tmp') as td:
  root=Path(td);src=root/'main.aw';src.write_text(SOURCE);executables={}
  for name,source in [('probe',src),('save',ROOT/'examples/apps/save/main.aw')]:
   r=subprocess.run([str(a.kcc.resolve()),'emit-c',str(source),'--syntax','next'],capture_output=True,text=True,check=True);c=root/(name+'.c');c.write_text(r.stdout);exe=root/name
   subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),str(ROOT/'tests/replace_faults.c'),'-Wl,--wrap=fsync,--wrap=close,--wrap=renameat','-lm','-o',str(exe)],check=True);executables[name]=exe
  for mode,status in [('file-sync',-1),('file-close',-1),('rename',-4),('dir-sync',1),('dir-close',1),('eintr',0)]:
   for name,exe in executables.items():
    folder=root/(mode+'-'+name);folder.mkdir();(folder/'target').write_bytes(b'old')
    if name=='probe':(folder/'temp').write_bytes(b'new')
    r=subprocess.run([str(exe),str(folder),'temp','target'],input=b'new',capture_output=True,env={**env,'REPLACE_FAULT':mode},timeout=10)
    actual=status
    code=0
    if name=='save':
     if mode=='file-close':actual=-1;code=4
     elif status<0:code=5
     elif status==1:code=6
    assert (r.returncode,r.stdout,r.stderr)==(code,str(actual).encode()+b'\n',b''),(mode,name,r.returncode,r.stdout,r.stderr)
    committed=status>=0
    assert (folder/'target').read_bytes()==(b'new' if committed else b'old') and (folder/'temp').exists()!=committed
    if not committed:assert (folder/'temp').read_bytes()==b'new'
    records.append(name+' '+mode+' publication/status/temporary checks')
  folder=root/'reuse';folder.mkdir();(folder/'temp').write_bytes(b'hello')
  def limit():resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
  r=subprocess.run([str(executables['probe']),str(folder)],capture_output=True,env=env,preexec_fn=limit,timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,b'0\n',b'') and (folder/'temp').read_bytes()==b'hello' and not (folder/'target').exists();records.append('400 replacements under32fd ceiling, no descriptor exhaustion')
  r=subprocess.run([str(executables['probe'])],capture_output=True,env=env,timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,b'-5\n'*3,b'');records.append('empty and embedded-NUL paths reject before syscalls')
 result={'status':'PASS','cases':len(records),'records':records,'compiler_sha256':hashlib.sha256(a.kcc.read_bytes()).hexdigest(),'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['tests/replace_faults.py','tests/replace_faults.c','compiler/native/files.c','examples/apps/save/main.aw']},'qualification':'strict generated-C ASan/UBSan with syscall wrappers, not hardware power-loss, NFS or hostile directory races'}
 a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'fault/reuse cases')
if __name__=='__main__':main()

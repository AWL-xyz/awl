"""Isolated Win32 driver tests using an explicitly fake backend, NOT backend acceptance."""
import argparse,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HELPER=r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>
#include <fstream>
#include <filesystem>
int wmain(int argc,wchar_t **argv){
 if(argc==3&&std::wstring(argv[1])==L"--child"){HANDLE f=CreateFileW(argv[2],GENERIC_WRITE,0,nullptr,CREATE_ALWAYS,0,nullptr);if(f==INVALID_HANDLE_VALUE)return 90;Sleep(INFINITE);return 0;}
 wchar_t buffer[32768];DWORD n=GetModuleFileNameW(nullptr,buffer,32768);if(!n||n>=32768)return 91;
 std::filesystem::path home=std::filesystem::path(buffer).parent_path();std::ifstream config(home/L"fixture-mode.txt");std::string mode;config>>mode;
 wchar_t path[1024];if(!GetEnvironmentVariableW(L"PATH",path,1024)||std::wstring(path)!=L"C:\\no-host-tools")return 92;
 if(mode=="timeout"){Sleep(INFINITE);return 0;}if(mode=="failure")return 7;
 if(mode=="invalid"){std::ofstream f(std::filesystem::path(argv[argc-1]),std::ios::binary);f<<"MZnot-an-executable";return 0;}
 if(mode=="spawn"){
  auto marker=home/L"held.marker";std::wstring command=L"\""+std::wstring(buffer)+L"\" --child \""+marker.wstring()+L"\"";STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
  if(!CreateProcessW(buffer,command.data(),nullptr,nullptr,FALSE,0,nullptr,nullptr,&si,&pi))return 93;
  CloseHandle(pi.hThread);CloseHandle(pi.hProcess);int i=0;while(GetFileAttributesW(marker.c_str())==INVALID_FILE_ATTRIBUTES&&i++<500)Sleep(10);if(i>=500)return 94;
 }
 return CopyFileW((home/L"payload.exe").c_str(),argv[argc-1],FALSE)?0:95;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--wine');p.add_argument('--compiler',type=Path,required=True);p.add_argument('--report',type=Path,default=ROOT/'tests/windows-driver-fixtures.json');a=p.parse_args();env={**os.environ,'WINEDEBUG':'-all'};records=[]
 def win(path):return 'Z:'+str(Path(path).resolve()).replace('/','\\') if a.wine else str(Path(path).resolve())
 def execute(args,code,stdout=None,contains=None):
  r=subprocess.run(([a.wine] if a.wine else [])+list(map(str,args)),env=env,capture_output=True,text=True,timeout=30)
  assert r.returncode==code,(args,r.returncode,r.stdout,r.stderr)
  if stdout is not None:assert r.stdout==stdout,r.stdout
  if contains:assert contains in r.stderr,r.stderr
  records.append({'argv':list(map(str,args)),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});return r
 with tempfile.TemporaryDirectory(prefix='Awl Win32 driver é ') as td:
  work=Path(td);bundle=work/'installation with spaces é';backend=bundle/'libexec/zig';(backend/'lib').mkdir(parents=True);(bundle/'bin').mkdir();shutil.copy2(a.bundle/'bin/kcc.exe',bundle/'bin/kcc.exe');kcc=win(bundle/'bin/kcc.exe');compiler=str(a.compiler.resolve())
  helper=work/'helper.cpp';helper.write_text(HELPER);cfile=work/'payload.c';cfile.write_text('#include <stdio.h>\nint main(void){puts("42");return 0;}')
  subprocess.run([compiler,'c++','-target','x86_64-windows-gnu','-std=c++20','-O2','-municode',str(helper),'-o',str(backend/'zig.exe')],check=True,timeout=180)
  subprocess.run([compiler,'cc','-target','x86_64-windows-gnu','-O2',str(cfile),'-o',str(backend/'payload.exe')],check=True,timeout=180)
  source=work/'input é.aw';source.write_text('function main()->i64 print(42) return 0 end');dest=work/'output é.exe';mode=backend/'fixture-mode.txt'
  mode.write_text('copy');execute([kcc,'build',win(source),'-o',win(dest)],0);assert dest.read_bytes()==(backend/'payload.exe').read_bytes()
  execute([kcc,'run',win(source)],0,stdout='42\n')
  before=dest.read_bytes()
  for label,error in [('failure','bundled backend failed'),('invalid','not a supported x86-64 PE')]:
   mode.write_text(label);execute([kcc,'build',win(source),'-o',win(dest)],2,contains=error);assert dest.read_bytes()==before
  # Independent malformed-PE outputs must never replace the old executable.
  payload=backend/'payload.exe';valid=payload.read_bytes();pe=int.from_bytes(valid[60:64],'little');section=pe+24+int.from_bytes(valid[pe+20:pe+22],'little')
  mutations=[(0,b'NO'),(60,(0xffffffff).to_bytes(4,'little')),(pe,b'NOPE'),(pe+4,(0x14c).to_bytes(2,'little')),(pe+22,(0x2002).to_bytes(2,'little')),(pe+24,(0x10b).to_bytes(2,'little')),(pe+6,(0).to_bytes(2,'little')),(pe+6,(97).to_bytes(2,'little')),(pe+20,(239).to_bytes(2,'little')),(pe+40,(0).to_bytes(4,'little')),(section+16,(0xffffffff).to_bytes(4,'little'))]
  mode.write_text('copy')
  for at,replacement in mutations:
   malformed=bytearray(valid);malformed[at:at+len(replacement)]=replacement;payload.write_bytes(malformed)
   execute([kcc,'build',win(source),'-o',win(dest)],2,contains='not a supported x86-64 PE');assert dest.read_bytes()==before
  payload.write_bytes(valid)
  mode.write_text('timeout');execute([kcc,'build',win(source),'-o',win(dest),'--build-timeout','1'],124,contains='wall-time limit');assert dest.read_bytes()==before
  mode.write_text('spawn');execute([kcc,'build',win(source),'-o',win(dest)],0);(backend/'held.marker').unlink();assert dest.read_bytes()==before
  execute([kcc,'build',win(source),'-o',win(source)],2,contains='refusing to overwrite source')
  link=work/'source hardlink.exe';os.link(source,link);execute([kcc,'build',win(source),'-o',win(link)],2,contains='refusing to overwrite source');link.unlink()
  imported=work/'helper.aw';imported.write_text('function value()->i64 return 42 end');source.write_text('import helper as h function main()->i64 print(h.value()) return 0 end')
  execute([kcc,'build',win(source),'-o',win(imported)],2,contains='refusing to overwrite source');assert imported.read_text()=='function value()->i64 return 42 end'
  assert not list(work.glob('.Awl-output-*')),'staged artifacts leaked'
  (backend/'zig.exe').unlink();execute([kcc,'run',win(source)],2,contains='bundled toolchain missing')
 out={'status':'passed','execution':'Wine emulation' if a.wine else 'native Windows','backend':'FAKE contributor fixture; does not prove actual installed Zig compilation','commands':records,'command_count':len(records),'skips':0,'covered':['spaces and non-ASCII installation/source/output paths','explicit backend path and restricted PATH','stdout forwarding','PE validation + 11 targeted output corruptions','preserve old output on failure/timeout','one-second backend timeout','job descendant termination/file-handle release','source/import/hardlink overwrite protection','temporary output cleanup','missing backend diagnosis']}
 a.report.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='commands'},indent=2))
if __name__=='__main__':main()

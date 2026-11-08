"""Actual Windows USER32/GDI window and Awl Pixelboard tests.
Native Windows: installed kcc build. Wine: Windows frontend emits C; separate Linux
contributor Zig cross-compiles. This never claims a Windows-host backend pass.
"""
import argparse,json,os,subprocess,tempfile,time,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--resume-from',type=Path);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--compiler',type=Path,required=True);p.add_argument('--wine');p.add_argument('--report',type=Path,default=ROOT/'tests/win32-gui.json');p.add_argument('--capture',type=Path,default=ROOT/'demos/win32/pixelboard.bmp');a=p.parse_args();bundle=a.bundle.resolve();compiler=a.compiler.resolve();env={**os.environ,'WINEDEBUG':'-all'};records=[]
 def win(path):return 'Z:'+str(Path(path).resolve()).replace('/','\\') if a.wine else str(Path(path).resolve())
 def invoke(args,timeout=180):
  start=time.monotonic();r=subprocess.run(([a.wine] if a.wine else [])+list(map(str,args)),env=env,capture_output=True,text=True,timeout=timeout)
  records.append({'argv':list(map(str,args)),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':round(time.monotonic()-start,3)});assert r.returncode==0,records[-1];return r
 def compile(source,exe,unicode=False):
  subprocess.run([str(compiler),'cc','-target','x86_64-windows-gnu','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',*(['-municode'] if unicode else []),str(source),'-luser32','-lgdi32','-lshell32','-o',str(exe)],check=True,timeout=180)
 a.capture.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='Awl-gui-') as td:
  work=Path(td);c=work/'runtime-test.c';c.write_text((ROOT/'tests/win32_runtime_test.c').read_text().replace('../compiler/native/kplatform.c',(bundle/'src/kplatform.c').as_posix()).replace('../compiler/native/kstrings.c',(bundle/'src/kstrings.c').as_posix()));runtime=work/'runtime.exe';compile(c,runtime);r=invoke([win(runtime)]);assert len([s for s in r.stdout.splitlines() if s.startswith('PASS ')])==17,r.stdout
  probe=work/'probe.exe';compile(ROOT/'tests/win32_gui_probe.c',probe,True);app=work/'pixelboard.exe';kcc=win(bundle/'bin/kcc.exe');main=win(bundle/'examples/apps/pixelboard/main.aw')
  if a.wine:
   emitted=invoke([kcc,'emit-c',main]);source=work/'pixelboard.c';source.write_text(emitted.stdout)
   # Generated runtime has many unused static intrinsics by design; same flags as driver.
   subprocess.run([str(compiler),'cc','-target','x86_64-windows-gnu','-std=c11','-O2',str(source),'-luser32','-lgdi32','-lshell32','-o',str(app)],check=True,timeout=180)
  else:invoke([kcc,'build',main,'-o',win(app)])
  snapshot=work/'drawing é.kpb'
  process=subprocess.Popen(([a.wine] if a.wine else [])+[win(app),win(snapshot)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   r=invoke([win(probe),win(a.capture),win(snapshot)],timeout=90);out,err=process.communicate(timeout=15);assert process.returncode==0 and out=='',(process.returncode,out,err)
   payload=snapshot.read_bytes();assert len(payload)==1164 and payload[:8]==b'KPBOARD1' and zlib.adler32(payload[:-4])==int.from_bytes(payload[-4:],'big')
   records.append({'application_exit':process.returncode,'stdout':out,'stderr':err});assert a.capture.is_file() and a.capture.stat().st_size>1000
  finally:
   if process.poll() is None:process.kill();process.communicate()
  resumed=work/'resumed.kpb';input_path=a.resume_from.resolve() if a.resume_from else snapshot
  process=subprocess.Popen(([a.wine] if a.wine else [])+[win(app),win(resumed),win(input_path)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   r=invoke([win(probe),win(a.capture),win(resumed),'resume'],timeout=90);out,err=process.communicate(timeout=15);assert process.returncode==0 and out=='',(process.returncode,out,err)
   assert resumed.read_bytes()==input_path.read_bytes();records.append({'restart_exit':process.returncode,'bytes_identical':True,'external_interop_fixture':str(a.resume_from) if a.resume_from else None})
  finally:
   if process.poll() is None:process.kill();process.communicate()
 out={'status':'passed','execution':'Windows PE under Wine' if a.wine else 'native Windows','installed_Windows_backend_used':not bool(a.wine),'runtime_test_groups':17,'actual_Awl_application_probe_checks':9,'input':'programmatic Win32 messages, not physical input devices','capture':str(a.capture),'records':records,'skips':0}
 a.report.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='records'},indent=2))
if __name__=='__main__':main()

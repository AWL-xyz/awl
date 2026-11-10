"""Installed Windows bundle gate. Native Windows by default; --wine is qualified emulation.
--frontend-only never claims installed backend acceptance. --cross-runtime compiles
emitted C using a separate Linux contributor Zig, NOT the Windows installed driver.
"""
import argparse,json,os,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--expected-version',default='0.23.0-dev');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--wine');p.add_argument('--frontend-only',action='store_true');p.add_argument('--cross-runtime',type=Path);p.add_argument('--report',type=Path,default=ROOT/'tests/windows-bundle-smoke.json');a=p.parse_args()
 bundle=a.bundle.resolve();kcc=bundle/'bin/kcc.exe';records=[]
 env={**os.environ,'WINEDEBUG':'-all'}
 if not a.wine:env['PATH']=r'C:\no-host-tools'
 def win(path):return 'Z:'+str(Path(path).resolve()).replace('/','\\') if a.wine else str(Path(path).resolve())
 def invoke(argv,code=0,stdout=None,contains=None):
  start=time.monotonic();r=subprocess.run(([a.wine] if a.wine else [])+list(map(str,argv)),env=env,capture_output=True,text=True,timeout=240)
  assert r.returncode==code,(argv,r.returncode,r.stdout,r.stderr)
  if stdout is not None:assert r.stdout==stdout,(argv,r.stdout,stdout)
  if contains:assert contains in r.stderr,(argv,r.stderr,contains)
  records.append({'argv':list(map(str,argv)),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':round(time.monotonic()-start,3)});return r
 version=invoke([win(kcc),'--version']);assert a.expected_version in version.stdout
 outputs=json.loads((ROOT/'tests/example-outputs.json').read_text())
 with tempfile.TemporaryDirectory(prefix='Awl windows space é ') as td:
  work=Path(td);source=work/'input é.aw';source.write_text('function main()->i64 print(42) return 0 end')
  invoke([win(kcc),'check',win(source)])
  invoke([win(kcc),'emit-c',win(source)])
  for f in sorted((bundle/'examples').glob('*.aw')):
   invoke([win(kcc),'check',win(f)]);c=invoke([win(kcc),'emit-c',win(f)])
   if a.cross_runtime:
    cfile=work/'program.c';exe=work/'program.exe';cfile.write_text(c.stdout)
    subprocess.run([str(a.cross_runtime.resolve()),'cc','-std=c11','-target','x86_64-windows-gnu','-O2',str(cfile),'-o',str(exe)],check=True,timeout=180)
    invoke([win(exe)],stdout=outputs[f.name])
   elif not a.frontend_only:invoke([win(kcc),'run',win(f)],stdout=outputs[f.name])
  app=bundle/'examples/apps/intstats/main.aw';tool=work/'intstats é.exe'
  if a.cross_runtime:
   c=invoke([win(kcc),'emit-c',win(app)]);cfile=work/'stats.c';cfile.write_text(c.stdout)
   subprocess.run([str(a.cross_runtime.resolve()),'cc','-std=c11','-target','x86_64-windows-gnu','-O2',str(cfile),'-o',str(tool)],check=True,timeout=180)
  elif not a.frontend_only:invoke([win(kcc),'build',win(app),'-o',win(tool)])
  if not a.frontend_only or a.cross_runtime:
   data=[42,-7,19,0,42,-9223372036854775808,9223372036854775807]
   expected='count\n7\nminimum\n'+str(min(data))+'\nmaximum\n'+str(max(data))+'\nsorted\n'+''.join(str(n)+'\n' for n in sorted(data))
   invoke([win(tool),*map(str,data)],stdout=expected)
   invoke([win(tool),'9223372036854775808'],code=2,stdout='invalid signed 64-bit integer argument\n')
   invoke([win(tool)],code=2,stdout='usage: intstats INTEGER [INTEGER ...]\n')
  if not a.frontend_only:
   invoke([win(kcc),'run',win(source)],stdout='42\n')
   invoke([win(kcc),'build',win(source),'-o',win(source)],code=2,contains='refusing to overwrite source')
   assert source.read_text()=='function main()->i64 print(42) return 0 end'
   source.write_text('function main()->i64 while true do end return 0 end')
   invoke([win(kcc),'run',win(source),'--run-timeout','1'],code=124,contains='wall-time limit')
   # Relocation including spaces/non-ASCII: installation location, not cwd/PATH.
   import shutil
   relocated=work/'relocated Awl é';shutil.copytree(bundle,relocated)
   invoke([win(relocated/'bin/kcc.exe'),'run',win(bundle/'examples/hello.aw')],stdout=outputs['hello.aw'])
   (relocated/'libexec/zig/zig.exe').unlink()
   invoke([win(relocated/'bin/kcc.exe'),'run',win(bundle/'examples/hello.aw')],code=2,contains='bundled toolchain missing')
 out={'status':'passed','execution':'Wine emulation' if a.wine else 'native Windows','frontend_only':a.frontend_only,'runtime_cross_compiled_by_separate_contributor_tool':bool(a.cross_runtime),'installed_backend_acceptance':not a.frontend_only,'commands':records,'command_count':len(records),'skips':0}
 a.report.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='commands'},indent=2))
if __name__=='__main__':main()

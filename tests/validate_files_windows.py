"""Exact 0.22 Windows preview subset gates under Wine. Never host acceptance."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 bundle=ROOT/'build/files-windows-exact/Awl';archive=ROOT/'build/Awl-0.22.0-dev-windows-x86_64-preview.tar.xz';zig=ROOT/'build/Awl-linux-x86_64/libexec/zig/zig';wine='/usr/lib/wine/wine64';env={**os.environ,'DISPLAY':':92','WINEPREFIX':str(ROOT/'build/wine/prefix'),'WINEDEBUG':'-all'};results={}
 jobs=[('integrity',['tests/windows_preview_integrity.py','--archive',str(archive),'--bundle',str(bundle),'--report','tests/files-windows-exact-integrity.json']),('frontend-runtime',['tests/windows_bundle_smoke.py','--bundle',str(bundle),'--wine',wine,'--frontend-only','--cross-runtime',str(zig),'--report','tests/files-windows-exact-frontend-runtime.json']),('files',['tests/files_windows.py','--frontend',str(bundle/'bin/kcc.exe'),'--examples',str(bundle/'examples'),'--compiler',str(zig),'--wine',wine,'--report','tests/files-windows-exact-files.json']),('driver-fixtures',['tests/windows_driver_fixtures.py','--bundle',str(bundle),'--compiler',str(zig),'--wine',wine,'--report','tests/files-windows-exact-driver-fixtures.json']),('gui',['tests/win32_gui.py','--bundle',str(bundle),'--compiler',str(zig),'--wine',wine,'--report','tests/files-windows-exact-gui.json','--capture','build/files-windows-pixelboard.bmp'])]
 for name,args in jobs:
  start=time.monotonic()
  with (ROOT/'tests'/('files-windows-exact-'+name+'.txt')).open('w') as f:r=subprocess.run([sys.executable,*args],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=480)
  results[name]={'exit':r.returncode,'seconds':round(time.monotonic()-start,3)};print(name,results[name],flush=True);assert not r.returncode,name
 def win(p):return 'Z:'+str(p).replace('/','\\')
 r=subprocess.run([wine,win(bundle/'bin/kcc.exe'),'run',win(bundle/'examples/hello.aw')],env=env,capture_output=True,text=True,timeout=180)
 results['installed-backend-probe']={'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'acceptance':False,'scope':'Wine probe, NOT native Windows host'};assert r.returncode==2 and 'unable to find zig self exe path' in r.stderr,results['installed-backend-probe']
 (ROOT/'tests/files-windows-exact-validation.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()

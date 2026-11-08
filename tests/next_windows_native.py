"""Windows PE compiler-internal gates under Wine, NOT native Windows-host acceptance."""
import hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];native=ROOT/'compiler/native';build=ROOT/'build/next-windows';build.mkdir(exist_ok=True,parents=True);zig=ROOT/'build/Awl-linux-x86_64/libexec/zig/zig';records=[]
for label,sources in [('next',['klex.cpp','knext_test.cpp']),('project',['klex.cpp','kproject_test.cpp'])]:
 start=time.monotonic();exe=build/(label+'.exe');subprocess.run([str(zig),'c++','-std=c++20','-target','x86_64-windows-gnu','-O1','-Wall','-Wextra','-Werror',*[str(native/s) for s in sources],'-o',str(exe)],check=True,timeout=300)
 env={**os.environ,'WINEPREFIX':str(ROOT/'build/next-wine'),'WINEDEBUG':'-all'};r=subprocess.run(['/usr/lib/wine/wine64','Z:'+str(exe).replace('/','\\')],env=env,capture_output=True,text=True,timeout=180);record={'phase':label,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':round(time.monotonic()-start,3),'pe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()};records.append(record);print(label,r.returncode,r.stdout,r.stderr,flush=True);assert r.returncode==0,record
(ROOT/'tests/next-production-windows-internals.json').write_text(json.dumps({'status':'passed','scope':__doc__,'native_Windows_host_accepted':False,'installed_Windows_backend_accepted':False,'records':records},indent=2)+'\n')

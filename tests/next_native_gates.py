"""Native sanitizer gates for candidate frontend and private verifier; contributor only."""
import hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];native=ROOT/'compiler/native';build=ROOT/'build/next-tests';build.mkdir(exist_ok=True,parents=True);records=[]
for label,sources in [('lexer',['klex.cpp','klex_test.cpp']),('frontend',['klex.cpp','kparse.cpp','kparse_test.cpp']),('verifier',['klex.cpp','kverify_test.cpp']),('project',['klex.cpp','kproject_test.cpp']),('next',['klex.cpp','kaesop_test.cpp'])]:
 start=time.monotonic();exe=build/(label+'-sanitized');command=['g++','-std=c++20','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',*[str(native/f) for f in sources],'-o',str(exe)];subprocess.run(command,check=True,timeout=240)
 argv=[str(exe)]+([str(p) for p in sorted((ROOT/'examples').glob('*.aw'))] if label=='frontend' else [])
 r=subprocess.run(argv,capture_output=True,text=True,timeout=180);record={'phase':label,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':round(time.monotonic()-start,3),'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()};records.append(record);print(label,r.returncode,r.stdout,r.stderr,flush=True);assert r.returncode==0,record
report={'status':'passed','scope':__doc__,'phases':records,'native_sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(native.iterdir()) if p.suffix in ['.h','.cpp','.inc']}};(ROOT/'tests/next-production-native-sanitized.json').write_text(json.dumps(report,indent=2)+'\n')

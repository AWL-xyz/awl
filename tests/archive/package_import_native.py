#!/usr/bin/env python3
import gzip,hashlib,json,subprocess,tempfile,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];native=ROOT/'compiler/native';records=[]
snapshot=lambda:{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(native.iterdir()) if p.suffix in ['.h','.cpp','.inc','.c']}
before=snapshot()
with tempfile.TemporaryDirectory(prefix='Awl-net-native-',dir='/var/tmp') as td:
 phases=[('lexer',['lex.cpp','lex_test.cpp']),('frontend',['lex.cpp','parse.cpp','parse_test.cpp']),('verifier',['lex.cpp','verify_test.cpp']),('project',['lex.cpp','project_test.cpp']),('next',['lex.cpp','aesop_test.cpp']),('module-numeric',['lex.cpp','module_numeric_test.cpp']),('streams',['lex.cpp','streams_test.cpp']),('typed-vectors',['lex.cpp','generic_test.cpp']),('tcp',['lex.cpp','tcp_test.cpp']),('replace',['lex.cpp','replace_test.cpp']),('enums',['lex.cpp','enum_test.cpp']),('views',['lex.cpp','view_test.cpp']),('process',['lex.cpp','process_test.cpp']),('clean-syntax',['lex.cpp','clean_test.cpp']),('exported-enums',['lex.cpp','export_test.cpp'])]
 def run(phase):
  label,sources=phase
  start=time.monotonic();exe=Path(td)/label
  subprocess.run(['g++','-std=c++20','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',*[str(native/f) for f in sources],'-o',str(exe)],check=True,timeout=240)
  argv=[str(exe)]+([str(p) for p in sorted((ROOT/'examples').glob('*.aw'))] if label=='frontend' else [])
  r=subprocess.run(argv,capture_output=True,text=True,timeout=180);record={'phase':label,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':round(time.monotonic()-start,3),'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()};print(label,r.returncode,r.stdout,r.stderr,flush=True);assert r.returncode==0,record;return record
 with ThreadPoolExecutor(max_workers=1) as pool:records=list(pool.map(run,phases))
assert snapshot()==before,'native source changed during qualification'
report={'status':'PASS','workers':1,'phases':records,'native_sources_sha256':before}
(ROOT/'tests/package-import-native.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))

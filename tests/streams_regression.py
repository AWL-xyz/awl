import argparse,concurrent.futures,hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1];results={}
p=argparse.ArgumentParser();p.add_argument('--python',default=sys.executable);args=p.parse_args()
def run(job):
 name,cmd,extra=job;start=time.monotonic();log=root/'tests'/('streams-'+name+'.txt')
 with log.open('w') as f:r=subprocess.run(cmd,cwd=root,env={**os.environ,**extra,'Awl_PLATFORM_TEST_CACHE':'/var/tmp/Awl-streams-shared-cache'},stdout=f,stderr=subprocess.STDOUT)
 text=log.read_text();return name,{'exit':r.returncode,'seconds':round(time.monotonic()-start,3),'skips':(' ... skipped ' in text or 'skipped=' in text),'log':str(log.relative_to(root)),'compiler_sha256':hashlib.sha256((root/'compiler/native/bin/kcc').read_bytes()).hexdigest()}
jobs=[('legacy-reference',[args.python,'-m','unittest','discover','-s','tests','-v'],{}),('legacy-native-parser',[args.python,'-m','unittest','discover','-s','tests','-v'],{'KCC_LEXER':'native','KCC_PARSER':'native'}),('legacy-native-frontend',[args.python,'tests/native_frontend_suite.py'],{})]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=dict(pool.map(run,jobs))
(root/'tests/streams-legacy-regression.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2));raise SystemExit(any(r['exit'] or r['skips'] for r in results.values()))

"""Development regression only: experimental next frontend, not release acceptance."""
import concurrent.futures,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(job):
 name,command,extra=job;start=time.monotonic();log=ROOT/'tests'/('module-numeric-'+name+'.txt')
 with log.open('w') as f:r=subprocess.run(command,cwd=ROOT,env={**os.environ,**extra},stdout=f,stderr=subprocess.STDOUT)
 text=log.read_text();return name,{'exit':r.returncode or int('skipped=' in text or ' ... skipped ' in text),'seconds':round(time.monotonic()-start,3),'log':str(log.relative_to(ROOT)),'compiler_sha256':hashlib.sha256((ROOT/'compiler/native/bin/kcc').read_bytes()).hexdigest(),'library_sha256':hashlib.sha256((ROOT/'compiler/native/bin/Awllex.so').read_bytes()).hexdigest()}
if __name__=='__main__':
 jobs=[('legacy-reference',[sys.executable,'-m','unittest','discover','-s','tests','-v'],{}),('legacy-native-parser',[sys.executable,'-m','unittest','discover','-s','tests','-v'],{'KCC_LEXER':'native','KCC_PARSER':'native'}),('legacy-native-frontend',[sys.executable,'tests/native_frontend_suite.py'],{}),('sanitized-c',[sys.executable,'tests/next_production.py','--sanitize-c','--report','tests/module-numeric-existing-sanitized-c.json'],{})]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=dict(pool.map(run,jobs))
 (ROOT/'tests/module-numeric-development-validation.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2),flush=True);sys.exit(any(r['exit'] for r in results.values()))

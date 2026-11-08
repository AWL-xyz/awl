"""0.23 contributor Linux gates; never archive/native-Windows acceptance."""
import concurrent.futures,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(job):
 name,command,extra=job;start=time.monotonic()
 with (ROOT/'tests'/('persistence-'+name+'.txt')).open('w') as f:r=subprocess.run(command,cwd=ROOT,env={**os.environ,**extra},stdout=f,stderr=subprocess.STDOUT)
 text=(ROOT/'tests'/('persistence-'+name+'.txt')).read_text();return name,{'exit':r.returncode or int('skipped=' in text or ' ... skipped ' in text),'seconds':round(time.monotonic()-start,3)}
if __name__=='__main__':
 jobs=[('reference-suite',[sys.executable,'-m','unittest','discover','-s','tests','-v'],{}),('native-parser-suite',[sys.executable,'-m','unittest','discover','-s','tests','-v'],{'KCC_LEXER':'native','KCC_PARSER':'native'}),('native-frontend-suite',[sys.executable,'tests/native_frontend_suite.py'],{}),('files-sanitized',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_files.py','-v'],{'Awl_BUILDER_SANITIZE':'1'}),('storage-sanitized',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_persistence.py','-v'],{'Awl_BUILDER_SANITIZE':'1'})]
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=dict(pool.map(run,jobs))
 (ROOT/'tests/persistence-development-validation.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2),flush=True);sys.exit(any(r['exit'] for r in results.values()))

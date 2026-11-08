"""Local development gates; not archive acceptance or benchmark evidence."""
import concurrent.futures,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(name,command,env):
 start=time.monotonic()
 with (ROOT/'tests'/('loop-owners-'+name+'.txt')).open('w') as f:r=subprocess.run(command,cwd=ROOT,env={**os.environ,**env},stdout=f,stderr=subprocess.STDOUT)
 return name,{'exit':r.returncode,'seconds':round(time.monotonic()-start,3)}
if __name__=='__main__':
 jobs=[('reference-suite',[sys.executable,'-m','unittest','discover','-s','tests','-v'],{}),('native-parser-suite',[sys.executable,'-m','unittest','discover','-s','tests','-v'],{'KCC_LEXER':'native','KCC_PARSER':'native'}),('native-frontend-suite',[sys.executable,'tests/native_frontend_suite.py'],{}),('focused-sanitized',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_loop_owners.py','-v'],{'Awl_BUILDER_SANITIZE':'1'})]
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=dict(pool.map(lambda j:run(*j),jobs))
 (ROOT/'tests/loop-owners-development-validation.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2),flush=True)
 sys.exit(any(r['exit'] for r in results.values()))

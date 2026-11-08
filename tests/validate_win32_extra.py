"""Additional local release gates, run after staging the product compiler."""
import concurrent.futures,json,os,subprocess,sys
from validate_win32 import run,ROOT
if __name__=='__main__':
 mods=['modules','strings','builders','cleanup','arrays','repeat','scoped_owner','borrows','moves','own_params','owned_results','branch_joins','match_joins','reinit','loop_owners','vectors']
 jobs=[('resources-sanitized',[sys.executable,'-m','unittest','-v',*['test_'+m for m in mods]],{'PYTHONPATH':str(ROOT/'tests'),'Awl_BUILDER_SANITIZE':'1'}),('platform-sanitized',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_platform.py','-v'],{'Awl_PLATFORM_SANITIZE':'1'}),('driver-sanitized',[sys.executable,'compiler/test_bundle_driver.py','--sanitize'],{}),('integer-runtime',[sys.executable,'tests/sanitizer_matrix.py','--frontend','native'],{})]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=dict(pool.map(lambda j:run(*j),jobs))
 (ROOT/'tests/win32-extra-validation.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2));sys.exit(any(r['exit'] for r in results.values()))

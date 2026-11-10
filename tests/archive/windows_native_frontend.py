"""Cross-build native frontend/private mutation tests for Windows and execute in Wine.
This gate exercises compiler internals, NOT installed backend acceptance or real Windows.
"""
import argparse,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];native=ROOT/'compiler/native';build=ROOT/'build/windows-native-tests';build.mkdir(exist_ok=True)
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',action='append',choices=['lexer','frontend','verifier','project']);p.add_argument('--compile-timeout',type=int,default=300);a=p.parse_args()
if a.compile_timeout<1:p.error('--compile-timeout must be positive')
zig=ROOT/'build/Awl-linux-x86_64/libexec/zig/zig';wine='/usr/lib/wine/wine64';records=[]
for label,sources in [('lexer',['lex.cpp','lex_test.cpp']),('frontend',['lex.cpp','parse.cpp','parse_test.cpp']),('verifier',['lex.cpp','verify_test.cpp']),('project',['lex.cpp','project_test.cpp'])]:
 if a.phase and label not in a.phase:continue
 exe=build/(label+'.exe');subprocess.run([str(zig),'c++','-std=c++20','-target','x86_64-windows-gnu','-O1','-Wall','-Wextra','-Werror',*[str(native/n) for n in sources],'-o',str(exe)],check=True,timeout=a.compile_timeout)
 argv=[wine,'Z:'+str(exe).replace('/','\\')]
 if label=='frontend':argv+=['Z:'+str(p).replace('/','\\') for p in sorted((ROOT/'examples').glob('*.aw'))]
 r=subprocess.run(argv,env={**os.environ,'WINEDEBUG':'-all'},capture_output=True,text=True,timeout=180)
 records.append({'phase':label,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});print(label,r.returncode,r.stdout,r.stderr,flush=True)
 assert r.returncode==0,records[-1]
(ROOT/'tests/windows-native-frontend.json').write_text(json.dumps({'status':'passed','execution':'Windows PE under Wine10, not real Windows','phases':records},indent=2)+'\n')

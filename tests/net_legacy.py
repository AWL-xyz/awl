#!/usr/bin/env python3
import argparse,lzma,hashlib,json,os,re,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--python',default=sys.executable);a=p.parse_args();binary=a.kcc.resolve();link=ROOT/'build/Awl-linux-x86_64';link.parent.mkdir(exist_ok=True);assert not link.exists();link.symlink_to(binary.parents[1],target_is_directory=True)
records={};logs={};env={**os.environ,'Awl_PLATFORM_TEST_CACHE':'/var/tmp/Awl-net-legacy-cache','PYTHONDONTWRITEBYTECODE':'1'}
for file in (ROOT/'tests').glob('test_*.py'):
 for key in re.findall(r'Awl_[A-Z_]+_TEST_BINARY',file.read_text()):env[key]=str(binary)
try:
 with tempfile.TemporaryDirectory(prefix='Awl-net-legacy-',dir='/var/tmp') as td:
  for name,args,extra in [('reference',['-m','unittest','discover','-s','tests','-v'],{}),('native-parser',['-m','unittest','discover','-s','tests','-v'],{'KCC_LEXER':'native','KCC_PARSER':'native'}),('native-frontend',['tests/native_frontend_suite.py'],{})]:
   start=time.monotonic();log=Path(td)/(name+'.txt')
   with log.open('w') as f:r=subprocess.run([a.python,*args],cwd=ROOT,env={**env,**extra},stdout=f,stderr=subprocess.STDOUT)
   text=log.read_text();logs[name]=text;(ROOT/'tests/net-legacy-logs.json.xz').write_bytes(lzma.compress(json.dumps(logs,separators=(',',':')).encode()))
   record={'exit':r.returncode,'seconds':round(time.monotonic()-start,3),'tests':int(re.search(r'Ran (\d+) tests',text).group(1)) if re.search(r'Ran (\d+) tests',text) else 0,'skips':(' ... skipped ' in text or 'skipped=' in text),'compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()};records[name]=record;print(name,record,flush=True);assert r.returncode==0 and not record['skips'] and record['tests']==564,text[-3000:]
 (ROOT/'tests/net-legacy.json').write_text(json.dumps(records,separators=(',',':'))+'\n')
finally:link.unlink()

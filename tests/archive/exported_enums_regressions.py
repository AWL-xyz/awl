#!/usr/bin/env python3
import argparse,gzip,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);a=p.parse_args();records=[]
for label,script,extra in [('network','network.py',[]),('network-sanitized','network.py',['--sanitize-c']),('json','json_parser.py',[]),('jget','jget.py',[]),('graphics','graphics.py',[]),('next','next_production.py',[]),('next-sanitized','next_production.py',['--sanitize-c']),('module-numeric','module_numeric.py',[]),('module-numeric-sanitized','module_numeric.py',['--sanitize-c']),('ASDK','ASDK_beta.py',[])]:
 report=Path('/var/tmp/Awl-enum-'+label+'.json');r=subprocess.run([sys.executable,str(ROOT/'tests'/script),('--awl' if script=='ASDK_beta.py' else '--kcc'),str(a.kcc.absolute().parent/'awl' if script=='ASDK_beta.py' else a.kcc.resolve()),'--report',str(report),*extra],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);print(label,r.returncode,r.stdout,r.stderr,flush=True);assert r.returncode==0,(label,r.stderr);records.append({'name':label,'report':json.loads(report.read_text())});report.unlink()
result={'status':'PASS','compiler_sha256':hashlib.sha256(a.kcc.read_bytes()).hexdigest(),'records':records}
(ROOT/'tests/exported-enums-regressions.json.gz').write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0))

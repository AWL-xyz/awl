"""Development regression only: structural checker coverage over every examples-next source, imports auto-loaded."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();binary=a.binary.resolve()
 sources=sorted((ROOT/'examples-next').rglob('*.aw'));records=[]
 for source in sources:
  r=subprocess.run([str(binary),str(source)],capture_output=True,text=True,timeout=20,cwd=ROOT)
  assert r.returncode==0,(source.relative_to(ROOT),r.stderr)
  assert 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr,(source,r.stderr)
  records.append({'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'exit':0})
 a.report.write_text(json.dumps({'status':'passed','scope':__doc__,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'checker_source_sha256':hashlib.sha256((ROOT/'compiler/next/syntax.cpp').read_bytes()).hexdigest(),'sources':len(records),'records':records},indent=2)+'\n')
 print('PASS',len(records),'example sources checked')
if __name__=='__main__':main()

#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'PATH':str(sdk/'bin'),'XDG_CACHE_HOME':'/var/tmp/Awl-rename-cache'};records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-rename-',dir='/var/tmp') as td:
  root=Path(td)
  for alias in ['awl','awL','aWl','aWL','Awl','AwL','AWl','AWL']:
   work=root/alias;work.mkdir();r=subprocess.run([alias,'--HeLp'],cwd=work,env=env,capture_output=True,text=True);assert r.returncode==0 and 'Awl Software Development Kit' in r.stdout and '.awproj' in r.stdout;records.append([alias,'help'])
   r=subprocess.run([alias,'InIt','Demo'],cwd=work,env=env,capture_output=True,text=True);assert r.returncode==0 and (work/'Demo.awproj').is_file() and (work/'main.aw').is_file(),r.stderr;records.append([alias,'init'])
   (work/'Lib.aw').write_text('exports(@r func answer()->i64 return 42; end;);')
   (work/'main.aw').write_text('use Lib.aw; func main()->i64 print(Lib.answer()); return 0; end;')
   r=subprocess.run([alias,'BuIlD'],cwd=work,env=env,capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr;r=subprocess.run([str(work/'build/Demo')],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,b'42\n',b'');records.append([alias,'multi-file build'])
   r=subprocess.run([alias,'BuIlD','main.aw','-o','single'],cwd=work,env=env,capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr;r=subprocess.run([str(work/'single')],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,b'42\n',b'');records.append([alias,'single-file build'])
   r=subprocess.run([alias,'--VeRsIoN'],cwd=work,env=env,capture_output=True,text=True);assert r.returncode==0 and 'Awl Software Development Kit' in r.stdout;records.append([alias,'version'])
  r=subprocess.run(['awl','build','Demo'],cwd=root,env=env,capture_output=True,text=True);assert r.returncode==2 and 'ambiguous' in r.stderr;records.append(['discovery','ambiguous child manifests'])
  r=subprocess.run(['awl','build','demo'],cwd=root,env=env,capture_output=True,text=True);assert r.returncode==2 and 'no immediate child' in r.stderr;records.append(['discovery','case-sensitive names'])
  work=root/'awl';(work/'main.aw').write_text('use lib.aw as lib; func main()->i64 print(lib.answer()); return 0; end;');r=subprocess.run(['awl','build'],cwd=work,env=env,capture_output=True,text=True);assert r.returncode==1 and ('case' in r.stderr or 'file' in r.stderr);records.append(['imports','case-sensitive path'])
  old=work/'build/Demo';before=old.read_bytes();(work/'main.aw').write_text('bad source');r=subprocess.run(['AwL','BUILD'],cwd=work,env=env,capture_output=True,text=True);assert r.returncode==1 and old.read_bytes()==before;records.append(['errors','prior executable preserved'])
  before=(work/'Demo.awproj').read_bytes();r=subprocess.run(['AWL','INIT','Demo'],cwd=work,env=env,capture_output=True,text=True);assert r.returncode==2 and (work/'Demo.awproj').read_bytes()==before;records.append(['errors','manifest never overwritten'])
 result={'status':'PASS','compiler_sha256':hashlib.sha256((sdk/'bin/kcc').read_bytes()).hexdigest(),'cases':len(records),'records':records,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'qualification':'Linux complete SDK, PATH excludes host compiler/Python, all eight command spellings and mixed-case verbs, project/import identity remains case-sensitive'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'Awl rename/command/project cases')
if __name__=='__main__':main()

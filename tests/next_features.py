"""Development gate, exact example outputs in native and ASan/UBSan builds, not a general ownership proof."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES={
 'structs':['struct equality ok','4','3','dock','12','18','dock v2','false','dock v3','dock v2','amber','6','5','4','3','6','36','7','structs done'],
 'loops':['15','1','2','3','0','1','2','5','0','10','20','alpha','beta','2','alpha','skip','15','1','2','4','buzz','4','loops done'],
 'containers':['true','2','3','false','true','false','1','nine','2','owl','3','7','9','8','64','true','false','true','2','true','true','1','alpha','0','false','5','4','18','containers done'],
 'resource-structs':['65','2','2','label dock','7'],
}
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();acc=(a.sdk/'bin/acc').resolve();records=[];env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/awl-import-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'}
 with tempfile.TemporaryDirectory(prefix='Awl-next-features-',dir='/var/tmp')as td:
  for name,expected in CASES.items():
   source=ROOT/'examples-next'/name;work=Path(td)/name;shutil.copytree(source,work);c=work/'main.c';r=subprocess.run([str(acc),'emit-c','main.aw'],cwd=work,capture_output=True);assert r.returncode==0,r.stderr;c.write_bytes(r.stdout)
   for mode in ['native','sanitized']:
    exe=work/(name+'-'+mode)
    cmd=[str(acc),'build','main.aw','-o',str(exe)]if mode=='native'else['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)]
    build=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=180);assert build.returncode==0,(name,mode,build.stderr)
    run=subprocess.run([str(exe)],cwd=work,env=env,capture_output=True,text=True,timeout=60);assert run.returncode==0 and not run.stderr,(name,mode,run.returncode,run.stderr);assert run.stdout.splitlines()==expected,(name,mode,run.stdout,expected)
    records.append({'example':name,'mode':mode,'sources_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted(source.glob('*.aw'))},'stdout_lines':len(expected),'exit':0})
 a.report.write_text(json.dumps({'status':'PASS','scope':__doc__,'compiler_sha256':hashlib.sha256(acc.read_bytes()).hexdigest(),'cases':records},separators=(',',':'))+'\n');print('PASS',len(records),'native/sanitized feature cases')
if __name__=='__main__':main()

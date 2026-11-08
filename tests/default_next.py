#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();kcc=sdk/'bin/kcc';awl=sdk/'bin/awl';env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-default-cache'};records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-default-tests-',dir='/var/tmp') as td:
  td=Path(td);next=td/'next.aw';legacy=td/'legacy.aw';next.write_text('func main: i64 { print(42); return 0; };');legacy.write_text('function main()->i64 print(42) return 0 end')
  def run(label,args,code=0,out=None,cwd=td):
   r=subprocess.run([str(x) for x in args],capture_output=True,env=env,cwd=cwd,timeout=180);assert r.returncode==code,(label,r.returncode,r.stdout,r.stderr)
   if out is not None:assert r.stdout==out,(label,r.stdout,r.stderr)
   records.append(label);return r
  for command in ['check','emit-ast','emit-checked-ast','emit-c','build','run']:
   suffix=['-o',td/'app'] if command=='build' else []
   r=run('default next '+command,[kcc,command,next,*suffix],out=b'42\n' if command=='run' else None)
   run('legacy needs opt-in '+command,[kcc,command,legacy,*suffix],1)
   run('explicit legacy '+command,[kcc,command,legacy,*suffix,'--syntax','legacy'],out=b'42\n' if command=='run' else None)
   run('explicit next '+command,[kcc,command,next,*suffix,'--syntax','next'],out=b'42\n' if command=='run' else None)
  x=run('default C',[kcc,'emit-c',next]).stdout;y=run('explicit next C',[kcc,'emit-c',next,'--syntax','next']).stdout;assert x==y;records.append('default and explicit next C are byte-identical')
  run('next not silently parsed as legacy',[kcc,'check',next,'--syntax','legacy'],1)
  run('unknown dialect',[kcc,'check',next,'--syntax','auto'],2);run('missing dialect',[kcc,'check',next,'--syntax'],2)
  invalid=run('default JSON diagnostic',[kcc,'check',legacy,'--diagnostic-format','json'],1);assert json.loads(invalid.stderr)['diagnostics'];records.append('JSON diagnostics structured')
  output=td/'preserve';output.write_bytes(b'previous output');run('wrong dialect preserves output',[kcc,'build',legacy,'-o',output],1);assert output.read_bytes()==b'previous output';records.append('preserved output bytes')
  for alias in ['awl','awL','aWl','aWL','Awl','AwL','AWl','AWL']:
   run(alias+' next default',[sdk/'bin'/alias,'BuIlD',next,'-o',td/'public']);run(alias+' next executable',[td/'public'],out=b'42\n')
  run('public explicit legacy',[awl,'build',legacy,'--syntax','legacy','-o',td/'public']);run('public legacy executable',[td/'public'],out=b'42\n')
  project=td/'project';project.mkdir();run('init defaults next',[awl,'init','Default'],cwd=project);assert 'syntax: next' in (project/'Default.awproj').read_text();run('implicit manifest build',[awl,'build'],cwd=project);run('initialized next executable',[project/'build/Default'])
  old=td/'old';old.mkdir();(old/'Old.awproj').write_text('format: 1\nentry: main.aw\nsyntax: legacy\n');(old/'main.aw').write_bytes(legacy.read_bytes());run('explicit legacy manifest',[awl,'build'],cwd=old);run('legacy manifest executable',[old/'build/Old'],out=b'42\n')
  for name in ['next','legacy']:
   run(name+' manifest override rejects opposite syntax',[awl,'build','--syntax',name],1,cwd=old if name=='next' else project)
  entry=ROOT/'examples-next/exported-enums/main.aw';run('exported results default check',[kcc,'check',entry]);run('exported results default build',[kcc,'build',entry,'-o',td/'configcheck']);settings=td/'settings.json';settings.write_text('{"host":"localhost","port":8080,"debug":true}');run('real typed configuration workload',[td/'configcheck',settings],out=b'localhost\n8080\ntrue\n')
 result={'status':'PASS','cases':len(records),'records':records,'compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'qualification':'actual native CLI and complete bundled backend with PATH excluding host tools, next default and explicit legacy, no syntax autodetection, native Windows not tested'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'default syntax cases')
if __name__=='__main__':main()

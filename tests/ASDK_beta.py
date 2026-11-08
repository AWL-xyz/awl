#!/usr/bin/env python3
"""ASDK front-door and real bundled-backend tests. Linux focus, no Windows acceptance."""
import argparse, hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--awl',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--metadata-only',action='store_true');a=p.parse_args();binary=a.awl.absolute();records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-ASDK-tests-') as tmp:
  base=Path(tmp);env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/tmp/Awl-ASDK-cache'}
  def case(label,args=(),cwd=None,status=0,contains=None):
   r=subprocess.run([str(binary),*args],cwd=cwd or base,env=env,capture_output=True,text=True,timeout=180)
   assert r.returncode==status,(label,r.returncode,r.stdout,r.stderr)
   if contains is not None:assert contains in r.stdout+r.stderr,(label,r.stdout,r.stderr)
   records.append({'case':label,'exit':r.returncode});return r
  def work(name):d=base/name;d.mkdir();return d
  def program(n=42):return f'func main()->i64 print({n}); return 0; end;\n'
  def manifest(d,name='Demo',entry='main.aw',syntax='next'):(d/(name+'.awproj')).write_text(f'format: 1\nentry: {entry}\nsyntax: {syntax}\n')
  def execute(d,path,expected):
   r=subprocess.run([str(d/path)],cwd=d,env=env,capture_output=True,text=True,timeout=10);assert (r.returncode,r.stdout,r.stderr)==(0,expected,''),(r.returncode,r.stdout,r.stderr)
  via_path=subprocess.run(['Awl'],cwd=base,env={**env,'PATH':str(binary.parent)},capture_output=True,text=True,timeout=10)
  assert via_path.returncode==0 and 'Awl Software Development Kit [Beta]' in via_path.stdout,(via_path.stdout,via_path.stderr)
  records.append({'case':'installed Awl discovered on terminal PATH without host tools','exit':0})
  case('bare Awl shows branded help',contains='Awl Software Development Kit [Beta]');case('--help', ['--help'],contains='awl build relative/file.aw');case('version',['--version'],contains='[Beta]')
  for cmd in ['run','install','check','emit-c','unknown']:case('not public: '+cmd,[cmd],status=2,contains='only init/build')
  for name in ['', '../oops','a/b','a.awl','-bad','a b','CON','LPT1','a'*65]:case('invalid init '+repr(name),['init',name],status=2,contains='usage: awl init')
  case('init missing name',['init'],status=2);case('init excess arguments',['init','Demo','extra'],status=2)
  d=work('init');case('init here',['init','Demo'],d,contains='Created Demo.awproj');assert (d/'Demo.awproj').read_text()=='format: 1\nentry: main.aw\nsyntax: next\n';assert 'func main()' in (d/'main.aw').read_text();assert not(d/'Demo').exists()
  before=(d/'main.aw').read_bytes(),(d/'Demo.awproj').read_bytes();case('repeat init never overwrites',['init','Demo'],d,status=2,contains='already exists');assert before==((d/'main.aw').read_bytes(),(d/'Demo.awproj').read_bytes())
  preserve=work('preserve');(preserve/'main.aw').write_text(program(73));case('preserve existing main',['init','Keep'],preserve,contains='Preserved main.aw');assert '73' in(preserve/'main.aw').read_text()
  linked=work('linked');(linked/'main.aw').symlink_to(preserve/'main.aw');case('reject source symlink init',['init','Link'],linked,status=2,contains='non-symlink');assert not(linked/'Link.awproj').exists()
  case('no project',['build'],work('empty'),status=2,contains='no .awproj project')
  multi=work('multi');manifest(multi,'One');manifest(multi,'Two');(multi/'main.aw').write_text(program());case('ambiguous current projects',['build'],multi,status=2,contains='multiple .awproj')
  parent=work('parent');child=parent/'unrelated-folder-name';child.mkdir();manifest(child);(child/'main.aw').write_text(program())
  case('named child missing',['build','Missing'],parent,status=2,contains='no immediate child');case('case-sensitive project name',['build','demo'],parent,status=2,contains='no immediate child')
  twin=parent/'twin';twin.mkdir();manifest(twin);(twin/'main.aw').write_text(program());case('ambiguous named child',['build','Demo'],parent,status=2,contains='ambiguous project');shutil.rmtree(twin)
  for text,error in [('entry: main.aw\n','requires format'),('format: 2\nentry: main.aw\n','unsupported'),('format: 1\nentry: main.aw\nentry: main.aw\n','duplicate'),('format: 1\nentry: main.aw\nunknown: x\n','unknown manifest'),('format: 1\nentry: main.aw\nsyntax: no\n','syntax must'),('format: 1\nentry: /tmp/main.aw\n','relative .aw'),('format: 1\nentry: main.txt\n','relative .aw'),('format: 1\nentry: main.aw\x00\n','NUL')]:
   bad=work('bad'+str(len(records)));(bad/'Bad.awproj').write_text(text);(bad/'main.aw').write_text(program());case('manifest validation '+error,['build'],bad,status=2,contains=error)
  outside=work('outside');(outside/'main.aw').write_text(program());inside=work('inside');manifest(inside,entry='../outside/main.aw');case('entry cannot escape project',['build'],inside,status=2,contains='inside the project')
  huge=work('huge');(huge/'Huge.awproj').write_text('x'*16385);case('manifest size bound',['build'],huge,status=2,contains='16 KiB')
  badout=work('bad-output');manifest(badout);(badout/'main.aw').write_text(program());(badout/'build').symlink_to(outside,target_is_directory=True);case('output directory symlink rejected',['build'],badout,status=2,contains='not a symlink')
  case('manifest output extension protected',['build','-o','Demo.awproj'],d,status=2,contains='refusing to overwrite');assert before[1]==(d/'Demo.awproj').read_bytes()
  alias=d/'manifest-alias';os.link(d/'Demo.awproj',alias);case('hardlink manifest output protected',['build','-o',str(alias)],d,status=2,contains='refusing to overwrite')
  for args,error in [(['--syntax','bad'],'syntax'),(['-O','4'],'optimization'),(['--build-timeout','0'],'timeout'),(['--build-memory-mib','1'],'memory'),(['-o'],'missing value'),(['--unknown','x'],'unknown build option'),(['-O','1','-O','2'],'duplicate')]:case('invalid build options '+str(args),['build',*args],d,status=2,contains=error)
  if not a.metadata_only:
   case('default project build no host tools',['build'],d);execute(d,Path('build/Demo'),'Hello from Awl!\n')
   case('named project finds actual manifest in differently named folder',['build','Demo'],parent);execute(child,Path('build/Demo'),'42\n')
   custom=work('custom-entry');(custom/'src').mkdir();(custom/'src/start.aw').write_text(program(19));manifest(custom,'Custom','src/start.aw');case('manifest custom relative entry',['build'],custom);execute(custom,Path('build/Custom'),'19\n')
   single=work('single');(single/'nested path').mkdir();(single/'nested path/file.aw').write_text(program(128));case('single relative path with spaces',['build','nested path/file.aw'],single);execute(single,Path('file'),'128\n')
   case('single custom output and options',['build','nested path/file.aw','-o','custom','-O','0','--build-timeout','30','--build-memory-mib','1024'],single);execute(single,Path('custom'),'128\n')
   legacy=work('legacy');(legacy/'main.aw').write_text('function main()->i64 print(17) return 0 end\n');manifest(legacy,'Old',syntax='legacy');case('legacy project manifest',['build'],legacy);execute(legacy,Path('build/Old'),'17\n');case('single legacy explicit option',['build','main.aw','--syntax','legacy'],legacy);execute(legacy,Path('main'),'17\n')
   (legacy/'Old.awproj').write_text('format: 1\nentry: main.aw\nsyntax: next\n');case('syntax flag overrides manifest',['build','--syntax','legacy'],legacy)
   (single/'broken.aw').write_text('func main()->i64 return unknown; end;');case('compiler diagnostic propagates',['build','broken.aw'],single,status=1,contains='unknown')
   libs=work('imports');shutil.copytree(ROOT/'examples-next/modules',libs,dirs_exist_ok=True);case('single file with real imports/state/math',['build','main.aw'],libs);execute(libs,Path('main'),'128.59\n42\n2\n1\n9\n1\n0.78539816339744828\n')
   case('refuse overwrite imported source',['build','main.aw','-o','Library.aw'],libs,status=2,contains='overwrite source')
   case('refuse overwrite entry source',['build','main.aw','-o','main.aw'],libs,status=2,contains='overwrite source')
   prior=(d/'build/Demo').read_bytes();(d/'main.aw').write_text('bad source');case('failed compile preserves prior executable',['build'],d,status=1);assert (d/'build/Demo').read_bytes()==prior
  report={'status':'PASS','cases':len(records),'records':records,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'mode':('ASan/UBSan native driver+compiler; ' if 'ASAN_OPTIONS' in os.environ else '')+('front-door metadata only' if a.metadata_only else 'real bundled Linux backend; PATH excludes host tools; resulting programs executed'),'windows_tested':False}
  a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
if __name__=='__main__':main()

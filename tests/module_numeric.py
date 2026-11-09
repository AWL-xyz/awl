"""Production module scalar state +f64/math, not complete-language/release acceptance."""
import argparse,hashlib,json,math,os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,default=ROOT/'build/Awl-linux-x86_64/bin/kcc');p.add_argument('--sanitize-c',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args();binary=a.kcc.resolve();records=[]
 def program(body):return 'func main()->i64 '+body+' return 0; end;'
 with tempfile.TemporaryDirectory(prefix='Awl-module-numeric-') as td:
  root=Path(td);env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(ROOT/'build/module-numeric-cache')}
  def test(label,files,output=None,error=None,numbers=None,legacy=False):
   work=root/str(len(records));work.mkdir()
   for name,text in files.items():f=work/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text,encoding='utf-8')
   mode='check' if error else 'emit-c' if a.sanitize_c else 'run';r=subprocess.run([str(binary),mode,str(work/'main.aw'),'--syntax','legacy' if legacy else 'next'],env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
   if error:assert r.returncode==1 and error in r.stderr,(label,r.returncode,r.stdout,r.stderr)
   else:
    assert r.returncode==0,(label,r.returncode,r.stderr)
    if a.sanitize_c:
     source=work/'out.c';source.write_text(r.stdout);exe=work/'app';subprocess.run([shutil.which('cc'),'-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(source),'-lm','-o',str(exe)],check=True,timeout=60);r=subprocess.run([str(exe)],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'},capture_output=True,text=True,timeout=10)
    assert r.returncode==0 and not r.stderr,(label,r.returncode,r.stderr)
    if numbers is not None:
     found=[float(v) for v in r.stdout.splitlines()];assert len(found)==len(numbers) and all(math.isclose(x,y,rel_tol=2e-15,abs_tol=1e-15) for x,y in zip(found,numbers)),(label,found,numbers)
    else:assert r.stdout==output,(label,r.stdout,output)
   records.append({'label':label,'exit':r.returncode,'expected_error':error})
  lib=(ROOT/'examples/modules/Library.aw').read_text();entry=(ROOT/'examples/modules/main.aw').read_text()
  test('actual requested private module numeric version, helper context, rw state',{'main.aw':entry,'Library.aw':lib},numbers=[128.59,42,2,1,9,1,math.pi/4])
  test('original full exports example is now executable',{'main.aw':(ROOT/'examples/exports/main.aw').read_text(),'Template.aw':(ROOT/'examples/exports/Template.aw').read_text()},'readonly variable\n1.0.0\n')
  test('all four math functions and literal arguments',{'main.aw':(ROOT/'examples/numeric/main.aw').read_text()},numbers=[128.59,128.59,1,1,9,math.pi/4,math.tau,2,3])
  test('private module int text bool mutable state',{'main.aw':'@p n: 41; @p text: "x"; @p ready: false; '+program('n: n+1; text: "updated"; ready: true; print(n); print(text); print(ready);')},error='identifier')
  test('private scalar state read and writes',{'main.aw':'@p n: 41; @p message: "x"; @p ready: false; '+program('n: n+1; message: "updated"; ready: true; print(n); print(message); print(ready);')},'42\nupdated\ntrue\n')
  test('local shadows module variable',{'main.aw':'@p value: 99; func f()->i64 @p value: 42; return value; end; '+program('print(f()); print(value);')},'42\n99\n')
  test('readonly exported value mutable from defining module',{'main.aw':'use Lib.aw as m; '+program('print(m.next()); print(m.x);'),'Lib.aw':'exports(@r x: 1; @r func next()->i64 x: x+1; return x; end;);'},'2\n2\n')
  test('duplicate imports share one state',{'main.aw':'use Lib.aw as a; use Lib.aw as b; '+program('a.count: 7; print(b.count);'),'Lib.aw':'exports(@rw count: 1;);'},'7\n')
  test('dependency then source declaration initialization order',{'main.aw':'use A.aw as a; @p result: a.total+1; '+program('print(result);'),'A.aw':'use B.aw as b; @p private_value: b.value+1; exports(@r total: private_value+1;);','B.aw':'exports(@r value: 39;);'},'42\n')
  test('global functions can read later-declared module state',{'main.aw':'func version()->f64 return value; end; @p value: 128.59; '+program('print(version());')},numbers=[128.59])
  test('user exact local version example',{'main.aw':'func version()->text @p version: "1.0.0"; return version; end; '+program('print(version());')},'1.0.0\n')
  test('pure math module initializers',{'main.aw':'@p half: pi/2; exports(@r answer: sqrt(1764);); '+program('print(sin(half)); print(answer);')},numbers=[1,42])
  test('typed float binding assignment return literal contexts',{'main.aw':'func f()->f64 return 7; end; '+program('@p n f64: 1; n: 2; print(n); print(f());')},numbers=[2,7])
  test('negative integer literal math inputs',{'main.aw':program('print(sin(-1)); print(atan2(-1, 1)); print(0.5 + -1);')},numbers=[math.sin(-1),-math.pi/4,-.5])
  test('numeric arithmetic comparisons and conversions',{'main.aw':program('@p x: 2.5; @p n: 2; print(x*2+1); print(x-1); print(x/2); print(x>2); print(x==2.5); print(f64(n));')},'6\n1.5\n1.25\ntrue\ntrue\n2\n')
  test('floating arrays and parameter result types',{'main.aw':'func twice(x:f64)->f64 return x*2; end; '+program('@p values: [1.5,2.5]; print(twice(values[1])); print(twice(2));')},numbers=[5,4])
  test('all four math calls with runtime input, not constant folding',{'main.aw':program('@p n: f64(clock_millis()); n: n*n+1; @p s: sin(n); @p c: cos(n); @p a: atan2(n,n); print(s>=-1.0 and s<=1.0); print(c>=-1.0 and c<=1.0); print(sqrt(n)>0.0); print(a>0.7 and a<0.8);')},'true\ntrue\ntrue\ntrue\n')
  test('NaN domain result follows IEEE equality',{'main.aw':program('@p x: sqrt(-1); print(x==x); print(x!=x);')},'false\ntrue\n')
  test('private read denied',{'main.aw':entry.replace('lib.get_version()','lib.version'),'Library.aw':lib},error='private/not exported')
  test('private write denied',{'main.aw':'use Library.aw as lib; '+program('lib.version: 1.0;'),'Library.aw':lib},error='private/not exported')
  test('readonly write denied',{'main.aw':'use Library.aw as lib; '+program('lib.fixed: 7;'),'Library.aw':lib},error='readonly/private')
  test('standalone r denied',{'main.aw':'@r value: 1; '+program('')},error='only valid inside exports')
  test('standalone rw denied',{'main.aw':'@rw value: 1; '+program('')},error='only valid inside exports')
  test('local r denied',{'main.aw':program('@r value: 1;')},error="expected 'p'")
  test('rw function denied',{'main.aw':'exports(@rw func f()->i64 return 1; end;); '+program('')},error='require @r')
  test('duplicate variables denied',{'main.aw':'@p x: 1; exports(@rw x: 2;); '+program('')},error='duplicate')
  test('variable function duplicate denied',{'main.aw':'@p f: 1; func f()->i64 return 1; end; '+program('')},error='duplicate')
  test('self initializer read denied',{'main.aw':'@p x: x+1; '+program('')},error='not-yet-initialized')
  test('forward initializer read denied',{'main.aw':'@p x: y; @p y: 1; '+program('')},error='not-yet-initialized')
  test('initializer user call deferred safely',{'main.aw':'func f()->i64 return 1; end; @p x: f(); '+program('')},error='initializers currently permit')
  test('initializer platform call deferred safely',{'main.aw':'@p x: clock_millis(); '+program('')},error='initializers currently permit')
  test('owned module resources not silently copied',{'main.aw':'@p x: spool_new(32); '+program('')},error='initializers currently permit')
  test('global arrays not silently stored',{'main.aw':'@p x: [1,2]; '+program('')},error='initializers currently permit')
  test('captured local cannot fall back to same-named module value',{'main.aw':'@p x: 999; '+program('@p x: 42; @p func h()->i64 return x; end; print(h());')},error='parent-local capture')
  test('captured local write cannot modify module instead',{'main.aw':'@p x: 999; '+program('@p x: 42; @p func h() x: 1; end; h();')},error='parent-local capture')
  test('helper value cannot fall back to module binding',{'main.aw':'@p h: 999; '+program('@p func h()->i64 return 42; end; @p value: h;')},error='not variable values')
  for label,body,err in [('numeric string not math','print(sin("1"));','math arguments'),('typed integer variable not implicitly float','@p n: 1; print(sin(n));','math arguments'),('typed width not implicitly float','print(sin(1u8));','math arguments'),('bad math arity','print(atan2(1));','math arguments'),('float remainder undefined','print(1.5%1.0);','arithmetic/comparison'),('float to integer conversion not unchecked','print(i64(1.5));','requires an integer'),('double declaration spacing','@p n: 128 . 59;','f64 decimal'),('not a semantic version number','@p n: 1.0.0;','identifier'),('wrong declared integer type','@p n i64: 128.59;','expected i64')]:test(label,{'main.aw':program(body)},error=err)
  test('out of range decimal literal',{'main.aw':program('@p n: '+('9'*256)+'.0;')},error='f64 decimal')
  test('legacy function spelling still works',{'main.aw':'function main()->i64 local n:i64=42 print(n) return 0 end'},'42\n',legacy=True)
  report={'status':'passed','scope':__doc__,'cases':len(records),'mode':'host-compiled generated C ASan/UBSan' if a.sanitize_c else 'installed Linux driver/shipped backend; PATH excludes host tools','compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'records':records};a.report.write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(records),report['mode'])
if __name__=='__main__':main()

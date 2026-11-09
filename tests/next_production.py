"""Actual production native pipeline, experimental --syntax next; not release acceptance."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,default=ROOT/'build/Awl-linux-x86_64/bin/kcc');p.add_argument('--sanitize-c',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args();kcc=a.kcc.resolve();records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-native-next-') as td:
  folder=Path(td);env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(ROOT/'build/next-production-cache')};serial=0
  def test(label,files,stdout=None,error=None,legacy=False):
   nonlocal serial
   serial+=1;work=folder/str(serial);work.mkdir()
   for name,text in files.items():
    f=work/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(text if isinstance(text,bytes) else text.encode())
   source=work/'main.aw';flags=['--syntax','legacy' if legacy else 'next'];command='check' if error else 'emit-c' if a.sanitize_c else 'run';r=subprocess.run([str(kcc),command,str(source),*flags,'--build-timeout','600'] if command=='run' else [str(kcc),command,str(source),*flags],env=env,capture_output=True,text=True,encoding="utf-8",timeout=180)
   if error:
    assert r.returncode==1 and error in r.stderr,(label,r.returncode,r.stdout,r.stderr)
   else:
    assert r.returncode==0,(label,r.returncode,r.stdout,r.stderr)
    if a.sanitize_c:
     c=work/'out.c';c.write_text(r.stdout);exe=work/'program';subprocess.run([shutil.which('cc'),'-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',str(c),'-o',str(exe)],check=True,timeout=60);r=subprocess.run([str(exe)],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'},capture_output=True,text=True,encoding="utf-8",timeout=10)
    assert (r.returncode,r.stdout,r.stderr)==(0,stdout,''),(label,r.returncode,r.stdout,r.stderr)
   records.append({'label':label,'command':command,'exit':r.returncode,'expected_error':error})
  def program(body):return 'func main() -> i64 '+body+' return 0; end;'
  library=(ROOT/'examples/native/Library.aw').read_text();entry=(ROOT/'examples/native/main.aw').read_text()
  test('actual private nested helper, own locals, original module not importer',{'main.aw':entry,'Library.aw':library},'42\n1.0.0\n')
  test('inferred scalar text bool widths arrays',{'main.aw':program('@p text_value: "é🙂; colon: text"; @p b: true; @p n: 7u16; @p data: [1,2,3]; print(text_value); print(b); print(n); print(data[2]);')},'é🙂; colon: text\ntrue\n7\n3\n')
  test('explicit type and compound terminators',{'main.aw':program('@p n i64: 4; while n>0 do n: n-1; end; if n==0 then print(42); else print(0); end;')},'42\n')
  test('initializer with side effect evaluated once',{'main.aw':'func f()->i64 print("once"); return 9; end; '+program('@p n: f(); print(n);')},'once\n9\n')
  test('inferred result consumes an owner exactly once',{'main.aw':'func consume(own b:spool)->i64 return 7; end; '+program('@p scoped b spool: spool.new(32); @p n: consume(move b); print(n);')},'7\n')
  test('nested recursion and typed parameters',{'main.aw':program('@p func fact(n:i64)->i64 if n==0 then return 1; else return n*fact(n-1); end; end; print(fact(6));')},'720\n')
  test('nested sibling calls retain lexical permissions',{'main.aw':program('@p func first()->i64 return 42; end; @p func second()->i64 return first(); end; print(second());')},'42\n')
  test('parameter passed explicitly to helper',{'main.aw':'func outer(n:i64)->i64 @p func helper(x:i64)->i64 return x*2; end; return helper(n); end; '+program('print(outer(21));')},'42\n')
  test('block locals do not leak into later func lookup',{'main.aw':'func f()->i64 return 42; end; '+program('if true then @p f: 1; print(f); end; print(f());')},'1\n42\n')
  test('block local does not block later helper declaration',{'main.aw':program('if true then @p helper: 1; print(helper); end; @p func helper()->i64 return 42; end; print(helper());')},'1\n42\n')
  test('unit return annotation may be omitted',{'main.aw':'func hello() print("hello"); end; '+program('hello();')},'hello\n')
  test('nested helper not activated until called',{'main.aw':program('@p func helper() print("must not run"); end; print("main only");')},'main only\n')
  test('default file namespace',{'main.aw':program('print(lib.f());').replace('func main','use lib.aw; func main',1),'lib.aw':'exports(@r func f()->i64 return 42; end;);'},'42\n')
  test('file imports its own private dependency',{'main.aw':'use lib/A.aw as a; '+program('print(a.f());'),'lib/A.aw':'use helper.aw as h; func private_value()->i64 return h.value(); end; exports(@r func f()->i64 return private_value(); end;);','lib/helper.aw':'exports(@r func value()->i64 return 42; end;);'},'42\n')
  for filename,spell in [('odd.name.aw','odd.name.aw'),('my-library.aw','my-library.aw'),('2026.aw','2026.aw'),('space name.aw','"space name.aw"'),('世界.aw','"世界.aw"')]:
   test('alias general filename '+filename,{'main.aw':'use '+spell+' as m; '+program('print(m.f());'),filename:'exports(@r func f()->i64 return 42; end;);'},'42\n')
  test('private module func denied',{'main.aw':entry.replace('lib.answer()','lib.private_bonus()'),'Library.aw':library},error='private/not exported')
  test('unqualified imports not injected',{'main.aw':entry.replace('lib.answer()','answer()'),'Library.aw':library},error='declaration')
  test('helper not exported by enclosing export',{'main.aw':entry.replace('lib.answer()','lib.helper()'),'Library.aw':library},error='declaration')
  test('caller local cannot supply callee free variable',{'main.aw':program('@p value: 42; print(m.f());').replace('func main','use mod.aw as m; func main',1),'mod.aw':'exports(@r func f()->i64 return value; end;);'},error='unknown local')
  test('capturing parent parameter rejected instead of stale stack access',{'main.aw':'func f(x:i64)->i64 @p func helper()->i64 return x; end; return helper(); end; '+program('print(f(42));')},error='parent-local capture')
  test('nested helper outside its enclosing func denied',{'main.aw':'func outer()->i64 @p func helper()->i64 return 42; end; return helper(); end; '+program('print(helper());')},error='unknown function')
  test('guessed generated helper name denied',{'main.aw':'func outer()->i64 @p func helper()->i64 return 42; end; return helper(); end; '+program('print(kn_nested_0());')},error='reserved internal')
  test('nested helper in conditional not yet allowed',{'main.aw':program('if true then @p func helper()->i64 return 42; end; print(helper()); end;')},error='directly')
  test('duplicate helper',{'main.aw':program('@p func h()->i64 return 1; end; @p func h()->i64 return 2; end;')},error='duplicate')
  test('helper binding shadow rejected',{'main.aw':program('@p func h()->i64 return 1; end; @p h: 2;')},error='shadows nested')
  test('duplicate export',{'main.aw':'exports(@r func f()->i64 return 1; end; @r func f()->i64 return 2; end;); '+program('')},error='duplicate export')
  test('duplicate aliases',{'main.aw':'use A.aw as m; use B.aw as m; '+program(''),'A.aw':'','B.aw':''},error='duplicate import alias')
  test('circular file imports',{'main.aw':'use A.aw; '+program(''),'A.aw':'use B.aw;','B.aw':'use A.aw;'},error='cyclic')
  test('missing file',{'main.aw':'use Missing.aw; '+program('')},error='missing or wrong-case')
  test('wrong file case',{'main.aw':'use library.aw; '+program(''),'Library.aw':library},error='wrong-case')
  test('wrong directory case',{'main.aw':'use Lib/A.aw; '+program(''),'lib/A.aw':library},error='wrong-case')
  test('package integration explicitly pending',{'main.aw':'use KCore; '+program('')},error='Package lookup is not integrated')
  test('module variable execution',{'main.aw':'@p version: "1.0.0"; '+program('print(version);')},'1.0.0\n')
  test('exported variable execution',{'main.aw':'exports(@r variable: "x";); '+program('print(variable);')},'x\n')
  test('legacy declaration rejected in next mode',{'main.aw':'func main()->i64 local n:i64=0; return n; end;'},error='use @p')
  test('legacy import rejected in next mode',{'main.aw':'import A; '+program('')},error='next syntax uses use')
  test('space before assignment colon',{'main.aw':program('@p n: 1; n : 2;')},error='no whitespace')
  test('space before parameter colon',{'main.aw':'func f(n :i64)->i64 return n; end; '+program('')},error='no whitespace')
  test('NUL import path rejected',{'main.aw':'use "bad\\u{0}.aw" as n; '+program('')},error='without NUL')
  test('missing use terminator',{'main.aw':'use A.aw '+program(''),'A.aw':''},error="expected ';'")
  test('missing exports terminator',{'main.aw':'exports(@r func f()->i64 return 42; end;) '+program('')},error="expected ';'")
  test('readwrite variable export execution',{'main.aw':'exports(@rw variable: 1;); '+program('variable: 2; print(variable);')},'2\n')
  test('space before declaration colon',{'main.aw':program('@p n : 1;')},error='no whitespace')
  test('equals initialization rejected',{'main.aw':program('@p n = 1;')},error="':' instead of '='")
  test('equals assignment rejected',{'main.aw':program('@p n: 1; n = 2;')},error="expected ';'")
  test('bad initializer type rejected',{'main.aw':program('@p n i64: "bad";')},error='expected i64')
  test('bad argument types rejected',{'main.aw':'func f(n:i64)->i64 return n; end; '+program('print(f("wrong"));')},error='argument')
  test('bad return type rejected',{'main.aw':'func main()->i64 return "bad"; end;'},error='expected i64')
  test('unit local inference rejected',{'main.aw':program('@p n: print(42);')},error='invalid value type unit')
  test('manual inferred resource not silently owned',{'main.aw':program('@p b: spool.new(32);')},error='inferred resources')
  test('duplicate semicolon rejected',{'main.aw':program('print(1);;')},error='double semicolons')
  source='func main()->i64 @p n: 1; if true then print(n); end; while n>0 do n: n-1; end; return 0; end;'
  for i,c in enumerate(source):
   if c==';':test('required terminator removed '+str(i),{'main.aw':source[:i]+source[i+1:]},error="expected ';'")
  test('old function declaration spelling rejected in next',{'main.aw':'function main()->i64 return 0; end;'},error="expected 'func'")
  test('old nested declaration spelling rejected in next',{'main.aw':program('@p function h()->i64 return 1; end;')},error='identifier')
  test('legacy mode still executes',{'main.aw':'function main()->i64 local n:i64=42 print(n) return 0 end'},'42\n',legacy=True)
  report={'status':'passed','scope':__doc__,'mode':'ASan/UBSan generated-C execution (contributor host compiler)' if a.sanitize_c else 'actual production native frontend/verifier/emitter/installed driver +shipped0.15.2 backend; PATH excludes host tools','compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'cases':len(records),'records':records};a.report.write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(records),'actual production next/legacy cases;',report['mode'])
if __name__=='__main__':main()

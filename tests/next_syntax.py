"""Executable structural/module tests, not full-language/type/runtime acceptance."""
import argparse,hashlib,json,os,random,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();binary=a.binary.resolve();records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-next-') as td:
  work=Path(td)
  def check(label,files,expected=0,diagnostic=None,packages=None):
   import shutil
   folder=work/'project'
   if folder.exists():shutil.rmtree(folder)
   folder.mkdir()
   for name,text in files.items():
    f=folder/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(text if isinstance(text,bytes) else text.encode())
   args=[str(binary),str(folder/'main.aw')]
   if packages:args+=['--packages',str(folder/packages)]
   r=subprocess.run(args,capture_output=True,text=True,timeout=5,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'})
   assert r.returncode==expected,(label,r.returncode,r.stderr)
   if diagnostic:assert diagnostic in r.stderr,(label,r.stderr)
   assert 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr,(label,r.stderr)
   records.append({'label':label,'exit':r.returncode,'expected_diagnostic':diagnostic})
  library='@p secret: "private"; exports(@r fixed: "read"; @rw mutable: "write"; @r func get() -> text @p func helper() -> text return secret; end; return helper(); end;);'
  entry='use lib/Template.aw as t; func main() -> i64 print(t.fixed); t.mutable: "changed"; print(t.get()); return 0; end;'
  check('qualified exports, mutable write, nested lexical helper',{'main.aw':entry,'lib/Template.aw':library})
  for member,code in [('secret','N212'),('helper','N212'),('missing','N212')]:check('private/missing '+member,{'main.aw':entry.replace('print(t.fixed)','print(t.'+member+')'),'lib/Template.aw':library},1,code)
  for member in ['fixed','get']:check('readonly assignment '+member,{'main.aw':entry.replace('t.mutable:',f't.{member}:'),'lib/Template.aw':library},1,'N213')
  check('unqualified export not injected',{'main.aw':entry.replace('print(t.fixed)','print(fixed)'),'lib/Template.aw':library},1,'N210')
  check('private binding in importer cannot supply callee context',{'main.aw':entry.replace('print(t.fixed)','@p foreign: "not visible"; print(t.fixed)'),'lib/Template.aw':library.replace('return secret','return foreign')},1,'N210')
  check('project file imports its own helper file',{'main.aw':'use lib/A.aw as a; func f() print(a.get()); end;','lib/A.aw':'use helper.aw as h; @p func private_helper() return h.value; end; exports(@r func get() return private_helper(); end;);','lib/helper.aw':'exports(@r value: 42;);'})
  check('nested func captures enclosing parameter',{'main.aw':'exports(@r func f(x:i64) -> i64 @p func helper() -> i64 return x; end; return helper(); end;);'})
  check('two modules export same name through distinct namespaces',{'main.aw':'use A.aw as a; use B.aw as b; func f() print(a.x+b.x); end;','A.aw':'exports(@r x: 1;);','B.aw':'exports(@r x: 2;);'})
  check('module variable write by defining function',{'main.aw':'exports(@r value: 0; @r func set() value: 1; end;);'})
  check('duplicate export across blocks',{'main.aw':'exports(@r x: 1;); exports(@rw x: 2;);'},1,'N112')
  check('duplicate private/export',{'main.aw':'@p x: 1; exports(@r x: 2;);'},1,'N112')
  check('functions cannot rw export',{'main.aw':'exports(@rw func f() end;);'},1,'N113')
  check('exports require permission',{'main.aw':'exports(x: 1;);'},1,'N100')
  check('exports cannot p',{'main.aw':'exports(@p x: 1;);'},1,'N110')
  check('old declaration rejected',{'main.aw':'func main() local x:i64=1; end;'},1,'N114')
  for text in ['@p x = 1;','@p x: = 1;','func main() @p x: 1; x = 2; end;']:check('equals rejected '+text,{'main.aw':text},1)
  check('space before initialization colon',{'main.aw':'@p x : 1;'},1,'N103')
  check('space before assignment colon',{'main.aw':'func f() @p x: 1; x : 2; end;'},1,'N103')
  check('typed declaration and typed parameter',{'main.aw':'@p n i64: 1; func f(x:i64) -> i64 return x+n; end;'})
  check('UTF8 literal and escaped quote',{'main.aw':'@p s: "é世界🙂\\\""; func f() print(s); end;'})
  for data in [b'\xff',b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\0']:check('invalid utf8 '+repr(data),{'main.aw':data},1,'N001')
  check('unquoted semantic version rejected',{'main.aw':'@p version: 1.0.0;'},1)
  check('missing file',{'main.aw':'use Missing.aw;'},1,'N201')
  check('wrong filename case',{'main.aw':'use template.aw;','Template.aw':library},1,'N201')
  check('wrong directory case',{'main.aw':'use Lib/Template.aw;','lib/Template.aw':library},1,'N201')
  check('wrong extension',{'main.aw':'use Template.K;','Template.K':library},1,'N121')
  check('circular import',{'main.aw':'use A.aw;','A.aw':'use B.aw;','B.aw':'use A.aw;'},1,'N203')
  check('self import',{'main.aw':'use main.aw;'},1,'N203')
  check('duplicate alias',{'main.aw':'use A.aw as m; use B.aw as m;','A.aw':'','B.aw':''},1,'N111')
  check('namespace/private collision',{'main.aw':'use A.aw as x; @p x: 1;','A.aw':''},1,'N111')
  check('package unavailable',{'main.aw':'use KCore;'},1,'N205')
  check('installed staging package',{'main.aw':'use KCore as k; func f() print(k.value); end;','packages/KCore/main.aw':'use inner.aw as i; exports(@r value: i.value;);','packages/KCore/inner.aw':'exports(@r value: 42;);'},packages='packages')
  check('wrong package case',{'main.aw':'use kcore;','packages/KCore/main.aw':''},1,'N201',packages='packages')
  check('relative child import and private helper',{'main.aw':'use lib/A.aw as a; func f() print(a.get()); end;','lib/A.aw':'use ../B.aw as b; exports(@r func get() return b.value; end;);','B.aw':'exports(@r value: 42;);'},1) # dot-prefix spelling intentionally unsupported by prototype grammar
  source='@p value: 1; func main() -> i64 @p x: 2; if x>0 then print(x); else print(value); end; while x>0 do x: x-1; end; return 0; end; exports(@r func read() -> i64 return value; end;);'
  check('if while exports delimiters',{'main.aw':source})
  for i,c in enumerate(source):
   if c==';':check('remove required semicolon '+str(i),{'main.aw':source[:i]+source[i+1:]},1)
  check('two commands without separator',{'main.aw':'func f() print(1) print(2); end;'},1,'N104')
  check('unbalanced call',{'main.aw':'func f() print((1); end;'},1)
  check('operator missing operand',{'main.aw':'@p x: 1+;'},1,'N106')
  check('nesting cap',{'main.aw':'@p x: '+'('*100+'1'+')'*100+';'},1,'N004')
  check('file cap',{'main.aw':b' '*1048577},1,'N004')
  # Deterministic structure mutations: no crash expectation; acceptance is not a semantic oracle.
  rng=random.Random(24)
  for n in range(200):
   mutation=source;start=rng.randrange(len(mutation));mutation=mutation[:start]+rng.choice(['@',';',')','end','use','"','\xff'])+mutation[start+1:]
   folder=work/'fuzz';folder.mkdir(exist_ok=True);(folder/'main.aw').write_bytes(mutation.encode('latin1'));r=subprocess.run([str(binary),str(folder/'main.aw')],capture_output=True,text=True,timeout=5,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'});assert r.returncode in [0,1],(n,r.returncode,r.stderr);assert 'Sanitizer' not in r.stderr and 'runtime error:' not in r.stderr,(n,r.stderr)
  report={'status':'passed','scope':__doc__,'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'compiler/next/syntax.cpp').read_bytes()).hexdigest(),'deterministic_cases':len(records),'seeded_structure_mutations':200,'records':records};a.report.write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(records),'deterministic checks +200 seeded structure mutations')
if __name__=='__main__':main()

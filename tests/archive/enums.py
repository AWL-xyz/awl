#!/usr/bin/env python3
import argparse,hashlib,json,os,random,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DECL='enum Outcome Value(value:i64); Empty(); end; '
def program(body,decl=DECL):return decl+'func main()->i64 '+body+' end;'
def match(value='Outcome.Value(7)',yes='print(x);',no='print(0);'):
 return 'match '+value+' then case Outcome.Value(x) then '+yes+' case Outcome.Empty() then '+no+' end;'
def main():
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--sanitized',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();kcc=a.kcc.resolve();env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1','XDG_CACHE_HOME':'/var/tmp/Awl-enum-cache'};records=[]
 positives=[('payload',program(match()+' return 0;'),b'7\n'),('empty',program(match('Outcome.Empty()')+' return 0;'),b'0\n'),('discard',program(match(yes='print(9);').replace('Value(x)','Value(_)')+' return 0;'),b'9\n'),('shadow',program('@p x: 3; '+match()+' print(x); return 0;'),b'7\n3\n'),('nested values',program('match Outer.Wrap(Outcome.Value(42)) then case Outer.Wrap(inner) then '+match('inner')+' end; return 0;',DECL+'enum Outer Wrap(inner:Outcome); end; '),b'42\n'),('f64 literal','enum Number Real(value:f64); end; func main()->i64 match Number.Real(-2) then case Number.Real(x) then print(x); return 0; end; end;',b'-2\n'),('text bool','enum Event Item(name:text,enabled:bool); end; func main()->i64 match Event.Item("café",true) then case Event.Item(name,enabled) then print(name); print(enabled); return 0; end; end;','café\ntrue\n'.encode()),('helper returns',DECL+'func make()->Outcome return Outcome.Value(13); end; func main()->i64 '+match('make()')+' return 0; end;',b'13\n'),('assignment',program('@p x: Outcome.Empty(); x: Outcome.Value(8); '+match('x')+' return 0;'),b'8\n'),('reuse',program('@p i: 0; @p total: 0; while i<2000 do '+match('Outcome.Value(i)','total: total+x;','total: total+1;')+' i: i+1; end; print(total); return 0;'),b'1999000\n')]
 negatives=[('empty enum',program('return 0;','enum U end;')),
 ('duplicate variant',program('return 0;','enum U A(); A(); end;')),
 ('duplicate field',program('return 0;','enum U A(x:i64,x:bool); end;')),
 ('unit payload',program('return 0;','enum U A(x:unit); end;')),
 ('recursive payload',program('return 0;','enum U A(x:U); end;')),
 ('resource payload',program('return 0;','enum U A(x:spool); end;')),
 ('vector payload',program('return 0;','enum U A(x:vector<i64>); end;')),
 ('array payload',program('return 0;','enum U A(x:[i64;2]); end;')),
 ('missing variant semicolon',program('return 0;',DECL.replace('value:i64);','value:i64)'))),
 ('missing enum semicolon',program('return 0;',DECL.replace('end;','end'))),
 ('double semicolon',program('return 0;',DECL.replace('Empty();','Empty();;'))),
 ('spaced field colon',program('return 0;',DECL.replace('value:i64','value :i64'))),
 ('legacy union spelling',program('return 0;',DECL.replace('enum','union'))),
 ('no cases',program('match Outcome.Empty() then end; return 0;')),
 ('missing case',program('match Outcome.Value(1) then case Outcome.Value(x) then print(x); end; return 0;')),
 ('duplicate case',program(match().replace('case Outcome.Empty() then print(0);','case Outcome.Value(y) then print(y);')+' return 0;')),
 ('binding arity',program(match().replace('Value(x)','Value()')+' return 0;')),
 ('escape binder',program(match()+' print(x); return 0;')),
 ('other arm binder',program(match(no='print(x);')+' return 0;')),
 ('constructor arity',program('@p x: Outcome.Value(); return 0;')),
 ('constructor type',program('@p x: Outcome.Value(true); return 0;')),
 ('unknown variant',program('@p x: Outcome.Other(); return 0;')),
 ('opaque fields',program('print(Outcome.Value(1).value); return 0;')),
 ('enum equality',program('print(Outcome.Empty()==Outcome.Empty()); return 0;')),
 ('scalar match',program(match('7')+' return 0;')),
 ('partial return',program(match(yes='return x;',no='print(0);'))),
 ('unreachable',program(match(yes='return x;',no='return 0;')+' return 0;')),
 ('missing match semicolon',program(match().replace('end;','end')+' return 0;')),
 ('too many variants',program('return 0;','enum U '+' '.join('V'+str(i)+'();' for i in range(129))+' end;')),
 ('enum keyword identifier','func enum()->i64 return 0; end; func main()->i64 return 0; end;'),
 ('readwrite enum forbidden','exports(@rw enum U A(); end;); func main()->i64 return 0; end;'),
 ('nested enum declaration',program('enum Local A(); end; return 0;'))]
 with tempfile.TemporaryDirectory(prefix='Awl-enum-tests-',dir='/var/tmp') as td:
  work=Path(td)
  for i,(name,source) in enumerate(negatives):
   src=work/'bad.aw';src.write_text(source);r=subprocess.run([str(kcc),'check',str(src),'--syntax','next'],capture_output=True,text=True,env=env,timeout=5);assert r.returncode==1 and 'error[' in r.stderr,(name,r.stdout,r.stderr);records.append(['rejected',name])
  for mode in ['bundled','sanitized']:
   for i,(name,source,want) in enumerate(positives):
    src=work/'main.aw';src.write_text(source);exe=work/'app';cmd='build' if mode=='bundled' else 'emit-c';r=subprocess.run([str(kcc),cmd,str(src),'--syntax','next']+(['-o',str(exe)] if mode=='bundled' else []),capture_output=True,text=True,env={**env,'PATH':'/no-host-tools'},timeout=180);assert r.returncode==0,(name,r.stderr)
    if mode=='sanitized':
     c=work/'main.c';c.write_text(r.stdout);subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)],check=True,timeout=90)
    r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=5);assert (r.returncode,r.stdout,r.stderr)==(0,want,b''),(mode,name,r.returncode,r.stdout,r.stderr);records.append([mode,name])
  (work/'Maker.aw').write_text('enum Secret Empty(); end; exports(@r func answer()->i64 match Secret.Empty() then case Secret.Empty() then return 42; end; end;);')
  src=work/'main.aw';src.write_text('use Maker.aw as m; func main()->i64 print(m.answer()); return 0; end;');r=subprocess.run([str(kcc),'build',str(src),'--syntax','next','-o',str(work/'app')],capture_output=True,env=env,timeout=90);assert r.returncode==0,r.stderr;r=subprocess.run([str(work/'app')],capture_output=True,env=env);assert (r.returncode,r.stdout,r.stderr)==(0,b'42\n',b'');records.append(['bundled','module private enum context'])
  src.write_text('use Maker.aw as m; func main()->i64 @p x: m.Secret.Empty(); return 0; end;');r=subprocess.run([str(kcc),'check',str(src),'--syntax','next'],capture_output=True,env=env);assert r.returncode==1 and b'private' in r.stderr;records.append(['rejected','foreign private enum'])
  minimum=-(1<<63);maximum=(1<<63)-1;rng=random.Random(428)
  values=[minimum,minimum+1,-3,-1,0,1,2,maximum-1,maximum];inputs=[(op,x,y) for op in ['+','-','*','/'] for x in values for y in values]
  inputs += [(rng.choice(['+','-','*','/']),rng.randrange(minimum,maximum+1),rng.randrange(minimum,maximum+1)) for _ in range(120)]
  counts={}
  for mode,exe in [('bundled',a.native),('sanitized',a.sanitized)]:
   for op,x,y in inputs:
    code=0
    if op=='/' and y==0:code=4;want='division by zero'
    else:
     value=x+y if op=='+' else x-y if op=='-' else x*y if op=='*' else (abs(x)//abs(y))*(-1 if (x<0)!=(y<0) else 1)
     if not minimum<=value<=maximum:code=4;want='arithmetic overflow'
     else:want=str(value)
    r=subprocess.run([str(exe.resolve()),op,str(x),str(y)],capture_output=True,env=env,timeout=5);assert (r.returncode,r.stdout,r.stderr)==(code,(want+'\n').encode(),b''),(mode,op,x,y,r.returncode,r.stdout,r.stderr)
   malformed=[(['+','','1'],3,'left invalid at byte 0'),(['+','+','1'],3,'left invalid at byte 1'),(['+','1','12é'],3,'right invalid at byte 2'),(['+','9223372036854775808','1'],3,'left integer overflow'),(['+','1','-9223372036854775809'],3,'right integer overflow'),(['?','1','2'],2,'unknown operator: ?')]
   for args,code,want in malformed:
    r=subprocess.run([str(exe.resolve()),*args],capture_output=True,env=env);assert (r.returncode,r.stdout,r.stderr)==(code,(want+'\n').encode(),b'')
   counts[mode]=len(inputs)+len(malformed)
 report={'status':'PASS','compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'feature_cases':len(records),'records':records,'calc_cases_per_mode':counts,'source_sha256':hashlib.sha256((ROOT/'examples/enums/main.aw').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'qualification':'private next enums with scalar/nested-enum payloads, no exported enum types, recursive/resource payloads or generic enum support'}
 a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(records),'feature cases,',counts)
if __name__=='__main__':main()

#!/usr/bin/env python3
import argparse,hashlib,json,os,random,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB='exports(@r enum Value Some(value:i64); None(); end; @r func make()->Value return Value.Some(42); end;);'
MAIN='use Lib.aw as m; func main()->i64 match m.make() then case m.Value.Some(x) then print(x); case m.Value.None() then print(0); end; return 0; end;'
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();kcc=sdk/'bin/kcc';env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-export-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'};records=[]
 def run(cmd,**kw):return subprocess.run(cmd,capture_output=True,timeout=180,env=env,**kw)
 with tempfile.TemporaryDirectory(prefix='Awl-export-test-',dir='/var/tmp') as td:
  td=Path(td);src=td/'main.aw';lib=td/'Lib.aw'
  positive=[('construct and type annotation','use Lib.aw as m; func echo(v:m.Value)->m.Value return v; end; func main()->i64 match echo(m.Value.Some(7)) then case m.Value.Some(x) then print(x); case m.Value.None() then print(0); end; return 0; end;',b'7\n'),('factory defining context',MAIN,b'42\n'),('empty constructor',MAIN.replace('m.make()','m.Value.None()'),b'0\n'),('alias identity',MAIN.replace('func main()', 'use Lib.aw as n; func main()').replace('m.make()','n.make()'),b'42\n')]
  for name,source,want in positive:
   src.write_text(source);lib.write_text(LIB)
   for mode in ['native','sanitized']:
    exe=td/'app';r=run([str(kcc),'build' if mode=='native' else 'emit-c',str(src),'--syntax','next',*(['-o',str(exe)] if mode=='native' else [])]);assert r.returncode==0,(name,r.stderr)
    if mode=='sanitized':
     c=td/'app.c';c.write_bytes(r.stdout);r=run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)]);assert r.returncode==0,r.stderr
    r=run([str(exe)]);assert (r.returncode,r.stdout,r.stderr)==(0,want,b''),(name,mode,r.stdout,r.stderr);records.append(mode+' '+name)
  negatives=[('private constructor',LIB.replace('exports(@r enum Value Some(value:i64); None(); end;', 'enum Value Some(value:i64); None(); end; exports('),MAIN.replace('m.make()','m.Value.None()')),('private pattern',LIB.replace('exports(@r enum Value Some(value:i64); None(); end;', 'enum Value Some(value:i64); None(); end; exports('),MAIN),('readwrite enum',LIB.replace('@r enum','@rw enum'),MAIN),('missing arm',LIB,MAIN.replace('case m.Value.None() then print(0);','')),('duplicate arm',LIB,MAIN.replace('case m.Value.None() then print(0);','case m.Value.Some(y) then print(y);')),('wrong payload',LIB,MAIN.replace('m.make()','m.Value.Some(true)')),('wrong arity',LIB,MAIN.replace('m.make()','m.Value.Some()')),('wrong pattern arity',LIB,MAIN.replace('Some(x)','Some()')),('wrong enum nominal type',LIB,MAIN.replace('func main()', 'enum Other Some(value:i64); None(); end; func main()').replace('m.make()','Other.None()')),('duplicate export declaration',LIB.replace('@r func make()', '@r enum Value A(); end; @r func make()'),MAIN),('resource payload',LIB.replace('value:i64','value:vector<i64>'),MAIN),('recursive layout',LIB.replace('value:i64','value:Value'),MAIN),('unknown variant',LIB,MAIN.replace('m.make()','m.Value.Other()')),('case sensitive type',LIB,MAIN.replace('m.Value','m.value')),('no enum outside exports annotation','@r enum Value Some(value:i64); None(); end;',MAIN)]
  for name,module,source in negatives:
   lib.write_text(module);src.write_text(source);r=run([str(kcc),'check',str(src),'--syntax','next']);assert r.returncode==1 and b'error[' in r.stderr,(name,r.stdout,r.stderr);records.append('rejected '+name)
  executables={};entry=ROOT/'examples/exported-enums/main.aw'
  for mode in ['native','sanitized']:
   exe=td/mode;r=run([str(kcc),'build' if mode=='native' else 'emit-c',str(entry),'--syntax','next',*(['-o',str(exe)] if mode=='native' else [])]);assert r.returncode==0,r.stderr
   if mode=='sanitized':
    c=td/'config.c';c.write_bytes(r.stdout);r=run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)]);assert r.returncode==0,r.stderr
   executables[mode]=exe
  rng=random.Random(1927);fixtures=[]
  for i in range(60):
   host=rng.choice(['localhost','café.example','127.0.0.1','dev.example']);port=rng.randrange(1,65536);debug=bool(rng.randrange(2));fixtures.append((json.dumps({'host':host,'port':port,'debug':debug},ensure_ascii=False).encode(),0,f'{host}\n{port}\n{str(debug).lower()}\n'.encode()))
  for field,values in [('host',['',' ',None,3,'x\n','x'*254]),('port',[0,-1,65536,8080.0,'8080',True,None]),('debug',[0,'true',None])]:
   for value in values:
    data={'host':'localhost','port':8080,'debug':False};data[field]=value;fixtures.append((json.dumps(data).encode(),5,f'schema\n{field}\n'.encode()))
  fixtures += [(b'{',4,b'json\n1\n'),(b'[]',5,b'schema\nhost\n'),(b'{"host":"x","port":1,"debug":false,"extra":0}',5,b'schema\nkeys\n'),(b'x'*16385,3,b'limit\n16385\n'),(b'\xff',3,b'io\n-5\n')]
  config=td/'settings.json'
  for mode,exe in executables.items():
   for i,(data,code,want) in enumerate(fixtures):
    config.write_bytes(data);r=run([str(exe),str(config)]);assert (r.returncode,r.stdout,r.stderr)==(code,want,b''),(mode,i,r.returncode,r.stdout,r.stderr);records.append(mode+' config '+str(i))
   config.unlink();r=run([str(exe),str(config)]);assert (r.returncode,r.stdout,r.stderr)==(3,b'missing\n',b'');records.append(mode+' missing file typed issue')
 result={'status':'PASS','cases':len(records),'records':records,'compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'compiler/native/kparse.cpp',ROOT/'compiler/native/kproject.inc',ROOT/'compiler/native/kverify.inc',Path(__file__).resolve(),*sorted((ROOT/'examples/exported-enums').rglob('*.aw'))]},'qualification':'candidate Linux compiler with complete existing SDK backend, strict generated-C ASan/UBSan, exported nonrecursive scalar/text/enum payloads only, not a new published SDK or capability stage'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'exported-enum and real configuration checks')
if __name__=='__main__':main()

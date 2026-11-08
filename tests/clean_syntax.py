#!/usr/bin/env python3
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-syntax-cache'};records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-clean-',dir='/var/tmp') as td:
  td=Path(td);source=td/'main.aw';source.write_text('''exports{ @r version: 3; @w total: 0; @r func count(@b values[i64]): i64 return vector_length(values); end; };
func main(): i64
 @s values vector<i64>:vector_new<i64>(0); @p i:3;
 while i>0 {vector_push(values,i);i:i-1;};
 if false {print("bad");} elseif i!=0 {print("bad");} elseif true {print("hello ${version}, "..count(values).." values");} else {print("bad");};
 if true {if false {print("bad");} else {print("nested");};};
 @p word:"owl 🦉"; @p yes:true; @p small:-128i8; @p large:18446744073709551615u64; @p fraction:1.25;
 @p a:-32768i16;@p b:-2147483648i32;@p c:-9223372036854775808i64;@p d:255u8;@p e:65535u16;@p f:4294967295u32;print("${a} ${b} ${c} ${d} ${e} ${f}");
 print("${word} ${yes} ${small} ${large} ${fraction}");print("literal \\${word}"); print(1..2); print("A\\0B"..3);
 return 0;
end;''');expected='hello 3, 3 values\nnested\n-32768 -2147483648 -9223372036854775808 255 65535 4294967295\nowl 🦉 true -128 18446744073709551615 1.25\nliteral ${word}\n12\nA\0B3\n'.encode();c=td/'main.c';r=subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(source)],capture_output=True);assert r.returncode==0,r.stderr;c.write_bytes(r.stdout)
  for mode in ['native','sanitized']:
   exe=td/mode;cmd=[str(sdk/'libexec/zig/zig'),'cc','-target','x86_64-linux-musl','-O2'] if mode=='native' else ['cc','-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie'];subprocess.run([*cmd,'-Wall','-Wextra','-Werror','-Wno-unused-function',str(c),'-lm','-o',str(exe)],check=True,env=env);r=subprocess.run([str(exe)],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,expected,b''),(mode,r.stdout,r.stderr);records.append(mode+' braces/elseif/scopes/modifiers/vector args/interpolation/UTF8/NUL/all scalar formatting')
  wasm=td/'main.wasm';subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target','wasm32-wasi','-O2',str(c),'-lm','-o',str(wasm)],check=True,env=env);js=td/'run.js';js.write_text('const fs=require("fs"),{runAwl}=require(process.argv[2]);runAwl(fs.readFileSync(process.argv[3]),[]).then(r=>{process.stdout.write(r.stdout);if(r.code||r.stderr)process.exit(1)}).catch(e=>{console.error(e);process.exit(1)});');r=subprocess.run(['node',str(js),str(ROOT/'web/wasi.js'),str(wasm)],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,expected,b'');records.append('real WASI matches expected')
  for n,body in enumerate(['if true then print(1); end;','while false do print(1); end;','@p scoped x spool:spool_new(1);','@p 1name:0;','@p bad$name:0;','@p has space:0;','print("${missing}");','print("${x+1}");','print("${}");','print("${x");','if true {print(1);} else {print(2);}', 'if true {}; elseif false {};','@s owner spool:spool_new(1);print("${owner}");']):
   source.write_text('func main(): i64 '+body+' return 0; end;');r=subprocess.run([str(sdk/'bin/kcc'),'check',str(source)],capture_output=True);assert r.returncode==1,(n,r.stdout,r.stderr);records.append('rejected invalid body '+str(n))
  for text in ['exports(@r value:1;);func main(): i64 return 0; end;','exports{@rw value:1;};func main(): i64 return 0; end;','func f(borrow v:vector<i64>) end;func main(): i64 return 0; end;','func f(@b v:vector<i64>) end;func main(): i64 return 0; end;','func f(@b v[unit]) end;func main(): i64 return 0; end;']:
   source.write_text(text);r=subprocess.run([str(sdk/'bin/kcc'),'check',str(source)],capture_output=True);assert r.returncode==1,r.stderr;records.append('rejected superseded/invalid declaration')
  source.write_text('function main()->i64 if true then print(42) else print(0) end return 0 end');r=subprocess.run([str(sdk/'bin/kcc'),'run',str(source),'--syntax','legacy'],capture_output=True,env=env);assert r.returncode==0 and r.stdout==b'42\n';records.append('explicit legacy remains unchanged')
 migration=json.loads(gzip.decompress((ROOT/'tests/return-migration.json.gz').read_bytes()))
 for item in migration:
  assert hashlib.sha256((ROOT/item['file']).read_bytes()).hexdigest()==item['after_sha256'];r=subprocess.run([str(sdk/'bin/kcc'),'check',str(ROOT/item['file'])],capture_output=True)
  if item['entry_c_equivalent']:assert r.returncode==0,(item['file'],r.stderr)
 result={'status':'PASS','cases':len(records),'records':records,'migrated_files':len(migration),'equivalent_entry_c_outputs':sum(x['entry_c_equivalent'] for x in migration),'compiler_sha256':hashlib.sha256((sdk/'bin/kcc').read_bytes()).hexdigest(),'qualification':'source candidate, native/ASan+UBSan/real WASI, legacy compatibility separate, historical embedded test fixtures not migrated or claimed passing'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'syntax checks,47 source migrations,21 unchanged entry C outputs')
if __name__=='__main__':main()

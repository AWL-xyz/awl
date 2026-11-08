#!/usr/bin/env python3
import argparse,hashlib,json,os,random,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-export-cache'};entry=ROOT/'examples-next/exported-enums/web.aw';cases=[];rng=random.Random(711)
 for i in range(96):
  host=rng.choice(['localhost','café.example','日本語.example','dev.example']);port=rng.randrange(1,65536);debug=bool(rng.randrange(2));source=json.dumps({'host':host,'port':port,'debug':debug},ensure_ascii=False);cases.append((source,0,f'{host}\n{port}\n{str(debug).lower()}\n'))
 for field,value in [('host',''),('host',42),('host','a\n'),('port',-1),('port',65536),('port',80.0),('debug',0),('debug','false')]:
  data={'host':'x','port':80,'debug':True};data[field]=value;cases.append((json.dumps(data),5,'schema\n'+field+'\n'))
 cases.extend([('[]',5,'schema\nhost\n'),('{',4,'json\n1\n'),('{"host":"x","port":1,"debug":true,"host":"y"}',5,'schema\nhost\n')])
 with tempfile.TemporaryDirectory(prefix='Awl-export-wasm-',dir='/var/tmp') as td:
  td=Path(td);c=td/'main.c';c.write_bytes(subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(entry),'--syntax','next'],capture_output=True,check=True,env=env).stdout);native=td/'native';wasm=td/'main.wasm'
  for target,out,extra in [('x86_64-linux-musl',native,[]),('wasm32-wasi',wasm,['-Wl,--max-memory=67108864'])]:subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target',target,'-Os','-Wall','-Wextra','-Werror','-Wno-unused-function',str(c),'-lm',*extra,'-o',str(out)],check=True,env=env)
  for source,code,want in cases:
   r=subprocess.run([str(native),source],capture_output=True,text=True,check=False);assert (r.returncode,r.stdout,r.stderr)==(code,want,''),(source,r.stdout,r.stderr)
  data=td/'cases.json';data.write_text(json.dumps(cases));js=td/'check.js';js.write_text('const fs=require("fs"),{runAwl}=require(process.argv[2]);(async()=>{const b=fs.readFileSync(process.argv[3]),a=JSON.parse(fs.readFileSync(process.argv[4]));for(let i=0;i<a.length;i++){const [s,code,out]=a[i],r=await runAwl(b,[s]);if(r.code!==code||r.stdout!==out||r.stderr!=="")throw Error("case "+i+JSON.stringify(r))}console.log(a.length)})().catch(e=>{console.error(e);process.exit(1)});');r=subprocess.run(['node',str(js),str(ROOT/'web/wasi.js'),str(wasm),str(data)],capture_output=True,text=True,timeout=60);assert r.returncode==0,(r.stdout,r.stderr)
  result={'status':'PASS','native_cases':len(cases),'wasm_cases':len(cases),'compiler_sha256':hashlib.sha256((sdk/'bin/kcc').read_bytes()).hexdigest(),'entry_sha256':hashlib.sha256(entry.read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(c.read_bytes()).hexdigest(),'wasm_sha256':hashlib.sha256(wasm.read_bytes()).hexdigest(),'wasm_bytes':wasm.stat().st_size,'qualification':'cross-module exported nested results executed natively and on real WASI using independent expected outputs, contributor build only, no browser DOM or published target claim'}
 a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(cases),'native and WASI exported-result cases')
if __name__=='__main__':main()

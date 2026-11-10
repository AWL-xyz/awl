#!/usr/bin/env python3
import argparse,ast,hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-slots-wasm-cache'};tree=ast.parse((ROOT/'tests/vector_ops.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');types=next(ast.literal_eval(n.value) for n in function.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='types' for t in n.targets));records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-slots-wasm-',dir='/var/tmp') as td:
  work=Path(td);runner=work/'run.cjs';runner.write_text("const fs=require('fs'),{runAwl}=require("+json.dumps(str(ROOT/'web/wasi.js'))+");runAwl(fs.readFileSync(process.argv[2]),[]).then(r=>console.log(JSON.stringify(r))).catch(e=>{console.error(e);process.exit(1)})")
  def run(c,want):
   wasm=work/'app.wasm';subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target','wasm32-wasi','-Os','-UNDEBUG','-Wl,--max-memory=67108864',str(c),'-lm','-o',str(wasm)],check=True,env=env,capture_output=True,timeout=180);r=subprocess.run(['node',str(runner),str(wasm)],capture_output=True,text=True,check=True,timeout=30);r=json.loads(r.stdout);assert r['code']==0 and r['stdout']==want and r['stderr']=='' and r['memoryBytes']<=67108864,r
  for ty,x,y,first,second in types:
   src=work/'main.aw';src.write_text('func main()->i64 @p scoped v vector<'+ty+'>: vector.new<'+ty+'>(4); vector.push(v,'+x+'); vector.push(v,'+y+'); vector.swap(v,0,1); print(vector.get(v,0)); print(vector.get(v,1)); vector.set(v,1,'+y+'); print(vector.truncate(v,1)); print(vector.capacity(v)); print(vector.truncate(v,2)); return 0; end;');r=subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(src),'--syntax','next'],capture_output=True,text=True,check=True,env=env);c=work/'main.c';c.write_text(r.stdout);run(c,second+'\n'+first+'\ntrue\n4\nfalse\n');records.append(ty)
  run(ROOT/'tests/vector_slots.c','PASS 440078 slot identity/kind/stale/churn/allocation/exhaustion assertions\n');records.append('440078 runtime assertions')
 result={'status':'PASS','compiler_sha256':hashlib.sha256((sdk/'bin/kcc').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':len(records),'records':records,'qualification':'current compiler typed vector operations and C runtime oracle executed as WASI in Node, standalone browser workbench has separate fresh acceptance, general JS editor is still a limited non-native subset'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'WASI vector/runtime cases')
if __name__=='__main__':main()

#!/usr/bin/env python3
import argparse,hashlib,json,os,random,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-view-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'};cases=[];want=[];functions=[];names=[]
 types=[(t,'11'+t,'22'+t,'11','22') for t in ['i8','i16','i32','i64','u8','u16','u32','u64']]+[('f64','1.25','2.5','1.25','2.5'),('bool','true','false','true','false'),('text','"café 🦉"','"日本語"','café 🦉','日本語')]
 for t,x,y,sx,sy in types:
  name='test_'+t;names.append(name);functions.append(f'''func read_{t}(value:view<{t}>)->{t} return view.get(value,0); end;
func {name}()->i64
 @p scoped v vector<{t}>: vector.new<{t}>(2);
 if not vector.valid(v) then return 9; end;
 vector.push(v,{x}); vector.push(v,{y});
 @p w: vector.view(v,0,2); @p sub: view.slice(w,1,1); @p alias: sub;
 print(view.length(w)); print(read_{t}(alias)); vector.set(v,1,{x}); print(view.get(sub,0));
 vector.set(v,0,{y}); vector.swap(v,0,1); print(view.get(sub,0));
 vector.reserve(v,2); vector.truncate(v,2); print(view.valid(w));
 print(vector.reserve(v,1048577)); print(view.valid(w));
 vector.reserve(v,3); print(view.valid(w));
 @p push: vector.view(v,0,2); vector.push(v,{x}); print(view.valid(push));
 @p remove: vector.view(v,0,3); vector.remove(v,0); print(view.valid(remove));
 @p pop: vector.view(v,0,2); vector.pop(v); print(view.valid(pop));
 @p insert: vector.view(v,0,1); vector.insert(v,1,{x}); print(view.valid(insert));
 @p truncate: vector.view(v,0,2); vector.truncate(v,1); print(view.valid(truncate));
 @p clear: vector.view(v,0,1); vector.clear(v); print(view.valid(clear));
 @p empty: vector.view(v,0,0); vector.clear(v); vector.truncate(v,0); print(view.valid(empty)); print(view.length(view.slice(empty,0,0)));
 return 0;
end;''');want+=['2',sy,sx,sy,'true','false','true','false','false','false','false','false','false','false','true','0']
 # Model a live descriptor separately from content: structural changes invalidate all existing descriptors
 rng=random.Random(604);body=['@p scoped v vector<i64>: vector.new<i64>(0);'];data=[];capacity=0;views=[]
 for n in range(400):
  op=rng.choice(['view','push','set','reserve','pop','truncate','clear'])
  changed=False
  if op=='view':
   start=rng.randrange(len(data)+1);count=rng.randrange(len(data)-start+1);name='w'+str(n);body.append(f'@p {name}: vector.view(v,{start},{count});');views.append([name,start,count,True])
  elif op=='push':
   value=rng.randrange(-200,201);body.append(f'vector.push(v,{value});');data.append(value);changed=True
   if len(data)>capacity:capacity=max(8,capacity*2)
  elif op=='set' and data:
   index=rng.randrange(len(data));value=rng.randrange(-200,201);body.append(f'vector.set(v,{index},{value});');data[index]=value
  elif op=='reserve':
   target=rng.randrange(33);body.append(f'vector.reserve(v,{target});');changed=target>capacity;capacity=max(capacity,target)
  elif op=='pop' and data:body.append('vector.pop(v);');data.pop();changed=True
  elif op=='truncate':
   target=rng.randrange(len(data)+1);body.append(f'vector.truncate(v,{target});');changed=target!=len(data);data=data[:target]
  elif op=='clear':body.append('vector.clear(v);');changed=bool(data);data=[]
  if changed:
   for view in views:view[3]=False
  for name,start,count,valid in views[-2:]:
   body.append(f'print(view.valid({name}));');want.append(str(valid).lower())
   if valid and count:body.append(f'print(view.get({name},0));');want.append(str(data[start]))
 functions.append('func model()->i64 '+' '.join(body)+' return 0; end;');names.append('model')
 # The returned descriptor doesn't retain a destroyed scoped owner
 functions.append('func escaped()->view<i64> @p scoped v vector<i64>: vector.new<i64>(1); vector.push(v,7); return vector.view(v,0,1); end;');functions.append('func escape_test()->i64 @p v: escaped(); print(view.valid(v)); return 0; end;');names.append('escape_test');want.append('false')
 functions.append('func borrow_window(borrow value:vector<i64>)->view<i64> return vector.view(value,0,1); end; func transfer(own value:vector<i64>)->own vector<i64> return move value; end; func consume(own value:vector<i64>) end; func move_test()->i64 @p scoped original vector<i64>: vector.new<i64>(1); vector.push(original,42); @p part: borrow_window(original); @p boxes [view<i64>;2]: [part,part]; @p scoped moved vector<i64>: transfer(move original); print(view.valid(boxes[0])); print(view.get(boxes[1],0)); consume(move moved); print(view.valid(part)); return 0; end;');names.append('move_test');want+=['true','42','false']
 source='\n'.join(functions)+'\nfunc main()->i64 '+' '.join(n+'();' for n in names)+' return 0; end;';expected=('\n'.join(want)+'\n').encode()
 with tempfile.TemporaryDirectory(prefix='Awl-view-test-',dir='/var/tmp') as td:
  td=Path(td);src=td/'main.aw';src.write_text(source);c=td/'main.c';r=subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(src)],capture_output=True,env=env);assert r.returncode==0,r.stderr;c.write_bytes(r.stdout)
  for mode in ['native','sanitized']:
   exe=td/mode;cmd=[str(sdk/'libexec/zig/zig'),'cc','-target','x86_64-linux-musl','-Os'] if mode=='native' else ['cc','-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie'];subprocess.run([*cmd,'-Wall','-Wextra','-Werror','-Wno-unused-function',str(c),'-lm','-o',str(exe)],env=env,check=True);r=subprocess.run([str(exe)],capture_output=True,env=env);assert (r.returncode,r.stdout,r.stderr)==(0,expected,b''),(mode,r.returncode,r.stdout[-200:],r.stderr);cases.append(mode+' 11 element types, live content, invalidation, escaped owner and400step independent model')
  wasm=td/'app.wasm';subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target','wasm32-wasi','-Os',str(c),'-lm','-Wl,--max-memory=67108864','-o',str(wasm)],env=env,check=True);js=td/'run.js';js.write_text('const fs=require("fs"),{runAwl}=require(process.argv[2]);runAwl(fs.readFileSync(process.argv[3]),[]).then(r=>{process.stdout.write(r.stdout);if(r.code||r.stderr)process.exit(1)}).catch(e=>{console.error(e);process.exit(1)});');r=subprocess.run(['node',str(js),str(ROOT/'web/wasi.js'),str(wasm)],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,expected,b''),(r.returncode,r.stdout[-100:],r.stderr);cases.append('real WASI matches independent expected output')
  negatives=['func bad(v:view<vector<i64>>)->i64 return 0; end;','func bad(v:view<unit>)->i64 return 0; end;','func bad(v:view<i64>)->i64 view_set(v,0,1); return 0; end;','func bad(v:vector<i64>)->i64 print(view.length(v)); return 0; end;','func bad(v:view<i64>)->i64 print(vector.length(v)); return 0; end;','func bad(v:view<i64>)->i64 print(view.get(v,true)); return 0; end;','func bad(v:view<i64>)->i64 print(view.get(v)); return 0; end;','func bad(v:view<i64>)->text return view.get(v,0); end;','func bad(borrow v:view<i64>)->i64 return 0; end;','func bad(own v:view<i64>)->i64 return 0; end;','enum E V(v:view<i64>); end;','func view.get()->i64 return 0; end;','func view()->i64 return 0; end;']
  for n,bad in enumerate(negatives):
   src.write_text(bad+' func main()->i64 return 0; end;');r=subprocess.run([str(sdk/'bin/kcc'),'check',str(src)],capture_output=True);assert r.returncode==1 and b'error[' in r.stderr,(n,r.stderr);cases.append('rejected invalid view program '+str(n))
  trap_ops=['@p w: vector.view(v,-1,0);','@p w: vector.view(v,0,-1);','@p w: vector.view(v,2,0);','@p w: vector.view(v,0,2);','@p w: vector.view(v,0,1); print(view.get(w,-1));','@p w: vector.view(v,0,1); print(view.get(w,1));','@p w: vector.view(v,0,1); vector.push(v,2); print(view.get(w,0));','@p w: vector.view(v,0,1); vector.clear(v); print(view.length(w));','@p w: vector.view(v,0,1); print(view.length(view.slice(w,1,1)));','@p w: vector.view(v,0,1); print(view.length(view.slice(w,0,9223372036854775807)));']
  trap_ops.append('@p w:escaped(); print(view.length(w));')
  trap_js=td/'trap.js';trap_js.write_text('const fs=require("fs"),{runAwl}=require(process.argv[2]);runAwl(fs.readFileSync(process.argv[3]),[]).then(()=>process.exit(2)).catch(e=>{if(e instanceof WebAssembly.RuntimeError){console.log("checked trap")}else{console.error(e);process.exit(3)}});')
  for n,op in enumerate(trap_ops):
   src.write_text('func escaped()->view<i64> @p scoped owner vector<i64>: vector.new<i64>(1); vector.push(owner,42); return vector.view(owner,0,1); end; func main()->i64 @p scoped v vector<i64>: vector.new<i64>(3); vector.push(v,1); '+op+' return 0; end;');r=subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(src)],capture_output=True);assert r.returncode==0,r.stderr;c.write_bytes(r.stdout);exe=td/'trap';subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)],check=True);r=subprocess.run([str(exe)],capture_output=True,env=env);assert r.returncode!=0 and b'Awl vector trap' in r.stderr and b'AddressSanitizer' not in r.stderr,(n,r.returncode,r.stderr);cases.append('sanitized range/stale trap '+str(n))
   if n in [5,6,7,10]:
    subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target','wasm32-wasi','-Os',str(c),'-lm','-o',str(wasm)],env=env,check=True);r=subprocess.run(['node',str(trap_js),str(ROOT/'web/wasi.js'),str(wasm)],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,b'checked trap\n',b''),(n,r.returncode,r.stdout,r.stderr);cases.append('real WASI checked range/stale trap '+str(n))
 result={'status':'PASS','cases':len(cases),'records':cases,'oracle_output_lines_per_runtime':len(want),'random_model_steps':400,'compiler_sha256':hashlib.sha256((sdk/'bin/kcc').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'qualification':'candidate source compiler, 11 scalar/text types on Linux native/ASan+UBSan/real WASI, runtime-checked descriptors not static lifetimes or concurrency'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(cases),'view checks,',len(want),'oracle lines each native/sanitized/WASI')
if __name__=='__main__':main()

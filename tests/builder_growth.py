#!/usr/bin/env python3
import argparse,json,hashlib,os,random,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',required=True,type=Path);p.add_argument('--report',required=True,type=Path);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-polish-cache'};rng=random.Random(217);text='';capacity=0;body=[];chunks=[];expected=[]
 def emit(code,value):body.append('print('+code+');');expected.append(str(value).lower() if isinstance(value,bool) else str(value))
 for step in range(500):
  action=rng.choice(['append','reserve','truncate','snapshot'])
  if action=='reserve':
   target=rng.choice([-1,0,8,64,256,1024,16777217]);ok=0<=target<=16777216;body.append(f'@p r{step}:text_builder_reserve(b,{target});');emit('r'+str(step),ok)
   if ok:capacity=max(capacity,target)
  elif action=='truncate':
   target=rng.randrange(-1,len(text)+3);ok=0<=target<=len(text);emit(f'text_builder_truncate(b,{target})',ok)
   if ok:text=text[:target]
  elif action=='append':
   value=rng.choice(['a','é','日本','🦉','é','\x00']);literal=json.dumps(value,ensure_ascii=False).replace('\\u0000','\\0');ok=len((text+value).encode())<=capacity;emit('text_builder_append(b,'+literal+')',0 if ok else 1)
   if ok:text+=value
  else:emit('text_builder_snapshot(b)',text)
  emit('text_builder_bytes(b)',len(text.encode()));emit('text_builder_length(b)',len(text));emit('text_builder_capacity(b)',capacity)
  if step%50==49:chunks.append('func part'+str(len(chunks))+'(@b b:text_builder) '+' '.join(body)+' end;');body=[]
 source=' '.join(chunks)+' func main(): i64 @s b text_builder:text_builder_new(0); '+''.join('part'+str(i)+'(b);' for i in range(len(chunks)))+' return 0; end;';want=('\n'.join(expected)+'\n').encode();records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-grow-',dir='/var/tmp') as td:
  td=Path(td);src=td/'main.aw';src.write_text(source);c=td/'main.c';r=subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(src)],capture_output=True);assert r.returncode==0,r.stderr;c.write_bytes(r.stdout)
  for mode in ['native','sanitized']:
   exe=td/mode;cmd=[str(sdk/'libexec/zig/zig'),'cc','-target','x86_64-linux-musl','-O2'] if mode=='native' else ['cc','-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie'];subprocess.run([*cmd,'-Wall','-Wextra','-Werror','-Wno-unused-function',str(c),'-lm','-o',str(exe)],check=True,env=env);r=subprocess.run([str(exe)],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,want,b''),(mode,r.returncode,r.stderr);records.append(mode+' 500step independent Unicode model')
  wasm=td/'model.wasm';subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target','wasm32-wasi','-O2',str(c),'-lm','-o',str(wasm)],check=True,env=env);js=td/'run.js';js.write_text('const fs=require("fs"),{runAwl}=require(process.argv[2]);runAwl(fs.readFileSync(process.argv[3]),[]).then(r=>{process.stdout.write(r.stdout);if(r.code||r.stderr)process.exit(1)}).catch(e=>{console.error(e);process.exit(1)});');r=subprocess.run(['node',str(js),str(ROOT/'web/wasi.js'),str(wasm)],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,want,b'');records.append('real WASI500step model')
 result={'status':'PASS','steps':500,'oracle_lines_per_runtime':len(expected),'records':records,'compiler_sha256':hashlib.sha256((sdk/'bin/kcc').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'qualification':'explicit growth, scalar-index truncation, failed/no-op preservation, UTF8/NUL/combining marks, not grapheme editing/concurrency/reclaimable immutable strings'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS500step model',len(expected),'oracle lines each native/sanitized/WASI')
if __name__=='__main__':main()

#!/usr/bin/env python3
import argparse,hashlib,json,os,random,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();kcc=a.kcc.resolve();rng=random.Random(932);oracle={};body=[];expected=[]
for i in range(600):
 key=str(rng.randrange(100))
 if rng.randrange(3)==0:
  body.append('print(map.remove(pairs,"'+key+'"));');expected.append(str(key in oracle).lower());oracle.pop(key,None)
 else:
  value=str(rng.randrange(999999));oracle[key]=value;body.append('print(map.put(pairs,"'+key+'","'+value+'"));');expected.append('true')
body.append('@p i: 0; while i<vector.length(pairs) do print(vector.get(pairs,i)); i: i+1; end;')
for key,value in sorted(oracle.items()):expected.extend([key,value])
body.extend(['print(map.find(pairs,"absent"));','vector.push(pairs,"odd");','print(map.find(pairs,"x"));','print(map.put(pairs,"x","v"));','print(map.remove(pairs,"x"));','@p scoped output vector<text>: vector.new<text>(0);','@p scoped builder spool: spool.new(2048);','i: 0; while i<32 do spool.codepoint(builder,u32(i)); i: i+1; end;','spool.append(builder,"é😀\\\"\\\\");','print(json.quote(spool.snapshot(builder),output));','print(vector.get(output,0));','spool.clear(builder);','i: 0; while i<1025 do spool.append(builder,"x"); i: i+1; end;','print(json.quote(spool.snapshot(builder),output));','print(vector.length(output));','@p b: buffer_new(1); defer buffer_free(b);','print(journal.load("unused",b,output));','print(journal.append("unused",1,1,"k","v",b));'])
expected.extend(['-1','-2','false','false','true',json.dumps(''.join(chr(i) for i in range(32))+'é😀"\\',ensure_ascii=False,separators=(',',':')),'false','1','-5','false'])
# Compare JSON semantically because control escape spellings are intentionally uniform.
records=[]
with tempfile.TemporaryDirectory(prefix='Awl-kv-helpers-',dir='/var/tmp') as td:
 folder=Path(td)
 for name in ['TextMap.aw','Json.aw','Journal.aw']:shutil.copyfile(ROOT/'examples-next/apps/kvserve'/name,folder/name)
 src=folder/'main.aw';src.write_text('use TextMap.aw as map; use Json.aw as json; use Journal.aw as journal; func main()->i64 @p scoped pairs vector<text>: vector.new<text>(0); '+' '.join(body)+' return 0; end;')
 for mode in ['bundled','sanitized']:
  exe=folder/mode;command='build' if mode=='bundled' else 'emit-c';r=subprocess.run([str(kcc),command,str(src),'--syntax','next']+(['-o',str(exe)] if mode=='bundled' else []),capture_output=True,text=True,env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-kv-cache'},timeout=120);assert r.returncode==0,r.stderr
  if mode=='sanitized':
   c=folder/'main.c';c.write_text(r.stdout);subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)],check=True,timeout=90)
  r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10);assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr);actual=r.stdout.splitlines();assert len(actual)==len(expected),(len(actual),len(expected))
  for i,(got,want) in enumerate(zip(actual,expected)):
   if i==len(expected)-5:assert json.loads(got)==json.loads(want),(i,got,want)
   else:assert got==want,(i,got,want)
  records.append({'mode':mode,'assertions':len(expected),'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()})
a.report.write_text(json.dumps({'status':'PASS','records':records},separators=(',',':'))+'\n');print('PASS',records)

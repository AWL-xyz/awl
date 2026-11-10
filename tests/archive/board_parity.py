#!/usr/bin/env python3
import hashlib,json,os,random,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];native=Path(sys.argv[1]).resolve();wasm=Path(sys.argv[2]).resolve();report=Path(sys.argv[3]);cases=[];rng=random.Random(821)
for n in range(64):
 tasks=[{'id':i+1,'title':rng.choice(['Ship the OWL 🦉','café noir','日本語','a literal <tag>','task " \\']),'note':rng.choice(['notes\nwith tabs\t','MORE Detail','日本語','']),'status':rng.choice(['todo','doing','done'])} for i in range(rng.randrange(33))];state={'version':1,'revision':n,'next_id':len(tasks)+1,'tasks':tasks};query=rng.choice(['','OWL','detail','日本','CAFÉ','café','<tag>','missing']);filt=rng.choice(['all','todo','doing','done']);expected=[t['id'] for t in tasks if (filt=='all' or filt==t['status']) and any(query.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')) in t[k].translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')) for k in ['title','note'])];cases.append(([json.dumps(state,ensure_ascii=False),query,filt],0,''.join(str(i)+'\n' for i in expected)))
base={'version':1,'revision':0,'next_id':1,'tasks':[]}
for bad in [{},[],{**base,'version':2},{**base,'revision':-1},{**base,'revision':1.0},{**base,'next_id':0},{**base,'extra':1},{**base,'tasks':[{'id':1,'title':'x','note':'','status':'todo'}]},{**base,'tasks':{}},{**base,'tasks':[None]}]:cases.append(([json.dumps(bad),'','all'],4,''))
for source in ['{','{"version":1,"version":1,"revision":0,"next_id":1,"tasks":[]}',' '*65537]:cases.append(([source,'','all'],4,''))
for query,filt in [('x'*161,'all'),('','bogus')]:cases.append(([json.dumps(base),query,filt],2,''))
worst={**base,'revision':32,'next_id':33,'tasks':[{'id':i,'title':'"'*160,'note':'\n'*256,'status':'doing'} for i in range(1,33)]};source=json.dumps(worst).replace('\\n','\\u000a');cases.append(([source,'','all'],0,''.join(str(i)+'\n' for i in range(1,33))))
# WASI host intentionally caps argv at64KiB, the one oversize parser-input probe is native-only
browser_cases=[]
for args,code,out in cases:
 r=subprocess.run([str(native),*args],capture_output=True,text=True,timeout=5);assert (r.returncode,r.stdout,r.stderr)==(code,out,''),(args[:1],r.returncode,r.stdout,r.stderr)
 if sum(len(s.encode())+1 for s in ['Awl',*args])<=65536:browser_cases.append((args,code,out))
with tempfile.TemporaryDirectory(prefix='Awl-board-parity-',dir='/var/tmp') as td:
 td=Path(td);data=td/'cases.json';data.write_text(json.dumps(browser_cases));js=td/'check.js';js.write_text('const fs=require("fs"),{runAwl}=require(process.argv[2]);(async()=>{const bytes=fs.readFileSync(process.argv[3]),cases=JSON.parse(fs.readFileSync(process.argv[4]));for(let i=0;i<cases.length;i++){const [args,code,out]=cases[i],r=await runAwl(bytes,args);if(r.code!==code||r.stdout!==out||r.stderr!=="")throw Error("case "+i+JSON.stringify(r))}console.log(cases.length)})().catch(e=>{console.error(e);process.exit(1)});');r=subprocess.run(['node',str(js),str(ROOT/'web/wasi.js'),str(wasm),str(data)],capture_output=True,text=True,timeout=60);assert r.returncode==0,(r.stdout,r.stderr)
result={'status':'PASS','native_cases':len(cases),'wasm_cases':len(browser_cases),'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),'wasm_sha256':hashlib.sha256(wasm.read_bytes()).hexdigest(),'qualification':'same Awl schema/filter source, independent ASCII-fold/status oracle, native and real WASI execution, Unicode is exact outside ASCII, no JS business-rule replacement'};report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(cases),'native /',len(browser_cases),'WASM parity cases')

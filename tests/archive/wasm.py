#!/usr/bin/env python3
import argparse,hashlib,importlib.util,json,os,random,statistics,subprocess,sys,tempfile,textwrap,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--wasm',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--playwright',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.playwright));from playwright.sync_api import sync_playwright
 spec=importlib.util.spec_from_file_location('json_oracle',ROOT/'tests/json_parser.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);source=(ROOT/'tests/json_parser.py').read_text();context={'rng':random.Random(8259),'json':json};exec(textwrap.dedent(source[source.index(' def tree'):source.index(' counts={}')]),context);cases=[]
 for s in context['corpus']:
  if '\0' in s:continue
  try:values,metadata=mod.oracle(s);want=(0,'ok\n'+str(metadata[2])+'\n'+str(len(values))+'\n'+values[0]+'\n')
  except (ValueError,AssertionError,IndexError,UnicodeError,OverflowError):want=None
  cases.append((s,'',want))
 for s,pointer,index in context['pointer_cases']:
  values,metadata=mod.oracle(s);want=(5,'selection\n'+str(index)+'\n') if index<0 else (0,'ok\n'+str(metadata[2+index*2])+'\n'+str(len(values))+'\n'+values[index]+'\n');cases.append((s,pointer,want))
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-wasm-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'};records={};timing=[]
 with tempfile.TemporaryDirectory(prefix='Awl-wasm-tests-',dir='/var/tmp') as td:
  work=Path(td);native=work/'native';kcc=a.sdk.resolve()/'bin/kcc';subprocess.run([str(kcc),'build',str(ROOT/'examples/parsing/web.aw'),'--syntax','next','-o',str(native)],check=True,env=env,capture_output=True);expected=[]
  for s,pointer,want in cases:
   r=subprocess.run([str(native),s,pointer],capture_output=True,env=env,timeout=5);r.stdout=r.stdout.decode();r.stderr=r.stderr.decode();assert not r.stderr
   if want:assert (r.returncode,r.stdout)==want,(s[:80],pointer,want,r.returncode,r.stdout)
   else:
    parts=r.stdout.splitlines();assert r.returncode==4 and parts[0]=='parse' and int(parts[1]) in [1,2,3] and 0<=int(parts[2])<=len(s.encode()),(s[:80],r.returncode,r.stdout)
   expected.append({'code':r.returncode,'stdout':r.stdout,'stderr':''})
  data=work/'cases.json';data.write_text(json.dumps([[s,p] for s,p,w in cases]));js=work/'node.cjs';js.write_text("const fs=require('fs'),{runAwl}=require("+json.dumps(str(ROOT/'web/wasi.js'))+");(async()=>{const bytes=fs.readFileSync(process.argv[2]),out=[];for(const args of JSON.parse(fs.readFileSync(process.argv[3])))out.push(await runAwl(bytes,args));console.log(JSON.stringify(out))})().catch(e=>{console.error(e);process.exit(1)})");r=subprocess.run(['node',str(js),str(a.wasm),str(data)],capture_output=True,text=True,check=True,timeout=120);actual=json.loads(r.stdout)
  for got,want in zip(actual,expected,strict=True):assert {k:got[k] for k in want}==want;assert got['memoryBytes']<=67108864
  records['native_json_oracle_cases']=len(cases);records['node_wasm_equivalence_cases']=len(actual)
  minimum=-(1<<63);maximum=(1<<63)-1;values=[minimum,minimum+1,-3,-1,0,1,2,maximum-1,maximum];rng=random.Random(428);inputs=[(op,x,y) for op in ['+','-','*','/'] for x in values for y in values]+[(rng.choice(['+','-','*','/']),rng.randrange(minimum,maximum+1),rng.randrange(minimum,maximum+1)) for _ in range(120)];wanted=[]
  for op,x,y in inputs:
   if op=='/' and y==0:code=4;out='division by zero'
   else:
    value=x+y if op=='+' else x-y if op=='-' else x*y if op=='*' else (abs(x)//abs(y))*(-1 if (x<0)!=(y<0) else 1);code=0 if minimum<=value<=maximum else 4;out=str(value) if code==0 else 'arithmetic overflow'
   wanted.append({'code':code,'stdout':out+'\n','stderr':''})
  calc=work/'calc.wasm';build=work/'calc.json';subprocess.run([sys.executable,str(ROOT/'web/build.py'),'--sdk',str(a.sdk),'--entry',str(ROOT/'examples/enums/main.aw'),'--output',str(work/'calc.html'),'--wasm',str(calc),'--report',str(build)],check=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True);data.write_text(json.dumps([[op,str(x),str(y)] for op,x,y in inputs]));r=subprocess.run(['node',str(js),str(calc),str(data)],capture_output=True,text=True,check=True,timeout=120)
  for got,want in zip(json.loads(r.stdout),wanted,strict=True):assert {k:got[k] for k in want}==want
  records['wasm_i64_enum_oracle_cases']=len(inputs)
  host=work/'host.cjs';host.write_text("const fs=require('fs'),{runAwl}=require("+json.dumps(str(ROOT/'web/wasi.js'))+");(async()=>{const b=fs.readFileSync(process.argv[2]);let n=0;for(const a of [[null],['a\\0b'],['\\uD800'],Array(257).fill('x'),['x'.repeat(65536)]]){try{await runAwl(b,a);throw Error('accepted bad args')}catch(e){if(e.message==='accepted bad args')throw e;n++}}for(const raw of [new Uint8Array([0]),new Uint8Array([0,97,115,109,1,0,0,0]),new Uint8Array([0,97,115,109,1,0,0,0,1,4,1,96,0,0,2,11,1,3,101,110,118,3,102,111,111,0,0])]){try{await runAwl(raw,[]);throw Error('accepted bad module')}catch(e){if(e.message==='accepted bad module')throw e;n++}}console.log(n)})().catch(e=>{console.error(e);process.exit(1)})");r=subprocess.run(['node',str(host),str(a.wasm)],capture_output=True,text=True,check=True);assert r.stdout.strip()=='8';records['host_rejection_cases']=8
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'],downloads_path=str(work));page=browser.new_page(viewport={'width':1160,'height':900});requests=[];page.on('request',lambda r:requests.append(r.url));page.goto((ROOT/'web/Awl-json-workbench.html').as_uri());assert page.title()=='Awl · json workbench'
   for (s,pointer,want),native_result in zip(cases,expected,strict=True):
    page.locator('#json').fill(s);page.locator('#pointer').fill(pointer);start=time.perf_counter();page.locator('#run').click();page.wait_for_function("!document.getElementById('run').disabled");assert page.locator('#status').inner_text()==('valid selection' if native_result['code']==0 else 'invalid json' if native_result['code']==4 else 'selection failed');timing.append((time.perf_counter()-start)*1000)
    if native_result['code']==0:
     parts=native_result['stdout'].split('\n');kind=int(parts[1]);text='(container)' if kind in [1,2] else '\n'.join(parts[3:])[:-1];assert page.locator('#value').text_content()==text,(s[:100],pointer,text,page.locator('#value').text_content())
   records['chromium_worker_ui_cases']=len(cases)
   page.evaluate("AwlWorkbench.inspect();document.getElementById('stop').click()");page.wait_for_timeout(100);assert page.locator('#status').inner_text()=='cancelled';records['cancellation_cases']=1
   page.evaluate("()=>{globalThis.RealWorker=Worker;globalThis.Worker=class extends RealWorker{constructor(){super(URL.createObjectURL(new Blob(['while(true){}'],{type:'text/javascript'})))}}}");page.locator('#run').click();page.wait_for_function("!document.getElementById('run').disabled",timeout=8000);assert '5 seconds' in page.locator('#value').inner_text();page.evaluate('()=>{globalThis.Worker=RealWorker}');records['worker_timeout_fault_cases']=1
   page.locator('#json').fill('{"service":{"port":9223372036854775807},"message":"hello 🌍"}');page.locator('#pointer').fill('/service/port');page.locator('#run').click();page.wait_for_function("!document.getElementById('run').disabled");assert page.locator('#value').inner_text()=='9223372036854775807';out=ROOT/'demos/wasm';out.mkdir(exist_ok=True);image=out/'browser-workbench.png';page.screenshot(path=str(work/'screen.png'),full_page=True)
   from PIL import Image
   Image.open(work/'screen.png').convert('RGB').quantize(colors=80).save(image,optimize=True);(out/'capture.json').write_text(json.dumps({'method':'actual Chromium page screenshot, palette-compressed without content changes','browser':browser.version,'image_sha256':sha(image),'html_sha256':sha(ROOT/'web/Awl-json-workbench.html'),'external_requests':[u for u in requests if not u.startswith(('file:','blob:','data:'))]},separators=(',',':'))+'\n');assert not [u for u in requests if not u.startswith(('file:','blob:','data:'))];page.set_content('<iframe sandbox="allow-scripts"></iframe>');page.locator('iframe').evaluate('(f,html)=>{f.srcdoc=html}',(ROOT/'web/Awl-json-workbench.html').read_text());frame=page.frame_locator('iframe');frame.locator('#run').click();frame.locator('#status').get_by_text('valid selection',exact=True).wait_for();assert frame.locator('#value').inner_text()=='5432';records['opaque_sandbox_iframe_cases']=1;browser.close()
 report={'status':'PASS','compiler_sha256':sha(a.sdk/'bin/kcc'),'harness_sha256':sha(Path(__file__)),'oracle_sha256':sha(ROOT/'tests/json_parser.py'),'wasm_sha256':sha(a.wasm),'html_sha256':sha(ROOT/'web/Awl-json-workbench.html'),'records':records,'browser_ui_median_ms':statistics.median(timing),'qualification':'native independent Python JSON oracle plus exact WASM/native parity, Chromium offline real-worker UI, whole automation latency not parser throughput, timeout is deliberate worker fault injection'};a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',records)
if __name__=='__main__':main()

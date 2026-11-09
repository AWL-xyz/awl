#!/usr/bin/env python3
import argparse,base64,gzip,hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description='contributor checked-C to WASI browser foundation, not a public ASDK target');p.add_argument('--sdk',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'web/Awl-json-workbench.html');p.add_argument('--wasm',type=Path);p.add_argument('--entry',type=Path,default=ROOT/'examples/parsing/web.aw');p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();kcc=sdk/'bin/kcc';zig=sdk/'libexec/zig/zig';start=time.monotonic();env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-wasm-cache'}
 with tempfile.TemporaryDirectory(prefix='Awl-wasm-build-',dir='/var/tmp') as td:
  c=Path(td)/'main.c';wasm=Path(td)/'app.wasm';r=subprocess.run([str(kcc),'emit-c',str(a.entry.resolve()),'--syntax','next'],capture_output=True,text=True,check=True,env=env);c.write_text(r.stdout)
  subprocess.run([str(zig),'cc','-target','wasm32-wasi','-Os','-Wall','-Wextra','-Werror','-Wno-unused-function',str(c),'-lm','-Wl,--max-memory=67108864','-o',str(wasm)],check=True,env=env);raw=wasm.read_bytes();packed=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
  if a.wasm:a.wasm.write_bytes(raw)
 template=(ROOT/'web/workbench.template.html').read_text();runtime=(ROOT/'web/wasi.js').read_text();html=template.replace('@@WASM@@',packed).replace('@@SOURCE@@',json.dumps(a.entry.read_text()).replace('</','<\\/')).replace('@@RUNTIME@@',json.dumps(runtime).replace('</','<\\/'));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(html)
 report={'status':'PASS','compiler_sha256':sha(kcc),'backend_sha256':sha(zig),'entry_sha256':sha(a.entry),'parser_sha256':sha(ROOT/'examples/parsing/Json.aw'),'runtime_sha256':sha(ROOT/'web/wasi.js'),'template_sha256':sha(ROOT/'web/workbench.template.html'),'builder_sha256':sha(Path(__file__)),'generated_c_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),'wasm_sha256':hashlib.sha256(raw).hexdigest(),'wasm_bytes':len(raw),'html_sha256':sha(a.output),'build_seconds':round(time.monotonic()-start,4),'target':'wasm32-wasi','memory_max_bytes':67108864,'qualification':'verified native compiler output, bundled backend, contributor pipeline, no in-browser compiler or accepted new SDK distribution'};a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS browser build',len(raw),'wasm bytes')
if __name__=='__main__':main()

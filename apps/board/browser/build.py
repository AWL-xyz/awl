#!/usr/bin/env python3
import argparse,base64,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
APP=ROOT/'apps/board'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description='contributor native/WASM board build, end users need no Python');p.add_argument('--sdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--wasm',type=Path);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-board-cache'}
 assert (APP/'vendor/Json.aw').read_bytes()==(ROOT/'examples/parsing/Json.aw').read_bytes().replace(b'if string.bytes(source) > 16384 then fail(result, 2, 16384);',b'if string.bytes(source) > 65536 then fail(result, 2, 65536);')
 with tempfile.TemporaryDirectory(prefix='Awl-board-build-',dir='/var/tmp') as td:
  td=Path(td);c=td/'filter.c';wasm=td/'filter.wasm'
  def emit(entry,dest):dest.write_bytes(subprocess.run([str(sdk/'bin/acc'),'emit-c',str(entry),'--syntax','next'],check=True,capture_output=True,env=env).stdout)
  def cc(src,out,target,extra=()):subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target',target,'-Os','-Wall','-Wextra','-Werror','-Wno-unused-function',str(src),'-lm',*extra,'-o',str(out)],check=True,env=env)
  emit(APP/'filter.aw',c);cc(c,wasm,'wasm32-wasi',['-Wl,--max-memory=67108864']);raw=wasm.read_bytes()
  if a.wasm:a.wasm.write_bytes(raw)
  html=(APP/'browser/board.template.html').read_text().replace('@@LOGO@@',(ROOT/'assets/branding/awl.svg').read_text()).replace('@@WASM@@',base64.b64encode(gzip.compress(raw,mtime=0)).decode()).replace('@@RUNTIME@@',json.dumps((ROOT/'web/wasi.js').read_text()).replace('</','<\\/'))
  (APP/'Assets.aw').write_text('exports(\n    @r func page() -> text\n        return '+json.dumps(html,ensure_ascii=False)+';\n    end;\n);\n')
  emit(APP/'main.aw',td/'main.c');a.output.parent.mkdir(parents=True,exist_ok=True);cc(td/'main.c',a.output.resolve(),'x86_64-linux-musl')
 report={'status':'PASS','compiler_sha256':sha(sdk/'bin/acc'),'native_sha256':sha(a.output),'native_bytes':a.output.stat().st_size,'wasm_sha256':hashlib.sha256(raw).hexdigest(),'wasm_bytes':len(raw),'html_bytes':len(html.encode()),'sources':{str(p.relative_to(ROOT)):sha(p) for p in sorted(APP.rglob('*')) if p.is_file()},'qualification':'Linux musl native and wasm32-wasi from unchanged verified Awl compiler, contributor-only build, no native Windows qualification'}
 a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS native/WASM build',report['native_bytes'],report['wasm_bytes'],report['html_bytes'])
if __name__=='__main__':main()

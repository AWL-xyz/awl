#!/usr/bin/env python3
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();acc=sdk/'bin/acc';awl=sdk/'bin/awl';records=[];env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/awl-import-cache'}
 with tempfile.TemporaryDirectory(prefix='Awl-local-packages-',dir='/var/tmp') as tmp:
  root=Path(tmp);project=root/'app';project.mkdir();(project/'packages').mkdir()
  def call(args,cwd,code=0):
   r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,capture_output=True,text=True,timeout=180);assert r.returncode==code,(args,r.returncode,r.stdout,r.stderr);return r
  for name,args in [('demo',['init','--pkg','demo']),('second',['init','second','--pkg'])]:
   work=root/name;work.mkdir();call([awl,*args],work);manifest=work/(name+'.awpkg');assert 'kind: package' in manifest.read_text();before=manifest.read_bytes();source=work/(name+'.aw');saved=source.read_bytes();call([awl,*args],work,2);assert manifest.read_bytes()==before and source.read_bytes()==saved;shutil.copytree(work,project/'packages'/name);records.append('init syntax and overwrite protection '+name)
  source=project/'main.aw';source.write_text('use demo;use second as other;func main: i64 {print(demo.hello("owl"));print(other.hello("world"));return 0;};');exe=root/'hello';call([awl,'build',source,'-o',exe],project);r=call([exe],project);assert r.stdout=='Hello, owl!\nHello, world!\n';records.append('created Package imports, explicit alias, native build/run')
  for mode in ['missing','wrong-name','wrong-format','traversal','private','cycle','wrong-case','duplicate-alias']:
   saved=(project/'packages/demo/demo.awpkg').read_text();lib=(project/'packages/demo/demo.aw').read_text();use='use demo;'
   if mode=='missing':use='use missing;';(project/'missing.aw').write_text('exports{@r func hello: text {return "bad fallback";};};')
   if mode=='wrong-name':(project/'packages/demo/demo.awpkg').write_text(saved.replace('name: demo','name: other'))
   if mode=='wrong-format':(project/'packages/demo/demo.awpkg').write_text(saved.replace('format: 1','format: 9'))
   if mode=='traversal':(project/'packages/demo/demo.awpkg').write_text(saved.replace('entry: demo.aw','entry: ../../main.aw'))
   if mode=='private':(project/'packages/demo/demo.aw').write_text('func hello :: who:text: text {return who;};')
   if mode=='cycle':(project/'packages/demo/demo.aw').write_text('use demo;'+lib)
   if mode=='wrong-case':use='use Demo as demo;'
   if mode=='duplicate-alias':use='use demo;use second as demo;'
   source.write_text(use+'func main: i64 {print(demo.hello("owl"));return 0;};');r=call([acc,'check',source],project,1);assert 'error[' in r.stderr;records.append('reject '+mode);(project/'packages/demo/demo.awpkg').write_text(saved);(project/'packages/demo/demo.aw').write_text(lib)
  for name in ['env','json','fsp']:shutil.copytree(ROOT/'packages'/name,project/'packages'/name)
  checks=[('A=x #comment\nB=\nC="quoted" #done\n',True,['A','B','C'],['x','','quoted'],0),('export HOST=🦉\r\nA=1\n',True,['HOST','A'],['🦉','1'],0),('A="one\\ntwo"\nB=\'raw#text\'\n',True,['A','B'],['one\ntwo','raw#text'],0),('A='+'x'*1024,True,['A'],['x'*1024],0),('K'*80+'=ok',True,['K'*80],['ok'],0),('A=x\nB=',True,['A','B'],['x',''],0),('A="bad',False,[],[],3),('9BAD=x',False,[],[],1),('A="x"junk',False,[],[],6),('A=#comment\n',True,['A'],[''],0),('A='+'x'*16383,False,[],[],5),('A=x\n'*257,False,['A']*256,['x']*256,4)]
  body=[]
  for i,(text,ok,keys,values,error) in enumerate(checks):
   literal=json.dumps(text,ensure_ascii=False);body+=['vector.clear(keys);vector.clear(values);','print(env.parse('+literal+',keys,values,result));','print(vector.get(result,0));','print(vector.length(keys));',f'for k{i} in keys {{print(k{i});}};',f'for v{i} in values {{print(v{i});}};']
  body+=['print(json.parse("{\\"ok\\":true}",tokens,result));','match fsp.read("input.txt") then case fsp.Read.Text(value) then print(value); case fsp.Read.Failed(issue) then return 9; end;']
  (project/'invalid.txt').write_bytes(b'\xff');(project/'large.txt').write_bytes(b'x'*16385)
  for fi,(filename,expected) in enumerate([('missing.txt','missing'),('invalid.txt','io:-5'),('large.txt','large:16385')]):
   body.append(('match fsp.read("'+filename+'") then case fsp.Read.Text(value) then return 8; case fsp.Read.Failed(issue) then match issue then case fsp.Issue.Missing() then print("missing"); case fsp.Issue.Io(code) then print("io:"..code); case fsp.Issue.TooLarge(bytes) then print("large:"..bytes); end; end;').replace('value)',f'value{fi})').replace('issue)',f'issue{fi})').replace('match issue then',f'match issue{fi} then').replace('code)',f'code{fi})').replace('..code)',f'..code{fi})').replace('bytes)',f'bytes{fi})').replace('..bytes)',f'..bytes{fi})'))
  source.write_text('use env;use json;use fsp;func main: i64 {@s keys vector<text>:vector.new<text>(0);@s values vector<text>:vector.new<text>(0);@s result vector<i64>:vector.new<i64>(0);vector.push(result,0);vector.push(result,0);@s tokens vector<text>:vector.new<text>(0);'+''.join(body)+'return 0;};');(project/'input.txt').write_text('file 🦉');want=''
  for text,ok,keys,values,error in checks:want+=str(ok).lower()+'\n'+str(error)+'\n'+str(len(keys))+'\n'+''.join(x+'\n'for x in keys+values)
  want+='true\nfile 🦉\nmissing\nio:-5\nlarge:16385\n';c=root/'stdlib.c';c.write_text(call([acc,'emit-c',source],project).stdout)
  for mode in ['native','sanitized']:
   exe=root/('stdlib-'+mode)
   if mode=='native':call([awl,'build',source,'-o',exe],project)
   else:call(['cc','-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',c,'-lm','-o',exe],project)
   r=call([exe],project);assert r.stdout==want and not r.stderr,(mode,r.stdout[-500:],want[-500:],r.stderr);records.append(mode+' env boundaries/comments/quotes/limits + json + fsp actual Package imports')
  source.write_text('use env;use json;func main: i64 {@s k vector<text>:vector.new<text>(0);@s v vector<text>:vector.new<text>(0);@s r vector<i64>:vector.new<i64>(0);vector.push(r,0);vector.push(r,0);print(env.parse("A=owl #comment\\n",k,v,r));print(env.get("A",k,v,"bad"));@s t vector<text>:vector.new<text>(0);print(json.parse("{}",t,r));return 0;};');c.write_text(call([acc,'emit-c',source],project).stdout);wasm=root/'package.wasm';call([sdk/'libexec/zig/zig','cc','-target','wasm32-wasi','-O2',c,'-lm','-o',wasm],project);js=root/'run.js';js.write_text('const fs=require("fs"),{runAwl}=require(process.argv[2]);runAwl(fs.readFileSync(process.argv[3]),[]).then(r=>{process.stdout.write(r.stdout);if(r.code||r.stderr)process.exit(1)});');r=call(['node',js,ROOT/'web/wasi.js',wasm],project);assert r.stdout=='true\nowl\ntrue\n';records.append('real WASI env/json Package imports')
 out={'status':'PASS','records':records,'compiler_sha256':hashlib.sha256(acc.read_bytes()).hexdigest(),'sources_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in (ROOT/'packages').rglob('*')if p.is_file()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'not_implemented':['db','time','websocket','fetch','server add/install']};a.report.write_text(json.dumps(out,separators=(',',':'))+'\n');print('PASS',len(records),'local Package groups')
if __name__=='__main__':main()

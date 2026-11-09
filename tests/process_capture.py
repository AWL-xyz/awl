#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,tempfile,time,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-process-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'};records=[];timings={}
 with tempfile.TemporaryDirectory(prefix='Awl-process-',dir='/var/tmp') as td:
  td=Path(td);fixture=td/'child';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'tests/process_child.c'),'-o',str(fixture)],check=True)
  source='func main[i64] { @s args vector<text>:vector.new<text>(0); @p i:3; while i<arg_count() { vector.push(args,arg_text(i)); i:i+1; }; @s out spool:spool.new(arg_i64(2)); @s err spool:spool.new(arg_i64(2)); if not spool.valid(out) or not spool.valid(err) { return 9; }; spool.append(out,"P");spool.append(err,"P"); print(process_capture(arg_text(0),vector.view(args,0,vector.length(args)),out,err,arg_i64(1)));print(spool.bytes(out));print(spool.snapshot(out));print(spool.bytes(err));print(spool.snapshot(err)); return 0; };';src=td/'main.aw';src.write_text(source);c=td/'main.c';c.write_bytes(subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(src)],capture_output=True,check=True).stdout)
  appc=td/'taskrun.c';appc.write_bytes(subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(ROOT/'apps/taskrun/main.aw')],capture_output=True,check=True).stdout)
  for mode in ['native','sanitized']:
   cmd=[str(sdk/'libexec/zig/zig'),'cc','-target','x86_64-linux-musl','-O2'] if mode=='native' else ['cc','-std=c11','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie']
   exe=td/mode;app=td/(mode+'-taskrun')
   for source_c,dest in [(c,exe),(appc,app)]:subprocess.run([*cmd,'-Wall','-Wextra','-Werror','-Wno-unused-function',str(source_c),'-lm','-o',str(dest)],check=True,env=env)
   def check(label,args,code=0,out=b'',err=b'',capacity=4096,timeout=1000,program=fixture,pass_fds=()):
    before=time.perf_counter();r=subprocess.run([str(exe),str(program),str(timeout),str(capacity),*map(str,args)],capture_output=True,env=env,timeout=5,pass_fds=pass_fds);elapsed=(time.perf_counter()-before)*1000;want=str(code).encode()+b'\n'+str(len(out)+1).encode()+b'\nP'+out+b'\n'+str(len(err)+1).encode()+b'\nP'+err+b'\n';assert (r.returncode,r.stdout,r.stderr)==(0,want,b''),(mode,label,r.returncode,r.stdout[:200],r.stderr);records.append(mode+' '+label);return elapsed
   check('explicit literal UTF8/empty/newline/metachar argv',['args','hello 🦉','','a\nb','; touch NEVER'],out='hello 🦉\n\na\nb\n; touch NEVER\n'.encode())
   check('exit status and separate output',['exit'],7,b'output',b'diagnostic');check('signal status',['signal'],-1015);check('invalid UTF8 atomic rollback',['bad'],-6);check('embedded NUL output',['nul'],out=b'A\0B');check('both pipes beyond kernel capacity',['both'],out=b'x'*262144,err=b'x'*262144,capacity=1048576);check('output overflow rollback',['burst'],-5);elapsed=check('execution timeout rollback',['sleep'],-4,timeout=30);assert elapsed<1500,elapsed;check('leader group change cleanup',['leavegroup'],-4,timeout=30);check('stdin EOF',['stdin']);check('no output with zero remaining capacity',['stdin'],capacity=1);check('missing executable',[],-2,program=td/'missing');check('not executable',[],-3,program=src);check('invalid timeout low',[],-1,timeout=0);check('invalid timeout high',[],-1,timeout=600001);check('too many arguments',['args']*129,-1);check('oversized argument',['args','a'*4097],-1)
   leak=os.open(td/'fd-secret',os.O_CREAT|os.O_RDWR,0o600)
   try:check('unrelated descriptor closed',['fds'],pass_fds=(leak,))
   finally:os.close(leak)
   pidfile=td/'pids';check('process group timeout',['group',pidfile],-4,timeout=100)
   for pid in pidfile.read_text().split():
    stat=Path('/proc')/pid/'stat';deadline=time.monotonic()+1
    while stat.exists() and stat.read_text().split(')')[1].split()[0]!='Z' and time.monotonic()<deadline:time.sleep(0.01)
    assert not stat.exists() or stat.read_text().split(')')[1].split()[0]=='Z',('running descendant',pid)
   plan=td/'tasks.json'
   def task(label,value,code,contains=b''):
    plan.write_text(json.dumps(value,ensure_ascii=False));r=subprocess.run([str(app),str(plan),'200'],capture_output=True,env=env,timeout=10);assert r.returncode==code and contains in r.stdout and not r.stderr,(mode,label,r.returncode,r.stdout,r.stderr);records.append(mode+' taskrun '+label);return r.stdout
   task('sequential execution',[[str(fixture),'args','literal; 🦉'],[str(fixture),'stdin']],0,b'all tasks passed\n')
   marker=td/('not-run-'+mode);task('schema validated before side effects',[[str(fixture),'write',str(marker)],[42]],2,b'invalid task plan');assert not marker.exists()
   task('fail fast',[[str(fixture),'exit'],[str(fixture),'write',str(marker)]],1,b'exit 7');assert not marker.exists()
   task('timeout',[[str(fixture),'sleep']],4,b'timeout');task('capture quota',[[str(fixture),'burst']],5,b'capture error -5');task('capture UTF8',[[str(fixture),'bad']],5,b'capture error -6');task('maximum16 tasks',[[str(fixture),'stdin']]*16,0,b'all tasks passed');task('128 literal arguments',[[str(fixture),'args',*(['x']*127)]],0,b'all tasks passed');task('missing',[[str(td/'missing')]],5,b'capture error -2')
   for i,bad in enumerate([[],{},[[]],[['']],[[str(fixture),True]],[[str(fixture),'\0']],[[str(fixture),'x'*4097]],[[str(fixture)]]*17,[[str(fixture),{}]],[[str(fixture),[[]]]]]):task('invalid schema '+str(i),bad,2)
   # Real build then execution, no shell or Python used by taskrun itself
   hello=td/'hello.aw';hello.write_text('func main[i64] { print("real native Awl task"); return 0; };');built=td/('built-'+mode);plan.write_text(json.dumps([[str(sdk/'bin/awl'),'build',str(hello),'-o',str(built)],[str(built)]]));r=subprocess.run([str(app),str(plan),'60000'],capture_output=True,env={**env,'PATH':'/no-host-tools'},timeout=120);assert r.returncode==0 and b'real native Awl task' in r.stdout and not r.stderr,(mode,r.returncode,r.stdout,r.stderr);records.append(mode+' taskrun real bundled SDK build/execute with no host PATH')
   times=[check('consumed latency sample '+str(i),['stdin']) for i in range(12)];timings[mode]={'samples_ms':[round(t,3) for t in times],'median_ms':round(statistics.median(times),3),'timeout30_observed_ms':round(elapsed,3)}
  # Stub is explicit in real WASI, not simulated native process support
  stub='func main[i64] { @s args vector<text>:vector.new<text>(0); @s out spool:spool.new(8); @s err spool:spool.new(8); print(process_capture("/bin/true",vector.view(args,0,0),out,err,100)); return 0; };';src.write_text(stub);c.write_bytes(subprocess.run([str(sdk/'bin/kcc'),'emit-c',str(src)],capture_output=True,check=True).stdout);wasm=td/'stub.wasm';subprocess.run([str(sdk/'libexec/zig/zig'),'cc','-target','wasm32-wasi','-O2',str(c),'-lm','-o',str(wasm)],env=env,check=True);js=td/'run.js';js.write_text('const fs=require("fs"),{runAwl}=require(process.argv[2]);runAwl(fs.readFileSync(process.argv[3]),[]).then(r=>{process.stdout.write(r.stdout);if(r.code||r.stderr)process.exit(1)}).catch(e=>{console.error(e);process.exit(1)});');r=subprocess.run(['node',str(js),str(ROOT/'web/wasi.js'),str(wasm)],capture_output=True);assert (r.returncode,r.stdout,r.stderr)==(0,b'-8\n',b'');records.append('real WASI unsupported result')
 result={'status':'PASS','cases':len(records),'records':records,'latency':timings,'compiler_sha256':sha(sdk/'bin/kcc'),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tests/process_capture.py',ROOT/'tests/process_child.c',*sorted((ROOT/'apps/taskrun').rglob('*.aw'))]},'qualification':'Linux native musl and ASan/UBSan, explicit WASI unsupported stub, bounded trusted synchronous commands, no static lifetime/async/concurrency/sandbox/Windows/publication claim'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'subprocess/taskrun checks',json.dumps(timings))
if __name__=='__main__':main()

#!/usr/bin/env python3
import argparse,hashlib,json,os,platform,random,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def Awl_source(slots,rounds):
 ballast=' '.join('@p scoped ballast'+str(i)+' vector<bool>: vector_new<bool>(0);' for i in range(slots-1))
 return 'func main()->i64 '+ballast+''' @p scoped v vector<i64>: vector_new<i64>(4096); if not vector_valid(v) then return 9; end; @p seed: i64(string_byte_at(arg_text(0),0)); @p i: 0; while i<4096 do if not vector_push(v,i+seed) then return 9; end; i: i+1; end; @p index: seed%4096; @p total: 0; @p round: 0; while round<'''+str(rounds)+''' do index: (index*17+23)%4096; @p value: vector_get(v,index)+1; vector_set(v,index,value); total: total+value; round: round+1; end; print(total); return 0; end;'''
def cpp_source(slots,rounds):return '''#include <vector>
#include <cstdint>
#include <cstdio>
int main(int,char**argv){std::vector<std::vector<bool>> ballast('''+str(slots-1)+''');std::vector<int64_t> v;v.reserve(4096);const int64_t seed=(unsigned char)argv[1][0];for(int64_t i=0;i<4096;i++)v.push_back(i+seed);int64_t index=seed%4096,total=0;for(int64_t r=0;r<'''+str(rounds)+''';r++){index=(index*17+23)%4096;int64_t value=v.at(index)+1;v.at(index)=value;total+=value;}std::printf("%lld\\n",(long long)total);}
'''
def rust_source(slots,rounds):return '''fn main(){let _ballast:Vec<Vec<bool>>=(0..'''+str(slots-1)+''').map(|_|Vec::new()).collect();let seed=std::env::args().nth(1).unwrap().as_bytes()[0] as i64;let mut v:Vec<i64>=Vec::with_capacity(4096);for i in 0..4096 {v.push(i+seed);}let mut index=seed%4096;let mut total:i64=0;for _ in 0..'''+str(rounds)+''' {index=(index*17+23)%4096;let value=v[index as usize]+1;v[index as usize]=value;total+=value;}println!("{}",total);}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--before',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--rounds',type=int,default=5000000);a=p.parse_args();sdk=a.sdk.resolve();zig=sdk/'libexec/zig/zig';kcc=sdk/'bin/kcc';env={**os.environ,'XDG_CACHE_HOME':'/var/tmp/Awl-perf-cache'};rng=random.Random(20261107);samples={};binaries={};commands={};rounds=a.rounds;assert 1<=rounds<=10000000
 with tempfile.TemporaryDirectory(prefix='Awl-vector-bench-',dir='/var/tmp') as td:
  work=Path(td)
  for slots in [1,16,64]:
   for name,compiler,source in [('Awl-before',a.before,Awl_source(slots,rounds)),('Awl-after',kcc,Awl_source(slots,rounds)),('cpp-at',None,cpp_source(slots,rounds)),('rust-release',None,rust_source(slots,rounds)),('rust-checked',None,rust_source(slots,rounds))]:
    key=name+'/'+str(slots);src=work/(name+str(slots));exe=Path(str(src)+'.exe')
    if compiler:
     src=src.with_suffix('.aw');src.write_text(source);r=subprocess.run([str(compiler),'emit-c',str(src),'--syntax','next'],capture_output=True,text=True,check=True,env=env);c=src.with_suffix('.c');c.write_text(r.stdout);command=[str(zig),'cc','-std=c11','-target','x86_64-linux-musl','-mcpu=baseline','-static','-O3',str(c),'-lm','-o',str(exe)]
    elif name=='cpp-at':src=src.with_suffix('.cpp');src.write_text(source);command=['g++','-std=c++20','-O3','-march=x86-64',str(src),'-o',str(exe)]
    else:src=src.with_suffix('.rs');src.write_text(source);command=['rustc','--edition=2021','-C','opt-level=3','-C','target-cpu=x86-64','-C','overflow-checks='+('yes' if name=='rust-checked' else 'no'),'--crate-name','vector_bench',str(src),'-o',str(exe)]
    subprocess.run(command,check=True,env=env,capture_output=True);binaries[key]=exe;samples[key]=[];commands[key]=command[:-1]+['<temporary executable>']
  index=ord('K')%4096;total=0;data=[i+ord('K') for i in range(4096)]
  for _ in range(rounds):index=(index*17+23)%4096;data[index]+=1;total+=data[index]
  want=(str(total)+'\n').encode()
  for exe in binaries.values():r=subprocess.run([str(exe),'K'],capture_output=True,check=True);assert r.stdout==want and not r.stderr
  for repeat in range(7):
   order=list(binaries);rng.shuffle(order)
   for key in order:
    start=time.perf_counter_ns();r=subprocess.run([str(binaries[key]),'K'],capture_output=True,check=True);elapsed=(time.perf_counter_ns()-start)/1e6;assert r.stdout==want and not r.stderr;samples[key].append(elapsed)
  lines=[f'{rng.randrange(100000):06d}'.encode() for _ in range(10000)];payload=b'\n'.join(lines);apps={};app_samples={}
  for name,compiler in [('before',a.before),('after',kcc)]:
   c=work/(name+'-ksort.c');exe=work/(name+'-ksort');r=subprocess.run([str(compiler),'emit-c',str(ROOT/'examples-next/apps/ksort/main.aw'),'--syntax','next'],capture_output=True,text=True,check=True,env=env);c.write_text(r.stdout);subprocess.run([str(zig),'cc','-std=c11','-target','x86_64-linux-musl','-mcpu=baseline','-static','-O3',str(c),'-lm','-o',str(exe)],check=True,env=env,capture_output=True)
   for unique in [False,True]:apps[name+('/unique' if unique else '/sort')]=(exe,unique);app_samples[name+('/unique' if unique else '/sort')]=[]
  for repeat in range(8):
   order=list(apps);rng.shuffle(order)
   for key in order:
    exe,unique=apps[key];want=b''.join(v+b'\n' for v in sorted(set(lines) if unique else lines));start=time.perf_counter_ns();r=subprocess.run([str(exe)]+(['--unique'] if unique else []),input=payload,capture_output=True,check=True);elapsed=(time.perf_counter_ns()-start)/1e6;assert r.stdout==want and not r.stderr
    if repeat:app_samples[key].append(elapsed)
  results={k:{'median_ms':statistics.median(v),'samples_ms':v} for k,v in samples.items()}
  result={'status':'PASS','compiler_before_sha256':sha(a.before),'compiler_after_sha256':sha(kcc),'harness_sha256':sha(Path(__file__)),'host':platform.platform(),'cpu_model':next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown'),'affinity':sorted(os.sched_getaffinity(0)),'rounds':rounds,'elements':4096,'checksum':total,'toolchains':{'rust':subprocess.check_output(['rustc','--version'],text=True).strip(),'cpp':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],'Awl_backend':subprocess.check_output([str(zig),'version'],text=True).strip()},'results':results,'ksort':{k:{'median_ms':statistics.median(v),'samples_ms':v} for k,v in app_samples.items()},'flags':commands,'qualification':'7 shuffled whole-process warm samples after excluded warmup, one machine, slot-pressure microbenchmark not representative application ranking, C++ .at and Rust indexing retain language bounds checks, Rust checked variant enables overflow checks, default C++/Rust arithmetic differs from Awl checked arithmetic, compiler versions/backends/libc differ, optimized ballast may disappear in C++/Rust, all checksums independently verified, no universal faster-than claim'}
 a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps({k:round(v['median_ms'],3) for k,v in results.items()}))
if __name__=='__main__':main()

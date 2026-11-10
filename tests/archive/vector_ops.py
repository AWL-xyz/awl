#!/usr/bin/env python3
import argparse,hashlib,json,os,resource,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();kcc=a.kcc.resolve();env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-perf-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'};records=[]
 types=[('i8','i8(-128)','i8(127)','-128','127'),('i16','i16(-32768)','i16(32767)','-32768','32767'),('i32','i32(-2147483648)','i32(2147483647)','-2147483648','2147483647'),('i64','-9223372036854775808','9223372036854775807','-9223372036854775808','9223372036854775807'),('u8','0u8','255u8','0','255'),('u16','0u16','65535u16','0','65535'),('u32','0u32','4294967295u32','0','4294967295'),('u64','0u64','18446744073709551615u64','0','18446744073709551615'),('bool','false','true','false','true'),('f64','-0.5','2.75','-0.5','2.75'),('text','"é🙂"','"雪"','é🙂','雪')]
 with tempfile.TemporaryDirectory(prefix='Awl-vector-ops-',dir='/var/tmp') as td:
  work=Path(td);src=work/'main.aw';exe=work/'app';last=''
  def emit(source):
   src.write_text(source);r=subprocess.run([str(kcc),'emit-c',str(src),'--syntax','next'],capture_output=True,text=True,check=True,env=env);return r.stdout
  def compile_c(text):
   c=work/'main.c';c.write_text(text);subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)],check=True,timeout=60)
  for mode in ['bundled','sanitized']:
   for ty,x,y,first,second in types:
    source='func main()->i64 @p scoped v vector<'+ty+'>: vector.new<'+ty+'>(4); vector.push(v,'+x+'); vector.push(v,'+y+'); vector.swap(v,0,1); print(vector.get(v,0)); print(vector.get(v,1)); vector.swap(v,0,0); print(vector.truncate(v,1)); print(vector.length(v)); print(vector.capacity(v)); print(vector.truncate(v,-1)); print(vector.truncate(v,2)); print(vector.get(v,0)); print(vector.truncate(v,0)); vector.push(v,'+x+'); print(vector.pop(v)); return 0; end;'
    last=emit(source)
    if mode=='bundled':subprocess.run([str(kcc),'build',str(src),'--syntax','next','-o',str(exe)],check=True,env=env,capture_output=True,timeout=180)
    else:compile_c(last)
    r=subprocess.run([str(exe)],capture_output=True,env=env,timeout=5);want=(second+'\n'+first+'\ntrue\n1\n4\nfalse\nfalse\n'+second+'\ntrue\n'+first+'\n').encode();assert (r.returncode,r.stdout,r.stderr)==(0,want,b''),(ty,mode,r.stdout,r.stderr);records.append([mode,ty])
  prefix='func main()->i64 @p v vector<i64>: vector.new<i64>(1); '
  for label,body in [('empty swap','vector.swap(v,0,0);'),('negative swap','vector.push(v,1); vector.swap(v,-1,0);'),('second out of bounds','vector.push(v,1); vector.swap(v,0,1);'),('stale swap','vector.free(v); vector.swap(v,0,0);'),('stale truncate','vector.free(v); vector.truncate(v,0);')]:
   compile_c(emit(prefix+body+' return 0; end;'));r=subprocess.run([str(exe)],capture_output=True,env=env);assert r.returncode!=0 and b'Awl vector trap:' in r.stderr and b'AddressSanitizer' not in r.stderr and b'runtime error:' not in r.stderr;records.append(['sanitized trap',label])
  for body in ['vector.swap(v,0);','vector.swap(v,0,true);','vector.truncate(v,true);','vector.swap(1,0,0);','vector.truncate(v,0,0);']:
   src.write_text(prefix+body+' return 0; end;');r=subprocess.run([str(kcc),'check',str(src),'--syntax','next'],capture_output=True,env=env);assert r.returncode==1 and b'error[' in r.stderr;records.append(['rejected',body])
  text=emit(prefix+'vector.push(v,1); print(vector.get(v,0)); vector.set(v,0,2); return 0; end;').replace('int main(void)','int original_main(void)')
  for access in ['k_vector_get_i64(v,0);','k_vector_set_i64(v,0,1);']:
   compile_c(text+'\nint main(void){KGenericVector v=k_generic_new(4,1,1);unsigned char x=7;k_generic_push(v,4,&x);'+access+'return 0;}');r=subprocess.run([str(exe)],capture_output=True,env=env);assert r.returncode!=0 and b'Awl vector trap:' in r.stderr and b'AddressSanitizer' not in r.stderr;records.append(['sanitized layout guard',access])
  slot=work/'slots';subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(ROOT/'tests/vector_slots.c'),'-o',str(slot)],check=True);r=subprocess.run([str(slot)],capture_output=True,text=True,env=env,check=True);assert '440078' in r.stdout and not r.stderr;records.append(['sanitized runtime identities',r.stdout.strip()])
 report={'status':'PASS','compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'runtime_test_sha256':hashlib.sha256((ROOT/'tests/vector_slots.c').read_bytes()).hexdigest(),'cases':len(records),'records':records};a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(records),'vector operation/identity cases')
if __name__=='__main__':main()

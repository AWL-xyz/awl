#!/usr/bin/env python3
import argparse,hashlib,io,json,os,random,re,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROBE='''use Json.aw as json;
func main()->i64
 if arg_text(0)=="--reuse" then
  @p scoped saved vector<text>: vector.new<text>(0);
  @p scoped status vector<i64>: vector.new<i64>(0);
  @p repeat: 0;
  while repeat<128 do
   if not json.parse("[true]",saved,status) then return 1; end;
   if vector.length(saved)!=3 then return 2; end;
   if json.parse("[1,]",saved,status) then return 3; end;
   if vector.length(saved)!=3 or vector.get(saved,1)!="true" then return 4; end;
   if json.locate("",saved,status)!=-4 then return 5; end;
   if not json.parse("null",saved,status) then return 6; end;
   if vector.length(saved)!=1 or vector.get(saved,0)!="null" then return 7; end;
   repeat: repeat+1;
  end;
  print("reuse passed"); return 0;
 end;
 @p b: buffer_new(16385); defer buffer_free(b);
 @p f: file_open(arg_text(0),0); if f<0 then return 8; end;
 @p n: 0; @p done: false;
 while n<16385 and not done do @p k: file_read(f,b,n,16385-n); if k<0 then file_close(f); return 8; end; if k==0 then done: true; else n: n+k; end; end;
 file_close(f);
 @p scoped tokens vector<text>: vector.new<text>(0);
 @p scoped result vector<i64>: vector.new<i64>(0);
 vector.push(tokens,"keep"); vector.push(result,999);
 print(json.parse(buffer_text(b,0,n),tokens,result));
 print(vector.length(result)); @p i: 0;
 while i<vector.length(result) do print(vector.get(result,i)); i: i+1; end;
 print(vector.length(tokens)); i: 0;
 while i<vector.length(tokens) do @p value: vector.get(tokens,i); print(string.bytes(value)); print(value); i: i+1; end;
 if arg_count()>1 then print(json.locate(arg_text(1),tokens,result)); end;
 return 0;
end;
'''
def oracle(source):
 decoder=json.JSONDecoder(parse_int=str,parse_float=str,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)));values=[];metadata=[];i=0
 def ws():
  nonlocal i
  while i<len(source) and source[i] in ' \t\r\n':i+=1
 def emit(kind,value,start):
  if len(values)==512 or len(value.encode('utf8'))>4096 and kind in [5,10]:raise OverflowError()
  values.append(value);metadata.extend([kind,len(source[:start].encode())])
 def visit(depth=0):
  nonlocal i
  ws();start=i;c=source[i]
  if c in '{[':
   if depth==16:raise OverflowError()
   kind=1 if c=='{' else 2;close='}' if kind==1 else ']';emit(kind,'',i);i+=1;ws()
   if source[i]!=close:
    while True:
     if kind==1:
      start=i;key,end=decoder.raw_decode(source,i);assert isinstance(key,str) and source[i]=='"';i=end;emit(10,key,start);ws();assert source[i]==':';i+=1
     visit(depth+1);ws()
     if source[i]==close:break
     assert source[i]==',';i+=1;ws()
   emit(kind+2,'',i);i+=1
  else:
   value,end=decoder.raw_decode(source,i);raw=source[i:end];kind=5 if c=='"' else 6 if c in '-0123456789' else 7 if raw=='true' else 8 if raw=='false' else 9
   if kind in [5,10]:value.encode('utf8')
   emit(kind,value if kind==5 else raw,start);i=end
 if len(source.encode())>16384:raise OverflowError()
 visit();ws();assert i==len(source)
 return values,[0,len(source.encode()),*metadata]
def main():
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();kcc=a.kcc.resolve();rng=random.Random(8259)
 def tree(depth=0):
  scalars=[None,True,False,rng.randrange(-100000,100000),rng.random(),''.join(rng.choices('abcé日本😀\x00\n\t"\\',k=rng.randrange(20)))]
  if depth<4:scalars.extend([[tree(depth+1) for _ in range(rng.randrange(4))],{str(i)+'é':tree(depth+1) for i in range(rng.randrange(4))}])
  return rng.choice(scalars)
 corpus=['{}','[]','null','true','false','-0','0.3','-12.25e+99','1e9999','123456789012345678901234567890',json.dumps(''.join(chr(i) for i in range(32))),r'"\uD834\uDD1E"',r'"\u0000\/\b\f\n\r\t\\\""','{"é":[1,true,{"a":"日本😀"}]}','{"a":1,"\\u0061":2}']
 corpus += [json.dumps(tree(),ensure_ascii=bool(i%2),separators=(',',':')) for i in range(180)]
 corpus += ['', ' ', '[1,]', '{"a":1,}', '{1:2}', '{"a" 1}', '{"a":}', '[,1]', '+1','01','-01','1.','1e','1e+','--1','NaN','Infinity','true false','nullx','"unterminated','"bad\x00raw"',r'"\x00"',r'"\u123"',r'"\uZZZZ"',r'"\uD800"',r'"\uDC00"',r'"\uD800\uD800"',r'"\uD800\u0041"','\ufeff{}','[true\v]']
 for _ in range(180):
  source=rng.choice(corpus[:195]);at=rng.randrange(len(source)+1);corpus.append(source[:at]+rng.choice('[]{}:,"\\x01 \n')+source[at:])
 corpus += ['['*16+'0'+']'*16,'['*17+'0'+']'*17,'"'+'x'*4096+'"','"'+'x'*4097+'"','['+','.join(['0']*510)+']','['+','.join(['0']*511)+']','0'+' '*16383,'0'+' '*16384,'"'+'😀'*1024+'"','"'+'😀'*1025+'"']
 pointer_cases=[('{"foo":["bar","baz"],"":0,"a/b":1,"m~n":2,"~1":3,"é":4}',p,want) for p,want in [('',0),('/foo/0',3),('/foo/1',4),('/',7),('/a~1b',9),('/m~0n',11),('/~01',13),('/é',15),('/missing',-1),('/foo/2',-1),('/foo/-',-1),('/foo/01',-2),('/foo/+1',-2),('/foo/'+'9'*200,-1),('/missing/~2',-2),('/bad~',-2),('#/foo',-2),('/foo/0/a',-1)]]
 pointer_cases += [('{"a":1,"\\u0061":2}','/a',-3),('null','',0),('null','/',-1),('{}','/'+'a'*4096,-2),('[]','/'*17,-2)]
 counts={};timings={};env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-json-cache','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'}
 with tempfile.TemporaryDirectory(prefix='Awl-json-tests-',dir='/var/tmp') as td:
  folder=Path(td);shutil.copyfile(ROOT/'examples/parsing/Json.aw',folder/'Json.aw');src=folder/'main.aw';src.write_text(PROBE)
  for mode in ['bundled','sanitized']:
   exe=folder/mode;cmd='build' if mode=='bundled' else 'emit-c';r=subprocess.run([str(kcc),cmd,str(src),'--syntax','next']+(['-o',str(exe)] if mode=='bundled' else []),capture_output=True,text=True,env=env,timeout=180);assert r.returncode==0,r.stderr
   if mode=='sanitized':
    c=folder/'main.c';c.write_text(r.stdout);subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)],check=True,timeout=90)
   elapsed=[];passed=0
   def run(source,pointer=None):
    file=folder/'input.json';file.write_bytes(source.encode());start=time.perf_counter_ns();r=subprocess.run([str(exe),str(file)]+([pointer] if pointer is not None else []),capture_output=True,env=env,timeout=5);elapsed.append((time.perf_counter_ns()-start)/1e6);assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr,source[:100]);stream=io.BytesIO(r.stdout);ok=stream.readline()==b'true\n';metadata=[int(stream.readline()) for _ in range(int(stream.readline()))];values=[]
    for _ in range(int(stream.readline())):
     n=int(stream.readline());values.append(stream.read(n).decode());assert stream.read(1)==b'\n'
    selected=int(stream.readline()) if pointer is not None else None;assert not stream.read();return ok,values,metadata,selected
   for source in corpus:
    try:want=oracle(source)
    except (ValueError,AssertionError,IndexError,UnicodeError,OverflowError):want=None
    ok,values,metadata,_=run(source)
    if want is not None:assert ok and (values,metadata)==want,(source[:120],values,metadata,want)
    else:assert not ok and values==['keep'] and len(metadata)==2 and metadata[0] in [1,2,3] and 0<=metadata[1]<=len(source.encode()),(source[:120],ok,values,metadata)
    passed+=1
   for source,pointer,want in pointer_cases:
    ok,_,_,selected=run(source,pointer);assert ok and selected==want,(source,pointer,selected,want);passed+=1
   # Exact byte diagnostics must count multibyte text before the error.
   ok,values,metadata,_=run('{"é":]');assert not ok and metadata==[1,6] and values==['keep'];passed+=1
   r=subprocess.run([str(exe),'--reuse'],capture_output=True,env=env,timeout=5);assert (r.returncode,r.stdout,r.stderr)==(0,b'reuse passed\n',b'');passed+=1
   counts[mode]=passed;timings[mode]={'process_median_ms':sorted(elapsed)[len(elapsed)//2],'qualification':'includes file input, process startup and token output, mixed valid/invalid bounded corpus, not parser-only throughput'}
 report={'status':'PASS','cases_per_mode':counts,'corpus_sha256':hashlib.sha256(json.dumps([corpus,pointer_cases],ensure_ascii=True).encode()).hexdigest(),'compiler_sha256':hashlib.sha256(kcc.read_bytes()).hexdigest(),'parser_sha256':hashlib.sha256((ROOT/'examples/parsing/Json.aw').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'timing':timings};a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print(report)
if __name__=='__main__':main()

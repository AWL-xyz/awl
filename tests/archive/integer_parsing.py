import hashlib,json,os,random,shutil,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];K=Path('/var/tmp/Awl-parsing-sdk/Awl/bin/kcc');rows=[]
def digits(n,b):
 s='';negative=n<0;n=abs(n)
 while n:s='0123456789abcdefghijklmnopqrstuvwxyz'[n%b]+s;n//=b
 return ('-' if negative else '')+(s or '0')
cases=[]
for b in range(2,37):
 for n in [0,1,-1,2**63-1,-2**63,2**63,-2**63-1]:cases.append((digits(n,b),b,n if -2**63<=n<2**63 else None))
rng=random.Random(20261106)
for _ in range(1000):
 n=rng.randrange(-2**63,2**63);b=rng.randrange(2,37);cases.append((digits(n,b).upper(),b,n))
for s in ['', '+','-',' 1','1 ','1x','0x10','0b10','1_0','١','雪','1\x00','--1','+-1']:
 if '\x00' not in s:cases.append((s,10,None))
for b in [-1,0,1,37,9223372036854775807]:cases.append(('1',b,None))
cases += [('+0',10,0),('-0',10,0),('00042',10,42)]
signed=cases
unsigned=[(digits(n,b),b,n if 0<=n<2**64 else None) for b in range(2,37) for n in [0,1,2**64-1,2**64,-1]]
for _ in range(1000):
 n=rng.randrange(2**64);b=rng.randrange(2,37);unsigned.append((digits(n,b).upper(),b,n))
unsigned += [('+',10,None),('-0',10,None),('+42',10,42),('',10,None),('1',1,None),('1',37,None),('1 ',10,None)]
with tempfile.TemporaryDirectory(prefix='Awl-parsing-',dir='/var/tmp') as td:
 w=Path(td);(w/'Integer.aw').write_bytes((R/'examples/parsing/Integer.aw').read_bytes());s=w/'main.aw'
 template='use Integer.aw as parse; func main()->i64 @p scoped v vector<i64>: vector.new<i64>(1); vector.push(v,42); print(parse.parse(arg.text(1),arg.i64(0),v)); print(vector.length(v)); print(vector.get(v,vector.length(v)-1)); return 0; end;'
 env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-parsing-cache'}
 for kind,mode in [(k,m) for k in ['signed','unsigned'] for m in ['native','sanitized']]:
  cases=signed if kind=='signed' else unsigned
  s.write_text(template if kind=='signed' else template.replace('<i64>','<u64>').replace('42);','42u64);').replace('parse.parse','parse.unsigned'))
  exe=w/(kind+'-'+mode);cmd='build' if mode=='native' else 'emit-c';r=subprocess.run([str(K),cmd,str(s),'--syntax','next']+(['-o',str(exe)] if mode=='native' else []),env=env,capture_output=True,text=True);assert r.returncode==0,r.stderr
  if mode=='sanitized':
   c=w/'a.c';c.write_text(r.stdout);subprocess.run([shutil.which('cc'),'-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(c),'-lm','-o',str(exe)],check=True)
  for text,base,value in cases:
   r=subprocess.run([str(exe),str(base),text],capture_output=True,text=True);expected='false\n1\n42\n' if value is None else f'true\n2\n{value}\n';assert (r.returncode,r.stdout,r.stderr)==(0,expected,''),(mode,text,base,r.stdout,r.stderr)
  rows.append([kind+' '+mode,len(cases)])
  if mode=='sanitized':
   marker='unsigned char *data=realloc(s->data,(size_t)capacity*s->width);';assert marker in c.read_text();c.write_text(c.read_text().replace(marker,'unsigned char *data=NULL;'))
   subprocess.run([shutil.which('cc'),'-std=c11','-O1','-fsanitize=address,undefined',str(c),'-lm','-o',str(exe)],check=True)
   r=subprocess.run([str(exe),'10','123'],capture_output=True,text=True);assert (r.returncode,r.stdout,r.stderr)==(0,'false\n1\n42\n','')

report={'status':'PASS','compiler_sha256':hashlib.sha256(K.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((R/'examples/parsing/Integer.aw').read_bytes()).hexdigest(),'runs':rows};(R/'tests/integer-parsing.json').write_text(json.dumps(report)+'\n');print(report)

"""Deterministic strict UTF-8 differential oracle plus Linux syscall fault injection."""
import hashlib,json,random,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 rng=random.Random(22);cases=[b'',b'\0',b'\xc2\x80',b'\xdf\xbf',b'\xe0\xa0\x80',b'\xed\x9f\xbf',b'\xee\x80\x80',b'\xf0\x90\x80\x80',b'\xf4\x8f\xbf\xbf']
 cases += [rng.randbytes(rng.randrange(13)) for _ in range(4000)]
 for _ in range(1000):
  cp=rng.randrange(0x110000)
  if not 0xd800<=cp<=0xdfff:cases.append(chr(cp).encode())
 fixture=''.join(b.hex()+'\n' for b in cases);expected=[]
 for b in cases:
  try:expected.append('1 '+str(len(b.decode('utf-8','strict'))))
  except UnicodeDecodeError:expected.append('0 0')
 results=[]
 with tempfile.TemporaryDirectory(prefix='Awl-file-oracle-') as td:
  for sanitized in [False,True]:
   exe=Path(td)/('test-asan' if sanitized else 'test');cmd=[shutil.which('cc'),'-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation']
   if sanitized:cmd+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
   subprocess.run([*cmd,str(ROOT/'tests/files_runtime_test.c'),'-o',str(exe)],check=True,timeout=60)
   r=subprocess.run([str(exe)],input=fixture,capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr;lines=r.stdout.splitlines();assert lines[1:]==expected;assert lines[0].startswith('PASS ');assert not r.stderr,r.stderr;results.append({'sanitized':sanitized,'exit':r.returncode,'runtime':lines[0],'UTF8_cases':len(cases)})
 report={'status':'passed','scope':'Linux contributor fault injection; strict UTF8 scalar-count differential against Python strict decoder. Neither product runtime Python dependency nor Windows backend acceptance.','seed':22,'fixture_sha256':hashlib.sha256(fixture.encode()).hexdigest(),'results':results};(ROOT/'tests/files-oracle.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

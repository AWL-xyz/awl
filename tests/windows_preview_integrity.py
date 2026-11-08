"""Archive integrity/resource gate; explicitly NOT Windows runtime acceptance."""
import argparse,hashlib,json,struct,tarfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def imports(p):
 b=p.read_bytes();assert b[:2]==b'MZ';pe=struct.unpack_from('<I',b,60)[0];assert b[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',b,pe+4)[0]==0x8664
 optional=struct.unpack_from('<H',b,pe+20)[0];assert struct.unpack_from('<H',b,pe+24)[0]==0x20b
 count=struct.unpack_from('<H',b,pe+6)[0];sections=[]
 for i in range(count):
  at=pe+24+optional+i*40;virtual,rva,size,offset=struct.unpack_from('<IIII',b,at+8);sections.append((rva,max(virtual,size),offset))
 def file_offset(rva):
  for start,size,offset in sections:
   if start<=rva<start+size:return offset+rva-start
  raise AssertionError(('RVA outside sections',rva))
 rva,size=struct.unpack_from('<II',b,pe+24+120);at=file_offset(rva);result=[]
 for i in range(min(size//20,256)):
  fields=struct.unpack_from('<IIIII',b,at+i*20)
  if not any(fields):break
  name=file_offset(fields[3]);end=b.index(0,name);result.append(b[name:end].decode('ascii'))
 return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--upstream',type=Path,default=ROOT/'build/zig-windows.zip');p.add_argument('--report',type=Path,default=ROOT/'tests/windows-preview-integrity.json');a=p.parse_args();bundle=a.bundle;m=json.loads((bundle/'manifest.json').read_text())
 assert digest(bundle/'bin/kcc.exe')==m['kcc_sha256'];assert digest(bundle/'libexec/zig/zig.exe')==m['zig_sha256']
 for name,h in m['compiler_sources_sha256'].items():assert digest(bundle/'src'/name)==h and digest(ROOT/'compiler/native'/name)==h,name
 with tarfile.open(a.archive) as t:
  members=t.getmembers();assert not any(x.name.startswith('/') or '..' in Path(x.name).parts for x in members)
 examples=[p for p in (ROOT/'examples').rglob('*') if p.is_file()]
 for path in examples:assert digest(path)==digest(bundle/path.relative_to(ROOT)),str(path)
 dlls=imports(bundle/'bin/kcc.exe')
 for s in dlls:
  lower=s.lower();assert lower in {'kernel32.dll','advapi32.dll','bcrypt.dll','msvcrt.dll','ntdll.dll','ucrtbase.dll'} or lower.startswith('api-ms-win-crt-') and lower.endswith('.dll'),s
 lock=json.loads((ROOT/'compiler/toolchain-windows-lock.json').read_text());assert a.upstream.stat().st_size==lock['bytes'] and digest(a.upstream)==lock['sha256'];verified=0
 with zipfile.ZipFile(a.upstream) as z:
  for item in z.infolist():
   if item.is_dir():continue
   relative=item.filename.split('/',1)[1];target=bundle/'libexec/zig'/relative;h=hashlib.sha256()
   with z.open(item) as f:
    while b:=f.read(1048576):h.update(b)
   assert target.is_file() and digest(target)==h.hexdigest(),relative;verified+=1
 out={'status':'archive integrity passed; NOT Windows runtime acceptance','sha256':digest(a.archive),'bytes':a.archive.stat().st_size,'archive_members':len(members),'source_hashes_verified_against_manifest_and_current_source':len(m['compiler_sources_sha256']),'examples_verified_against_current_source':len(examples),'kcc_and_zig_hashes_verified':True,'unmodified_full_upstream_files_content_verified':verified,'compiler_DLL_imports':dlls,'DLL_qualification':'Windows OS/UCRT API sets only; stock real-Windows execution still pending','installed_backend_acceptance':False,'real_windows_execution':False}
 a.report.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()

"""Exact extracted Linux artifact, source/examples and whole upstream content gate."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 bundle=ROOT/'build/archive-isolation-root/relocated Awl';archive=ROOT/'build/Awl-0.22.0-dev-linux-x86_64.tar.xz';m=json.loads((bundle/'manifest.json').read_text());assert m['version']=='0.22.0-dev'
 assert sha(bundle/'bin/kcc')==m['kcc_sha256'];assert sha(bundle/'libexec/zig/zig')==m['zig_sha256']
 for n,h in m['compiler_sources_sha256'].items():assert sha(bundle/'src'/n)==h==sha(ROOT/'compiler/native'/n),n
 examples=list((ROOT/'examples').rglob('*.aw'))
 for p in examples:assert sha(p)==sha(bundle/p.relative_to(ROOT)),str(p)
 for binary in [bundle/'bin/kcc',bundle/'libexec/zig/zig']:
  assert 'INTERP' not in subprocess.check_output(['readelf','-l',str(binary)],text=True)
 lock=json.loads((ROOT/'compiler/toolchain-lock.json').read_text());upstream=ROOT/'.cache/toolchains/zig-0.15.2.tar.xz';assert sha(upstream)==lock['sha256'] and upstream.stat().st_size==lock['bytes'];count=0
 with tarfile.open(upstream) as t:
  for item in t:
   if not item.isfile():continue
   relative=item.name.split('/',1)[1];target=bundle/'libexec/zig'/relative;f=t.extractfile(item);h=hashlib.sha256()
   while data:=f.read(1048576):h.update(data)
   assert target.is_file() and sha(target)==h.hexdigest(),relative;assert target.stat().st_mode&0o777==item.mode&0o777,relative;count+=1
 report={'status':'passed','archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'source_hashes':len(m['compiler_sources_sha256']),'examples_compared_to_current_source':len(examples),'unmodified_full_upstream_files_and_modes':count,'kcc_and_zig_static_ELF':True,'scope':'Integrity only; separate exact extracted/offline execution gates required.'};(ROOT/'tests/files-linux-exact-integrity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

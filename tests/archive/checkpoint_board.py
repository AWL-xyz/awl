#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 reports={n:json.loads((ROOT/f'tests/board-{n}.json').read_text()) for n in ['build','linux','public','sanitized','faults','parity','limits','limits-sanitized','browser','package']}
 assert all(r['status']=='PASS' for r in reports.values())
 assert [reports[n]['cases'] for n in ['linux','public','sanitized','faults','limits','limits-sanitized','browser','package']]==[198,198,198,24,6,6,23,4]
 assert reports['parity']['native_cases']==80 and reports['parity']['wasm_cases']==79
 compiler=sha(ROOT/'compiler/native/bin/kcc');assert compiler==reports['build']['compiler_sha256']=='21856c691451f9c6b1483b4940878dc5f5c0993d7e7c9dbd740be8fb449742f1'
 for path,digest in reports['build']['sources'].items():assert sha(ROOT/path)==digest,path
 public=reports['public']['executable_sha256'];assert public==reports['browser']['executable_sha256']==reports['limits']['executable_sha256']==reports['package']['executable_sha256']
 assert reports['linux']['executable_sha256']==reports['build']['native_sha256']
 assert reports['sanitized']['executable_sha256']==reports['limits-sanitized']['executable_sha256']
 assert reports['parity']['wasm_sha256']==reports['build']['wasm_sha256']
 assert sha(ROOT/'demos/board/Awl-board.png')==reports['browser']['photo_sha256']
 archive=ROOT.parent/'Awl-board-0.1-linux-x86_64.tar.xz';assert sha(archive)==reports['package']['archive_sha256'];assert archive.with_name(archive.name+'.sha256').read_text().split()[0]==sha(archive)
 sdk={}
 for name,digest in [('Awl-0.24.0-dev-linux-x86_64.tar.xz','b8d14d845a1b3c730fac028f775c0c8e276a5e49c8d4b76b56623db1b0f1a1df'),('Awl-0.24.0-dev-windows-x86_64-preview.tar.xz','50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec')]:
  assert sha(ROOT.parent/name)==digest;sdk[name]=digest
 assert (ROOT/'apps/board/vendor/Json.aw').read_bytes()==(ROOT/'examples/parsing/Json.aw').read_bytes().replace(b'if string.bytes(source) > 16384 then fail(result, 2, 16384);',b'if string.bytes(source) > 65536 then fail(result, 2, 65536);')
 files=0;size=0;links=0
 for p in ROOT.parent.rglob('*'):
  if p.is_symlink():links+=1
  elif p.is_file():files+=1;size+=p.stat().st_size
 assert files<10000 and size<128000000,(files,size)
 bound=[p for p in (ROOT/'apps/board').rglob('*') if p.is_file()]+[ROOT/f'tests/board-{n}.json' for n in reports]+list((ROOT/'tests').glob('board*.py'))+[ROOT/'tests/board_faults.c',Path(__file__).resolve(),ROOT/'docs/CAPABILITY-ASSESSMENT.md',ROOT/'demos/board/Awl-board.png']
 result={'status':'PASS','capability':{'points':11,'maximum':45,'percentage':24.4,'change':'browser1->2, other eight areas unchanged'},'compiler_sha256':compiler,'public_executable_sha256':public,'application_archive':{'name':archive.name,'sha256':sha(archive),'bytes':archive.stat().st_size},'unchanged_sdk_archives':sdk,'sources_and_evidence':{str(p.relative_to(ROOT)):sha(p) for p in sorted(set(bound))},'home_at_check':{'bytes':size,'regular_files':files,'symlinks':links},'public_build':{'command':'awl build apps/board/main.aw -o awl-board -O 2','environment':'PATH=/no-host-tools, complete validated Linux SDK backend only'},'sanitizer_build':{'compiler':'host cc strict generated-C contributor acceptance','flags':'-std=c11 -O1 -Wall -Wextra -Werror -Wno-unused-function -fsanitize=address,undefined -fno-sanitize-recover=all -no-pie','fault_wrapper':'tests/board_faults.c'},'qualification':'useful bounded Linux full-stack app, native Awl plus shared Awl WASM and JS DOM/WASI glue, one server per trusted directory, contributor browser build, no native Windows/general DOM/concurrency/auth/TLS/locking acceptance, existing SDK archives unchanged'}
 (ROOT/'tests/board-checkpoint.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS board checkpoint',size,'bytes',files,'files',archive.stat().st_size,'archive bytes')
if __name__=='__main__':main()

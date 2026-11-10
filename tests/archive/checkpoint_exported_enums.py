#!/usr/bin/env python3
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 def load(n):
  p=ROOT/'tests'/n;raw=p.read_bytes();return json.loads(gzip.decompress(raw) if n.endswith('.gz') else raw)
 feature=load('exported-enums.json');compiler=feature['compiler_sha256'];assert feature['status']=='PASS' and feature['cases']==187
 for path,digest in feature['source_sha256'].items():assert sha(ROOT/path)==digest,path
 wasm=load('exported-enums-wasm.json');assert wasm['status']=='PASS' and wasm['compiler_sha256']==compiler and wasm['native_cases']==wasm['wasm_cases']==107
 private=load('exported-enums-private-regression.json');assert private['status']=='PASS' and private['compiler_sha256']==compiler and private['feature_cases']==54 and private['calc_cases_per_mode']=={'bundled':450,'sanitized':450}
 native=load('exported-enums-native.json.gz');assert native['status']=='PASS' and len(native['phases'])==11 and all(r['exit']==0 for r in native['phases'])
 verify=load('exported-enums-verifier.json');assert verify['status']=='PASS' and verify['cases']==7
 legacy=load('exported-enums-legacy.json');assert len(legacy)==3 and all(r['exit']==0 and r['tests']==564 and not r['skips'] and r['compiler_sha256']==compiler for r in legacy.values())
 regressions=load('exported-enums-regressions.json.gz');assert regressions['status']=='PASS' and regressions['compiler_sha256']==compiler and len(regressions['records'])==10
 board=load('exported-enums-board-parity.json');assert board['status']=='PASS' and board['candidate_compiler_sha256']==compiler
 assert sha(ROOT/'compiler/native/bin/kcc')==board['accepted_compiler_sha256']=='21856c691451f9c6b1483b4940878dc5f5c0993d7e7c9dbd740be8fb449742f1'
 paths=[p for p in (ROOT/'compiler/native').iterdir() if p.suffix in ['.cpp','.h','.inc','.c']]+list((ROOT/'examples/exported-enums').rglob('*.aw'))+list((ROOT/'tests').glob('exported*'))+[Path(__file__).resolve(),ROOT/'docs/EXPORTED-ENUMS.md',ROOT/'history/pre-exported-enums.tar.xz']
 archives={p.name:sha(p) for p in ROOT.parent.glob('*.tar.xz')}
 files=0;size=0
 for p in ROOT.parent.rglob('*'):
  if p.is_file() and not p.is_symlink():files+=1;size+=p.stat().st_size
 assert size<128000000 and files<10000,(size,files)
 result={'status':'PASS','candidate_compiler_sha256':compiler,'checked_in_compiler_unchanged':board['accepted_compiler_sha256'],'capability':{'points':11,'maximum':45,'percentage':24.4,'change':'none, language composition gap closed, not another cumulative workload stage'},'source_and_evidence_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths)) if p.is_file() and p.name not in ['exported-enums-checkpoint.json','exported-enums-home-audit.json']},'unchanged_public_archives':archives,'home_at_check':{'bytes':size,'regular_files':files},'qualification':'source-development Linux compiler, scalar/text/nonrecursive exported enums, native/sanitized/WASI and legacy qualification, published SDK/compiler binaries remain unchanged and do not yet contain this feature, no native Windows/generics/resource-payload claim','candidate_build_flags':'g++ -std=c++20 -O2 -Wall -Wextra -Werror -s -flto -ffunction-sections -fdata-sections -Wl,--gc-sections -static','candidate_shared_flags':'g++ -std=c++20 -Os -Wall -Wextra -Werror -shared -fPIC -fvisibility=hidden -s'}
 (ROOT/'tests/exported-enums-checkpoint.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS source checkpoint',size,'bytes',files,'files')
if __name__=='__main__':main()

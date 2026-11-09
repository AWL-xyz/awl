#!/usr/bin/env python3
import gzip,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HOME=ROOT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 focused=json.loads((ROOT/'tests/clean-syntax.json').read_text());assert focused['status']=='PASS' and focused['cases']==22 and focused['migrated_files']==47 and focused['equivalent_entry_c_outputs']==21
 verifier=json.loads((ROOT/'tests/clean-syntax-verifier.json').read_text());assert verifier['status']=='PASS' and verifier['cases']==8
 for name,digest in verifier['compiler_sources_sha256'].items():assert sha(ROOT/'compiler/native'/name)==digest,name
 migration=json.loads(gzip.decompress((ROOT/'tests/syntax-migration.json.gz').read_bytes()));assert len(migration)==47 and sum(x['entry_c_equivalent'] for x in migration)==21
 for item in migration:assert sha(ROOT/item['file'])==item['after_sha256'],item['file']
 for name in ['strings','generic','process']:subprocess.run(['python3',str(ROOT/'compiler'/('generate_'+name+'.py')),'--check'],check=True)
 release='3ae0337c85e535364bb774faa7ee1dffffc9187a39b77561038881d56d5f9971';assert sha(ROOT/'compiler/native/bin/kcc')==release
 protected={'Awl-0.24.0-dev-windows-x86_64-preview.tar.xz':'50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec'}
 for name,digest in protected.items():assert sha(HOME/name)==digest,name
 paths=['tests/clean-syntax.json','tests/clean-syntax-verifier.json','tests/syntax-migration.json.gz','tests/clean_syntax.py','compiler/migrate_next.py','docs/AESOP.md'];bound={p:sha(ROOT/p) for p in paths}
 files=[p for p in HOME.rglob('*') if p.is_file() and not p.is_symlink()];size=sum(p.stat().st_size for p in files);assert size<128000000 and len(files)<10000
 result={'status':'PASS','source_candidate_only':True,'candidate_compiler_sha256':focused['compiler_sha256'],'published_compiler_sha256':release,'bound_sha256':bound,'protected_archives':protected,'syntax_checks':22,'independent_verifier_cases':8,'migrated_files':47,'equivalent_entry_c_outputs':21,'qualifications':'native/ASan+UBSan/real WASI syntax checks, separate legacy compatibility, taskrun/logwindow native smoke, no broad old-fixture/editor/Windows/new SDK qualification','capability':'26.7%=12/45 unchanged','home_bytes_before_report':size,'home_files_before_report':len(files)}
 (ROOT/'tests/clean-syntax-checkpoint.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS clean syntax checkpoint',size,'bytes',len(files),'files')
if __name__=='__main__':main()

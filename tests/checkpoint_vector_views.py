#!/usr/bin/env python3
import gzip,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HOME=ROOT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CANDIDATE='8b31e29355d106192d08b430e167976c729aebc885b2449fc9604628357a95ed'
RELEASE='3ae0337c85e535364bb774faa7ee1dffffc9187a39b77561038881d56d5f9971'
def main():
 reports={}
 for name,count in [('vector-views',31),('vector-views-default',62),('vector-views-enums',187),('vector-views-typed',56),('vector-views-ops',35),('vector-views-logwindow',104)]:
  path=ROOT/'tests'/(name+'.json');d=json.loads(path.read_text());assert d['status']=='PASS' and d['cases']==count and d['compiler_sha256']==CANDIDATE,(name,d);reports[path.name]=sha(path)
 views=json.loads((ROOT/'tests/vector-views.json').read_text());assert views['oracle_output_lines_per_runtime']==981 and views['random_model_steps']==400;assert views['harness_sha256']==sha(ROOT/'tests/vector_views.py')
 log=json.loads((ROOT/'tests/vector-views-logwindow.json').read_text());assert log['harness_sha256']==sha(ROOT/'tests/logwindow.py')
 native_path=ROOT/'tests/vector-views-native.json.gz';native=json.loads(gzip.decompress(native_path.read_bytes()));assert native['status']=='PASS' and len(native['phases'])==12 and all(p['exit']==0 and not p['stderr'] for p in native['phases']);assert native['phases'][-1]['stdout']=='PASS 12 view independent verifier cases\n'
 for name,digest in native['native_sources_sha256'].items():assert sha(ROOT/'compiler/native'/name)==digest,name
 reports[native_path.name]=sha(native_path)
 runtime_path=ROOT/'tests/vector-views-runtime.json';runtime=json.loads(runtime_path.read_text());assert runtime['status']=='PASS' and len(runtime['cases'])==5;assert runtime['source_sha256']==sha(ROOT/'tests/vector_views_runtime.c') and runtime['runtime_sha256']==sha(ROOT/'compiler/native/kgeneric.c');reports[runtime_path.name]=sha(runtime_path)
 benchmark_path=ROOT/'benchmarks/vector-views.json';bench=json.loads(benchmark_path.read_text());assert bench['status']=='PASS' and bench['candidate_compiler_sha256']==CANDIDATE and bench['baseline_compiler_sha256']==RELEASE;assert [r['consumed_checksum'] for r in bench['results']]==[643289760,40724386816];reports['../benchmarks/vector-views.json']=sha(benchmark_path)
 subprocess.run(['python3',str(ROOT/'compiler/generate_generic.py'),'--check'],check=True)
 assert sha(ROOT/'compiler/native/bin/kcc')==RELEASE
 protected={'Awl-0.24.0-dev-windows-x86_64-preview.tar.xz':'50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec'}
 for name,digest in protected.items():
  assert sha(HOME/name)==digest,name
 files=[p for p in HOME.rglob('*') if p.is_file() and not p.is_symlink()];size=sum(p.stat().st_size for p in files);assert size<128000000 and len(files)<10000,(size,len(files))
 sources={str(p.relative_to(ROOT)):sha(p) for base in ['apps/logwindow'] for p in sorted((ROOT/base).rglob('*')) if p.is_file()};sources.update({str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tests/vector_views.py',ROOT/'tests/logwindow.py',ROOT/'tests/vector_views_benchmark.py',ROOT/'tests/vector_views_runtime.c',ROOT/'tests/vector_views_native.py',ROOT/'docs/VECTOR-VIEWS.md']})
 result={'status':'PASS','candidate_compiler_sha256':CANDIDATE,'unchanged_published_compiler_sha256':RELEASE,'source_candidate_only':True,'reports_sha256':reports,'source_sha256':sources,'protected_archives':protected,'native_sanitizer_phases':12,'capability_score':'24.4%=11/45, unchanged','qualification':'11 scalar/text read-only live vector views, runtime lifetime/epoch/range checks, Linux native/ASan+UBSan/real WASI, no static borrowing/concurrency/arbitrary element types/native Windows acceptance/new SDK publication','home_bytes_before_report':size,'home_files_before_report':len(files)}
 (ROOT/'tests/vector-views-checkpoint.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS checked view source checkpoint,12 native sanitizer phases, published0.25 unchanged,',size,'bytes',len(files),'files')
if __name__=='__main__':main()

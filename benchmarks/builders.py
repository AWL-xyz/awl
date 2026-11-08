#!/usr/bin/env python3
"""Measured warm full builds and validated synthetic whole-process workloads."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
    env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')};builds=[];runtime={}
    with tempfile.TemporaryDirectory(prefix='Awl-builders-bench-') as td:
        root=Path(td);out=root/'program'
        def build(source):
            start=time.perf_counter();r=subprocess.run([str(KCC),'build',str(source),'-O','2','-o',str(out)],env=env,capture_output=True,text=True,timeout=120)
            elapsed=(time.perf_counter()-start)*1000;assert r.returncode==0,r.stderr;return elapsed
        example=ROOT/'examples/builders/main.aw';build(example)
        expected='Awl café | 42\n14\n15\nInvalid scalar: recovered\nframe=99999\n100000 updates, one reusable builder\n'
        for _ in range(7):
            builds.append(build(example));r=subprocess.run([str(out)],env=env,capture_output=True,text=True);assert(r.returncode,r.stdout)==(0,expected),r.stderr
        for name,n in [('reuse',1000000),('create_release',100000)]:
            before='local b:spool=spool_new(64)' if name=='reuse' else ''
            inside='spool_clear(b)' if name=='reuse' else 'local b:spool=spool_new(64) if not spool_valid(b) then return 3 end'
            after='spool_free(b)' if name=='create_release' else ''
            final='spool_free(b)' if name=='reuse' else ''
            source=root/'bench.aw';source.write_text(f'function main()->i64 {before} local i:i64=0 local sum:i64=0 while i<{n} do {inside} if spool_append(b,"frame=")!=0 then return 1 end if spool_i64(b,i)!=0 then return 2 end sum=sum+spool_bytes(b) {after} i=i+1 end {final} print(sum) return 0 end')
            build(source);checksum=6*n+sum(len(str(i)) for i in range(n));samples=[]
            for i in range(8):
                start=time.perf_counter();r=subprocess.run([str(out)],env=env,capture_output=True,text=True);elapsed=(time.perf_counter()-start)*1000
                assert(r.returncode,r.stdout)==(0,str(checksum)+'\n'),r.stderr
                if i:samples.append(elapsed)
            runtime[name]={'iterations':n,'samples_ms':samples,'median_ms':statistics.median(samples),'checksum':checksum,'configured_builder_capacity_bytes':64,'expected_final_live_payload_bytes':0,'payload_evidence':'Private runtime accounting test separately validates64/32-byte reusable payload semantics and zero string-region allocations; this benchmark is not an RSS/fragmentation proof.'}
    report={'version':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Seven warm full source-to-static-executable example builds (all stages/linking) and seven whole-process wall samples each synthetic workload (startup/output included). Different iteration counts are not a direct speed comparison. No general application, concurrency, allocator fragmentation/RSS or production performance claim. Checksums validated.', 'build_samples_ms':builds,'build_median_ms':statistics.median(builds),'runtime':runtime}
    (ROOT/'benchmarks/builders-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

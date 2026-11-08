#!/usr/bin/env python3
"""Small native string workload: warm full builds and whole-executable timings.
No broad application, allocator throughput, or compiler-speedup claim."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
    env={**os.environ,'PATH':'/no-host-tools'};build_samples=[];runtime={}
    with tempfile.TemporaryDirectory(prefix='Awl-string-bench-') as td:
        root=Path(td);out=root/'program'
        def build(source):
            begin=time.perf_counter();r=subprocess.run([str(KCC),'build',str(source),'-O','2','-o',str(out)],env=env,capture_output=True,text=True,timeout=120)
            elapsed=(time.perf_counter()-begin)*1000;assert r.returncode==0,r.stderr;return elapsed
        example=ROOT/'examples/strings/main.aw';build(example)
        for _ in range(7):
            build_samples.append(build(example));r=subprocess.run([str(out)],capture_output=True,text=True,env=env)
            assert (r.returncode,r.stdout)==(0,'Hello, Awl 🚀!\n6\n9\n🚀\ntrue\nAnswer: 42\n'),r.stderr
        for label,text in [('ascii','abcdef'),('utf8','Aé🚀éZ')]:
            source=root/'work.aw';source.write_text('function main()->i64 local s:string="'+text+'" local sum:i64=0 local i:i64=0 while i<900000 do sum=sum+i64(string_codepoint(s,i%6)) i=i+1 end print(sum) return 0 end')
            build(source);expected=str(sum(map(ord,text))*150000)+'\n'
            samples=[]
            for i in range(8):
                start=time.perf_counter();r=subprocess.run([str(out)],env=env,capture_output=True,text=True);elapsed=(time.perf_counter()-start)*1000
                assert (r.returncode,r.stdout)==(0,expected),r.stderr
                if i:samples.append(elapsed)
            runtime[label]={'samples_ms':samples,'median_ms':statistics.median(samples),'checksum':expected.strip(),'scalars':len(text),'bytes':len(text.encode()),'codepoint_calls':900000}
    report={'compiler':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Local synthetic seven-sample warm full example builds, including all compiler stages and static linking. Runtime whole-process wall time includes startup/printing, 900000 scalar-indexed lookups into six-scalar text and checked integer accumulation, validated checksums. No allocator throughput/grapheme/general-app/large-input or speedup claim. O(index) scalar scanning remains.', 'build_samples_ms':build_samples,'build_median_ms':statistics.median(build_samples),'runtime':runtime}
    (ROOT/'benchmarks/strings-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

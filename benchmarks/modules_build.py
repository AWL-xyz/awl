#!/usr/bin/env python3
"""Full native warm builds: three-file module example vs equivalent monolith.
Tiny workload, same backend/flags; not general module scalability/perf evidence.
"""
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
KCC=ROOT/'build/Awl-linux-x86_64/bin/kcc'
def main():
    entry=ROOT/'examples/modules/main.aw'
    texts=[p.read_text() for p in [entry,entry.parent/'geometry/points.aw',entry.parent/'results.aw']]
    monolith='\n'.join('\n'.join(line for line in s.splitlines() if not line.startswith('import ')) for s in texts).replace('geo.','').replace('r.','')
    env={**os.environ,'PATH':'/no-host-tools'}
    with tempfile.TemporaryDirectory(prefix='Awl-module-bench-') as td:
        folder=Path(td);single=folder/'monolith.aw';single.write_text(monolith);output=folder/'program'
        def build(source):
            begin=time.perf_counter();r=subprocess.run([str(KCC),'build',str(source),'-O','2','-o',str(output)],capture_output=True,text=True,env=env,timeout=120)
            elapsed=(time.perf_counter()-begin)*1000
            assert r.returncode==0,r.stderr
            r=subprocess.run([str(output)],capture_output=True,text=True,env=env)
            assert (r.returncode,r.stdout)==(0,'10\n15\n3\n'),r.stderr
            return elapsed
        build(single);build(entry)
        samples={'monolith':[],'modules':[]}
        for i in range(7):
            for label in (['monolith','modules'] if i%2==0 else ['modules','monolith']):samples[label].append(build(single if label=='monolith' else entry))
    report={'compiler_version':subprocess.check_output([str(KCC),'--version'],text=True).strip(),'scope':'Full source-to-static-executable builds; tiny equivalent example; warm shared backend cache; alternating order; startup/filesystem/frontend/verification/C/codegen/linking included. Not a large-project or generated-runtime performance claim.',
            'samples_ms':samples,'median_ms':{k:statistics.median(v) for k,v in samples.items()},'module_files':3,'expected_output':'10\n15\n3\n'}
    (ROOT/'benchmarks/modules-build-latest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

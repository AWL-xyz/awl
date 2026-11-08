"""Actual Windows PE execution evidence under Wine; explicitly not native-host acceptance."""
from pathlib import Path
import hashlib,json,os,statistics,subprocess,time
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];bundle=ROOT/'build/windows-exact/Awl';wine='/usr/lib/wine/wine64';env={**os.environ,'WINEPREFIX':str(ROOT/'build/wine/prefix'),'WINEDEBUG':'-all'}
def win(p):return 'Z:'+str(p.resolve()).replace('/','\\')
def run(args):return subprocess.run([wine,*args],env=env,capture_output=True,text=True,timeout=180)
kcc=win(bundle/'bin/kcc.exe');source=win(bundle/'examples/apps/intstats/main.aw')
version=run([kcc,'--version']);assert version.returncode==0
checked=run([kcc,'check',source]);assert checked.returncode==0
blocked=run([kcc,'run',win(bundle/'examples/hello.aw')]);assert blocked.returncode==2 and 'unable to find zig self exe path: Unexpected' in blocked.stderr
upstream=run([win(bundle/'libexec/zig/zig.exe'),'env']);assert upstream.returncode!=0 and 'unable to find zig self exe path: Unexpected' in upstream.stderr
report=json.loads((ROOT/'tests/windows-exact-frontend-runtime.json').read_text());stats=next(c for c in report['commands'] if c['stdout'].startswith('count\n7\n'))
assert stats['stdout']=='count\n7\nminimum\n-9223372036854775808\nmaximum\n9223372036854775807\nsorted\n-9223372036854775808\n-7\n0\n19\n42\n42\n9223372036854775807\n'
samples=[]
for i in range(7):
 start=time.perf_counter();r=run([kcc,'check',source]);samples.append((time.perf_counter()-start)*1000);assert r.returncode==0
benchmark={'scope':'Seven warmed whole-process check (not full-build) samples of modular intstats by exact-extracted Windows kcc.exe under Wine10; emulator/process/filesystem overhead included. Not real Windows performance. Full Windows build benchmark blocked by upstream backend self-path failure.','samples_ms':samples,'median_ms':statistics.median(samples)}
(ROOT/'benchmarks/windows-frontend-wine.json').write_text(json.dumps(benchmark,indent=2)+'\n')
evidence={'execution':'Windows PE under Wine10, not native Windows','version_stdout':version.stdout,'check_stdout':checked.stdout,'intstats':stats,'installed_run':{'exit':blocked.returncode,'stderr':blocked.stderr},'direct_upstream_zig_env':{'exit':upstream.returncode,'stderr':upstream.stderr},'benchmark':benchmark}
(ROOT/'demos/windows/execution.json').write_text(json.dumps(evidence,indent=2)+'\n')
im=Image.new('RGB',(1400,1070),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,29),'Awl / 0.20.0-dev · WINDOWS PORT',font=f(19),fill='#78e2bd')
d.text((48,75),'Native compiler. Two required platforms.',font=f(36),fill='#f1f5fd')
d.text((48,135),'Linux accepted release retained · Windows complete engineering preview · no SDK required by design',font=f(21),fill='#a4b8d1')
d.rounded_rectangle((48,184,1352,284),radius=12,fill='#203149')
d.text((69,203),'ACTUAL WINDOWS COMPILER OUTPUT · Windows PE executed under Wine10',font=f(18),fill='#78e2bd')
d.text((69,240),version.stdout.strip(),font=f(21,True),fill='#e4edff')
d.rounded_rectangle((48,306,698,783),radius=14,fill='#0a101a')
d.text((69,327),'ACTUAL WINDOWS INTSTATS STDOUT',font=f(18),fill='#78e2bd')
d.text((69,359),'PE cross-built by separate Linux test tool; run in Wine.',font=f(16),fill='#a4b8d1')
for i,line in enumerate(stats['stdout'].splitlines()):d.text((69,400+i*25),line,font=f(21,True),fill='#88edc0')
d.rounded_rectangle((720,306,1352,783),radius=14,fill='#19243a')
lines=['IMPLEMENTED / TESTED WITH QUALIFICATIONS','• Native kcc.exe + Win32 build/run driver','• Job supervision, timeouts, atomic output','• UTF-16 arguments / UTF-8 source provenance','• Spaces + non-ASCII paths; protected sources','• 21 fake-backend driver cases; NOT real backend','• 325 + 10,000 Windows verifier corruptions','• Linux: 530 tests × 3 frontend paths; zero skips','','WINDOWS ACCEPTANCE IS NOT COMPLETE','• Actual installed-backend build: BLOCKED here','• Real Windows-host CI included, NOT run','• Windows GUI window creation: still missing']
for i,line in enumerate(lines):d.text((741,330+i*33),line,font=f(18),fill='#78e2bd' if i==0 else '#f3b6ba' if i==9 else '#dbe8fc')
d.rounded_rectangle((48,806,1352,929),radius=14,fill='#30202b')
d.text((69,824),'ACTUAL UPSTREAM BLOCKER · reproduced by direct zig.exe env without Awl',font=f(19),fill='#f3b6ba')
d.text((69,864),'error: unable to find zig self exe path: Unexpected',font=f(23,True),fill='#f3b6ba')
d.text((69,899),'Wine10 backend self-path incompatibility. No Linux backend substituted to conceal it.',font=f(16),fill='#e3aeb7')
d.text((48,955),'Next: real Windows build/run acceptance + Win32 GUI parity, then portable file/stream I/O.',font=f(21),fill='#afbed3')
d.text((48,1005),'Actual execution transcript, not a GUI screenshot. Windows support remains an unfinished milestone.',font=f(17),fill='#8295b0')
im.save(ROOT/'demos/windows/native-windows-preview.png',optimize=True)
print(json.dumps({'version':version.stdout.strip(),'backend_exit':blocked.returncode,'direct_upstream_exit':upstream.returncode,'wine_check_median_ms':benchmark['median_ms']},indent=2))

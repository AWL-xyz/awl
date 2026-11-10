"""Render actual self-contained native product output; no invented GUI capture."""
from pathlib import Path
import os,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
kcc=Path(os.environ.get('Awl_PREVIEW_KCC',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/builders/main.aw')],env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')},capture_output=True,text=True,check=True,timeout=120)
expected='Awl café | 42\n14\n15\nInvalid scalar: recovered\nframe=99999\n100000 updates, one reusable builder\n'
assert r.stdout==expected,r.stdout
im=Image.new('RGB',(1280,960),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,30),'Awl / 0.8.3-dev',font=f(17),fill='#70e1bf')
d.text((48,68),'Reusable text. Reclaimed storage.',font=f(35),fill='#f4f7ff')
d.text((48,122),'Typed builder  /  Atomic append failures  /  Recoverable errors',font=f(20),fill='#a0b3ce')
d.rounded_rectangle((48,171,1232,246),radius=14,fill='#1c293c')
d.text((68,184),'GENERAL-PURPOSE 1.0 ROADMAP',font=f(13),fill='#94a9c8')
d.text((68,210),'~15%  ·  subjective scope estimate, not a completeness measurement',font=f(19),fill='#dce8fa')
d.rounded_rectangle((48,267,1232,548),radius=14,fill='#192337')
d.text((70,285),'ACTUAL EXAMPLE LOOP · examples/builders/main.aw',font=f(14),fill='#70e1bf')
lines=['while i<100000 do','    spool.clear(b)','    if spool.append(b,"frame=")!=0 then return 5 end','    if spool.i64(b,i)!=0 then return 6 end','    i=i+1','end']
for i,line in enumerate(lines):d.text((70,323+i*32),line,font=f(22,True),fill='#dae8fc')
d.rounded_rectangle((48,568,1232,839),radius=14,fill='#0a101a')
d.text((70,586),'ACTUAL NATIVE PROGRAM OUTPUT · Awl-ONLY TOOLCHAIN',font=f(14),fill='#91a8c9')
for i,line in enumerate(r.stdout.splitlines()):d.text((70,624+i*32),line,font=f(23,True),fill='#85eec1')
d.text((48,862),'One 64-byte builder reused, then explicitly released. Not ownership checking.',font=f(18),fill='#afbed3')
d.text((48,896),'Snapshots still use the bounded string region. Output preview, not a GUI screenshot.',font=f(16),fill='#8295b0')
p=ROOT/'demos/builders/reusable-text.png';im.save(p,optimize=True);print(r.stdout);print(p,p.stat().st_size)

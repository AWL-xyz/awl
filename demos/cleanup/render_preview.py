"""Render actual self-contained native product output; no invented GUI capture."""
from pathlib import Path
import os,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
kcc=Path(os.environ.get('Awl_PREVIEW_KCC',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/cleanup/main.aw')],env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')},capture_output=True,text=True,check=True,timeout=120)
expected='frame=99999\n100000 calls: scoped cleanup on every return\ncafé\nInner scope released before this line\n'
assert r.stdout==expected,r.stdout
im=Image.new('RGB',(1280,960),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,30),'Awl / 0.8.4-dev',font=f(17),fill='#70e1bf')
d.text((48,68),'Capture now. Release on scope exit.',font=f(35),fill='#f4f7ff')
d.text((48,122),'Scoped defer  /  LIFO release order  /  Early-return cleanup',font=f(20),fill='#a0b3ce')
d.rounded_rectangle((48,171,1232,246),radius=14,fill='#1c293c')
d.text((68,184),'GENERAL-PURPOSE 1.0 ROADMAP',font=f(13),fill='#94a9c8')
d.text((68,210),'~15%  ·  subjective scope estimate, not a completeness measurement',font=f(19),fill='#dce8fa')
d.rounded_rectangle((48,267,1232,548),radius=14,fill='#192337')
d.text((70,285),'EXAMPLE CORE · printing branch omitted',font=f(14),fill='#70e1bf')
lines=['local b:spool=spool.new(64)','if not spool.valid(b) then return 1 end','defer spool.free(b)','if spool.append(b,"frame=")!=0 then return 2 end','if spool.i64(b,index)!=0 then return 3 end','return 0']
for i,line in enumerate(lines):d.text((70,323+i*32),line,font=f(22,True),fill='#dae8fc')
d.rounded_rectangle((48,568,1232,839),radius=14,fill='#0a101a')
d.text((70,586),'ACTUAL NATIVE PROGRAM OUTPUT · Awl-ONLY TOOLCHAIN',font=f(14),fill='#91a8c9')
for i,line in enumerate(r.stdout.splitlines()):d.text((70,624+i*32),line,font=f(23,True),fill='#85eec1')
d.text((48,862),'Handle captured once; released on normal scope exit or return.',font=f(18),fill='#afbed3')
d.text((48,896),'Not ownership/borrow checking or abort unwinding. Actual output, not a GUI screenshot.',font=f(16),fill='#8295b0')
p=ROOT/'demos/cleanup/scoped-resource-cleanup.png';im.save(p,optimize=True);print(r.stdout);print(p,p.stat().st_size)

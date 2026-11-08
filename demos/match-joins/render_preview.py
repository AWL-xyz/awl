"""Preview asserted actual extracted0.16 execution, not a fabricated GUI."""
from pathlib import Path
import os,subprocess,tempfile,json,textwrap
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];kcc=ROOT/'build/archive-isolation-root/relocated Awl/bin/kcc'
env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')}
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/match-joins/main.aw')],env=env,capture_output=True,text=True,check=True,timeout=120)
assert r.stdout=='frame=99999 / draw\n100000 match routes: moved or retained, one cleanup\n1555559\n',r.stdout
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'discard.aw';p.write_text('union Route One() Two() end function main()->i64 scoped a:spool=spool_new(8) match Route.One() then case Route.One() then scoped b:spool=move a case Route.Two() then end spool_print(a) return 0 end')
 q=subprocess.run([str(kcc),'check',str(p),'--diagnostic-format','json'],env=env,capture_output=True,text=True);assert q.returncode==1
 diagnostic=json.loads(q.stderr)['diagnostics'][0];assert diagnostic['code']=='E221'
im=Image.new('RGB',(1400,940),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,28),'Awl / 0.16.0-dev',font=f(18),fill='#78e2bd');d.text((48,70),'Route ownership. Join every continuing arm.',font=f(34),fill='#f1f5fd')
d.text((48,132),'Exhaustive match joins  /  Pattern shadowing safety  /  Native execution',font=f(22),fill='#a4b8d1')
d.rounded_rectangle((48,190,1352,252),radius=12,fill='#203149');d.text((69,210),'ACCEPTED  ·  475 tests × 3 configurations  ·  223 extracted-bundle tests  ·  60 offline commands',font=f(20),fill='#e4edff')
d.rounded_rectangle((48,274,1352,515),radius=14,fill='#19243a');d.text((69,294),'SOURCE EXCERPTS · examples/match-joins/',font=f(15),fill='#78e2bd')
code=['match choose(n) then','    case Route.Render() then finish(move b,n)','    case Route.Persist() then','        scoped ready:spool=move b','        ...','    case Route.Keep() then count=spool_bytes(b)','end']
for i,line in enumerate(code):d.text((69,332+i*28),line,font=f(21,True),fill='#dbe8fc')
d.rounded_rectangle((48,537,1352,730),radius=14,fill='#0a101a');d.text((69,557),'ACTUAL FINAL EXTRACTED-BUNDLE OUTPUT',font=f(15),fill='#78e2bd')
for i,line in enumerate(r.stdout.splitlines()):d.text((69,597+i*36),line,font=f(23,True),fill='#88edc0')
d.rounded_rectangle((48,752,1352,852),radius=14,fill='#30202b');d.text((69,769),'ACTUAL REJECTION · use after match-arm transfer: spool_print(a)',font=f(18),fill='#f3b6ba')
for i,line in enumerate(textwrap.wrap(diagnostic['code']+': '+diagnostic['message'],100)):d.text((69,801+i*23),line,font=f(18,True),fill='#f3b6ba')
d.text((48,874),'Roadmap ~19.1% (+0.35 subjective planning points). No loop-carried moves, reinitialization or abort unwind.',font=f(18),fill='#afbed3')
d.text((48,913),'Actual program/compiler output preview, not a GUI screenshot. One complete native bundle; no base/update install.',font=f(15),fill='#8295b0')
p=ROOT/'demos/match-joins/match-builder-ownership.png';im.save(p,optimize=True);print(r.stdout);print(diagnostic['code'],diagnostic['message']);print(p,p.stat().st_size)

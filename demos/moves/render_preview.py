"""Assert and show actual extracted native release output and E221 rejection."""
from pathlib import Path
import os,subprocess,tempfile,json,textwrap
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
kcc=Path(os.environ.get('Awl_PREVIEW_KCC',str(ROOT/'build/archive-isolation-root/relocated Awl/bin/kcc')))
env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')}
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/moves/main.aw')],env=env,capture_output=True,text=True,check=True,timeout=120)
assert r.stdout=='frame=99999 / moved\n100000 local moves: one release per owner\n1888890\nMoved unavailable descriptor remains unavailable\nfalse\n',r.stdout
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'moved.aw';p.write_text('function main()->i64 scoped building:spool=spool.new(32) scoped ready:spool=move building print(spool.valid(building)) return 0 end')
 q=subprocess.run([str(kcc),'check',str(p),'--diagnostic-format','json'],env=env,capture_output=True,text=True,timeout=20);assert q.returncode==1
 diagnostic=json.loads(q.stderr)['diagnostics'][0];assert diagnostic['code']=='E221'
im=Image.new('RGB',(1280,940),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,26),'Awl / 0.12.0-dev',font=f(18),fill='#78e2bd');d.text((48,68),'Move the owner. Retire the old binding.',font=f(34),fill='#f1f5fd')
d.text((48,124),'Same-block transfer  /  Static use-after-move rejection  /  Exactly one normal-exit release',font=f(19),fill='#a4b8d1')
d.rounded_rectangle((48,176,1232,239),radius=12,fill='#203149');d.text((69,196),'ROADMAP ~17.3%  |  +0.30 accepted planning points — subjective, not measured completeness',font=f(18),fill='#e4edff')
d.rounded_rectangle((48,260,632,662),radius=14,fill='#19243a');d.rounded_rectangle((652,260,1232,662),radius=14,fill='#0a101a')
d.text((69,282),'SOURCE EXCERPTS · examples/moves/main.aw',font=f(14),fill='#78e2bd');d.text((675,282),'ACTUAL EXTRACTED-BUNDLE OUTPUT',font=f(14),fill='#78e2bd')
code=['scoped building:spool=','    spool.new(32)','','prepare(building,n)','','scoped ready:spool=move building','','spool.append(ready," / moved")','return spool.bytes(ready)']
for i,line in enumerate(code):d.text((69,324+i*34),line,font=f(18,True),fill='#dbe8fc')
for i,line in enumerate(r.stdout.splitlines()):d.text((675,335+i*58),line,font=f(18,True),fill='#88edc0' if line in ['1888890','false'] else '#dbe8fc')
d.rounded_rectangle((48,684,1232,854),radius=14,fill='#30202b');d.text((69,704),'OLD BINDING USE · actual compiler rejection after move',font=f(15),fill='#f3b6ba');d.text((69,742),'spool.valid(building)',font=f(22,True),fill='#f5d5db')
for i,line in enumerate(textwrap.wrap(diagnostic['code']+': '+diagnostic['message'],95)):d.text((69,789+i*28),line,font=f(18,True),fill='#f3b6ba')
d.text((48,876),'Local scoped builders only; no cross-block, function-argument/return or aggregate ownership transfer.',font=f(17),fill='#afbed3')
d.text((48,912),'Actual program/compiler output preview, not a GUI screenshot. Complete native bundle; no base or overlay.',font=f(14),fill='#8295b0')
p=ROOT/'demos/moves/local-builder-moves.png';im.save(p,optimize=True);print(r.stdout);print(diagnostic['code'],diagnostic['message']);print(p,p.stat().st_size)

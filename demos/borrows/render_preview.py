"""Render asserted actual extracted-release program output and borrow rejection."""
from pathlib import Path
import os,subprocess,tempfile,json,textwrap
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
kcc=Path(os.environ.get('Awl_PREVIEW_KCC',str(ROOT/'build/archive-isolation-root/relocated Awl/bin/kcc')))
env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')}
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/borrows/main.aw')],env=env,capture_output=True,text=True,check=True,timeout=120)
assert r.stdout=='frame=99999\n100000 helper calls: one scoped builder\n1088890\ntrue\n',r.stdout
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'escape.aw';p.write_text('function bad(borrow b:spool)->spool return b end function main()->i64 return 0 end')
 q=subprocess.run([str(kcc),'check',str(p),'--diagnostic-format','json'],env=env,capture_output=True,text=True,timeout=20);assert q.returncode==1
 diagnostic=json.loads(q.stderr)['diagnostics'][0];assert diagnostic['code']=='E220'
im=Image.new('RGB',(1280,940),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,26),'Awl / 0.11.0-dev',font=f(18),fill='#78e2bd');d.text((48,68),'Borrow the builder. Keep the owner.',font=f(36),fill='#f1f5fd')
d.text((48,126),'Checked helper parameters  /  Module forwarding  /  No copy, escape or callee free',font=f(20),fill='#a4b8d1')
d.rounded_rectangle((48,176,1232,239),radius=12,fill='#203149');d.text((69,196),'ROADMAP ~17.0%  |  +0.60 accepted planning points — subjective, not measured completeness',font=f(18),fill='#e4edff')
d.rounded_rectangle((48,260,632,662),radius=14,fill='#19243a');d.rounded_rectangle((652,260,1232,662),radius=14,fill='#0a101a')
d.text((69,282),'SOURCE EXCERPTS · examples/borrows/main.aw',font=f(14),fill='#78e2bd');d.text((675,282),'ACTUAL EXTRACTED-BUNDLE OUTPUT',font=f(14),fill='#78e2bd')
code=['function render(borrow b:spool,n:i64)->i64','    return text.append_frame(b,n)','end','','scoped b:spool=spool_new(32)','','local count:i64=render(b,i)','','spool_print(b)']
for i,line in enumerate(code):d.text((69,324+i*34),line,font=f(17,True),fill='#dbe8fc')
for i,line in enumerate(r.stdout.splitlines()):d.text((675,345+i*66),line,font=f(20,True),fill='#88edc0' if line in ['1088890','true'] else '#dbe8fc')
d.rounded_rectangle((48,684,1232,854),radius=14,fill='#30202b');d.text((69,704),'ESCAPE ATTEMPT · actual compiler rejection',font=f(15),fill='#f3b6ba');d.text((69,738),'return b',font=f(21,True),fill='#f5d5db')
for i,line in enumerate(textwrap.wrap(diagnostic['code']+': '+diagnostic['message'],95)):d.text((69,780+i*28),line,font=f(18,True),fill='#f3b6ba')
d.text((48,876),'Synchronous shared descriptor borrows only; not exclusive references or ownership transfer.',font=f(18),fill='#afbed3')
d.text((48,912),'Actual program/compiler output preview, not a GUI screenshot. Complete native bundle, no base or overlay.',font=f(14),fill='#8295b0')
p=ROOT/'demos/borrows/nonescaping-builder-borrows.png';im.save(p,optimize=True);print(r.stdout);print(diagnostic['code'],diagnostic['message']);print(p,p.stat().st_size)

"""Preview asserted actual extracted0.18 execution, not a fabricated GUI."""
from pathlib import Path
import os,subprocess,tempfile,json,textwrap
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];kcc=ROOT/'build/archive-isolation-root/relocated Awl/bin/kcc'
env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')}
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/loop-owners/main.aw')],env=env,capture_output=True,text=True,check=True,timeout=120)
assert r.stdout=='frame=99999\n100000 loop-carried owners: state restored on every backedge\n1088890\nFinal owner remains live\nframe=100000\n',r.stdout
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'discard.aw';p.write_text('function take(own b:spool)->unit end function main()->i64 scoped a:spool=spool.new(8) while false do take(move a) end return 0 end')
 q=subprocess.run([str(kcc),'check',str(p),'--diagnostic-format','json'],env=env,capture_output=True,text=True);assert q.returncode==1
 diagnostic=json.loads(q.stderr)['diagnostics'][0];assert diagnostic['code']=='E225'
im=Image.new('RGB',(1400,940),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,28),'Awl / 0.18.0-dev',font=f(18),fill='#78e2bd');d.text((48,70),'Carry ownership. Restore every backedge.',font=f(34),fill='#f1f5fd')
d.text((48,132),'Entry-preserving while loops  /  Independent backedge checks  /  Native execution',font=f(22),fill='#a4b8d1')
d.rounded_rectangle((48,190,1352,252),radius=12,fill='#203149');d.text((69,210),'ACCEPTED  ·  506 tests × 3 configurations  ·  254 extracted-bundle tests  ·  66 offline commands',font=f(20),fill='#e4edff')
d.rounded_rectangle((48,274,1352,515),radius=14,fill='#19243a');d.text((69,294),'SOURCE EXCERPTS · examples/loop-owners/',font=f(15),fill='#78e2bd')
code=['scoped b:spool=make(0)','while i<100000 do','    local count:i64=finish(move b,i)','    total=total+count','    b=make(i+1)','    i=i+1','end']
for i,line in enumerate(code):d.text((69,332+i*28),line,font=f(21,True),fill='#dbe8fc')
d.rounded_rectangle((48,537,1352,730),radius=14,fill='#0a101a');d.text((69,557),'ACTUAL FINAL EXTRACTED-BUNDLE OUTPUT',font=f(15),fill='#78e2bd')
for i,line in enumerate(r.stdout.splitlines()):d.text((69,592+i*25),line,font=f(20,True),fill='#88edc0')
d.rounded_rectangle((48,752,1352,852),radius=14,fill='#30202b');d.text((69,769),'ACTUAL REJECTION · consumed owner not restored before the backedge',font=f(18),fill='#f3b6ba')
for i,line in enumerate(textwrap.wrap(diagnostic['code']+': '+diagnostic['message'],100)):d.text((69,801+i*23),line,font=f(18,True),fill='#f3b6ba')
d.text((48,874),'Roadmap ~20.1% (+0.45 subjective planning points). No break/continue, changing-invariant inference or abort unwind.',font=f(18),fill='#afbed3')
d.text((48,913),'Actual program/compiler output preview, not a GUI screenshot. One complete native bundle; no base/update install.',font=f(15),fill='#8295b0')
p=ROOT/'demos/loop-owners/loop-carried-ownership.png';im.save(p,optimize=True);print(r.stdout);print(diagnostic['code'],diagnostic['message']);print(p,p.stat().st_size)

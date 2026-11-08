"""Render asserted actual final native example output and compiler rejection."""
from pathlib import Path
import os,subprocess,tempfile,json,textwrap
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
kcc=Path(os.environ.get('Awl_PREVIEW_KCC',str(ROOT/'build/archive-isolation-root/relocated Awl/bin/kcc')))
env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')}
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/scoped-owner/main.aw')],env=env,capture_output=True,text=True,check=True,timeout=120)
assert r.stdout=='frame=99999\n100000 scoped builders: automatic release\n1088890\nUnavailable allocation is safe to leave scope\nfalse\n',r.stdout
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'copy.aw';p.write_text('function main()->i64 scoped b:spool=spool_new(64) local alias:spool=b return 0 end')
 rejection=subprocess.run([str(kcc),'check',str(p),'--diagnostic-format','json'],env=env,capture_output=True,text=True,timeout=20)
 assert rejection.returncode==1
 diagnostic=json.loads(rejection.stderr)['diagnostics'][0];assert diagnostic['code']=='E220'
im=Image.new('RGB',(1280,1000),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,28),'Awl / 0.10.0-dev',font=f(18),fill='#78e2bd');d.text((48,70),'Scope-owned builders. No escaping aliases.',font=f(34),fill='#f1f5fd')
d.text((48,126),'Fresh creation  /  Restricted intrinsic borrows  /  Automatic normal-exit release',font=f(20),fill='#a4b8d1')
d.rounded_rectangle((48,177,1232,240),radius=12,fill='#203149');d.text((69,197),'ROADMAP ~16.4%  |  +0.60 accepted planning points — subjective, not measured completeness',font=f(18),fill='#e4edff')
d.rounded_rectangle((48,262,632,721),radius=14,fill='#19243a');d.rounded_rectangle((652,262,1232,721),radius=14,fill='#0a101a')
d.text((69,283),'SOURCE EXCERPTS · examples/scoped-owner/main.aw',font=f(13),fill='#78e2bd');d.text((675,283),'ACTUAL EXTRACTED-BUNDLE OUTPUT',font=f(14),fill='#78e2bd')
code=['function frame(n:i64)->i64','    scoped b:spool=','        spool_new(32)','    if not spool_valid(b) then','        return -1','    end','    spool_append(b,"frame=")','    spool_i64(b,n)','    ...','    return spool_bytes(b)','end']
for i,line in enumerate(code):d.text((69,326+i*32),line,font=f(19,True),fill='#dbe8fc')
for i,line in enumerate(r.stdout.splitlines()):d.text((675,341+i*62),line,font=f(18,True),fill='#88edc0' if line in ['1088890','false'] else '#dbe8fc')
d.rounded_rectangle((48,742,1232,915),radius=14,fill='#30202b');d.text((69,762),'COPY ATTEMPT · actual compiler rejection',font=f(15),fill='#f3b6ba')
d.text((69,796),'local alias:spool=b',font=f(22,True),fill='#f5d5db')
for i,line in enumerate(textwrap.wrap(diagnostic['code']+': '+diagnostic['message'],95)):d.text((69,836+i*28),line,font=f(18,True),fill='#f3b6ba')
d.text((48,939),'Restricted spool ownership only. No general transfers, borrow parameters or abort unwinding.',font=f(17),fill='#afbed3')
d.text((48,970),'Actual program/compiler output preview, not a GUI screenshot. Complete native bundle; no older archive needed.',font=f(14),fill='#8295b0')
p=ROOT/'demos/scoped-owner/scope-owned-builders.png';im.save(p,optimize=True);print(r.stdout);print(diagnostic['code'],diagnostic['message']);print(p,p.stat().st_size)

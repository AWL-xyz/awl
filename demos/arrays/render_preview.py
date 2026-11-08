"""Render asserted final native program output, regrouping pairs into a table."""
import os,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
kcc=Path(os.environ.get('Awl_PREVIEW_KCC',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/arrays/main.aw')],env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')},capture_output=True,text=True,check=True,timeout=120)
expected='Typed arrays: original / doubled\n3\n6\n7\n14\n11\n22\n15\n30\nNested update\n42\nValue copies preserve the original\ntrue\n'
assert r.stdout==expected,r.stdout
output=r.stdout.splitlines();rows=[(output[1+i*2],output[2+i*2]) for i in range(4)]
im=Image.new('RGB',(1280,960),'#101621');d=ImageDraw.Draw(im)
def f(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,30),'Awl / 0.9.0-dev',font=f(17),fill='#70e1bf');d.text((48,68),'Typed arrays. Checked access. Value copies.',font=f(32),fill='#f4f7ff')
d.text((48,120),'Nested arrays  /  Element updates  /  Functions, structs and modules',font=f(19),fill='#a0b3ce')
d.rounded_rectangle((48,167,1232,242),radius=14,fill='#1c293c')
d.text((70,180),'GENERAL-PURPOSE 1.0 ROADMAP',font=f(13),fill='#94a9c8');d.text((70,206),'~15.5%  |  +0.60 planning points for accepted array milestone',font=f(19),fill='#dce8fa')
d.rounded_rectangle((48,263,1232,524),radius=14,fill='#192337');d.text((70,282),'SOURCE EXCERPTS · examples/arrays/main.aw',font=f(14),fill='#70e1bf')
code=['local original:[i64;4]=[3,7,11,15]','local result:Samples=Samples(doubled(original))','local grid:[[i64;2];2]=[[1,2],[3,4]]','grid[1][0]=42','print(grid[1][0])']
for i,line in enumerate(code):d.text((70,321+i*34),line,font=f(23,True),fill='#dae8fc')
d.rounded_rectangle((48,544,1232,849),radius=14,fill='#0a101a');d.text((70,563),'ACTUAL NATIVE OUTPUT · pairs regrouped into columns',font=f(14),fill='#91a8c9')
d.text((70,604),'Original',font=f(21),fill='#9db0c9');d.text((285,604),'Doubled',font=f(21),fill='#9db0c9')
for i,(a,b) in enumerate(rows):d.text((70,645+i*42),a,font=f(27,True),fill='#dbe8fc');d.text((285,645+i*42),b,font=f(27,True),fill='#85eec1')
d.text((575,614),output[9],font=f(21),fill='#9db0c9');d.text((575,651),output[10],font=f(34,True),fill='#85eec1')
d.text((575,716),'Original preserved after copy/update?',font=f(20),fill='#9db0c9');d.text((575,752),output[12],font=f(27,True),fill='#85eec1')
d.text((48,870),'Fixed-size value arrays, not dynamic collections or ownership. Large copies can use stack space.',font=f(16),fill='#afbed3')
d.text((48,904),'Roadmap progress is subjective, not measured completeness. Output preview, not a GUI screenshot.',font=f(15),fill='#8295b0')
p=ROOT/'demos/arrays/typed-arrays.png';im.save(p,optimize=True);print(r.stdout);print(p,p.stat().st_size)

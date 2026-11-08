"""Preview asserted output of the final extracted complete native bundle."""
from pathlib import Path
import subprocess,os
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
kcc=Path(os.environ.get('Awl_PREVIEW_KCC',str(ROOT/'build/archive-isolation-root/relocated Awl/bin/kcc')))
r=subprocess.run([str(kcc),'run',str(ROOT/'examples/repeat/main.aw')],env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':str(Path.home()/'.cache')},capture_output=True,text=True,check=True,timeout=120)
assert r.stdout=='Compact fixed arrays\nSeed evaluated once\n1024\n7168\nIndependent rows after copy\n0\n42\n0\n',r.stdout
im=Image.new('RGB',(1280,850),'#101621');d=ImageDraw.Draw(im)
def f(size,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),size)
d.text((48,25),'Awl / 0.9.1-dev',font=f(18),fill='#78e2bd');d.text((48,65),'Compact arrays. One complete download.',font=f(34),fill='#f1f5fd')
d.text((48,121),'Native compiler + pinned toolchain + runtime resources. No base / update install.',font=f(20),fill='#a4b8d1')
d.rounded_rectangle((48,171,1232,230),radius=12,fill='#203149');d.text((69,188),'ROADMAP  ~15.8%   |   +0.30 accepted planning points (subjective, not measured completeness)',font=f(18),fill='#e4edff')
d.rounded_rectangle((48,252,632,745),radius=14,fill='#19243a');d.rounded_rectangle((652,252,1232,745),radius=14,fill='#0a101a')
d.text((69,273),'SOURCE EXCERPTS · examples/repeat/main.aw',font=f(14),fill='#78e2bd');d.text((675,273),'ACTUAL EXTRACTED-BUNDLE OUTPUT',font=f(15),fill='#78e2bd')
code=['function seed()->i64','    print("Seed evaluated once")','    return 7','end','','local values:[i64;1024]=[seed();1024]','','local grid:[[i64;4];3]=[[0;4];3]','grid[1][2]=42']
for i,line in enumerate(code):d.text((69,319+i*39),line,font=f(21,True),fill='#dbe8fc')
for i,line in enumerate(r.stdout.splitlines()):d.text((675,325+i*46),line,font=f(24,True),fill='#88edc0' if line in ['1024','7168','42'] else '#dbe8fc')
d.text((48,771),'Seed runs once; nested array copies are independent. Resource descriptor copies still alias.',font=f(18),fill='#afbed3')
d.text((48,806),'Fixed arrays, not ownership or dynamic containers. Real output preview, not a GUI screenshot.',font=f(16),fill='#8295b0')
p=ROOT/'demos/repeat/compact-arrays-complete-bundle.png';im.save(p,optimize=True);print(r.stdout);print(p,p.stat().st_size)

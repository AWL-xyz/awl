"""Contributor preview: execute native Awl-emitted C, then render actual stdout.
Uses host cc/Pillow only for this preview fixture, not installed Awl use."""
from pathlib import Path
import subprocess,tempfile
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
    c=Path(td)/'preview.c';exe=Path(td)/'preview'
    r=subprocess.run([str(root/'compiler/native/bin/kcc'),'emit-c',str(root/'examples/strings/preview.aw')],capture_output=True,text=True,check=True);c.write_text(r.stdout)
    subprocess.run(['cc','-std=c11','-O2',str(c),'-o',str(exe)],check=True)
    r=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
    assert r.stdout=='Hello, Awl café!\nScalars: 9\nBytes: 10\nSlice: café\ntrue\n',r.stdout
im=Image.new('RGB',(1200,780),'#101622');d=ImageDraw.Draw(im)
def font(n,mono=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+('DejaVuSansMono.ttf' if mono else 'DejaVuSans.ttf'),n)
d.text((48,35),'Awl / 0.8.2-dev',font=font(17),fill='#72e0c0');d.text((48,70),'Native UTF-8 strings',font=font(36),fill='#f0f5ff')
d.text((48,124),'Immutable text  /  Unicode scalar slicing  /  Exact byte counts',font=font(18),fill='#9cacc3')
d.rounded_rectangle((40,177,1160,470),radius=16,fill='#182336');d.text((64,197),'EXAMPLE  ·  examples/strings/preview.aw',font=font(15),fill='#72e0c0')
lines=['local text: string = "Awl café"','print("Hello, " + text + "!")','print("Scalars: " + string.fromi64(string.length(text)))','print("Bytes: " + string.fromi64(string.bytes(text)))','print("Slice: " + string.slice(text,5,4))','print(string.codepoint(text,8) == 233u32)']
for i,line in enumerate(lines):d.text((64,238+i*32),line,font=font(21,True),fill='#d5e3f8')
d.rounded_rectangle((40,490,1160,714),radius=16,fill='#0b111b');d.text((64,507),'ACTUAL PROGRAM OUTPUT',font=font(14),fill='#8498b5')
for i,line in enumerate(r.stdout.splitlines()):d.text((64,540+i*30),line,font=font(22,True),fill='#81ebbc')
d.text((48,738),'Output preview, not a GUI screenshot. String storage is bounded; ownership remains unfinished.',font=font(14),fill='#9cacc3')
p=root/'demos/strings/utf8-example.png';im.save(p,optimize=True);print(r.stdout);print('Preview bytes:',p.stat().st_size)

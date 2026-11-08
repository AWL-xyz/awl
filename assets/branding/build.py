"""Contributor-only deterministic conversions of the user-supplied SVG master"""
from pathlib import Path
import hashlib,io,json,importlib.metadata
import resvg_py
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
source=(ROOT/'awl.svg').read_text()
raw=resvg_py.svg_to_bytes(svg_string=source,skip_system_fonts=True)
master=Image.open(io.BytesIO(raw)).convert('RGBA')
assert master.size==(512,524)
master.save(ROOT/'awl.png',optimize=True)
large=Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=source,width=1024,height=1048,skip_system_fonts=True))).convert('RGBA')
large.save(ROOT/'awl@2x.png',optimize=True)
icon=Image.new('RGBA',(1024,1024),(0,0,0,0))
ImageDraw.Draw(icon).rounded_rectangle((0,0,1023,1023),radius=192,fill='#000000')
mark=large.resize((896,917),Image.Resampling.LANCZOS)
icon.alpha_composite(mark,(64,53))
icon=icon.resize((512,512),Image.Resampling.LANCZOS)
assert icon.getpixel((0,0))[3]==0 and icon.getpixel((256,16))==(0,0,0,255)
icon.save(ROOT/'awl-icon.png',optimize=True)
icon.save(ROOT/'awl.ico',format='ICO',sizes=[(s,s) for s in [16,24,32,48,64,128,256]])
# Check transparent cutouts and luminance masking, not just successful decoding
assert master.getpixel((0,0))[3]==0 and master.getpixel((188,186))[3]==255
assert master.getpixel((188,144))[3]==0 and master.getpixel((256,220))[3]==0
unmasked=Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=source.replace(' mask="url(#owl-mask)"',''),skip_system_fonts=True))).convert('RGBA')
assert sum(master.getchannel('A').tobytes())<sum(unmasked.getchannel('A').tobytes())
with Image.open(ROOT/'awl.ico') as ico:
 sizes=sorted(ico.ico.sizes());assert sizes==[(s,s) for s in [16,24,32,48,64,128,256]]
 for size in sizes:assert ico.ico.getimage(size).size==size
report={'status':'PASS','origin':'user-supplied SVG, geometry/mask/white fill retained, not AI generated','master_dimensions':[512,524],'png_2x_dimensions':[1024,1048],'icon_background':'#000000','icon_corner_radius_px':96,'icon_outside_corners':'transparent','ico_sizes':sizes,'renderer':'resvg-py '+importlib.metadata.version('resvg-py'),'pillow':importlib.metadata.version('Pillow'),'checks':['transparency','pupils','eye/beak cutouts','luminance-mask reduces coverage','all seven ICO frames decode','rounded pure-black background with transparent outside corners'],'files':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in [ROOT/n for n in ['awl.svg','awl.png','awl@2x.png','awl-icon.png','awl.ico','build.py']]},'release_scope':'repository branding assets and README only, existing SDK archives and compiler/browser execution artifacts unchanged'}
(ROOT/'validation.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
print('PASS logo rendering, transparency/mask checks and seven ICO sizes')

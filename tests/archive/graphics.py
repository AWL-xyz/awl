#!/usr/bin/env python3
import argparse,hashlib,json,os,random,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();rng=random.Random(5727);width,height=17,13;cases=[];font=json.loads((ROOT/'tests/font5x7.json').read_text())
 for _ in range(65):cases.append(('line',[rng.randrange(-30,35) for i in range(4)]+[rng.randrange(16777216)]))
 for _ in range(35):cases.append(('rect',[rng.randrange(-20,25),rng.randrange(-20,25),rng.randrange(30),rng.randrange(30),rng.randrange(16777216)]))
 for _ in range(35):cases.append(('circle',[rng.randrange(-20,25),rng.randrange(-20,25),rng.randrange(18),rng.randrange(16777216)]))
 cases += [('line',[-32768,-32768,32767,32767,1]),('line',[3,4,3,4,9]),('circle',[0,0,0,7]),('rect',[-1,-1,2,2,8])]
 for text in ['A','a','0123456789','hello','A\nB','?','é😀',''.join(chr(i) for i in range(32,127))]:
  for scale in [1,2,8]:cases.append(('draw_text',[-2,-1,text,scale,16777215]))
 for code in range(32,127):cases.append(('draw_text',[0,0,chr(code),1,16777215]))
 cases += [('line',[-32769,0,1,1,3]),('line',[0,0,32768,0,1]),('line',[0,0,0,0,-1]),('rect',[0,0,-1,3,2]),('rect',[0,0,65537,1,2]),('circle',[0,0,4097,1]),('circle',[0,0,-1,1]),('draw_text',[0,0,'A',0,1]),('draw_text',[0,0,'x'*513,1,1]),('rect',[0,0,3,3,16777216])]
 def oracle(kind,args):
  pixels=[0]*(width*height);*_,color=args;valid=0<=color<=16777215
  def dot(x,y):
   if 0<=x<width and 0<=y<height:pixels[y*width+x]=color
  if kind=='line':
   x,y,xx,yy,_=args;valid=valid and all(-32768<=v<=32767 for v in args[:4])
   if valid:
    dx=abs(xx-x);dy=abs(yy-y);major=max(dx,dy)
    for step in range(major+1):
     mx=step if dx>=dy else (2*step*dx+major)//(2*major)
     my=step if dy>=dx else (2*step*dy+major)//(2*major)
     dot(x+(mx if xx>=x else -mx),y+(my if yy>=y else -my))
  elif kind in ['rect','circle']:
   x,y=args[:2];valid=valid and -32768<=x<=32767 and -32768<=y<=32767
   if kind=='rect':valid=valid and all(0<=v<=65536 for v in args[2:4])
   else:valid=valid and 0<=args[2]<=4096
   if valid:
    for row in range(height):
     for col in range(width):
      inside=(x<=col<x+args[2] and y<=row<y+args[3]) if kind=='rect' else (col-x)**2+(row-y)**2<=args[2]**2
      if inside:dot(col,row)
  else:
   x,y,text,scale,_=args;valid=valid and -32768<=x<=32767 and -32768<=y<=32767 and 1<=scale<=8 and len(text)<=512;column=x;row=y
   if valid:
    for char in text:
     if char=='\n':column=x;row+=8*scale;continue
     if 'a'<=char<='z':char=char.upper()
     rows=font.get(char,font['?'])
     for py,bits in enumerate(rows):
      for px in range(5):
       if bits>>(4-px)&1:
        for sy in range(scale):
         for sx in range(scale):dot(column+px*scale+sx,row+py*scale+sy)
     column+=6*scale
  return valid,pixels
 body=[];expected=[]
 for kind,args in cases:
  literals=[json.dumps(x,ensure_ascii=False) if isinstance(x,str) else str(x) for x in args]
  body.append(f'gfx.surface(pixels,{width},{height},0); print(gfx.{kind}(pixels,{width},{height},'+','.join(literals)+')); i: 0; while i<vector.length(pixels) do print(vector.get(pixels,i)); i: i+1; end;')
  valid,pixels=oracle(kind,args);expected.extend([str(valid).lower(),*[str(x) for x in pixels]])
 body += ['print(gfx.rgb(0,128,255)); print(gfx.rgb(-1,0,0)); print(gfx.gray(255)); print(gfx.gray(256));','print(gfx.surface(pixels,2048,2048,0)); print(vector.length(pixels));','print(gfx.rect(pixels,18,13,0,0,1,1,1));']
 expected+=['33023','-1','16777215','-1','false','221','false']
 reports=[]
 with tempfile.TemporaryDirectory(prefix='Awl-draw-tests-',dir='/var/tmp') as td:
  work=Path(td);shutil.copyfile(ROOT/'examples/apps/colorlab/Graphics.aw',work/'Graphics.aw');src=work/'main.aw';src.write_text('use Graphics.aw as gfx; func main()->i64 @p scoped pixels vector<i64>: vector.new<i64>(0); @p i: 0; '+' '.join(body)+' return 0; end;')
  for mode in ['bundled','sanitized']:
   exe=work/mode;cmd='build' if mode=='bundled' else 'emit-c';r=subprocess.run([str(a.kcc.resolve()),cmd,str(src),'--syntax','next']+(['-o',str(exe)] if mode=='bundled' else []),capture_output=True,text=True,env={**os.environ,'PATH':'/no-host-tools','XDG_CACHE_HOME':'/var/tmp/Awl-draw-cache'},timeout=180);assert r.returncode==0,r.stderr
   if mode=='sanitized':
    c=work/'main.c';c.write_text(r.stdout);subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-no-pie',str(c),'-lm','-o',str(exe)],check=True,timeout=90)
   begin=time.perf_counter_ns();r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20);elapsed=(time.perf_counter_ns()-begin)/1e6;assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr);actual=r.stdout.splitlines();assert len(actual)==len(expected),(len(actual),len(expected))
   for i,(got,want) in enumerate(zip(actual,expected)):assert got==want,(i,i//222,cases[min(i//222,len(cases)-1)],got,want)
   reports.append({'mode':mode,'cases':len(cases)+7,'pixel_and_status_assertions':len(expected),'whole_process_ms':elapsed,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()})
 report={'status':'PASS','compiler_sha256':hashlib.sha256(a.kcc.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'examples/apps/colorlab/Graphics.aw').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'font_rows_sha256':hashlib.sha256((ROOT/'tests/font5x7.json').read_bytes()).hexdigest(),'runs':reports,'qualification':'source-level CPU rasterizer, independent closed-form line and per-pixel shape oracles, font fixture and implementation share authored glyph designs, no native font engine, timing includes stdout verification data'}
 a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print(report)
if __name__=='__main__':main()

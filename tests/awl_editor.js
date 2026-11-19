#!/usr/bin/env node
// Contributor harness: exercises the in-browser Aesop-syntax interpreter that
// ships inside editor/awl-editor.html, no browser or network required.
const fs=require('fs'),path=require('path');
const html=fs.readFileSync(process.argv[2],'utf8');
const cut=(a,b)=>{const i=html.indexOf(a),j=html.indexOf(b);if(i<0||j<0)throw Error('missing marker '+a+' / '+b);return html.slice(i,j);};
const core=path.join(require('os').tmpdir(),'awl-editor-core-'+process.pid+'.js');
fs.writeFileSync(core,cut('/* ---------- language definition ---------- */','/* ---------- state ---------- */')+'\n'+
  cut('/* ---------- in-browser Aesop-syntax interpreter ---------- */','function runProgram(')+'\nmodule.exports={EXAMPLES,kernRun,parse};\n');
const lib=require(core);fs.unlinkSync(core);
const records=[];
const expect=(ok,label)=>{if(!ok)throw Error('failed: '+label);records.push(label);};
const run=(files,entry)=>{
  const map=Object.fromEntries(files.map(f=>[f.name,f.text]));
  const out=[],vis={w:0,h:0,buf:null,frames:[],bytes:0,clock:0,slept:false,title:'',closed:false,capped:false};
  return {code:Number(lib.kernRun(map[entry],out,vis,map)),out,frames:vis.frames.length};
};
let r=run([{name:'main.aw',text:lib.EXAMPLES['hello.aw']}],'main.aw');
expect(JSON.stringify(r.out)===JSON.stringify(['1','2','6','24','120','720','5040','40320','362880','3628800']),'factorial example prints 1..10 factorials');
r=run([{name:'main.aw',text:lib.EXAMPLES['enums.aw']}],'main.aw');
expect(JSON.stringify(r.out)===JSON.stringify(['7','division by zero','overflow']),'enum, match and divide-by-zero traps');
r=run([{name:'main.aw',text:lib.EXAMPLES['math.aw']}],'main.aw');
expect(JSON.stringify(r.out)===JSON.stringify(['19.634954084936208','9.0','1.0','0.7853981633974483','260']),'f64 math, pi and checked conversion');
r=run(lib.EXAMPLES['modules'],'modules.aw');
expect(JSON.stringify(r.out)===JSON.stringify(['128.59','42','2','1','999.0']),'module exports, @w write and private binding context');
r=run([{name:'main.aw',text:lib.EXAMPLES['visual.aw']}],'main.aw');
expect(r.code===0&&r.frames===60,'visual gradient records 60 frames');
r=run([{name:'main.aw',text:lib.EXAMPLES['bounce.aw']}],'main.aw');
expect(r.code===0&&r.frames===90,'bouncing square records 90 frames');
const rejects=(label,source)=>{let bad=false;try{lib.parse(source);}catch(e){bad=true;}expect(bad,label);};
rejects('old arrow result syntax rejected','func main()->i64 return 0; end;');
rejects('old parenthesized parameters rejected','func size(v:i64) -> i64 return v; end; func main[i64] { return 0; };');
rejects('old end; function body rejected','func main: i64 return 0; end;');
rejects('old colon result rejected','func main: i64 { return 0; };');
rejects('old trailing parameter result rejected','func size :: v:i64: i64 { return v; };');
const prog=lib.parse('func size[i64] :: @b values[i64], etc[i64] { return 0; };\nfunc main[i64] { return 0; };');
expect(prog.fns.size.params.length===2&&prog.fns.size.ret==='i64'&&prog.fns.main.params.length===0,'func :: parameters and bare main header parse');
r=run([{name:'main.aw',text:'func choose :: b:bool { if b { return 7; } else { return 9; }; }; func main { print(choose(false)); return 0; };'}],'main.aw');
expect(r.code===0&&r.out[0]==='9','inferred function and entry-point results');
r=run([{name:'main.aw',text:'func main { print(answer()); return 0; }; func answer { return 42; };'}],'main.aw');
expect(r.out[0]==='42','forward inferred result');
r=run([{name:'main.aw',text:'func main { @p stamp: clock.wall(); print(stamp >= 0); return 0; };'}],'main.aw');
expect(r.code===0&&r.out[0]==='true','wall-clock intrinsic has a checked i64 result');
r=run([{name:'main.aw',text:'func main { print(i64.convert(1.5)); print(i8.convert(1000.0)); print(u64.convert(-1.5)); print(f64.convert(1.5)); print(isnum(1.5)); print(isnum("x")); print(i64.match(1)); print(text.match("x")); return 0; };'}],'main.aw');
expect(r.code===0&&JSON.stringify(r.out)===JSON.stringify(['1','127','0','1.5','true','false','true','true']),'numeric conversions, isnum and type match');
r=run([{name:'main.aw',text:String.raw`func read :: s:text { return string.toi64(s); };
func main {
  print(read("+00090")); print(read("-9223372036854775808"));
  print(string.i64valid("9223372036854775808")); print(string.i64valid("2\n"));
  print(string.i64valid("-")); print(string.i64valid("１")); return 0;
};`}],'main.aw');
expect(r.code===0&&JSON.stringify(r.out)===JSON.stringify(['90','-9223372036854775808','false','false','false','false']),'strict signed decimal text and inferred result');
let decimalTrap=false;try{run([{name:'main.aw',text:'func main { return string.toi64("+x"); };'}],'main.aw');}catch(e){decimalTrap=e.trap&&e.message.includes('invalid signed integer');}
expect(decimalTrap,'invalid decimal text traps');
r=run([{name:'main.aw',text:`@p high: bits.shl(1u64, 63);
func invert :: x:u64 { return bits.not(x); };
func count :: x:u64 { return bits.popcount(invert(x)); };
func main {
  print(bits.and(high, 18446744073709551615u64));
  print(bits.or(high, 1u64)); print(bits.xor(high, high));
  print(bits.shl(255u8, 7)); print(bits.shr(high, 63));
  print(bits.rotl(high, 1)); print(bits.rotr(1u64, 1)); print(bits.rotl(15u16, 0));
  print(count(high)); return 0;
};`}],'main.aw');
expect(r.code===0&&JSON.stringify(r.out)===JSON.stringify(['9223372036854775808','9223372036854775809','0','128','1','1','9223372036854775808','15','63']),'exact unsigned words and inferred bit operation results');
for (const expression of ['bits.shl(1u8, -1)', 'bits.rotr(1u64, 64)']) {
  let trapped=false;try{run([{name:'main.aw',text:`func main { print(${expression}); return 0; };`}],'main.aw');}catch(e){trapped=e.trap&&e.message.includes('bit count outside word width');}
  expect(trapped,'invalid bit count traps: '+expression);
}
for (const expression of ['bits.not(1)', 'bits.xor(1u8, 1u64)', 'bits.shr(1u8, 1u8)']) {
  let rejected=false;try{run([{name:'main.aw',text:`func main { print(${expression}); return 0; };`}],'main.aw');}catch(e){rejected=!e.trap&&e.message.includes('needs');}
  expect(rejected,'invalid bit argument type: '+expression);
}
r=run([{name:'main.aw',text:'use Mask.aw as bits; func main { print(bits.xor(3, 4)); return 0; };'},
       {name:'Mask.aw',text:'exports{ @r func xor[i64] :: a:i64, b:i64 { return a + b; }; };'}],'main.aw');
expect(r.code===0&&r.out[0]==='7','module aliases take precedence over the bits namespace');
r=run([{name:'main.aw',text:'func main { @p w: window.open(2,2); print(window.width(w)); window.title(w,"x"); print(window.present(w)); window.close(w); return 0; };'}],'main.aw');
expect(r.code===0&&r.out[0]==='2'&&r.out[1]==='true','namespace window API');
let mixed=false;try{run([{name:'main.aw',text:'func main { @p a: 2; @p b: 1.5; print(a * b); return 0; };'}],'main.aw');}catch(e){mixed=true;}expect(mixed,'strict mixed numeric arithmetic');

for(const source of ['func bad :: b:bool { if b { return 1; } else { return false; }; }; func main { print(bad(true)); return 0; };','func bad { return bad(); }; func main { print(bad()); return 0; };','func bad :: b:bool { if b { return 1; }; }; func main { print(bad(true)); return 0; };']) {
  let rejected=false;try{run([{name:'main.aw',text:source}],'main.aw');}catch(e){rejected=true;}expect(rejected,'editor rejects mixed/circular/incomplete inferred results');
}
const examples=Object.fromEntries(Object.entries(lib.EXAMPLES).map(([k,v])=>[k,Array.isArray(v)?v:[{name:k,text:v}]]));
fs.writeFileSync(process.argv[3],JSON.stringify(examples));
console.log(records.length+' in-browser interpreter checks passed');

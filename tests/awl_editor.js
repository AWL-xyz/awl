#!/usr/bin/env node
// Contributor harness: exercises the in-browser next-syntax interpreter that
// ships inside editor/awl-editor.html, no browser or network required.
const fs=require('fs'),path=require('path');
const html=fs.readFileSync(process.argv[2],'utf8');
const cut=(a,b)=>{const i=html.indexOf(a),j=html.indexOf(b);if(i<0||j<0)throw Error('missing marker '+a+' / '+b);return html.slice(i,j);};
const core=path.join(require('os').tmpdir(),'awl-editor-core-'+process.pid+'.js');
fs.writeFileSync(core,cut('/* ---------- language definition ---------- */','/* ---------- state ---------- */')+'\n'+
  cut('/* ---------- in-browser next-syntax interpreter ---------- */','function runProgram(')+'\nmodule.exports={EXAMPLES,kernRun,parse};\n');
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
rejects('old parenthesized parameters rejected','func size(v:i64) -> i64 return v; end; func main: i64 { return 0; };');
rejects('old end; function body rejected','func main: i64 return 0; end;');
const prog=lib.parse('func size :: @b values[i64], etc[i64]: i64 { return 0; };\nfunc main: i64 { return 0; };');
expect(prog.fns.size.params.length===2&&prog.fns.size.ret==='i64'&&prog.fns.main.params.length===0,'func :: parameters and bare main header parse');
const examples=Object.fromEntries(Object.entries(lib.EXAMPLES).map(([k,v])=>[k,Array.isArray(v)?v:[{name:k,text:v}]]));
fs.writeFileSync(process.argv[3],JSON.stringify(examples));
console.log(records.length+' in-browser interpreter checks passed');

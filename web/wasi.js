'use strict';
async function runAwl(bytes,args){
 const encoder=new TextEncoder(),decoder=new TextDecoder('utf-8',{fatal:true});
 if(!Array.isArray(args)||args.some(s=>typeof s!=='string'||s.includes('\0')||/[\uD800-\uDFFF]/u.test(s)))throw Error('arguments must be valid unicode strings without NUL');
 const argv=['Awl',...args].map(s=>encoder.encode(s)),total=argv.reduce((n,b)=>n+b.length+1,0);
 if(total>65536||argv.length>256)throw Error('argument limit');
 const mod=await WebAssembly.compile(bytes);let instance,code=0,written=0;const chunks=[[],[]],exit={};
 const memory=()=>instance.exports.memory;
 const range=(p,n)=>{p>>>=0;n>>>=0;if(p>memory().buffer.byteLength||n>memory().buffer.byteLength-p)throw Error('guest memory range');return p};
 const view=()=>new DataView(memory().buffer);
 const set32=(p,n)=>view().setUint32(range(p,4),n,true);
 const wasi={
  args_sizes_get:(n,size)=>{set32(n,argv.length);set32(size,total);return 0},
  args_get:(p,buf)=>{range(p,argv.length*4);range(buf,total);for(const arg of argv){set32(p,buf);p+=4;new Uint8Array(memory().buffer,buf,arg.length).set(arg);buf+=arg.length;new Uint8Array(memory().buffer)[buf++]=0}return 0},
  fd_fdstat_get:(fd,p)=>{if(fd!==1&&fd!==2)return 8;range(p,24);new Uint8Array(memory().buffer,p,24).fill(0);view().setUint8(p,2);view().setBigUint64(p+8,64n,true);return 0},
  fd_write:(fd,p,n,out)=>{if(fd!==1&&fd!==2)return 8;n>>>=0;if(n>1024)return 28;range(out,4);range(p,n*8);let count=0;const parts=[];for(let i=0;i<n;i++){const a=view().getUint32(p+i*8,true),b=view().getUint32(p+i*8+4,true);range(a,b);count+=b;if(written+count>1048576)throw Error('output limit');parts.push(new Uint8Array(memory().buffer,a,b).slice())}written+=count;chunks[fd-1].push(...parts);set32(out,count);return 0},
  fd_seek:fd=>(fd===1||fd===2)?70:8,
  fd_close:()=>8,
  proc_exit:n=>{code=n>>>0;throw exit}
 };
 for(const item of WebAssembly.Module.imports(mod))if(item.module!=='wasi_snapshot_preview1'||item.kind!=='function'||!Object.hasOwn(wasi,item.name))throw Error('unsupported import '+item.module+'.'+item.name);
 instance=await WebAssembly.instantiate(mod,{wasi_snapshot_preview1:wasi});
 if(!(instance.exports.memory instanceof WebAssembly.Memory)||typeof instance.exports._start!=='function')throw Error('command ABI required');
 try{instance.exports._start()}catch(e){if(e!==exit)throw e}
 const text=parts=>{const size=parts.reduce((n,p)=>n+p.length,0),all=new Uint8Array(size);let i=0;for(const p of parts){all.set(p,i);i+=p.length}return decoder.decode(all)};
 return {code,stdout:text(chunks[0]),stderr:text(chunks[1]),memoryBytes:memory().buffer.byteLength};
}
if(typeof module!=='undefined')module.exports={runAwl};

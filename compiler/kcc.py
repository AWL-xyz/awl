#!/usr/bin/env python3
"""KCC bootstrap 0.7: .aw -> typed structured KIR0 -> ISO C11 -> native."""
from __future__ import annotations
import argparse
import dataclasses as D
from functools import wraps
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

VERSION = '0.7.1'
MAX_SOURCE_BYTES = 1_048_576
MAX_TOKENS = 100_000
MAX_DEPTH = 64
MAX_DIAGNOSTICS = 20
MAX_IDENTIFIER = 128

@D.dataclass
class Diagnostic:
    code: str
    message: str
    line: int = 1
    column: int = 1
    end_column: int = 2
    start: int = 0
    end: int = 0

class Error(Exception):
    def __init__(self, message=None, diagnostics=None):
        self.diagnostics = diagnostics or []
        super().__init__(message if message is not None else '\n'.join(
            f'{d.line}:{d.column}: {d.message}' for d in self.diagnostics))

def problem(token, message, code='E100'):
    return Diagnostic(code, message, token.line, token.column,
                      token.column + max(1, token.end-token.start), token.start, token.end)

def source_error(token, message, code='E100'):
    return Error(diagnostics=[problem(token, message, code)])

def bounded(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        self.depth += 1
        try:
            if self.depth > MAX_DEPTH:
                raise source_error(self.ts[self.i], f'syntax nesting exceeds {MAX_DEPTH}', 'E002')
            return method(self, *args, **kwargs)
        finally:
            self.depth -= 1
    return wrapped


@D.dataclass
class Token:
    text: str
    line: int
    column: int
    start: int = 0
    end: int = 0

@D.dataclass
class Node:
    kind: str
    token: Token
    value: object = None
    children: list = D.field(default_factory=list)
    type: str | None = None
    symbol: str | None = None
    literal_type: str | None = None

RX = re.compile(r'(?P<space>[ \t\r]+)|(?P<nl>\n)|(?P<comment>--[^\n]*)|(?P<int>[0-9]+(?:[iu](?:8|16|32|64))?)|(?P<id>[A-Za-z_][A-Za-z_0-9]*)|(?P<op>->|==|!=|<=|>=|[+*/%<>=():,;.\-])')
INTEGERS={f'{sign}{bits}':(sign=='i',bits) for sign in ('i','u') for bits in (8,16,32,64)}
SIGNED={ty for ty,(signed,_) in INTEGERS.items() if signed}

def bounds(ty):
    signed,bits=INTEGERS[ty]
    return (-(1<<(bits-1)),(1<<(bits-1))-1) if signed else (0,(1<<bits)-1)

def integer_token(text):
    match=re.fullmatch(r'([0-9]+)([iu](?:8|16|32|64))?',text)
    return (int(match[1]),match[2] or 'i64') if match else None

RESERVED = set('function local if then else end while do return true false and or not i64 u64 bool unit struct union match case'.split()) | set(INTEGERS)

def lex_python(text):
    if len(text)>MAX_SOURCE_BYTES:
        raise Error(diagnostics=[Diagnostic('E001',f'source exceeds {MAX_SOURCE_BYTES} bytes')])
    try: encoded=text.encode('utf-8')
    except UnicodeEncodeError: raise Error(diagnostics=[Diagnostic('E008','source must be UTF-8')])
    if len(encoded)>MAX_SOURCE_BYTES:
        raise Error(diagnostics=[Diagnostic('E001',f'source exceeds {MAX_SOURCE_BYTES} bytes')])
    tokens=[]; pos=0; line=1; col=1
    while pos < len(text):
        m=RX.match(text,pos)
        if not m: raise source_error(Token(text[pos],line,col,pos,pos+1), f'unexpected character {text[pos]!r}', 'E101')
        s=m.group(); kind=m.lastgroup
        if kind not in ('space','nl','comment'):
            t=Token(s,line,col,pos,m.end())
            if kind=='id' and len(s)>MAX_IDENTIFIER:
                raise source_error(t,f'identifier exceeds {MAX_IDENTIFIER} characters','E003')
            if kind=='int' and m.end()<len(text) and (text[m.end()].isalnum() or text[m.end()]=='_'):
                raise source_error(t,'invalid integer suffix or missing token separator','E101')
            if kind=='int' and len(re.match('[0-9]+',s).group())>256:
                raise source_error(t,'integer literal exceeds 256 digits','E004')
            if len(tokens)>=MAX_TOKENS:
                raise source_error(t,f'token count exceeds {MAX_TOKENS}','E005')
            tokens.append(t)
        if kind=='nl': line+=1; col=1
        else: col+=len(s)
        pos=m.end()
    tokens.append(Token('<eof>',line,col,pos,pos))
    return tokens

# Optional native scanner ABI. Python retains language-specific diagnostic policy,
# token-object construction, parsing, checking and C emission during migration.
_NATIVE_LIBRARIES={}
_NATIVE_DLL_DIRECTORIES=[]
def native_library_path():
    configured=os.environ.get('Awl_LEXER_LIBRARY')
    if configured: return Path(configured).resolve()
    suffix='.dll' if os.name=='nt' else '.dylib' if platform.system()=='Darwin' else '.so'
    return Path(__file__).resolve().parent/'native/bin'/('Awllex'+suffix)

def load_native_lexer():
    import ctypes as C
    path=native_library_path()
    if str(path) in _NATIVE_LIBRARIES: return _NATIVE_LIBRARIES[str(path)]
    class NativeToken(C.Structure):
        _fields_=[(n,C.c_uint32) for n in ('start','end','line','column','flags')]
    class NativeResult(C.Structure):
        _fields_=[('tokens',C.POINTER(NativeToken)),('owner',C.c_void_p)]+[(n,C.c_uint32) for n in ('count','position','line','column')]
    try:
        if os.name=='nt' and hasattr(os,'add_dll_directory'):
            directories=[path.parent]
            info=path.parent/'build-info.json'
            if info.is_file():
                try: directories.append(Path(json.loads(info.read_text())['toolchain_directory']))
                except (ValueError,KeyError): pass
            for directory in directories:
                if directory.is_dir(): _NATIVE_DLL_DIRECTORIES.append(os.add_dll_directory(str(directory)))
        lib=C.CDLL(str(path))
        lib.Awl_lex_abi_version.restype=C.c_uint32
        lib.Awl_lex_token_size.restype=lib.Awl_lex_result_size.restype=C.c_size_t
        if (lib.Awl_lex_abi_version()!=1 or lib.Awl_lex_token_size()!=C.sizeof(NativeToken)
                or lib.Awl_lex_result_size()!=C.sizeof(NativeResult)):
            raise Error('native lexer ABI mismatch; rebuild and restart KCC')
        lib.Awl_lex.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(NativeResult)]; lib.Awl_lex.restype=C.c_int
        lib.Awl_lex_free.argtypes=[C.POINTER(NativeResult)]; lib.Awl_lex_free.restype=None
        lib.Awl_lex_benchmark.argtypes=[C.c_char_p,C.c_size_t,C.c_uint32,C.POINTER(C.c_double),C.POINTER(C.c_uint64)]
        lib.Awl_lex_benchmark.restype=C.c_int
    except (OSError,AttributeError) as e:
        raise Error(f'native lexer unavailable at {path}; run python compiler/build_native.py or select --lexer python ({e})')
    _NATIVE_LIBRARIES[str(path)]=(lib,NativeResult)
    return lib,NativeResult

def lex_native(text):
    import ctypes as C
    if len(text)>MAX_SOURCE_BYTES:
        raise Error(diagnostics=[Diagnostic('E001',f'source exceeds {MAX_SOURCE_BYTES} bytes')])
    try: encoded=text.encode('utf-8')
    except UnicodeEncodeError: raise Error(diagnostics=[Diagnostic('E008','source must be UTF-8')])
    if len(text)>MAX_SOURCE_BYTES or len(encoded)>MAX_SOURCE_BYTES:
        raise Error(diagnostics=[Diagnostic('E001',f'source exceeds {MAX_SOURCE_BYTES} bytes')])
    lib,Result=load_native_lexer(); result=Result(); tokens=[]
    status=lib.Awl_lex(encoded,len(encoded),C.byref(result))
    try:
        if status==3: raise Error(diagnostics=[Diagnostic('E001',f'source exceeds {MAX_SOURCE_BYTES} bytes')])
        if status==4: raise Error(diagnostics=[Diagnostic('E008','source must be UTF-8')])
        if status not in (0,1,2) or result.count>MAX_TOKENS+1 or not result.owner:
            raise Error('invalid response from native lexer')
        # Decode the contiguous POD array in bulk. Accessing each ctypes
        # structure field individually was measurably slower than Python lexing.
        import struct
        if result.count and not result.tokens: raise Error('missing native token buffer')
        buffer=(C.c_ubyte*(result.count*20)).from_address(C.addressof(result.tokens.contents)) if result.count else b''
        for begin,end,line,column,flags in struct.iter_unpack('=IIIII',buffer):
            if not (0<=begin<end<=len(text)) or flags not in (0,1,2):
                raise Error('invalid token from native lexer')
            t=Token(text[begin:end],line,column,begin,end)
            if flags==2 and len(t.text)>MAX_IDENTIFIER:
                raise source_error(t,f'identifier exceeds {MAX_IDENTIFIER} characters','E003')
            if flags==1:
                if t.end<len(text) and (text[t.end].isalnum() or text[t.end]=='_'):
                    raise source_error(t,'invalid integer suffix or missing token separator','E101')
                if len(re.match('[0-9]+',t.text).group())>256:
                    raise source_error(t,'integer literal exceeds 256 digits','E004')
            if len(tokens)>=MAX_TOKENS:
                raise source_error(t,f'token count exceeds {MAX_TOKENS}','E005')
            tokens.append(t)
        if status==1:
            pos=result.position
            if pos>=len(text): raise Error('invalid error offset from native lexer')
            raise source_error(Token(text[pos],result.line,result.column,pos,pos+1),f'unexpected character {text[pos]!r}','E101')
        if status or result.position!=len(text): raise Error('invalid completion from native lexer')
        tokens.append(Token('<eof>',result.line,result.column,result.position,result.position))
        return tokens
    finally: lib.Awl_lex_free(C.byref(result))

def lex(text,backend=None):
    backend=backend or os.environ.get('KCC_LEXER','python')
    if backend=='python': return lex_python(text)
    if backend=='native': return lex_native(text)
    raise Error(f'unknown lexer backend {backend!r}; choose python or native')

class Parser:
    def __init__(self,text,lexer=None): self.ts=lex(text,lexer); self.i=0; self.depth=0; self.diagnostics=[]
    def peek(self): return self.ts[self.i].text
    def pop(self):
        t=self.ts[self.i]
        if t.text!='<eof>': self.i+=1
        return t
    def fail(self,msg):
        t=self.ts[self.i]; raise source_error(t,f'{msg}; got {t.text!r}')
    def take(self,s):
        if self.peek()!=s: self.fail(f'expected {s!r}')
        return self.pop()
    def ident(self):
        if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', self.peek()) or self.peek() in RESERVED: self.fail('expected identifier')
        return self.pop()
    def typ(self):
        if self.peek() in set(INTEGERS) | {'bool','unit'}: return self.pop().text
        return self.ident().text
    def record(self, error):
        # Resource-limit failures terminate immediately; never recover past them.
        if any(d.code.startswith('E00') for d in error.diagnostics): raise error
        self.diagnostics.extend(error.diagnostics)
        if len(self.diagnostics)>=MAX_DIAGNOSTICS:
            raise Error(diagnostics=self.diagnostics[:MAX_DIAGNOSTICS])
    def program(self):
        fs=[]
        while self.peek()!='<eof>':
            start=self.i
            try:
                fs.append(self.structure() if self.peek()=='struct' else self.union() if self.peek()=='union' else self.function())
            except Error as e:
                self.record(e)
                if self.i==start: self.pop()
                while self.peek() not in ('function','struct','union','<eof>'): self.pop()
        if self.diagnostics: raise Error(diagnostics=self.diagnostics)
        return fs
    def structure(self):
        t=self.take('struct'); name=self.ident().text; fields=[]
        while self.peek()!='end':
            if self.peek()==';': self.pop(); continue
            field=self.ident(); self.take(':')
            fields.append(Node('field_decl',field,(field.text,self.typ())))
        self.take('end'); return Node('struct',t,name,fields)
    def union(self):
        t=self.take('union'); name=self.ident().text; variants=[]
        while self.peek()!='end':
            if self.peek()==';': self.pop(); continue
            v=self.ident(); fields=[]; self.take('(')
            if self.peek()!=')':
                while True:
                    f=self.ident(); self.take(':'); fields.append(Node('field_decl',f,(f.text,self.typ())))
                    if self.peek()!=',': break
                    self.pop()
            self.take(')'); variants.append(Node('variant_decl',v,v.text,fields))
        self.take('end'); return Node('union',t,name,variants)
    def match(self,t):
        value=self.expr(); self.take('then'); arms=[]
        while self.peek()=='case':
            c=self.pop(); owner=self.ident().text; self.take('.'); variant=self.ident().text
            self.take('('); binders=[]
            if self.peek()!=')':
                while True:
                    b=self.ident(); binders.append(Node('pattern_bind',b,b.text))
                    if self.peek()!=',': break
                    self.pop()
            self.take(')'); self.take('then'); body=self.block({'case','end'})
            arms.append(Node('case',c,(owner,variant),[binders,body]))
        self.take('end'); return Node('match',t,None,[value,arms])
    def function(self):
        t=self.take('function'); name=self.ident().text; self.take('('); params=[]
        if self.peek()!=')':
            while True:
                p=self.ident(); self.take(':'); params.append(Node('param',p,(p.text,self.typ())))
                if self.peek()!=',': break
                self.pop()
        self.take(')'); self.take('->'); ret=self.typ()
        body=self.block({'end'}); self.take('end')
        return Node('function',t,(name,ret),[params,body])
    @bounded
    def block(self,stops):
        out=[]
        while self.peek() not in stops:
            if self.peek() in ('<eof>','function','struct','union'): self.fail('unterminated block')
            if self.peek()==';': self.pop(); continue
            start=self.i
            try: out.append(self.statement())
            except Error as e:
                self.record(e)
                # Panic-mode recovery at a separator, block boundary, or a
                # later-line statement starter. No partial program is checked.
                if self.i==start: self.pop()
                while self.peek() not in stops | {'<eof>','function','struct','union',';'}:
                    t=self.ts[self.i]
                    if t.line>self.ts[start].line and t.text in ('local','return','if','while','match'):
                        break
                    self.pop()
                if self.peek()==';': self.pop()
        return out
    def statement(self):
        t=self.pop(); s=t.text
        if s=='local':
            name=self.ident().text; self.take(':'); ty=self.typ(); self.take('=')
            return Node('local',t,(name,ty),[self.expr()])
        if s=='return': return Node('return',t,None,[self.expr()])
        if s=='match': return self.match(t)
        if s=='if':
            cond=self.expr(); self.take('then'); yes=self.block({'else','end'}); no=[]
            if self.peek()=='else': self.pop(); no=self.block({'end'})
            self.take('end'); return Node('if',t,None,[cond,yes,no])
        if s=='while':
            cond=self.expr(); self.take('do'); body=self.block({'end'}); self.take('end')
            return Node('while',t,None,[cond,body])
        if re.fullmatch('[A-Za-z_][A-Za-z_0-9]*',s) and s not in RESERVED and self.peek()=='=':
            self.pop(); return Node('assign',t,s,[self.expr()])
        self.i-=1
        target=self.expr()
        if self.peek()=='=':
            self.pop(); return Node('store',t,None,[target,self.expr()])
        return Node('expr',t,None,[target])
    def arguments(self):
        self.take('('); args=[]
        if self.peek()!=')':
            while True:
                args.append(self.expr())
                if self.peek()!=',': break
                self.pop()
        self.take(')'); return args
    PREC={'or':1,'and':2,'==':3,'!=':3,'<':4,'>':4,'<=':4,'>=':4,'+':5,'-':5,'*':6,'/':6,'%':6}
    @bounded
    def expr(self,minimum=0):
        t=self.pop(); s=t.text
        next_integer=integer_token(self.peek()) if s=='-' else None
        if s=='-' and next_integer and next_integer[1] in SIGNED and next_integer[0]==-bounds(next_integer[1])[0]:
            self.pop(); left=Node('int',t,-next_integer[0],literal_type=next_integer[1])
        elif s in ('-','not'): left=Node('unary',t,s,[self.expr(7)])
        elif s=='(':
            left=self.expr(); self.take(')')
        elif integer_token(s):
            value,ty=integer_token(s); left=Node('int' if ty in SIGNED else 'uint',t,value,literal_type=ty)
        elif s in INTEGERS:
            left=Node('convert',t,s,self.arguments())
        elif s in ('true','false'): left=Node('bool',t,s=='true')
        elif re.fullmatch('[A-Za-z_][A-Za-z_0-9]*',s) and s not in RESERVED:
            if self.peek()=='.' and self.i+2<len(self.ts) and self.ts[self.i+2].text=='(':
                self.pop(); variant=self.ident().text; args=self.arguments()
                left=Node('union_ctor',t,(s,variant),args)
            elif self.peek()=='(':
                self.pop(); args=[]
                if self.peek()!=')':
                    while True:
                        args.append(self.expr())
                        if self.peek()!=',': break
                        self.pop()
                self.take(')'); left=Node('call',t,s,args)
            else: left=Node('name',t,s)
        else: raise source_error(t,f'expected expression; got {s!r}')
        while self.peek()=='.':
            self.pop(); field=self.ident(); left=Node('field',field,field.text,[left])
        while self.peek() in self.PREC and self.PREC[self.peek()]>=minimum:
            op=self.pop(); right=self.expr(self.PREC[op.text]+1); left=Node('binary',op,op.text,[left,right])
        return left

SCALARS=set(INTEGERS) | {'bool'}
MAX_VALUE_BYTES=1_048_576

def layout_values(declarations):
    """Finite aggregate graph and bootstrap size budget, NOT an exported ABI."""
    aggregates={}; names=set()
    for d in declarations:
        name=d.value if d.kind in ('struct','union') else d.value[0]
        if name in names or name=='print': raise source_error(d.token,f'duplicate/reserved declaration {name}','E210')
        names.add(name)
        if d.kind in ('struct','union'): aggregates[name]=d
    order=[]; sizes={t:(bits//8,bits//8) for t,(_,bits) in INTEGERS.items()}
    sizes['bool']=(1,1)
    heights={t:0 for t in SCALARS}; visiting=set()
    def error(d,msg): raise source_error(d.token,msg,'E210')
    def fields_layout(fields,depth,d):
        if len(fields)>128: error(d,'aggregate exceeds 128 fields')
        offset=0; align=1; names=set(); height=0
        for f in fields:
            fn,ft=f.value
            if fn in names: error(f,f'duplicate field {fn}')
            names.add(fn)
            if ft not in SCALARS and ft not in aggregates: error(f,f'invalid field type {ft}')
            size,alignment=visit(ft,depth+1); height=max(height,heights[ft]+1)
            if height>MAX_DEPTH: error(d,'aggregate nesting limit exceeded')
            offset=(offset+alignment-1)//alignment*alignment+size; align=max(align,alignment)
            if offset>MAX_VALUE_BYTES: error(d,'aggregate value exceeds size budget')
        return (offset+align-1)//align*align,align,height
    def visit(name,depth):
        if name in sizes: return sizes[name]
        d=aggregates[name]
        if name in visiting: error(d,'recursive value layout is not permitted')
        if depth>MAX_DEPTH: error(d,'aggregate nesting limit exceeded')
        visiting.add(name)
        if d.kind=='struct':
            if not d.children: error(d,'empty structs are not supported')
            size,align,height=fields_layout(d.children,depth,d)
        else:
            if not d.children: error(d,'empty unions are not supported')
            if len(d.children)>128: error(d,'union exceeds 128 variants')
            variant_names=set(); payload=1; align=1; height=1
            for v in d.children:
                if v.value in variant_names: error(v,f'duplicate variant {v.value}')
                variant_names.add(v.value)
                vs,va,vh=fields_layout(v.children,depth,d)
                payload=max(payload,vs); align=max(align,va); height=max(height,vh)
            size=(4+align-1)//align*align+payload; align=max(4,align)
            size=(size+align-1)//align*align
        if size>MAX_VALUE_BYTES: error(d,'aggregate value exceeds size budget')
        visiting.remove(name); sizes[name]=(size,align); heights[name]=height; order.append(d)
        return sizes[name]
    for name in aggregates: visit(name,1)
    return order,sizes

class Checker:
    def __init__(self,fs):
        self.declarations=fs; self.fs=[f for f in fs if f.kind=='function']
        self.structs={d.value:{f.value[0]:f.value[1] for f in d.children} for d in fs if d.kind=='struct'}
        self.unions={d.value:{v.value:v for v in d.children} for d in fs if d.kind=='union'}
        self.sigs={}; self.serial=0
    def valid_type(self,n,ty,unit=False):
        if ty not in SCALARS and ty not in self.structs and ty not in self.unions and not (unit and ty=='unit'):
            self.err(n,f'unknown or invalid value type {ty}')
    def place(self,n,env):
        if n.kind=='name': return self.expr(n,env)
        if n.kind=='field':
            base=self.place(n.children[0],env)
            if base not in self.structs or n.value not in self.structs[base]: self.err(n,f'unknown field {n.value} on {base}')
            n.type=self.structs[base][n.value]; return n.type
        self.err(n,'field assignment requires a local-rooted place')
    def err(self,n,msg): raise source_error(n.token,msg,'E200')
    def fresh(self): self.serial+=1; return f'k_v{self.serial}'
    def check(self):
        layout_values(self.declarations)
        for f in self.fs:
            name,ret=f.value; params=f.children[0]
            if name in self.sigs or name=='print': self.err(f,f'duplicate/reserved function {name}')
            if any(p.value[1]=='unit' for p in params): self.err(f,'unit parameters are not permitted')
            self.valid_type(f,ret,unit=True)
            for p in params: self.valid_type(p,p.value[1])
            self.sigs[name]=([p.value[1] for p in params],ret)
        if self.sigs.get('main') != ([], 'i64'): raise Error(diagnostics=[Diagnostic('E201','entry point must be function main() -> i64')])
        for f in self.fs:
            env={}; self.ret=f.value[1]
            for p in f.children[0]:
                name,ty=p.value
                if name in env: self.err(p,f'duplicate parameter {name}')
                p.symbol=self.fresh(); env[name]=(ty,p.symbol)
            returns=self.block(f.children[1],env)
            if self.ret!='unit' and not returns: self.err(f,'not every path returns a value')
        return self.declarations
    def require(self,n,got,want):
        if got!=want: self.err(n,f'expected {want}, found {got}')
    def expr(self,n,env):
        k=n.kind
        if k in ('int','uint'):
            ty=n.literal_type
            if ty not in INTEGERS or (k=='int')!=(ty in SIGNED): self.err(n,'invalid integer literal type')
            low,high=bounds(ty)
            if not low<=n.value<=high: self.err(n,f'integer literal outside {ty} range')
        elif k=='convert':
            if n.value not in INTEGERS or len(n.children)!=1: self.err(n,'integer conversion expects exactly one argument')
            src=self.expr(n.children[0],env)
            if src not in INTEGERS: self.err(n,'integer conversion requires an integer value')
            ty=n.value
        elif k=='field':
            base=self.expr(n.children[0],env)
            if base not in self.structs or n.value not in self.structs[base]: self.err(n,f'unknown field {n.value} on {base}')
            ty=self.structs[base][n.value]
        elif k=='bool': ty='bool'
        elif k=='name':
            if n.value not in env: self.err(n,f'unknown local {n.value}')
            ty,n.symbol=env[n.value]
        elif k=='union_ctor':
            owner,variant=n.value
            if owner not in self.unions: self.err(n,f'unknown union {owner}')
            if variant not in self.unions[owner]: self.err(n,f'unknown variant {owner}.{variant}')
            expected=[f.value[1] for f in self.unions[owner][variant].children]
            args=[self.expr(x,env) for x in n.children]
            if args!=expected: self.err(n,f'variant argument types {args} do not match {expected}')
            ty=owner
        elif k=='call':
            args=[self.expr(x,env) for x in n.children]
            if n.value=='print':
                if len(args)!=1 or args[0] not in SCALARS: self.err(n,'print expects one integer or bool')
                ty='unit'
            elif n.value in self.structs:
                expected=list(self.structs[n.value].values()); ty=n.value
                if args!=expected: self.err(n,f'constructor argument types {args} do not match {expected}')
            else:
                if n.value not in self.sigs: self.err(n,f'unknown function {n.value}')
                expected,ty=self.sigs[n.value]
                if args!=expected: self.err(n,f'argument types {args} do not match {expected}')
        elif k=='unary':
            ty=self.expr(n.children[0],env)
            if n.value=='not': self.require(n,ty,'bool')
            elif ty not in SIGNED: self.err(n,f'unary minus requires a signed integer, found {ty}')
        elif k=='binary':
            a,b=[self.expr(x,env) for x in n.children]; op=n.value
            if op in ('and','or'):
                self.require(n,a,'bool'); self.require(n,b,'bool'); ty='bool'
            elif op in ('==','!='):
                if a!=b or a not in SCALARS: self.err(n,'equality requires matching scalar types')
                ty='bool'
            else:
                if a not in INTEGERS or a!=b: self.err(n,'arithmetic/comparison requires matching integer types')
                ty='bool' if op in ('<','>','<=','>=') else a
        else: self.err(n,'invalid expression')
        n.type=ty; return ty
    def match(self,n,env):
        ty=self.expr(n.children[0],env)
        if ty not in self.unions: self.err(n,'match requires a tagged union value')
        seen=set(); all_return=True
        for arm in n.children[1]:
            owner,variant=arm.value
            if owner!=ty: self.err(arm,f'case type {owner} does not match {ty}')
            if variant not in self.unions[ty]: self.err(arm,f'unknown variant {ty}.{variant}')
            if variant in seen: self.err(arm,f'duplicate case {ty}.{variant}')
            seen.add(variant); fields=self.unions[ty][variant].children; binders,body=arm.children
            if len(binders)!=len(fields): self.err(arm,'pattern payload count does not match variant')
            branch=env.copy(); names=set()
            for b,f in zip(binders,fields):
                b.type=f.value[1]
                if b.value=='_': continue
                if b.value in names: self.err(b,f'duplicate pattern binding {b.value}')
                names.add(b.value); b.symbol=self.fresh(); branch[b.value]=(b.type,b.symbol)
            total=self.block(body,branch); all_return=all_return and total
        missing=set(self.unions[ty])-seen
        if missing: self.err(n,'non-exhaustive match; missing: '+', '.join(sorted(missing)))
        return all_return
    def block(self,stmts,outer):
        env=outer.copy(); declared=set(); returns=False
        for n in stmts:
            if returns: self.err(n,'unreachable statement')
            k=n.kind
            if k=='local':
                name,ty=n.value
                if name in declared: self.err(n,f'duplicate local {name}')
                if ty=='unit': self.err(n,'unit locals are not permitted')
                self.valid_type(n,ty)
                self.require(n,self.expr(n.children[0],env),ty)
                n.symbol=self.fresh(); env[name]=(ty,n.symbol); declared.add(name)
            elif k=='assign':
                if n.value not in env: self.err(n,f'unknown local {n.value}')
                ty,n.symbol=env[n.value]; self.require(n,self.expr(n.children[0],env),ty)
            elif k=='store':
                ty=self.place(n.children[0],env); self.require(n,self.expr(n.children[1],env),ty)
            elif k=='return':
                self.require(n,self.expr(n.children[0],env),self.ret); returns=True
            elif k=='expr': self.expr(n.children[0],env)
            elif k=='if':
                self.require(n,self.expr(n.children[0],env),'bool')
                a=self.block(n.children[1],env); b=self.block(n.children[2],env); returns=a and b
            elif k=='match':
                returns=self.match(n,env)
            elif k=='while':
                self.require(n,self.expr(n.children[0],env),'bool'); self.block(n.children[1],env)
        return returns

RUNTIME = r'''/* Generated by KCC 0.7. Checked integer arithmetic; no managed runtime. */
#include <stdint.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
static _Noreturn void k_trap(void) { fputs("Awl arithmetic trap\n", stderr); abort(); }
static _Noreturn void k_bad_tag(void) { fputs("Awl invalid union tag\n", stderr); abort(); }
static void k_print_bool(bool x) { puts(x ? "true" : "false"); }
'''
CT={ty:('int' if signed else 'uint')+str(bits)+'_t' for ty,(signed,bits) in INTEGERS.items()}
CT.update({'bool':'bool','unit':'void'})

def integer_runtime(required=None):
    """C11 helpers: never perform an overflowing signed host operation or an
    out-of-range signed narrowing. Exact-width semantics do not follow C promotions.
    """
    lines=[]
    def add(name,code):
        if required is None or name in required: lines.append(code)
    for ty,(signed,bits) in INTEGERS.items():
        ct=CT[ty]; hi=('INT' if signed else 'UINT')+str(bits)+'_MAX'; lo='INT'+str(bits)+'_MIN'
        fmt='PRId64' if signed else 'PRIu64'; wide='int64_t' if signed else 'uint64_t'
        add('k_print_'+ty,f'static void k_print_{ty}({ct} x) {{ printf("%" {fmt} "\\n", ({wide})x); }}')
        for op,sign in [('add','+'),('sub','-'),('mul','*'),('div','/'),('rem','%')]:
            guard=''; expression=f'a {sign} b'
            if op in ('div','rem'):
                guard=f'if (b==0'+(f' || (a=={lo} && b==-1)' if signed else '')+') k_trap();'
            elif ty=='i64':
                guard={'add':'if ((b>0 && a>INT64_MAX-b)||(b<0 && a<INT64_MIN-b)) k_trap();',
                       'sub':'if ((b<0 && a>INT64_MAX+b)||(b>0 && a<INT64_MIN+b)) k_trap();',
                       'mul':'if (a>0 ? (b>0 ? a>INT64_MAX/b : b<INT64_MIN/a) : (a<0 ? (b>0 ? a<INT64_MIN/b : b<0 && a<INT64_MAX/b) : false)) k_trap();'}[op]
            elif ty=='u64':
                guard={'add':'if (a>UINT64_MAX-b) k_trap();','sub':'if (a<b) k_trap();',
                       'mul':'if (b && a>UINT64_MAX/b) k_trap();'}[op]
            else:
                if not signed and op=='sub': guard='if (a<b) k_trap();'
                expression=f'({wide})a {sign} ({wide})b'
                guard+=f'{wide} r = {expression}; '
                guard+=f'if (r>{hi}'+(f' || r<{lo}' if signed else '')+') k_trap();'
                expression='r'
            # Small integers promote to int for division/remainder, which is safe
            # after checking the type-specific minimum / -1 case above.
            add(f'k_{ty}_{op}',f'static {ct} k_{ty}_{op}({ct} a, {ct} b) {{ {guard} return ({ct})({expression}); }}')
    for dst,(ds,db) in INTEGERS.items():
        maximum=('INT' if ds else 'UINT')+str(db)+'_MAX'; minimum='INT'+str(db)+'_MIN'
        for src,(ss,sb) in INTEGERS.items():
            guards=[]
            if ss and ds and sb>db: guards=[f'a<{minimum} || a>{maximum}']
            elif not ss and not ds and sb>db: guards=[f'a>{maximum}']
            elif ss and not ds:
                guards=['a<0']
                if sb>db: guards.append(f'(uint64_t)a>{maximum}')
            elif not ss and ds and sb>=db: guards=[f'(uint64_t)a>(uint64_t){maximum}']
            guard=''.join(f'if ({g}) k_trap(); ' for g in guards)
            add(f'k_convert_{src}_{dst}',f'static {CT[dst]} k_convert_{src}_{dst}({CT[src]} a) {{ {guard}return ({CT[dst]})a; }}')
    return '\n'.join(lines)+'\n'

def ctype(ty): return CT[ty] if ty in CT else 'k_s_'+ty
class Emitter:
    """Linearize operands to preserve left-to-right evaluation despite C argument order."""
    def __init__(self,fs):
        self.declarations=fs; self.fs=[f for f in fs if f.kind=='function']
        self.structs={d.value:d for d in fs if d.kind=='struct'}
        self.unions={d.value:d for d in fs if d.kind=='union'}
        self.lines=[]; self.serial=0; self.depth=0; self.helpers=set()
    def helper(self,name,*args):
        self.helpers.add(name); return name+'('+', '.join(args)+')'
    def line(self,s): self.lines.append('    '*self.depth+s)
    def temp(self,ty,expr):
        if ty=='unit': self.line(expr+';'); return ''
        self.serial+=1; name=f'k_t{self.serial}'; self.line(f'{ctype(ty)} {name} = {expr};'); return name
    def expr(self,n):
        k=n.kind
        if k in ('int','uint'):
            value='INT64_MIN' if n.value==-(1<<63) else f'{"INT64_C" if k=="int" else "UINT64_C"}({n.value})'
            return f'(({ctype(n.type)})({value}))'
        if k=='convert':
            source=self.expr(n.children[0]); src=n.children[0].type
            return self.temp(n.type,self.helper(f'k_convert_{src}_{n.type}',source))
        if k=='field':
            base=self.expr(n.children[0]); return self.temp(n.type,f'{base}.k_f_{n.value}')
        if k=='bool': return 'true' if n.value else 'false'
        if k=='name': return self.temp(n.type,n.symbol)
        if k=='unary':
            a=self.expr(n.children[0]); return self.temp(n.type,f'(!{a})' if n.value=='not' else self.helper(f'k_{n.type}_sub','0',a))
        if k=='binary':
            a=self.expr(n.children[0]); op=n.value
            if op in ('and','or'):
                t=self.temp('bool',a); self.line(f'if ({"!" if op=="or" else ""}{t}) {{'); self.depth+=1
                b=self.expr(n.children[1]); self.line(f'{t} = {b};'); self.depth-=1; self.line('}'); return t
            b=self.expr(n.children[1]); fun={'+':'add','-':'sub','*':'mul','/':'div','%':'rem'}.get(op)
            return self.temp(n.type,self.helper(f'k_{n.children[0].type}_{fun}',a,b) if fun else f'({a} {op} {b})')
        if k=='union_ctor':
            owner,variant=n.value; variants=self.unions[owner].children
            index=next(i for i,v in enumerate(variants) if v.value==variant); fields=variants[index].children
            args=[self.expr(a) for a in n.children]
            init=', '.join('.k_f_'+f.value[0]+' = '+a for f,a in zip(fields,args)) or '.k_unused = 0'
            return self.temp(n.type,f'({ctype(n.type)}){{.k_tag = {index}, .k_data.k_v_{variant} = {{{init}}}}}')
        if k=='call':
            args=[self.expr(a) for a in n.children]
            if n.value in self.structs:
                fields=self.structs[n.value].children
                init=', '.join('.k_f_'+f.value[0]+' = '+a for f,a in zip(fields,args))
                return self.temp(n.type,f'({ctype(n.type)}){{{init}}}')
            name='k_print_'+n.children[0].type if n.value=='print' else 'k_fn_'+n.value
            call=self.helper(name,*args) if n.value=='print' else f'{name}({", ".join(args)})'
            return self.temp(n.type,call)
        raise Error('internal emitter error')
    def block(self,body):
        for n in body:
            k=n.kind
            if k=='local':
                x=self.expr(n.children[0]); self.line(f'{ctype(n.value[1])} {n.symbol} = {x};')
            elif k=='assign':
                x=self.expr(n.children[0]); self.line(f'{n.symbol} = {x};')
            elif k=='store':
                target=self.place(n.children[0]); x=self.expr(n.children[1]); self.line(f'{target} = {x};')
            elif k=='return':
                x=self.expr(n.children[0]); self.line(f'return {x};' if x else 'return;')
            elif k=='expr': self.expr(n.children[0])
            elif k=='if':
                c=self.expr(n.children[0]); self.line(f'if ({c}) {{'); self.depth+=1; self.block(n.children[1]); self.depth-=1
                self.line('} else {'); self.depth+=1; self.block(n.children[2]); self.depth-=1; self.line('}')
            elif k=='match': self.match(n)
            elif k=='while':
                self.line('while (true) {'); self.depth+=1; c=self.expr(n.children[0]); self.line(f'if (!{c}) break;'); self.block(n.children[1]); self.depth-=1; self.line('}')
    def match(self,n):
        snapshot=self.expr(n.children[0]); variants=self.unions[n.children[0].type].children
        self.line(f'switch ({snapshot}.k_tag) {{'); self.depth+=1
        for arm in n.children[1]:
            variant=arm.value[1]; index=next(i for i,v in enumerate(variants) if v.value==variant)
            self.line(f'case {index}: {{'); self.depth+=1
            for b,f in zip(arm.children[0],variants[index].children):
                if b.value!='_':
                    self.line(f'{ctype(b.type)} {b.symbol} = {snapshot}.k_data.k_v_{variant}.k_f_{f.value[0]};')
            self.block(arm.children[1]); self.line('break;'); self.depth-=1; self.line('}')
        self.line('default: k_bad_tag();'); self.depth-=1; self.line('}')
    def place(self,n):
        if n.kind=='name': return n.symbol
        return self.place(n.children[0])+'.k_f_'+n.value
    def signature(self,f):
        name,ret=f.value
        args=', '.join(ctype(p.value[1])+' '+p.symbol for p in f.children[0]) or 'void'
        return f'static {ctype(ret)} k_fn_{name}({args})'
    def emit(self):
        verify_ir(self.declarations)
        self.lines=[]; self.helpers=set()
        order,_=layout_values(self.declarations)
        for d in order:
            self.line(f'typedef struct k_s_{d.value} {{')
            if d.kind=='struct':
                for f in d.children: self.line(f'    {ctype(f.value[1])} k_f_{f.value[0]};')
            else:
                self.line('    uint32_t k_tag;'); self.line('    union {')
                for v in d.children:
                    self.line('        struct {')
                    for f in v.children: self.line(f'            {ctype(f.value[1])} k_f_{f.value[0]};')
                    if not v.children: self.line('            uint8_t k_unused;')
                    self.line(f'        }} k_v_{v.value};')
                self.line('    } k_data;')
            self.line(f'}} k_s_{d.value};')
        for f in self.fs: self.line(self.signature(f)+';')
        for f in self.fs:
            self.line(self.signature(f)+' {'); self.depth=1; self.block(f.children[1]); self.depth=0; self.line('}')
        self.line('int main(void) { return (int)((uint64_t)k_fn_main() & UINT64_C(255)); }')
        return RUNTIME+integer_runtime(self.helpers)+'\n'.join(self.lines)+'\n'

def check_tree_limits(fs):
    stack=[(f,1) for f in fs]; count=0
    while stack:
        item,depth=stack.pop()
        if isinstance(item,list):
            stack.extend((x,depth) for x in item); continue
        if not isinstance(item,Node): raise Error('invalid internal tree')
        count+=1
        if depth>MAX_DEPTH:
            raise source_error(item.token,f'IR nesting exceeds {MAX_DEPTH}','E006')
        if count>MAX_TOKENS:
            raise source_error(item.token,'IR node budget exceeded','E007')
        stack.extend((x,depth+1) for x in item.children)

def verify_ir(fs):
    """Independent read-only KIR0 verifier; never repairs type/symbol metadata.

    Protects the C emitter from malformed types, free symbols, bad operator shapes,
    unchecked literals, forged calls, missing returns and invalid identifiers.
    Not a proof that the frontend implements the intended language semantics.
    """
    def fail(message): raise Error(diagnostics=[Diagnostic('E500','IR verification failed: '+message)])
    def need(condition,message):
        if not condition: fail(message)
    def ident(name):
        return isinstance(name,str) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name) and name not in RESERVED
    def pair(value): return isinstance(value,tuple) and len(value)==2
    def node(n,kind=None,arity=None):
        need(isinstance(n,Node),'expected node')
        need(isinstance(n.children,list),'children must be a list')
        need(isinstance(n.token,Token),'missing source token')
        if kind is not None: need(n.kind==kind,'invalid node kind')
        if arity is not None: need(len(n.children)==arity,'invalid child count for '+n.kind)
    need(isinstance(fs,list),'function list required')
    sigs={}; used=set(); structs={}; unions={}; aggregate_names=set()
    for d in fs:
        node(d)
        need(d.kind in ('struct','union','function'),'invalid declaration kind')
        if d.kind in ('struct','union'):
            need(ident(d.value) and d.value!='print' and d.value not in aggregate_names,'invalid aggregate name')
            aggregate_names.add(d.value)
        if d.kind=='struct':
            need(ident(d.value) and d.value!='print' and d.value not in structs,'invalid struct name')
            fields={}
            for f in d.children:
                node(f,'field_decl',0); need(pair(f.value),'invalid field declaration')
                name,ty=f.value
                need(ident(name) and name not in fields,'invalid/duplicate field name')
                need(isinstance(ty,str),'invalid field type'); fields[name]=ty
            structs[d.value]=fields
        elif d.kind=='union':
            variants={}
            for v in d.children:
                node(v,'variant_decl'); need(ident(v.value) and v.value not in variants,'invalid/duplicate variant name')
                fields={}
                for f in v.children:
                    node(f,'field_decl',0); need(pair(f.value),'invalid payload declaration')
                    name,ty=f.value
                    need(ident(name) and name not in fields,'invalid/duplicate payload field')
                    need(isinstance(ty,str),'invalid payload type'); fields[name]=ty
                variants[v.value]=fields
            unions[d.value]=variants
    def value_type(ty): return isinstance(ty,str) and (ty in SCALARS or ty in structs or ty in unions)
    for fields in structs.values():
        need(all(value_type(t) for t in fields.values()),'invalid struct field type')
    for variants in unions.values():
        for fields in variants.values(): need(all(value_type(t) for t in fields.values()),'invalid variant payload type')
    functions=[f for f in fs if f.kind=='function']
    def binding(n,ty):
        need(isinstance(n.symbol,str) and re.fullmatch(r'k_v[1-9][0-9]*',n.symbol),'invalid binding symbol')
        need(n.symbol not in used,'duplicate binding symbol')
        need(value_type(ty),'invalid binding type'); used.add(n.symbol)
    for f in functions:
        node(f,'function',2); need(pair(f.value),'invalid function signature')
        name,ret=f.value
        need(ident(name) and name!='print' and name not in sigs and name not in aggregate_names,'invalid/duplicate function name')
        need(ret=='unit' or value_type(ret),'invalid return type')
        params,body=f.children
        need(isinstance(params,list) and isinstance(body,list),'invalid function children')
        types=[]; names=set()
        for p in params:
            node(p,'param',0); need(pair(p.value),'invalid parameter')
            pn,pt=p.value
            need(ident(pn) and pn not in names,'invalid/duplicate parameter name')
            names.add(pn); binding(p,pt); types.append(pt)
        sigs[name]=(types,ret)
    try: layout_values(fs)
    except Error as error: fail(str(error))
    need(sigs.get('main')==([], 'i64'),'invalid entry point')

    def expression(n,env):
        node(n); k=n.kind
        if k in ('int','uint'):
            node(n,arity=0); ty=n.literal_type
            need(isinstance(ty,str) and ty in INTEGERS,'invalid literal type')
            need((k=='int')==(ty in SIGNED),'literal signedness mismatch')
            low,high=bounds(ty); need(type(n.value) is int and low<=n.value<=high,'invalid integer literal')
        elif k=='convert':
            node(n,arity=1); need(isinstance(n.value,str) and n.value in INTEGERS,'invalid conversion target')
            need(expression(n.children[0],env) in INTEGERS,'invalid conversion operand'); ty=n.value
        elif k=='field':
            node(n,arity=1); base=expression(n.children[0],env)
            need(base in structs and isinstance(n.value,str) and n.value in structs[base],'invalid field projection')
            ty=structs[base][n.value]
        elif k=='bool':
            node(n,arity=0); need(type(n.value) is bool,'invalid boolean literal'); ty='bool'
        elif k=='name':
            node(n,arity=0); need(isinstance(n.value,str) and n.value in env,'free local name')
            ty,sym=env[n.value]; need(n.symbol==sym,'incorrect resolved local symbol')
        elif k=='unary':
            node(n,arity=1); need(n.value in ('-','not'),'invalid unary operator')
            ty=expression(n.children[0],env)
            need(ty=='bool' if n.value=='not' else ty in SIGNED,'unary operand type')
        elif k=='binary':
            node(n,arity=2); op=n.value
            need(isinstance(op,str) and op in Parser.PREC,'invalid binary operator')
            a=expression(n.children[0],env); b=expression(n.children[1],env)
            if op in ('and','or'): need(a==b=='bool','logical operand types'); ty='bool'
            elif op in ('==','!='): need(a==b and a in SCALARS,'equality operand types'); ty='bool'
            else:
                need(a==b and a in INTEGERS,'arithmetic/comparison operand types')
                ty='bool' if op in ('<','>','<=','>=') else a
        elif k=='union_ctor':
            need(pair(n.value),'invalid union constructor'); owner,variant=n.value
            need(ident(owner) and owner in unions and ident(variant) and variant in unions[owner],'unknown union constructor')
            args=[expression(x,env) for x in n.children]
            need(args==list(unions[owner][variant].values()),'invalid union arguments'); ty=owner
        elif k=='call':
            need(ident(n.value),'invalid callee name'); args=[expression(x,env) for x in n.children]
            if n.value=='print': need(len(args)==1 and args[0] in SCALARS,'invalid print call'); ty='unit'
            elif n.value in structs:
                need(args==list(structs[n.value].values()),'invalid constructor arguments'); ty=n.value
            else:
                need(n.value in sigs,'unknown callee'); expected,ty=sigs[n.value]
                need(args==expected,'invalid call arguments')
        else: fail('invalid expression kind')
        need(n.type==ty,'incorrect expression type annotation'); return ty

    def place(n,env):
        node(n)
        if n.kind=='name': return expression(n,env)
        need(n.kind=='field','invalid assignment place'); node(n,arity=1)
        base=place(n.children[0],env)
        need(base in structs and isinstance(n.value,str) and n.value in structs[base],'invalid place field')
        ty=structs[base][n.value]; need(n.type==ty,'incorrect place annotation'); return ty

    def matched(n,env,ret):
        node(n,'match',2); ty=expression(n.children[0],env)
        need(ty in unions,'match on non-union'); arms=n.children[1]
        need(isinstance(arms,list),'invalid arm list'); seen=set(); total=True
        for arm in arms:
            node(arm,'case',2); need(pair(arm.value),'invalid case identity'); owner,variant=arm.value
            need(owner==ty and isinstance(variant,str) and variant in unions[ty],'invalid case variant')
            need(variant not in seen,'duplicate case'); seen.add(variant)
            binders,body=arm.children; need(isinstance(binders,list),'invalid binder list')
            fields=list(unions[ty][variant].values()); need(len(binders)==len(fields),'pattern arity mismatch')
            names=set(); branch=env.copy()
            for b,ft in zip(binders,fields):
                node(b,'pattern_bind',0); need(ident(b.value),'invalid pattern name')
                need(b.type==ft,'pattern annotation mismatch')
                if b.value=='_': need(b.symbol is None,'discard has a symbol'); continue
                need(b.value not in names,'duplicate pattern binding'); names.add(b.value)
                binding(b,ft); branch[b.value]=(ft,b.symbol)
            arm_total=block(body,branch,ret); total=total and arm_total
        need(seen==set(unions[ty]),'non-exhaustive match')
        return total

    def block(body,outer,ret):
        need(isinstance(body,list),'invalid block'); env=outer.copy(); declared=set(); total=False
        for n in body:
            node(n); need(not total,'unreachable statement'); k=n.kind
            if k=='local':
                node(n,arity=1); need(pair(n.value),'invalid local'); name,ty=n.value
                need(ident(name) and name not in declared,'invalid/duplicate local name')
                need(expression(n.children[0],env)==ty,'local initializer type')
                binding(n,ty); declared.add(name); env[name]=(ty,n.symbol)
            elif k=='assign':
                node(n,arity=1); need(isinstance(n.value,str) and n.value in env,'assignment to free local')
                ty,sym=env[n.value]; need(n.symbol==sym,'assignment symbol mismatch')
                need(expression(n.children[0],env)==ty,'assignment type')
            elif k=='store':
                node(n,arity=2); need(place(n.children[0],env)==expression(n.children[1],env),'field store type')
            elif k=='return':
                node(n,arity=1); need(expression(n.children[0],env)==ret,'return type'); total=True
            elif k=='expr': node(n,arity=1); expression(n.children[0],env)
            elif k=='if':
                node(n,arity=3); need(expression(n.children[0],env)=='bool','if condition type')
                a=block(n.children[1],env,ret); b=block(n.children[2],env,ret); total=a and b
            elif k=='match': total=matched(n,env,ret)
            elif k=='while':
                node(n,arity=2); need(expression(n.children[0],env)=='bool','while condition type')
                block(n.children[1],env,ret)
            else: fail('invalid statement kind')
        return total
    check_tree_limits(fs)
    for f in functions:
        env={p.value[0]:(p.value[1],p.symbol) for p in f.children[0]}
        total=block(f.children[1],env,f.value[1])
        need(f.value[1]=='unit' or total,'missing total return')
    return None

# Contributor syntax/typed-arena adapters. Standalone kcc never calls Python.
def native_parser_api():
    import ctypes as C
    lib,Result=load_native_lexer()
    TokenRecord=Result._fields_[0][1]._type_
    try:
        lib.Awl_parse_abi_version.restype=C.c_uint32
        if lib.Awl_parse_abi_version()!=1: raise Error('native parser ABI mismatch; rebuild and restart KCC')
        lib.Awl_parse_tokens.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(TokenRecord),C.c_uint32,C.POINTER(C.c_void_p)]
        lib.Awl_parse_tokens.restype=C.c_int
        lib.Awl_parse_json.argtypes=[C.c_void_p,C.POINTER(C.c_size_t)]; lib.Awl_parse_json.restype=C.c_void_p
        lib.Awl_parse_node_count.argtypes=[C.c_void_p]; lib.Awl_parse_node_count.restype=C.c_uint32
        lib.Awl_parse_free.argtypes=[C.c_void_p]; lib.Awl_parse_free.restype=None
        lib.Awl_parse_benchmark.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(TokenRecord),C.c_uint32,C.c_uint32,C.POINTER(C.c_double),C.POINTER(C.c_uint64)]
        lib.Awl_parse_benchmark.restype=C.c_int
    except AttributeError: raise Error('native parser unavailable; rebuild with python compiler/build_native.py')
    return lib,TokenRecord

def native_token_records(tokens,Record):
    import struct
    data=bytearray(len(tokens)*20)
    for i,t in enumerate(tokens): struct.pack_into('=IIIII',data,i*20,t.start,t.end,t.line,t.column,0)
    # The array keeps its backing bytearray alive for the entire FFI call.
    return (Record*len(tokens)).from_buffer(data)

def native_syntax_arena(text,lexer=None):
    import ctypes as C
    tokens=lex(text,lexer); encoded=text.encode('utf-8')
    lib,Record=native_parser_api(); records=native_token_records(tokens,Record); handle=C.c_void_p()
    status=lib.Awl_parse_tokens(encoded,len(encoded),records,len(records),C.byref(handle))
    try:
        if status or not handle: raise Error(f'native parser failed with status {status}')
        size=C.c_size_t(); data=lib.Awl_parse_json(handle,C.byref(size))
        if not data or size.value>67108864: raise Error('invalid native syntax export')
        arena=json.loads(C.string_at(data,size.value).decode('utf-8'))
        if arena.get('format')!='KAST-arena-v1': raise Error('unknown native syntax format')
        diagnostics=[]
        for d in arena['diagnostics']:
            if not 0<=d['token']<len(tokens): raise Error('invalid syntax diagnostic token')
            diagnostics.append(problem(tokens[d['token']],d['message'],d['code']))
        if diagnostics: raise Error(diagnostics=diagnostics)
        return arena,tokens
    finally:
        if handle: lib.Awl_parse_free(handle)

def parse_native(text,lexer=None):
    arena,tokens=native_syntax_arena(text,lexer)
    return hydrate_native_arena(arena,tokens)

def hydrate_native_arena(arena,tokens,typed=False):
    values=[]
    if len(arena['nodes'])>200002: raise Error('native syntax node budget exceeded')
    for i,row in enumerate(arena['nodes']):
        if any(type(c) is not int or c<0 or c>=i for c in row['children']):
            raise Error('invalid native syntax reference')
        children=[values[c] for c in row['children']]
        if row['kind']=='#list': values.append(children); continue
        token=row['token']
        if type(token) is not int or not 0<=token<len(tokens): raise Error('invalid native syntax token')
        kind=row['value_kind']; value=row['value']
        if kind=='pair': value=(value,row['second'])
        elif kind=='integer':
            if not re.fullmatch('-?[0-9]{1,256}',value): raise Error('invalid native integer spelling')
            value=int(value)
        elif kind=='bool': value=value=='true'
        elif kind=='null': value=None
        elif kind!='string': raise Error('invalid native syntax value kind')
        values.append(Node(row['kind'],tokens[token],value,children,type=(row.get('type') or None) if typed else None,symbol=(row.get('symbol') or None) if typed else None,literal_type=row['literal_type'] or None))
    if any(type(c) is not int or not 0<=c<len(values) for c in arena['roots']):
        raise Error('invalid native syntax root')
    return [values[i] for i in arena['roots']]

def check_native_source(text):
    """Developer/reference bridge only. Standalone kcc does not call Python."""
    return native_source_output(text)

def emit_native_c(text):
    """Contributor adapter to native verified C emission, not the installed path."""
    return native_source_output(text,emit_c=True)

def native_source_output(text,emit_c=False):
    import ctypes as C
    try: source=text.encode('utf-8')
    except UnicodeEncodeError: raise Error(diagnostics=[Diagnostic('E008','source must be UTF-8')])
    lib,_=native_parser_api()
    lib.Awl_parse_source.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(C.c_void_p)]; lib.Awl_parse_source.restype=C.c_int
    lib.Awl_check_unit.argtypes=[C.c_void_p]; lib.Awl_check_unit.restype=C.c_int
    lib.Awl_verify_unit.argtypes=[C.c_void_p]; lib.Awl_verify_unit.restype=C.c_int
    lib.Awl_render_diagnostics.argtypes=[C.c_void_p,C.c_char_p,C.c_int,C.POINTER(C.c_size_t)]; lib.Awl_render_diagnostics.restype=C.c_void_p
    unit=C.c_void_p()
    status=lib.Awl_parse_source(source,len(source),C.byref(unit))
    try:
        if status or not unit: raise Error(f'native source frontend failed with status {status}')
        status=lib.Awl_check_unit(unit)
        if status==2: raise Error('native semantic checker failed internally')
        if status==0:
            if emit_c:
                lib.Awl_emit_c.argtypes=[C.c_void_p,C.POINTER(C.c_void_p),C.POINTER(C.c_size_t)];lib.Awl_emit_c.restype=C.c_int
                output=C.c_void_p();output_size=C.c_size_t()
                status=lib.Awl_emit_c(unit,C.byref(output),C.byref(output_size))
            else: status=lib.Awl_verify_unit(unit)
            if status==2: raise Error('native verifier/backend failed internally')
        if status:
            size=C.c_size_t(); report=lib.Awl_render_diagnostics(unit,b'<source>',1,C.byref(size))
            if not report: raise Error('native diagnostic export failed')
            data=json.loads(C.string_at(report,size.value).decode('utf-8'))
            raise Error(diagnostics=[Diagnostic(**d) for d in data['diagnostics']])
        if emit_c:
            if not output or output_size.value>67108864: raise Error('native C export failed')
            return C.string_at(output,output_size.value).decode('utf-8')
        size=C.c_size_t(); data=lib.Awl_parse_json(unit,C.byref(size))
        if not data or size.value>67108864: raise Error('native checked syntax export failed')
        return json.loads(C.string_at(data,size.value).decode('utf-8'))
    finally:
        if unit: lib.Awl_parse_free(unit)

def parse_text(text,lexer=None,parser=None):
    backend=parser or os.environ.get('KCC_PARSER','python')
    if backend=='python': fs=Parser(text,lexer).program()
    elif backend=='native': fs=parse_native(text,lexer)
    else: raise Error(f'unknown parser backend {backend!r}; choose python or native')
    check_tree_limits(fs)
    return fs

def compile_text(text,lexer=None,parser=None):
    fs=parse_text(text,lexer,parser)
    fs=Checker(fs).check()
    verify_ir(fs)
    return fs

def render_diagnostics(error, source, filename, fmt='text'):
    ds=error.diagnostics or [Diagnostic('E900',str(error))]
    if fmt=='json':
        return json.dumps({'file':str(filename),'diagnostics':[D.asdict(d) for d in ds]},indent=2)
    lines=source.splitlines(); rendered=[]
    for d in ds:
        line=lines[d.line-1] if 0<d.line<=len(lines) else ''
        # Tabs count as one source column, expanded only for display. Limit
        # long lines/carets so diagnostics cannot amplify huge source tokens.
        start=max(0,d.column-1); lo=max(0,start-60); hi=min(len(line),start+100)
        fragment=line[lo:hi]; prefix='...' if lo else ''
        caret=len(prefix)+len(line[lo:start].expandtabs(4))
        width=max(1,min(80,len(line[start:min(d.end_column-1,hi)].expandtabs(4))))
        rendered.append(f'{filename}:{d.line}:{d.column}: error[{d.code}]: {d.message}'
                        + ('\n  '+prefix+fragment.expandtabs(4)+'\n  '+' '*caret+'^'+'~'*(width-1) if line else ''))
    return '\n'.join(rendered)

def read_source(path):
    # Bounded read, including files that grow after stat or are special files.
    with path.open('rb') as f: data=f.read(MAX_SOURCE_BYTES+1)
    if len(data)>MAX_SOURCE_BYTES:
        raise Error(diagnostics=[Diagnostic('E001',f'source exceeds {MAX_SOURCE_BYTES} bytes')])
    try: return data.decode('utf-8')
    except UnicodeDecodeError: raise Error(diagnostics=[Diagnostic('E008','source must be UTF-8')])

def find_cc(explicit=None):
    cc=explicit or os.environ.get('CC') or ('gcc' if os.name=='nt' else 'cc')
    path=shutil.which(cc)
    if not path: raise Error(f'C compiler {cc!r} not found; install GCC/Clang or pass --cc PATH (one executable)')
    return path

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--version',action='version',version=VERSION)
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('doctor')
    for cmd in ('check','emit-c','emit-ir','build','run'):
        q=sub.add_parser(cmd); q.add_argument('source',type=Path)
        q.add_argument('--parser',choices=['python','native'],default=None)
        q.add_argument('--lexer',choices=['python','native'],default=None)
        q.add_argument('--diagnostic-format',choices=['text','json'],default='text')
        if cmd in ('emit-c','emit-ir','build'): q.add_argument('-o','--output',type=Path)
        if cmd in ('build','run'):
            q.add_argument('--cc'); q.add_argument('-O',choices=['0','1','2','3'],default='2'); q.add_argument('--sanitize',action='store_true')
    a=p.parse_args(argv)
    source=''
    try:
        if a.cmd=='doctor':
            print(json.dumps({'kcc':VERSION,'host_os':platform.system(),'host_arch':platform.machine(),'python':platform.python_version(),'c_compiler':find_cc(),'frontend':'Python checker/emitter; optional C++20 lexer and parser','default_parser':os.environ.get('KCC_PARSER','python'),'default_lexer':os.environ.get('KCC_LEXER','python'),'native_lexer_library_present':native_library_path().is_file(),'backend':'C11 bootstrap; host baseline only','gpu':'not implemented','hardware_dispatch':'not implemented'},indent=2)); return 0
        if a.source.suffix!='.aw': raise Error('Awl source files must use .aw')
        source=read_source(a.source)
        fs=compile_text(source,a.lexer,a.parser)
        if a.cmd=='check': print(f'{a.source}: checked'); return 0
        if a.cmd in ('emit-c','emit-ir'):
            text=Emitter(fs).emit() if a.cmd=='emit-c' else json.dumps({'format':'KIR0-structured-v0.5','declarations':[D.asdict(f) for f in fs]},indent=2)+'\n'
            if a.output: a.output.write_text(text,encoding='utf-8')
            else: print(text,end='')
            return 0
        cc=find_cc(a.cc)
        with tempfile.TemporaryDirectory(prefix='kcc-') as td:
            c=Path(td)/'program.c'; c.write_text(Emitter(fs).emit(),encoding='utf-8')
            exe=(a.output or a.source.with_suffix('.exe' if os.name=='nt' else '')).resolve() if a.cmd=='build' else Path(td)/('program.exe' if os.name=='nt' else 'program')
            flags=['-std=c11','-O'+a.O,'-Wall','-Wextra']
            if a.sanitize: flags+=['-fsanitize=undefined,address','-fno-omit-frame-pointer']
            proc=subprocess.run([cc,*flags,str(c),'-o',str(exe)],capture_output=True,text=True)
            if proc.returncode: raise Error('native backend failed:\n'+proc.stderr)
            if a.cmd=='build': print(exe); return 0
            return subprocess.run([str(exe)]).returncode
    except Error as e:
        print(render_diagnostics(e,source,getattr(a,'source','<driver>'),getattr(a,'diagnostic_format','text')),file=sys.stderr)
        return 1
    except (OSError,RecursionError) as e:
        print(f'kcc: error: {e}',file=sys.stderr); return 1
if __name__=='__main__': sys.exit(main())

#!/usr/bin/env python3
"""One-way contributor migration of the previous next surface syntax, not a parser compatibility mode."""
import argparse,re
from pathlib import Path
TOKEN=re.compile(r'--[^\n]*|"(?:\\.|[^"\\\r\n])*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+(?:[iu](?:8|16|32|64))?|::|->|==|!=|<=|>=|[^\s]')
def type_end(words,k):
 if words[k] in ('view','vector') and k+1<len(words) and words[k+1]=='<':return k+3
 if words[k]=='[':return k+4
 if k+1<len(words) and words[k+1]=='.':return k+2
 return k
def migrate(source):
 tokens=[m for m in TOKEN.finditer(source) if not m[0].startswith('--')];words=[m[0] for m in tokens];edits=[];stack=[];parens=[];signature=False;pending=None
 def put(i,text,end=None):edits.append((tokens[i].start(),tokens[i if end is None else end].end(),text))
 for i,w in enumerate(words):
  before=words[i-1] if i else '';after=words[i+1] if i+1<len(words) else ''
  if w.startswith(chr(34)):
   escaped='';slashes=0
   for j,c in enumerate(w):
    if c=='$' and j+1<len(w) and w[j+1]=='{' and slashes%2==0:escaped+='\\'
    escaped+=c;slashes=slashes+1 if c=='\\' else 0
   if escaped!=w:put(i,escaped)
  if w in ['func','if','while','match','case']:pending=w
  if w=='func':stack.append('func');signature=True
  elif w in ['match','enum']:stack.append(w)
  elif w=='then':
   if pending=='if':stack.append('if');put(i,'{')
   pending=None
  elif w=='do' and pending=='while':stack.append('while');put(i,'{');pending=None
  elif w=='{' and pending in ('if','while'):pending=None
  elif w=='else' and stack and stack[-1]=='if':put(i,'} else {')
  elif w=='end':
   if not stack:raise ValueError('unbalanced old next end')
   if stack.pop() in ['func','if','while']:put(i,'}')
  elif w=='(':
   kind='exports' if before=='exports' else 'signature' if signature else 'other'
   parens.append((kind,i));signature=False
  elif w==')':
   if not parens:raise ValueError('unbalanced old next parentheses')
   kind,open_i=parens.pop()
   if kind=='exports':put(i,'}')
   elif kind=='signature':
    empty=(open_i+1==i);has_ret=after in (':','->')
    if empty:put(open_i,'' if has_ret else ' {',i)
    else:put(open_i,' :: ');put(i,'' if has_ret else ' {')
    if has_ret:
     k=i+2
     if words[k:k+2]==['@','o']:k+=2
     elif words[k]=='own':k+=1
     end_k=type_end(words,k)
     put(end_k,words[end_k]+' {')
  if w=='(' and before=='exports':put(i,'{')
  if w=='->':put(i,': ')
  if w=='borrow':put(i,'@b')
  if w=='own' and after!=':' and (before=='->' or parens and parens[-1][0]=='signature'):put(i,'@o')
  if w=='scoped' and i>=2 and words[i-2:i]==['@','p']:put(i-2,'@s',i)
  if w=='rw' and before=='@':put(i,'w')
  if parens and parens[-1][0]=='signature' and w==':' and words[i+1:i+3]==['vector','<'] and words[i+4:i+5]==['>']:put(i,'['+words[i+3]+']',i+4)
 if stack or parens:raise ValueError('unterminated old next source')
 for start,end,text in sorted(edits,reverse=True):source=source[:start]+text+source[end:]
 return source
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('files',nargs='+',type=Path);a=p.parse_args()
 converted={path:migrate(path.read_text()) for path in a.files}
 for path,text in converted.items():path.write_text(text)

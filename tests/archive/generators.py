"""Seeded, typed expression generator with a Python value oracle (no eval)."""
def integer(rng,depth):
    if not depth or rng.random()<0.3:
        value=rng.randint(-20,20); return str(value),value
    a,x=integer(rng,depth-1); b,y=integer(rng,depth-1)
    op=rng.choice(['+','-','*','/','%'])
    if op in ('/','%') and y==0: b,y='1',1
    quotient=abs(x)//abs(y) * (-1 if (x<0)!=(y<0) else 1) if y else 0
    value={'+':lambda:x+y,'-':lambda:x-y,'*':lambda:x*y,'/':lambda:quotient,'%':lambda:x-quotient*y}[op]()
    if not -(1<<63)<=value<(1<<63): return '0',0
    return f'({a} {op} {b})',value

def boolean(rng,depth):
    if not depth or rng.random()<0.4:
        a,x=integer(rng,2); b,y=integer(rng,2); op=rng.choice(['==','!=','<','>','<=','>='])
        v={'==':x==y,'!=':x!=y,'<':x<y,'>':x>y,'<=':x<=y,'>=':x>=y}[op]
        return f'({a} {op} {b})',v
    if rng.random()<0.3:
        a,x=boolean(rng,depth-1); return f'(not {a})',not x
    a,x=boolean(rng,depth-1); b,y=boolean(rng,depth-1); op=rng.choice(['and','or'])
    return f'({a} {op} {b})',(x and y) if op=='and' else (x or y)

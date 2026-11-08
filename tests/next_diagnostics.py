"""Development gate: exact compiler diagnostics for typos, borrow misuse and misplaced control flow."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STRUCT='struct Row {\n    count:i64;\n    label:string;\n};\n'
CASES=[
 ('unknown field suggests the real one',STRUCT+'func main: i64 {\n    @p r Row: Row(1,"a");\n    print(r.cuont);\n    return 0;\n};\n','E200',"unknown field cuont on Row, did you mean 'count'?"),
 ('unknown function suggests the real one','func helper :: n:i64: i64 {\n    return n;\n};\nfunc main: i64 {\n    print(helpr(1));\n    return 0;\n};\n','E200',"unknown function helpr, did you mean 'helper'?"),
 ('unknown local suggests the real one','func main: i64 {\n    @p counter: 1;\n    print(cuonter);\n    return 0;\n};\n','E200',"unknown local cuonter, did you mean 'counter'?"),
 ('unknown variant suggests the real one','enum Kind A(); B(); end;\nfunc main: i64 {\n    @p k Kind: Kind.A();\n    match k then\n        case Kind.B() then print(1);\n        case Kind.C() then print(2);\n    end;\n    return 0;\n};\n','E200',"unknown variant Kind.C, did you mean 'A'?"),
 ('mutable borrow of a temporary',STRUCT+'func grow :: @m r:Row {\n    r.count: r.count + 1;\n};\nfunc main: i64 {\n    grow(Row(1,"a"));\n    return 0;\n};\n','E229',"@m arguments must be an existing local, field or element"),
 ('mutable borrow of a scalar',STRUCT+'func grow :: @m n:i64 {\n    return;\n};\nfunc main: i64 {\n    return 0;\n};\n','E229',"@m parameters must be a struct type, not i64"),
 ('mutable borrow type mismatch',STRUCT+'func grow :: @m r:Row, by:i64 {\n    r.count: r.count + by;\n};\nfunc main: i64 {\n    @p r Row: Row(1,"a");\n    grow(r,"two");\n    return 0;\n};\n','E200',"argument types ['Row', 'string'] do not match ['Row', 'i64']"),
 ('break outside a loop','func main: i64 {\n    break;\n    return 0;\n};\n','E226','break outside for/while loop'),
 ('bare return in a value function','func value: i64 {\n    return;\n};\nfunc main: i64 {\n    return 0;\n};\n','E200','return without a value in a function returning i64'),
 ('use after move','func main: i64 {\n    @s b spool: spool.new(4);\n    @p drained: drain(move b);\n    print(spool.snapshot(b));\n    return 0;\n};\nfunc drain :: @o scratch:spool: i64 {\n    return spool.length(scratch);\n};\n','E221','use of moved builder b'),
 ('struct equality rejects mismatched struct types','struct A {\n    x:i64;\n};\nstruct B {\n    x:i64;\n};\nfunc main: i64 {\n    @p a A: A(1);\n    @p b B: B(1);\n    if a == b {\n        print(1);\n    };\n    return 0;\n};\n','E200','equality requires matching scalar types or structs of scalars'),
 ('struct equality rejects enum fields','enum Kind A(); B(); end;\nstruct P {\n    k:Kind;\n};\nfunc main: i64 {\n    @p a P: P(Kind.A());\n    @p b P: P(Kind.A());\n    if a == b {\n        print(1);\n    };\n    return 0;\n};\n','E200','equality requires matching scalar types or structs of scalars'),
 ('resource struct cannot be copied','struct Bag {\n    counts:map<text,i64>;\n    name:string;\n};\nfunc main: i64 {\n    @s c map<text,i64>: map.new<text,i64>(4);\n    @s bag Bag: Bag(move c,\"a\");\n    @p copy Bag: bag;\n    return 0;\n};\n','E220','restricted builder cannot be copied, released or escape'),
 ('resource struct rejects a non-move owner argument','struct Bag {\n    counts:map<text,i64>;\n    name:string;\n};\nfunc main: i64 {\n    @s c map<text,i64>: map.new<text,i64>(4);\n    @s bag Bag: Bag(c,\"a\");\n    return 0;\n};\n','E222','own arguments require explicit same-block move in a direct call'),
 ('resource struct needs a scoped binding','struct Bag {\n    counts:map<text,i64>;\n    name:string;\n};\nfunc main: i64 {\n    @p x: Bag(map.new<text,i64>(4),\"a\");\n    return 0;\n};\n','E223','a struct holding owned resources must initialize a scoped binding'),
 ('resource struct cannot be an enum payload','struct Bag {\n    counts:map<text,i64>;\n    name:string;\n};\nenum E P(b:Bag); end;\nfunc main: i64 { return 0; };\n','E210','enum payload requires a scalar or enum value'),
 ('builtins use category.function','func main: i64 {\n    @s b spool: spool_new(8);\n    return 0;\n};\n','E102','call builtins as category.function, use spool.new(...)'),
 ('missing package is an error, never a local fallback','use nothere;\nfunc main: i64 {\n    return 0;\n};\n','E300',"package 'nothere' is not installed"),
]
def main():
    p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();binary=a.compiler.resolve();records=[]
    with tempfile.TemporaryDirectory(prefix='Awl-next-diagnostics-') as td:
        for index,(label,source,code,message) in enumerate(CASES):
            folder=Path(td)/str(index);folder.mkdir()
            (folder/'main.aw').write_text(source)
            r=subprocess.run([str(binary),'check','main.aw'],cwd=folder,capture_output=True,text=True,timeout=60)
            assert r.returncode==1,(label,r.returncode,r.stdout,r.stderr)
            assert 'error['+code+']' in r.stderr,(label,r.stderr)
            assert message in r.stderr,(label,message,r.stderr)
            records.append({'case':label,'code':code,'message':message,'stderr':r.stderr.strip()})
    a.report.write_text(json.dumps({'status':'passed','scope':__doc__,'compiler_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'cases':records},indent=2)+'\n')
    print('PASS',len(records),'diagnostics matched exactly')
if __name__=='__main__':main()

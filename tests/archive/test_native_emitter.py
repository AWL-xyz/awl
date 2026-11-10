import ctypes as C
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from test_kcc import kcc, ROOT
import generators
from test_native_checker import BINARY

@unittest.skipUnless(BINARY.is_file(),'build native standalone frontend first')
class NativeEmitter(unittest.TestCase):
    def compare(self,source):
        expected=kcc.Emitter(kcc.compile_text(source,'python','python')).emit()
        actual=kcc.emit_native_c(source);self.assertEqual(actual,expected);return actual
    def test_example_byte_parity(self):
        for p in (ROOT/'examples').glob('*.aw'):self.compare(p.read_text())
    def test_generated_runtime_templates_current(self):
        p=subprocess.run([sys.executable,str(ROOT/'compiler/generate_runtime.py'),'--check'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_cli_emits_without_development_tool_path(self):
        p=ROOT/'examples/results.aw'
        result=subprocess.run([str(BINARY),'emit-c',str(p)],env={'PATH':'/no-development-tools','LC_ALL':'C'},capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,self.compare(p.read_text()))
    def test_empty_helpers_and_forward_layout(self):
        for source in ['function main()->i64 return 0 end','struct Outer p:Inner end struct Inner x:u8 end function main()->i64 local o:Outer=Outer(Inner(1u8)) print(o.p.x) return 0 end','function f()->unit return print(true) end function main()->i64 f() return 0 end']:
            self.compare(source)
    def test_backend_rejects_untyped_arena_without_repair(self):
        lib,_=kcc.native_parser_api();lib.Awl_parse_source.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(C.c_void_p)];lib.Awl_parse_source.restype=C.c_int
        lib.Awl_emit_c.argtypes=[C.c_void_p,C.POINTER(C.c_void_p),C.POINTER(C.c_size_t)];lib.Awl_emit_c.restype=C.c_int
        unit=C.c_void_p();source=b'function main()->i64 return 0 end'
        self.assertEqual(lib.Awl_parse_source(source,len(source),C.byref(unit)),0)
        def arena():
            size=C.c_size_t();data=lib.Awl_parse_json(unit,C.byref(size));return json.loads(C.string_at(data,size.value))
        try:
            before=arena();output=C.c_void_p();size=C.c_size_t()
            self.assertEqual(lib.Awl_emit_c(unit,C.byref(output),C.byref(size)),1)
            self.assertFalse(output);self.assertEqual(size.value,0)
            after=arena();self.assertEqual(before['nodes'],after['nodes']);self.assertEqual(after['diagnostics'][0]['code'],'E500')
            self.assertEqual(lib.Awl_emit_c(None,C.byref(output),C.byref(size)),2)
        finally:lib.Awl_parse_free(unit)
    def test_integer_family_and_conversion_parity(self):
        calls=[]
        for ty in kcc.INTEGERS:
            lo,hi=kcc.bounds(ty);calls.extend([f'print({lo}{ty})',f'print({hi}{ty})'])
            for op in ['+','-','*','/','%']:calls.append(f'print(4{ty}{op}2{ty})')
            for dst in kcc.INTEGERS:calls.append(f'print({dst}(1{ty}))')
        self.compare('function main()->i64 '+' '.join(calls)+' return 0 end')
    @unittest.skipUnless(shutil.which(os.environ.get('CC','cc')),'contributor C toolchain required for runtime differential tests')
    def test_generated_expression_runtime_oracle(self):
        rng=random.Random(711);calls=[];expected=[]
        for _ in range(100):
            for generate in [generators.integer,generators.boolean]:
                expr,value=generate(rng,3);calls.append('print('+expr+')');expected.append(str(value).lower())
        source='function main()->i64 '+' '.join(calls)+' return 0 end'
        self.run_c(self.compare(source),'\n'.join(expected)+'\n')
    @unittest.skipUnless(shutil.which(os.environ.get('CC','cc')),'contributor C toolchain required for runtime differential tests')
    def test_evaluation_order_and_short_circuit(self):
        source='''struct P a:i64 b:i64 end union U V(p:P) end
function stamp(x:i64)->i64 print(x) return x end
function pair(a:i64,b:i64)->i64 return a*10+b end
function flag()->bool print(99) return true end
function main()->i64
print(pair(stamp(1),stamp(2)))
print(false and flag()) print(true or flag())
local p:P=P(stamp(3),stamp(4)) p.a=stamp(5)
match U.V(p) then case U.V(q) then print(q.a+q.b) end
return 0 end'''
        self.run_c(self.compare(source),'1\n2\n12\nfalse\ntrue\n3\n4\n5\n9\n')
    def run_c(self,code,expected):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'program.c';path.write_text(code)
            exe=Path(td)/('program.exe' if os.name=='nt' else 'program')
            for opt in ['0','3']:
                subprocess.run([os.environ.get('CC','cc'),'-std=c11','-O'+opt,str(path),'-o',str(exe)],check=True,capture_output=True,timeout=60)
                result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
                self.assertEqual((result.returncode,result.stdout),(0,expected),result.stderr)
if __name__=='__main__':unittest.main()

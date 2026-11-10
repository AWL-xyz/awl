import dataclasses as D
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from test_kcc import kcc, ROOT

BINARY=ROOT/'compiler/native/bin'/('kcc.exe' if os.name=='nt' else 'kcc')
@unittest.skipUnless(BINARY.is_file(),'build native standalone frontend first')
class NativeChecker(unittest.TestCase):
    def outcome(self,text,native):
        try:
            if native:
                arena=kcc.check_native_source(text)
                fs=kcc.hydrate_native_arena(arena,kcc.lex_python(text),True)
                kcc.verify_ir(fs)
            else: fs=kcc.compile_text(text,'python','python')
            return ('ok',fs)
        except kcc.Error as e: return ('error',[D.asdict(d) for d in e.diagnostics])
    def compare(self,text): self.assertEqual(self.outcome(text,False),self.outcome(text,True))
    def test_examples_typed_tree_parity(self):
        for p in (ROOT/'examples').glob('*.aw'): self.compare(p.read_text())
    def test_semantic_negative_cases(self):
        for body in ['return true','local x:u8=1 return 0','return x','local x:i64=0 local x:i64=1 return 0','if 1 then return 0 end','print(1i8+1i16) return 0','print(i8(true)) return 0','return 0 print(1)','print(-1u8) return 0']:
            self.compare('function main()->i64 '+body+' end')
    def test_layout_failures(self):
        for decl in ['struct P x:P end','union U V(x:P) end struct P x:U end','struct P end','union U end','struct P x:unit end','struct P x:i64 x:bool end','union U A() A() end','struct P x:i64 end function P()->i64 return 0 end']:
            self.compare(decl+' function main()->i64 return 0 end')
    def test_entry_point(self):
        for source in ['', 'function other()->i64 return 0 end','function main(x:i64)->i64 return x end','function main()->u8 return 0u8 end']: self.compare(source)
    def test_unicode_lexical_policy(self):
        for cp in [0,1,39,92,127,133,160,233,178,0x301,0x2028,0x1f600,0x10ffff]:
            self.compare('function main()->i64 print(1'+chr(cp)+') return 0 end')
    def test_resource_limits(self):
        for text in ['x'*1048577,'1 '*100001,'function main()->i64 local '+('x'*129)+':i64=0 return 0 end','function main()->i64 return '+('1'*257)+' end']:
            self.compare(text)
    def test_literal_extremes(self):
        for ty in kcc.INTEGERS:
            low,high=kcc.bounds(ty)
            for v in [low-1,low,high,high+1]: self.compare(f'function main()->i64 print({v}{ty}) return 0 end')
    def test_malformed_source_mutations(self):
        rng=random.Random(708); seeds=[p.read_text() for p in (ROOT/'examples').glob('*.aw')]
        for i in range(1000):
            text=rng.choice(seeds); lo=rng.randrange(len(text)); hi=min(len(text),lo+rng.randrange(1,16))
            text=text[:lo]+rng.choice(['','true','Missing','u8','end',')','case'])+text[hi:]
            with self.subTest(case=i): self.compare(text)
    def test_cli_check_without_path_tools(self):
        for p in (ROOT/'examples').glob('*.aw'):
            result=subprocess.run([str(BINARY),'check',str(p)],env={'PATH':'/no-development-tools','LC_ALL':'C'},capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
    def test_cli_json_diagnostics(self):
        source='function main()->i64 return true end'
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.aw';p.write_text(source)
            result=subprocess.run([str(BINARY),'check',str(p),'--diagnostic-format','json'],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,1)
            reference=self.outcome(source,False)[1]
            self.assertEqual(json.loads(result.stderr)['diagnostics'],reference)
    def test_build_without_bundle_has_no_host_fallback(self):
        result=subprocess.run([str(BINARY),'build',str(ROOT/'examples/hello.aw')],capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertTrue('bundled toolchain missing' in result.stderr or 'not implemented for this host' in result.stderr,result.stderr)
    def test_raw_invalid_utf8_cli(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.aw';p.write_bytes(bytes.fromhex('40ff'))
            result=subprocess.run([str(BINARY),'check',str(p),'--diagnostic-format','json'],capture_output=True,text=True)
            self.assertEqual(json.loads(result.stderr)['diagnostics'][0]['code'],'E008')
if __name__=='__main__': unittest.main()

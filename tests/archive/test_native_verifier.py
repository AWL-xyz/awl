import ctypes as C
import json
import unittest
from test_kcc import kcc, ROOT

@unittest.skipUnless(kcc.native_library_path().is_file(),'build native frontend first')
class NativeVerifier(unittest.TestCase):
    def setUp(self):
        self.lib,_=kcc.native_parser_api()
        self.lib.Awl_parse_source.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(C.c_void_p)]; self.lib.Awl_parse_source.restype=C.c_int
        for name in ['Awl_check_unit','Awl_verify_unit']:
            getattr(self.lib,name).argtypes=[C.c_void_p];getattr(self.lib,name).restype=C.c_int
    def unit(self,text):
        data=text.encode();p=C.c_void_p()
        self.assertEqual(self.lib.Awl_parse_source(data,len(data),C.byref(p)),0)
        self.assertTrue(p);self.addCleanup(self.lib.Awl_parse_free,p);return p
    def arena(self,p):
        size=C.c_size_t();raw=self.lib.Awl_parse_json(p,C.byref(size))
        self.assertTrue(raw);return json.loads(C.string_at(raw,size.value))
    def test_verified_arena_is_unchanged_on_success(self):
        for path in (ROOT/'examples').glob('*.aw'):
            p=self.unit(path.read_text());self.assertEqual(self.lib.Awl_check_unit(p),0)
            before=self.arena(p)
            self.assertEqual(self.lib.Awl_verify_unit(p),0)
            self.assertEqual(self.lib.Awl_verify_unit(p),0)
            self.assertEqual(self.arena(p),before)
    def test_untyped_arena_rejected_not_repaired(self):
        p=self.unit('function main()->i64 return 0 end');before=self.arena(p)
        self.assertEqual(self.lib.Awl_verify_unit(p),1)
        after=self.arena(p)
        self.assertEqual(before['nodes'],after['nodes'])
        self.assertEqual(before['roots'],after['roots'])
        self.assertEqual(after['diagnostics'][0]['code'],'E500')
        self.assertIn('annotation',after['diagnostics'][0]['message'])
    def test_existing_source_diagnostics_preserved(self):
        p=self.unit('function main()->i64 return @ end');before=self.arena(p)
        self.assertTrue(before['diagnostics'])
        self.assertEqual(self.lib.Awl_verify_unit(p),1)
        self.assertEqual(self.arena(p),before)
    def test_invalid_handle(self): self.assertEqual(self.lib.Awl_verify_unit(None),2)
    def test_verified_aggregate_control_flow(self):
        source='''union U A(x:u64) B() end
function choose(v:U)->u64
match v then case U.A(n) then return n case U.B() then return 0u64 end
end
function main()->i64 print(choose(U.A(18446744073709551615u64))) return 0 end'''
        fs=kcc.hydrate_native_arena(kcc.check_native_source(source),kcc.lex_python(source),True)
        kcc.verify_ir(fs)
        self.assertEqual(fs,kcc.compile_text(source,'python','python'))
if __name__=='__main__':unittest.main()

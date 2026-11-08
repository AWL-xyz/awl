#!/usr/bin/env python3
"""Developer regression runner: route default compile_text through C++ frontend.
Explicit parser/lexer selections remain reference/bridge tests. C emission,
IR verification, runtime tests and subprocess Python CLI tests remain bootstrap.
The installed native executable never uses this adapter.
"""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_kcc import kcc
reference=kcc.compile_text

def compile_native(text,lexer=None,parser=None):
    if lexer is not None or parser is not None: return reference(text,lexer,parser)
    arena=kcc.check_native_source(text)
    fs=kcc.hydrate_native_arena(arena,kcc.lex_python(text),True)
    kcc.verify_ir(fs)
    return fs

if __name__=='__main__':
    kcc.compile_text=compile_native
    suite=unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())

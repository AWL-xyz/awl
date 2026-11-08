#!/usr/bin/env python3
"""Contributor-only generator for pinned native Unicode classification tables.
Run with a Python interpreter whose unicodedata version is exactly 15.1.0.
The installed frontend uses only the generated C++ data, never this script.
"""
from pathlib import Path
import unicodedata

if __name__=='__main__':
    if unicodedata.unidata_version!='15.1.0':
        raise SystemExit('Requires Unicode 15.1.0; refusing an implicit language-policy change')
    out=['// Generated with Python Unicode 15.1.0. Data only; no Python runtime dependency.',
         '// See third-party/UNICODE-LICENSE.txt and compiler/generate_unicode.py.',
         'struct UnicodeRange { uint32_t first,last; };']
    for name,test in [('alnum',str.isalnum),('printable',str.isprintable)]:
        ranges=[]; first=last=None
        for cp in range(128,0x110000):
            if test(chr(cp)):
                if first is None: first=cp
                last=cp
            elif first is not None: ranges.append((first,last)); first=None
        if first is not None: ranges.append((first,last))
        out+=['constexpr UnicodeRange unicode_'+name+'[]={']
        out+=['{'+str(a)+','+str(b)+'},' for a,b in ranges]
        out+=['};']
    (Path(__file__).resolve().parent/'native/unicode_tables.inc').write_text('\n'.join(out)+'\n')

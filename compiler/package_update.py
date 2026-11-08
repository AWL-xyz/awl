#!/usr/bin/env python3
"""Contributor: package compact native0.8-dev overlay for complete Awl0.7.1.
This is NOT a standalone compiler distribution. The original full prefix supplies
its unchanged pinned native toolchain/resources; no Python is used after install.
"""
import hashlib
import json
from pathlib import Path
import tarfile
ROOT=Path(__file__).resolve().parents[1]
BASE_SHA='73777a7de251f2dc75b1f89db07c7c0f515d422a1762c63c1d41a5e149d72ef4'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    prefix=ROOT/'build/Awl-linux-x86_64'
    m=json.loads((prefix/'manifest.json').read_text())
    assert m['version']=='0.24.0-dev'
    assert digest(prefix/'bin/kcc')==m['kcc_sha256']
    assert digest(prefix/'libexec/zig/zig')==m['zig_sha256']
    for name,sha in m['compiler_sources_sha256'].items():assert digest(prefix/'src'/name)==sha
    info={'version':'0.24.0-dev','kind':'development overlay, NOT standalone','requires':'Complete Awl0.7.1-preview Linux x86-64 installation; keep its libexec/zig unchanged',
          'base_archive':'Awl-0.7.1-preview-linux-x86_64.tar.xz','base_archive_sha256':BASE_SHA,
          'apply':'From inside unpacked Awl prefix: tar -xJf /path/to/Awl-0.24.0-dev-native-update.tar.xz',
          'runtime':'No Python/host SDK/Xlib/SDL needed; windows require supported local X11 display',
          'warning':'Experimental process-lifetime strings and manual checked handles, not a full language/production application platform',
          'kcc_sha256':m['kcc_sha256'],'required_zig_sha256':m['zig_sha256']}
    (prefix/'UPDATE.json').write_text(json.dumps(info,indent=2)+'\n')
    output=ROOT.parent/'Awl-0.24.0-dev-native-update.tar.xz'
    def normalized(item):
        item.uid=item.gid=0;item.uname=item.gname='';item.mtime=0;return item
    with tarfile.open(output,'w:xz',preset=6) as archive:
        for name in ['bin/kcc','src','examples','LICENSE','README.md','manifest.json','UPDATE.json','NATIVE-WINDOWS.md','MODULES.md','STRINGS.md','SPOOLS.md','ROADMAP.md','SCOPED-CLEANUP.md','ARRAYS.md','REPEATED-ARRAYS.md','PROCESS-LIMITS.md','validation']:
            archive.add(prefix/name,arcname=name,filter=normalized)
    sha=digest(output);output.with_name(output.name+'.sha256').write_text(sha+'  '+output.name+'\n')
    print(output,output.stat().st_size,sha)
if __name__=='__main__':main()

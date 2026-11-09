#!/usr/bin/env python3
"""Contributor-only successor bundle builder. Not run by installed kcc.

Rebuilds a complete Linux bundle from a previously published, resource-verified
archive plus the current source tree and a freshly built host compiler. The
bundled upstream toolchain tree is copied byte-for-byte and re-verified against
the previous archive before the new archive is written, so no overlay and no
partial resource tree can be published.
"""
import argparse,hashlib,json,os,shutil,tarfile
from pathlib import Path
from distribution_privacy import scrub_private
ROOT=Path(__file__).resolve().parents[1]
ALIASES=['acc','awl','awL','aWl','aWL','Awl','AwL','AWl','AWL']
COPY=['docs','examples','third-party','assets','apps','web','editor','packages']
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while data:=f.read(1048576):h.update(data)
    return h.hexdigest()
def tree_digest(folder):
    h=hashlib.sha256()
    for p in sorted(folder.rglob('*')):
        rel=str(p.relative_to(folder))
        if p.is_symlink():h.update(f'L {rel} {os.readlink(p)}\n'.encode())
        elif p.is_file():h.update(f'F {rel} {sha(p)}\n'.encode())
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True,help='previously published complete archive; its libexec tree is inherited unchanged')
    p.add_argument('--compiler',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    stage=a.stage.resolve()
    if stage.exists():shutil.rmtree(stage)
    with tarfile.open(a.base) as t:t.extractall(stage,filter='data')
    if stage.name!='Awl':shutil.move(str(stage),str(stage.parent/'Awl')) if False else None
    prefix=stage/'Awl';assert prefix.is_dir(),'base archive must contain Awl/'
    resources=tree_digest(prefix/'libexec/zig')
    # Rebuild the whole source/doc/app surface from the working tree.
    for name in COPY:
        target=prefix/name
        if target.exists():shutil.rmtree(target)
        shutil.copytree(ROOT/name,target,ignore=shutil.ignore_patterns("[Rr][Oo][Aa][Dd][Mm][Aa][Pp].md", "agents.md", "memory.md", "to-do.md", "history"))
    src=prefix/'src'
    if src.exists():shutil.rmtree(src)
    src.mkdir()
    for f in sorted((ROOT/'compiler/native').iterdir()):
        if f.suffix in ['.cpp','.h','.inc','.c']:shutil.copy2(f,src/f.name)
    comp=prefix/'compiler'
    if comp.exists():shutil.rmtree(comp)
    shutil.copytree(ROOT/'compiler',comp,ignore=shutil.ignore_patterns('bin','__pycache__','.cache'))
    for name in ['LICENSE','CHANGELOG.md']:
        if (ROOT/name).is_file():shutil.copy2(ROOT/name,prefix/name)
    readme=('''# Awl Software Development Kit [Beta]

0.26.0-dev

Linux x86-64 experimental standalone SDK, exact published archive qualification is recorded separately

extract the entire Awl directory and add its bin directory to PATH, keep libexec adjacent to bin

```sh
awl
awl init Demo
awl build
awl build examples/collections/main.aw -o collections
```

no end-user Python, host compiler, SDK or additional backend download is needed

Aesop is the only syntax, function results may be inferred, `func size :: @b values[i64] { ... };` and `func main[i64] { ... };` are both supported

public beta commands remain init/build only, acc is the compiler driver and kcc is a compatibility filename, run/install/Packages/registry are not public beta commands

editor/awl-editor.html is the single-file Aesop subset editor, not the native compiler, web/Awl-json-workbench.html runs freshly compiled WebAssembly with a bounded browser host

bundled upstream resources are inherited byte-for-byte from the0.25 archive and re-verified by compiler/package_successor.py, see manifest.json and RELEASE-0.26.md

see docs for syntax, runtime limits and workload assessment, native Windows acceptance is deferred, no full 3D, general widgets, concurrency, TLS/auth or arbitrary owned generics are claimed
''')
    (prefix/'README.md').write_text(readme)
    if (ROOT/'RELEASE-0.26.md').is_file():shutil.copy2(ROOT/'RELEASE-0.26.md',prefix/'RELEASE-0.26.md')
    binary=prefix/'bin/kcc'
    shutil.copy2(a.compiler,binary);binary.chmod(0o755)
    for name in ALIASES:
        link=prefix/'bin'/name
        if link.exists() or link.is_symlink():link.unlink()
        link.symlink_to('kcc')
    version=json.loads((ROOT/'BUNDLE-README.md').read_text().splitlines()[2].split(' ')[0]) if False else None
    (prefix/'validation'/'README.md').write_text('historical rename-* and default-* reports in this directory bind the previous0.25 compiler, not the current binary, the0.26 editor evidence is validation/awl-editor.json, exact successor acceptance is recorded in the workspace tests/ directory\n')
    if (ROOT/'tests/awl-editor.json').is_file():shutil.copy2(ROOT/'tests/awl-editor.json',prefix/'validation/awl-editor.json')
    manifest=json.loads((prefix/'manifest.json').read_text())
    scrub_private(prefix)
    manifest.pop('legacy_requires_explicit_syntax',None)
    old_examples=prefix/'examples-next'
    if old_examples.is_dir():shutil.rmtree(old_examples)
    manifest.update(version='0.26.0-dev',kcc_sha256=sha(binary),default_syntax='aesop',supported_syntaxes=['aesop'],
        windows_native_host_accepted=False,editor={'aesop':'editor/awl-editor.html'},
        resources_inherited_from={'archive':a.base.name,'sha256':sha(a.base),'libexec_tree_sha256':resources,'files_verified':manifest.get('upstream_files_verified',0)},
        compiler_sources_sha256={f.name:sha(f) for f in sorted(src.iterdir()) if f.is_file()},
        status='experimental Linux SDK, current Aesop syntax, separately qualify the exact distribution archive')
    (prefix/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    # files.json cannot list its own digest, it is verified by archive member count instead
    inventory={str(f.relative_to(prefix)):({'symlink':os.readlink(f)} if f.is_symlink() else {'sha256':sha(f),'bytes':f.stat().st_size}) for f in sorted(prefix.rglob('*')) if (f.is_file() or f.is_symlink()) and f.name!='files.json'}
    (prefix/'files.json').write_text(json.dumps(inventory,separators=(',',':'))+'\n')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def normalized(info):
        info.uid=info.gid=0;info.uname=info.gname='';info.mtime=1794009600;return info
    with tarfile.open(a.output,'w:xz',preset=6) as t:t.add(prefix,arcname='Awl',filter=normalized)
    with tarfile.open(a.output) as t:
        members=t.getmembers()
        assert all(m.name=='Awl' or m.name.startswith('Awl/') for m in members)
        assert t.getmember('Awl/files.json')
        for name,entry in inventory.items():
            member=t.getmember('Awl/'+name)
            if 'symlink' in entry:assert member.issym() and member.linkname==entry['symlink'],name
            else:
                h=hashlib.sha256()
                with t.extractfile(member) as f:
                    while data:=f.read(1048576):h.update(data)
                assert member.size==entry['bytes'] and h.hexdigest()==entry['sha256'],name
        extracted=stage.parent/'verify026'
        if extracted.exists():shutil.rmtree(extracted)
        t.extractall(extracted,filter='data')
    assert tree_digest(extracted/'Awl/libexec/zig')==resources,'inherited resource tree changed'
    shutil.rmtree(extracted)
    result={'status':'PASS','version':'0.26.0-dev','compiler_sha256':sha(binary),'manifest_sha256':sha(prefix/'manifest.json'),'inventory_sha256':sha(prefix/'files.json'),
        'base_archive':{'name':a.base.name,'sha256':sha(a.base)},'libexec_tree_sha256':resources,'inventory_entries':len(inventory),
        'archive_sha256':sha(a.output),'archive_bytes':a.output.stat().st_size,'archive_members':len(members),'harness_sha256':sha(Path(__file__))}
    a.output.with_suffix(a.output.suffix+'.sha256').write_text(result['archive_sha256']+'  '+a.output.name+'\n')
    a.report.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()

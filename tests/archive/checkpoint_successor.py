#!/usr/bin/env python3
"""Verifies the published 0.26 Linux SDK, the retired 0.25 archive, current
editor evidence and the whole-workspace budget."""
import hashlib,json,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    publication=json.loads((ROOT/'tests/default-publication.json').read_text())
    successor=json.loads((ROOT/'tests/successor-0.26.json').read_text())
    editor=json.loads((ROOT/'tests/awl-editor.json').read_text())
    archive=ROOT.parent/publication['new_archive']
    assert sha(archive)==publication['sha256']==successor['archive']['sha256']
    assert archive.with_name(archive.name+'.sha256').read_text().split()[0]==publication['sha256']
    assert publication['replacement_exact_archive_accepted_before_retirement']
    assert not (ROOT.parent/publication['retired_archive']).exists()
    assert not (ROOT.parent/(publication['retired_archive']+'.sha256')).exists()
    with tarfile.open(archive) as tar:
        members={m.name:m for m in tar.getmembers()}
        def text(name):
            with tar.extractfile(members['Awl/'+name]) as f:return f.read()
        manifest=json.loads(text('manifest.json'))
        inventory=json.loads(text('files.json'))
        assert manifest['version']=='0.26.0-dev' and manifest['default_syntax']=='next'
        assert manifest['resources_inherited_from']['libexec_tree_sha256']==successor['successor_builder']['libexec_tree_sha256']==publication['resources_provenance']['libexec_tree_sha256']
        assert manifest['resources_inherited_from']['files_verified']==publication['resources_provenance']['upstream_files_verified']==18105
        assert hashlib.sha256(text('bin/kcc')).hexdigest()==manifest['kcc_sha256']
        for name,digest in manifest['compiler_sources_sha256'].items():
            assert hashlib.sha256(text('src/'+name)).hexdigest()==digest,name
        for name in ['editor/awl-editor.html','editor/Awl-studio.html','RELEASE-0.26.md','docs/AESOP.md','docs/RELEASE-0.26.md','validation/awl-editor.json']:
            assert 'Awl/'+name in members,name
        assert inventory['editor/awl-editor.html']['sha256']==editor['html_sha256']
        assert hashlib.sha256(text('editor/awl-editor.html')).hexdigest()==editor['html_sha256']
        assert manifest['editor']['next']=='editor/awl-editor.html'
        assert b'func main[i64] {' in text('README.md')
        starter=text('src/ASDK.inc')
        assert b'func main[i64] {\\n    print(\\"Hello from Awl!\\");\\n    return 0;\\n};\\n' in starter
        assert b'next_syntax?"}":"end"' in text('src/parse.cpp')
    info=json.loads((ROOT/'compiler/native/bin/build-info.json').read_text())
    assert sha(ROOT/'compiler/native/bin/kcc')==info['standalone']['sha256'],'workspace compiler diverged from build-info'
    assert sha(ROOT.parent/'Awl-0.24.0-dev-windows-x86_64-preview.tar.xz')=='50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec'
    assert sha(ROOT.parent/'Awl-board-0.1-linux-x86_64.tar.xz')==json.loads((ROOT/'tests/board-package.json').read_text())['archive_sha256']
    files=[p for p in ROOT.parent.rglob('*') if p.is_file() and not p.is_symlink()]
    size=sum(p.stat().st_size for p in files)
    assert size<128000000 and len(files)<10000,(size,len(files))
    result={'status':'PASS','archive':publication,'published_compiler_sha256':manifest['kcc_sha256'],'editor_sha256':editor['html_sha256'],
        'workspace_compiler_sha256':info['standalone']['sha256'],'library_sha256':info['library_sha256'],'retired_archive':publication['retired_archive'],
        'home':{'bytes':size,'regular_files':len(files)},
        'bound_sha256':{'tests/default-publication.json':sha(ROOT/'tests/default-publication.json'),'tests/successor-0.26.json':sha(ROOT/'tests/successor-0.26.json'),
            'tests/awl-editor.json':sha(ROOT/'tests/awl-editor.json'),'editor/awl-editor.html':sha(ROOT/'editor/awl-editor.html'),'RELEASE-0.26.md':sha(ROOT/'RELEASE-0.26.md'),
            'docs/AESOP.md':sha(ROOT/'docs/AESOP.md'),'tests/default_next.py':sha(ROOT/'tests/default_next.py'),'tests/awl_editor.py':sha(ROOT/'tests/awl_editor.py')},
        'capability':'26.7%=12/45 unchanged',
        'qualification':'complete0.26 Linux SDK published, inherited upstream resources re-verified,0.25 retired only after the exact successor passed, Windows preview and board download unchanged and unaccepted, workspace compiler remains the historical published0.25 binary'}
    (ROOT/'tests/successor-checkpoint.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('PASS successor checkpoint',size,len(files))
if __name__=='__main__':main()

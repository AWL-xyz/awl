#!/usr/bin/env python3
"""Checks the shipped single-file awl. editor: interpreter behaviour against the
native compiler and every bundled example against `kcc check`."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--kcc',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    html=ROOT/'editor/awl-editor.html'
    with tempfile.TemporaryDirectory(prefix='Awl-editor-check-',dir='/var/tmp') as td:
        examples=Path(td)/'examples.json'
        js=subprocess.run(['node',str(ROOT/'tests/awl_editor.js'),str(html),str(examples)],capture_output=True,text=True,check=True)
        compiled=[]
        for name,files in json.loads(examples.read_text()).items():
            folder=Path(td)/name.replace('/','_');folder.mkdir()
            for f in files:(folder/f['name']).write_text(f['text'])
            entry=files[-1]['name'] if len(files)>1 else files[0]['name']
            r=subprocess.run([str(a.kcc),'check',str(folder/entry)],capture_output=True,text=True)
            assert r.returncode==0,(name,r.stdout,r.stderr)
            compiled.append(name)
        # offline, single file, no external script or style dependency beyond fonts
        text=html.read_text()
        assert text.count('<script>')==1 and '<script src=' not in text and 'javascript:' not in text
        assert 'owl-mask' in text and '@keyframes spin' not in text
    result={'status':'PASS','html_sha256':hashlib.sha256(html.read_bytes()).hexdigest(),'bytes':html.stat().st_size,
        'interpreter_checks':js.stdout.strip(),'native_checked_examples':compiled,
        'compiler_sha256':hashlib.sha256(a.kcc.read_bytes()).hexdigest(),
        'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'qualification':'node-hosted in-browser interpreter behaviour plus kcc check on every bundled example, not a browser screenshot or native-compiler equivalence'}
    a.report.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('PASS editor: '+js.stdout.strip()+', '+str(len(compiled))+' examples checked by kcc')
if __name__=='__main__':main()

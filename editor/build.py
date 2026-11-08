"""Contributor helper. The delivered HTML has no runtime dependency on this script."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
files={str(p.relative_to(root)):p.read_text() for folder in ['examples','examples-next'] for p in sorted((root/folder).rglob('*.aw'))}
shell=(root/'editor/shell.html').read_text()
html=shell.replace('__SOURCES__',json.dumps(files,ensure_ascii=True).replace('<','\\u003c')).replace('__RUNTIME__',json.dumps((root/'editor/runtime.js').read_text()).replace('<','\\u003c'))
(root/'editor/Awl-studio.html').write_text(html)
print(f'Bundled {len(files)} examples; {len(html.encode())} bytes; no external resources')

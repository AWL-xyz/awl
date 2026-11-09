"""Exclude local planning material without modifying bundled upstream toolchains"""
from pathlib import Path
import shutil
PRIVATE_FILES = {'roadmap.md', 'agents.md', 'memory.md', 'to-do.md'}
PROJECT_DIRS = ('docs', 'compiler', 'src', 'examples', 'examples-next', 'apps', 'web', 'editor')
def scrub_private(prefix):
    prefix = Path(prefix)
    for p in list(prefix.iterdir()):
        if p.name.lower() in PRIVATE_FILES:
            p.unlink()
    history = prefix / 'history'
    if history.is_symlink():
        history.unlink()
    elif history.exists():
        shutil.rmtree(history)
    for name in PROJECT_DIRS:
        folder = prefix / name
        if folder.is_symlink() or not folder.is_dir():
            continue
        for p in folder.rglob('*'):
            if p.name.lower() in PRIVATE_FILES and (p.is_file() or p.is_symlink()):
                p.unlink()

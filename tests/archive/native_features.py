"""Contributor test version gates: minimum versions, not brittle release allowlists.
These gates select tests, not assert feature support; the selected tests prove it.
"""
import re,subprocess
from pathlib import Path
def supports_version(binary,minimum):
    if not Path(binary).is_file():return False
    try:text=subprocess.check_output([str(binary),'--version'],text=True,timeout=10).strip()
    except (OSError,subprocess.SubprocessError):return False
    match=re.fullmatch(r'KCC (\d+)\.(\d+)\.(\d+)(?:[-\s].*)?',text)
    return bool(match and tuple(map(int,match.groups()))>=tuple(minimum))

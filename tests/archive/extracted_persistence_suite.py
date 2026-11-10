"""Final native feature gates against the exact archive-extracted compiler."""
import os,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KCC=ROOT/'build/archive-isolation-root/relocated Awl/bin/kcc'
for p in (ROOT/'tests').glob('test_*.py'):
 for name in re.findall(r'Awl_[A-Z_]+_TEST_BINARY',p.read_text()):os.environ[name]=str(KCC)
import test_bundle
test_bundle.KCC=KCC
names=['test_'+m for m in ['modules','strings','builders','cleanup','arrays','repeat','scoped_owner','borrows','moves','own_params','owned_results','branch_joins','match_joins','reinit','loop_owners','vectors','files','persistence','platform','bundle','driver_limits']]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names));sys.exit(int(not r.wasSuccessful() or bool(r.skipped)))

"""Publish only the exact validated0.23 artifacts; protect0.22 until then."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):return json.loads((ROOT/'tests'/name).read_text())
def main():
 for name in ['persistence-development-validation.json','persistence-extra-validation.json']:
  assert all(x['exit']==0 for x in load(name).values()),name
 for name,n in [('reference-suite',564),('native-parser-suite',564),('native-frontend-suite',564),('linux-extracted-suite',312)]:
  text=(ROOT/'tests'/('persistence-'+name+'.txt')).read_text();assert f'Ran {n} tests' in text and text.rstrip().endswith('OK') and 'skipped=' not in text,name
 assert all(x['exit']==0 for x in load('persistence-windows-exact-validation.json').values() if isinstance(x,dict) and 'acceptance' not in x)
 for name in ['persistence-faults.json','persistence-cli.json','persistence-windows-native-frontend.json','persistence-windows-exact-gui.json','persistence-windows-exact-files.json']:
  assert load(name)['status']=='passed',name
 assert len(load('persistence-windows-native-frontend.json')['phases'])==4
 text=(ROOT/'tests/persistence-native-sanitized.txt').read_text();assert '357 targeted corruptions, 10000 seeded structural corruptions passed' in text and 'filesystem C ABI passed' in text
 offline=load('persistence-linux-exact-offline.json');linux=load('persistence-linux-exact-integrity.json');windows=load('persistence-windows-exact-integrity.json');gui=load('persistence-windows-exact-gui.json');assert offline['status']==linux['status']=='passed';assert gui['actual_Awl_application_probe_checks']==9
 assert len(offline['commands'])==83 and offline['tested_archive']['sha256']==linux['archive_sha256']
 artifacts={}
 for osname,filename,expected,size in [('linux','Awl-0.23.0-dev-linux-x86_64.tar.xz',linux['archive_sha256'],linux['archive_bytes']),('windows','Awl-0.23.0-dev-windows-x86_64-preview.tar.xz',windows['sha256'],windows['bytes'])]:
  source=ROOT/'build'/filename;assert source.stat().st_size==size and sha(source)==expected
  assert source.with_name(filename+'.sha256').read_text().split()==[expected,filename]
  target=ROOT.parent/filename;assert not target.exists();tmp=target.with_name(filename+'.publishing');assert not tmp.exists();shutil.copyfile(source,tmp);assert sha(tmp)==expected;tmp.replace(target);shutil.copy2(source.with_name(filename+'.sha256'),target.with_name(filename+'.sha256'))
  artifacts[osname]={'path':str(target),'bytes':size,'sha256':expected,'artifact_integrity_passed':True,'native_host_accepted':osname=='linux','qualification':'Linux engineering release, recorded host only' if osname=='linux' else 'Complete merged native-host preview; qualified cross-link/PE/Wine subsets ONLY, not native Windows host acceptance'}
 # Only matching protected prior release assets are eligible for deletion.
 removed=[]
 for filename,expected in [('Awl-0.22.0-dev-linux-x86_64.tar.xz','df2d0acd3c7180bd2b0cb467169cfb40aa3d09bcca445ab07309316bd299ea99'),('Awl-0.22.0-dev-windows-x86_64-preview.tar.xz','1ab0c99d11c0a18094132af275a589282a80f49fb18338a05f3a31c15dc3e400')]:
  target=ROOT.parent/filename;assert sha(target)==expected;assert target.with_name(filename+'.sha256').read_text().split()==[expected,filename];target.unlink();target.with_name(filename+'.sha256').unlink();removed.append(filename)
 report={'version':'0.23.0-dev','artifacts':artifacts,'development':{'suite_methods_per_frontend_configuration':564,'configurations':3,'file_sanitizer_methods':22,'storage_sanitizer_methods':10,'resource_sanitizer_methods':257,'platform_sanitizer_methods':15,'syscall_fault_modes':8,'actual_app_cli_cases':6,'private_native_phases_per_platform':4,'targeted_verifier_corruptions':357,'seeded_structural_corruptions':10000},'exact_linux':{'offline_commands':83,'extracted_methods':312,'integer_matrix_checks':348,'trap_cases':5,'source_hashes':33,'example_files':43,'complete_backend_files_and_modes':18105,'no_host_development_tools_python_shell_network':True},'exact_windows_preview':{'frontend_runtime_commands':22,'fake_backend_driver_fixture_commands':21,'runtime_groups':17,'actual_Awl_app_groups':9,'source_hashes':33,'example_files':43,'complete_backend_files_content':18105,'actual_native_Linux_saved_sample_loaded_and_resaved_identically':True,'native_windows_host_accepted':False,'installed_backend_probe':load('persistence-windows-exact-validation.json')['installed-backend-probe'],'real_windows_CI':'configured, not claimed remotely executed'},'performance_reports':['benchmarks/persistence-latest.json','benchmarks/persistence-build-latest.json'],'real_capture_provenance':['demos/persistence/capture.json','demos/persistence/windows-capture.json'],'coarse_progress':{'points':6,'maximum':45,'percent':13.3,'change':'Desktop1→2: actual bounded drawing persistence across launches, with success/error tests; not points for syntax/test counts. Full3D/backend/browser/ASDK/site/default Packages remain absent.'},'nonclaims':['atomic replacement or crash durability','malicious-file authentication','production desktop toolkit','keyboard layout/text/IME normalization','native Windows-host acceptance','universal or whole-app checksum microbenchmark gains'],'superseded_archives_removed_after_matching_exact_gates':removed,'cleanup_status':'pending final whole-parent audit'}
 (ROOT/'tests/persistence-release-acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

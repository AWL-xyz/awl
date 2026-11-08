import subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from native_features import supports_version
class VersionGates(unittest.TestCase):
    def check(self,text,minimum,expected):
        with tempfile.NamedTemporaryFile() as f,patch('native_features.subprocess.check_output',return_value=text):self.assertEqual(supports_version(f.name,minimum),expected)
    def test_future_minor_releases_do_not_skip_existing_features(self):
        for text in ['KCC 0.11.0-dev borrows preview','KCC 0.12.0-dev','KCC 1.0.0']:
            self.check(text,(0,8,4),True)
    def test_numeric_not_lexical_version_order(self):
        self.check('KCC 0.9.9-dev',(0,10,0),False);self.check('KCC 0.10.0-dev',(0,10,0),True)
    def test_wrong_vendor_malformed_or_missing_binary(self):
        for text in ['Python 3.13.0','KCC preview','KCC 0.11','KCC 0.11.0-notice\nextra'] :self.check(text,(0,8,0),False)
        self.assertFalse(supports_version('/nonexistent/Awl/kcc',(0,8,0)))
    def test_failed_version_command(self):
        with tempfile.NamedTemporaryFile() as f,patch('native_features.subprocess.check_output',side_effect=subprocess.TimeoutExpired('kcc',10)):self.assertFalse(supports_version(f.name,(0,8,0)))

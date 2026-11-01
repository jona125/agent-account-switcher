import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / 'codex-account'
PARSER = PROJECT / 'lib' / 'read_config.py'

class ConfigurationTests(unittest.TestCase):
    def test_default_paths(self):
        result = subprocess.run(['python3', str(PARSER), str(PROJECT / 'config.xml'), 'shared-home'], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), str(Path.home() / '.codex'))

    def test_local_paths_and_launcher(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            config = path / 'local.xml'
            config.write_text(f'<codex-account-config><accounts-dir>{path}/accounts</accounts-dir><shared-home>{path}/shared</shared-home></codex-account-config>')
            env = dict(os.environ, CODEX_ACCOUNT_CONFIG=str(config))
            env.pop('CODEX_ACCOUNTS_DIR', None)
            env.pop('CODEX_SHARED_HOME', None)
            result = subprocess.run([str(SCRIPT), 'list'], env=env, capture_output=True, text=True, check=True)
            self.assertIn('No accounts yet', result.stdout)
            self.assertTrue((path / 'accounts' / 'accounts').is_dir())

    def test_bad_config_and_repository_storage_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / 'local.xml'
            config.write_text('<codex-account-config><accounts-dir>relative</accounts-dir><shared-home>/tmp/shared</shared-home></codex-account-config>')
            env = dict(os.environ, CODEX_ACCOUNT_CONFIG=str(config))
            env.pop('CODEX_ACCOUNTS_DIR', None)
            env.pop('CODEX_SHARED_HOME', None)
            result = subprocess.run([str(SCRIPT), 'list'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            env['CODEX_ACCOUNTS_DIR'] = str(PROJECT / 'credentials')
            result = subprocess.run([str(SCRIPT), 'list'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('outside the project', result.stderr)

if __name__ == '__main__':
    unittest.main()

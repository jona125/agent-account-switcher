import os
from pathlib import Path
import subprocess
import shutil
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

    def test_first_run_creates_and_preserves_local_config(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / 'project'
            project.mkdir()
            shutil.copy2(SCRIPT, project / 'codex-account')
            shutil.copy2(PROJECT / 'config.xml', project / 'config.xml')
            shutil.copytree(PROJECT / 'lib', project / 'lib')
            env = dict(os.environ, CODEX_ACCOUNTS_DIR=str(Path(temp) / 'accounts'),
                       CODEX_SHARED_HOME=str(Path(temp) / 'shared'))
            env.pop('CODEX_ACCOUNT_CONFIG', None)
            subprocess.run([str(project / 'codex-account'), 'help'], env=env, check=True, capture_output=True)
            local = project / 'config.local.xml'
            self.assertEqual(local.read_bytes(), (project / 'config.xml').read_bytes())
            local.write_text('custom local content')
            subprocess.run([str(project / 'codex-account'), 'help'], env=env, check=True, capture_output=True)
            self.assertEqual(local.read_text(), 'custom local content')

    def test_other_agents_dispatch_without_exposing_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            bin_dir = path / 'bin'
            bin_dir.mkdir()
            log = path / 'calls'
            for program in ('claude', 'copilot'):
                stub = bin_dir / program
                stub.write_text('#!/bin/bash\nprintf "%s|%s|%s\\n" "${0##*/}" "${CLAUDE_CONFIG_DIR:-}" "$*" >> "$MOCK_LOG"\n')
                stub.chmod(0o755)
            shared = path / 'claude-shared'
            (shared / 'projects').mkdir(parents=True)
            env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
                       CODEX_ACCOUNTS_DIR=str(path / 'accounts'), CODEX_SHARED_HOME=str(path / 'codex-shared'),
                       CLAUDE_SHARED_HOME=str(shared), MOCK_LOG=str(log))
            subprocess.run([str(SCRIPT), '--agent', 'claude', 'add', 'work'], env=env, check=True)
            subprocess.run([str(SCRIPT), '--agent', 'claude', 'run', '--', '--resume'], env=env, check=True)
            subprocess.run([str(SCRIPT), '--agent', 'copilot', 'run', '--', '--resume'], env=env, check=True)
            self.assertEqual((path / 'accounts/claude/accounts/work/projects').resolve(), (shared / 'projects').resolve())
            calls = log.read_text()
            self.assertIn('claude|' + str(path / 'accounts/claude/accounts/work') + '|auth login', calls)
            self.assertIn('|--resume', calls)
            self.assertIn('copilot||--resume', calls)

    def test_named_profiles_route_to_correct_agent(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            binary = base / 'bin'
            binary.mkdir()
            for name, body in {
                'gh': '#!/bin/bash\nprintf "mock-token"\n',
                'copilot': '#!/bin/bash\ntest "$COPILOT_GITHUB_TOKEN" = mock-token || exit 7\nprintf "copilot:%s\\n" "$*"\n',
                'codex': '#!/bin/bash\nprintf "codex:%s:%s\\n" "$CODEX_HOME" "$*"\n',
            }.items():
                path = binary / name
                path.write_text(body)
                path.chmod(0o755)
            accounts = base / 'store'
            (accounts / 'accounts' / 'old').mkdir(parents=True)
            shared = base / 'shared'
            (shared / 'sessions').mkdir(parents=True)
            env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'],
                       CODEX_ACCOUNTS_DIR=str(accounts), CODEX_SHARED_HOME=str(shared))
            launcher = str(PROJECT / 'agent-account')
            subprocess.run([launcher, 'add', 'github', 'copilot', 'CHANGJO1_alcon'], env=env, check=True, capture_output=True)
            listed = subprocess.run([launcher, 'list'], env=env, check=True, capture_output=True, text=True).stdout
            self.assertIn('old', listed)
            self.assertIn('codex', listed)
            self.assertIn('github', listed)
            self.assertIn('copilot', listed)
            self.assertIn('credential available', listed)
            self.assertNotIn('mock-token', listed)
            result = subprocess.run([launcher, 'run', 'github', '--', '--resume'], env=env, check=True, capture_output=True, text=True)
            self.assertIn('copilot:--resume', result.stdout)
            self.assertNotIn('mock-token', result.stdout)
            self.assertEqual((accounts / 'copilot/accounts/github/github-user').read_text().strip(), 'CHANGJO1_alcon')
            subprocess.run([launcher, 'use', 'old'], env=env, check=True, capture_output=True)
            result = subprocess.run([launcher, 'run', '--', 'resume'], env=env, check=True, capture_output=True, text=True)
            self.assertIn(str(accounts / 'accounts/old'), result.stdout)
            self.assertIn('resume', result.stdout)
            duplicate = subprocess.run([launcher, 'add', 'old', 'copilot', 'example'], env=env, capture_output=True)
            self.assertNotEqual(duplicate.returncode, 0)

    def test_list_reports_unavailable_login_without_stopping(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            binary = base / 'bin'
            binary.mkdir()
            for name in ('gh', 'codex', 'claude'):
                program = binary / name
                program.write_text('#!/bin/bash\nexit 1\n')
                program.chmod(0o755)
            accounts = base / 'store'
            (accounts / 'accounts' / 'old').mkdir(parents=True)
            env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'],
                       CODEX_ACCOUNTS_DIR=str(accounts), CODEX_SHARED_HOME=str(base / 'shared'))
            result = subprocess.run([str(PROJECT / 'agent-account'), 'list'], env=env, check=True, capture_output=True, text=True)
            self.assertIn('old', result.stdout)
            self.assertIn('check login', result.stdout)

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

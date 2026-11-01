"""Exercise profile workflows using isolated homes and mock CLI programs."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT / 'agent-account'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.root = self.base / 'accounts'
        self.shared = self.base / 'codex-home'
        (self.shared / 'sessions').mkdir(parents=True)
        self.claude_home = self.base / 'claude-home'
        (self.claude_home / 'projects').mkdir(parents=True)
        self.log = self.base / 'calls'
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        CODEX_ACCOUNTS_DIR=str(self.root), CODEX_SHARED_HOME=str(self.shared),
                        CLAUDE_SHARED_HOME=str(self.claude_home), MOCK_LOG=str(self.log))
        for key in ('CODEX_ACCOUNT_CONFIG', 'GH_TOKEN', 'GITHUB_TOKEN', 'COPILOT_GITHUB_TOKEN'):
            self.env.pop(key, None)
        self.stub('codex', '''#!/bin/bash
printf 'codex:%s:%s\\n' "$CODEX_HOME" "$*" >> "$MOCK_LOG"
if [[ "$*" == *login* && "${FAIL_CODEX:-}" == 1 ]]; then exit 1; fi
if [[ "$*" == *resume* ]]; then test -f "$CODEX_HOME/sessions/session-fixture" || exit 8; fi
''')
        self.stub('claude', '''#!/bin/bash
printf 'claude:%s:%s\\n' "$CLAUDE_CONFIG_DIR" "$*" >> "$MOCK_LOG"
if [[ "$*" == *login* && "${FAIL_CLAUDE:-}" == 1 ]]; then exit 1; fi
if [[ "$*" == *--resume* ]]; then test -f "$CLAUDE_CONFIG_DIR/projects/session-fixture" || exit 8; fi
''')
        self.stub('gh', '''#!/bin/bash
printf 'gh:%s\\n' "$*" >> "$MOCK_LOG"
[[ "${FAIL_GH:-}" != 1 ]] || exit 1
printf '%s' "${MOCK_TOKEN:-fake-secret}"
''')
        self.stub('copilot', '''#!/bin/bash
printf 'copilot:%s\\n' "$*" >> "$MOCK_LOG"
[[ "$COPILOT_GITHUB_TOKEN" == "${MOCK_TOKEN:-fake-secret}" ]] || exit 9
if [[ "$*" == *--resume* ]]; then test -f "$COPILOT_HOME/session-fixture" || exit 8; fi
''')

    def stub(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def run_cli(self, *args, env=None, success=True):
        result = subprocess.run([str(LAUNCHER), *args], env=env or self.env,
                                text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def test_resume_each_agents_own_history_across_profiles(self):
        (self.shared / 'sessions/session-fixture').write_text('codex')
        (self.claude_home / 'projects/session-fixture').write_text('claude')
        copilot_home = self.base / 'copilot-home'
        copilot_home.mkdir()
        (copilot_home / 'session-fixture').write_text('copilot')
        self.env['COPILOT_HOME'] = str(copilot_home)
        for name, agent in [('c1', 'codex'), ('c2', 'codex'), ('a1', 'claude'), ('a2', 'claude')]:
            self.run_cli('add', name, agent)
        self.run_cli('add', 'g1', 'copilot', 'first_user')
        self.run_cli('add', 'g2', 'copilot', 'second_user')
        for name in ('c1', 'c2'):
            self.run_cli('run', name, '--', 'resume', 'session-fixture')
            self.assertEqual((self.root / 'accounts' / name / 'sessions').resolve(), (self.shared / 'sessions').resolve())
        for name in ('a1', 'a2'):
            self.run_cli('run', name, '--', '--resume', 'session-fixture')
            self.assertEqual((self.root / 'claude/accounts' / name / 'projects').resolve(), (self.claude_home / 'projects').resolve())
        for name in ('g1', 'g2'):
            self.run_cli('run', name, '--', '--resume', 'session-fixture')
        calls = self.log.read_text()
        self.assertIn('--user first_user', calls)
        self.assertIn('--user second_user', calls)

    def test_use_and_named_run_choose_correct_profiles(self):
        for name, agent in [('one', 'codex'), ('two', 'claude')]:
            self.run_cli('add', name, agent)
        self.run_cli('add', 'three', 'copilot', 'third_user')
        for name in ('one', 'two', 'three'):
            self.run_cli('use', name)
            self.run_cli('run', '--', '--version')
            self.assertEqual((self.root / 'agent-selected').read_text().strip(), name)
        self.run_cli('run', 'one', '--', '--version')
        self.assertEqual((self.root / 'agent-selected').read_text().strip(), 'three')
        calls = self.log.read_text()
        self.assertIn(str(self.root / 'accounts/one'), calls)
        self.assertIn(str(self.root / 'claude/accounts/two'), calls)
        self.assertIn('--user third_user', calls)

    def test_failed_login_retry_and_missing_commands_do_not_change_selection(self):
        self.run_cli('add', 'good', 'codex')
        failed_env = dict(self.env, FAIL_CLAUDE='1')
        self.run_cli('add', 'retry', 'claude', env=failed_env, success=False)
        self.assertEqual((self.root / 'agent-selected').read_text().strip(), 'good')
        self.run_cli('login', 'retry')
        self.assertEqual((self.root / 'agent-selected').read_text().strip(), 'good')
        self.run_cli('use', 'missing', success=False)
        self.assertEqual((self.root / 'agent-selected').read_text().strip(), 'good')
        (self.bin / 'gh').unlink()
        missing_env = dict(self.env, PATH=str(self.bin) + ':/usr/bin:/bin')
        self.run_cli('add', 'no-gh', 'copilot', 'user', env=missing_env, success=False)
        self.assertFalse((self.root / 'copilot/accounts/no-gh').exists())

    def test_inherited_authentication_environment_is_not_cleared(self):
        self.run_cli('add', 'c1', 'codex')
        self.run_cli('add', 'a1', 'claude')
        self.stub('codex', '#!/bin/bash\ntest "$OPENAI_API_KEY" = sentinel || exit 7\n')
        self.stub('claude', '#!/bin/bash\ntest "$ANTHROPIC_API_KEY" = sentinel || exit 7\n')
        env = dict(self.env, OPENAI_API_KEY='sentinel', ANTHROPIC_API_KEY='sentinel')
        self.run_cli('run', 'c1', '--', '--version', env=env)
        self.run_cli('run', 'a1', '--', '--version', env=env)

    def test_empty_github_token_prevents_copilot_launch(self):
        self.run_cli('add', 'github', 'copilot', 'test_user')
        self.stub('gh', '#!/bin/bash\nexit 0\n')
        self.log.write_text('')
        result = self.run_cli('run', 'github', success=False)
        self.assertIn('empty token', result.stderr)
        self.assertNotIn('copilot:', self.log.read_text())

    def test_copilot_failure_never_launches_or_persists_token(self):
        self.run_cli('add', 'github', 'copilot', 'CHANGJO1_alcon')
        self.log.write_text('')
        failed_env = dict(self.env, FAIL_GH='1')
        result = self.run_cli('run', 'github', env=failed_env, success=False)
        self.assertNotIn('copilot:', self.log.read_text())
        self.assertNotIn('fake-secret', result.stdout + result.stderr)
        self.assertEqual((self.root / 'copilot/accounts/github/github-user').read_text(), 'CHANGJO1_alcon\n')
        self.assertNotIn('fake-secret', ''.join(p.read_text() for p in self.root.rglob('*') if p.is_file()))
        self.run_cli('run', 'github', '--', '--version')
        self.assertIn('--hostname github.com --user CHANGJO1_alcon', self.log.read_text())


if __name__ == '__main__':
    unittest.main()

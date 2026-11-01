import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT / 'agent-account'


class ShortFlagsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'args'
        for name, script in {
            'gh': '#!/bin/bash\nprintf fake-token\n',
            'copilot': '#!/bin/bash\nprintf "<%s>\\n" "$@" > "$MOCK_LOG"\n',
            'codex': '#!/bin/bash\nexit 0\n',
        }.items():
            path = self.bin / name
            path.write_text(script)
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        CODEX_ACCOUNTS_DIR=str(self.root / 'accounts'),
                        CODEX_SHARED_HOME=str(self.root / 'shared'), MOCK_LOG=str(self.log))
        self.env.pop('CODEX_ACCOUNT_CONFIG', None)

    def run_cli(self, *args, success=True):
        result = subprocess.run([str(LAUNCHER), *args], env=self.env, text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def test_aliases_cover_commands_and_help(self):
        help_text = self.run_cli('-h').stdout
        for short, long in [('-a', 'add'), ('-l', 'list'), ('-u', 'use'), ('-r', 'run'),
                            ('-s', 'status'), ('-i', 'login'), ('-h', 'help')]:
            self.assertIn(short, help_text)
            self.assertIn(long, help_text)
        self.assertEqual(help_text, self.run_cli('help').stdout)
        self.run_cli('-a', 'work', 'copilot', 'sample_user')
        self.assertIn('work', self.run_cli('-l').stdout)
        self.run_cli('-u', 'work')
        self.assertIn('credentials available', self.run_cli('-s', 'work').stdout)
        self.assertIn('gh auth login', self.run_cli('-i', 'work').stdout)
        self.run_cli('-r', 'work', '--', '-a', '--model', 'example')
        self.assertEqual(self.log.read_text().splitlines(), ['<-a>', '<--model>', '<example>'])

    def test_flags_after_run_are_not_wrapper_aliases(self):
        self.run_cli('add', 'work', 'copilot', 'sample_user')
        for command in ('run', '-r'):
            self.run_cli(command, 'work', '--', '-h', '-u', 'value')
            self.assertEqual(self.log.read_text().splitlines(), ['<-h>', '<-u>', '<value>'])
        self.run_cli('-z', success=False)


if __name__ == '__main__':
    unittest.main()

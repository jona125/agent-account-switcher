# Agent instructions

This macOS project wraps Codex, Claude Code, and GitHub Copilot CLI using named account profiles. Bash, Python 3, and the selected CLI must be installed.

- Use `./agent-account list` to see profile names and agent types. `use NAME` selects a profile for future launches; `run NAME -- ARGS` launches one without changing that selection. Add profiles with `add NAME codex`, `add NAME claude`, or `add NAME copilot GITHUB_USERNAME`.
- The old `codex-account` command remains compatible. Do not change account selection, log out, or alter credentials or history unless requested.
- CLI session histories are separate. Codex shares local history across its profiles; Claude history sharing is experimental and unverified with authenticated sessions. Do not open the same session in two processes at once.
- `config.xml` contains defaults; ignored `config.local.xml` holds local overrides. Keep credentials, session data, and local configuration out of Git. Never print or copy credentials. Copilot obtains a `gh` token at launch; do not log it.
- Verify changes with `python3 -m unittest discover -s tests -v` and `for f in agent-account codex-account lib/codex-backend lib/claude-account; do bash -n "$f"; done`. Use temporary directories and mock credentials for tests.

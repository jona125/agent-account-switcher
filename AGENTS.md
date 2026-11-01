# Agent instructions

This macOS tool wraps the installed Codex CLI so separate accounts can use shared local session history. It requires Bash, Python 3, and `codex` on PATH.

- Run `./codex-account list` to list accounts and `./codex-account status NAME` to check login status.
- Run `./codex-account run --account NAME -- resume --all` to select an existing session, or omit `resume --all` to start a new one. `use NAME` sets the default for future wrapper launches; it does not change a running session.
- To continue a conversation under another account, exit the existing session first, then resume it with the other account. Do not run two processes against the same session simultaneously. Shared-history resumption has been tested in isolation; concurrent authenticated use has not been verified.
- `config.xml` contains portable defaults. Put machine-specific paths in the ignored `config.local.xml`; see the README for overrides. Keep credentials and session storage outside this repository. Never print, copy, or commit credentials or local configuration.
- Do not log out, switch the default account, change account configuration, or alter shared history unless requested. Preserve existing history and credentials.
- Verify changes with `python3 -m unittest discover -s tests -v` and `bash -n codex-account`. Use temporary directories and mock credentials for tests.

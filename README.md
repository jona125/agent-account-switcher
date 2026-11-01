# Codex account switcher for macOS

A terminal wrapper for using multiple Codex CLI logins. It does not change your existing `~/.codex` or your ordinary `codex` command. Codex must already be installed and available on PATH.

```sh
~/.local/bin/codex-account add personal
~/.local/bin/codex-account add work
~/.local/bin/codex-account list
~/.local/bin/codex-account use work
~/.local/bin/codex-account run
~/.local/bin/codex-account run --account personal -- exec 'Explain this project'
~/.local/bin/codex-account status
```

If `~/.local/bin` is on your PATH, use `codex-account` directly. Each `add` opens the standard Codex login flow; choose the intended ChatGPT account in the browser. If the browser automatically signs into the wrong account, use a browser profile or private window with the desired account. To refresh a login, run `codex-account login NAME`.

Each account has a separate Codex home under `~/.local/share/codex-accounts/accounts/NAME`, with separate file-based credentials and settings. Credentials are sensitive; keep the directory private and do not sync or commit it. The wrapper links session files to your existing `~/.codex` home and configures the shared SQLite state there, so both accounts can find the same sessions. Existing settings, skills, plugins, and MCP connections are not automatically copied. `CODEX_ACCOUNTS_DIR` overrides account storage; `CODEX_SHARED_HOME` overrides the shared home. If an account already has its own session files, the wrapper stops rather than overwrite them; those files are not automatically merged.

The wrapper passes all CLI arguments to Codex, including `exec`, `resume`, and other subcommands. Selection applies to future wrapper launches. It does not change a running process or automatically switch the desktop app, IDE extensions, remote daemons, or plain `codex` commands. Environment-provided credentials or an independently configured remote server may override local credentials; check `status` and your environment when applicable. Run `codex-account help` for options.

To continue a conversation with a different account, exit the original CLI session, then run `codex-account run --account work -- resume --all` and select it. Switch back in the same way. Avoid having two processes actively edit the same conversation at once. The wrapper disables the shared daemon for its launches to keep account credentials scoped to the selected process. This arrangement was tested by resuming an isolated copy of an old session from two homes; live authenticated turns across accounts have not yet been tested.

## Local configuration

The tracked `config.xml` contains portable defaults. On first use, the launcher creates `config.local.xml` in the project directory from those defaults. Edit that ignored file to customize paths for this Mac; existing local files are never overwritten. If it cannot be created, the launcher uses the defaults. Both settings must be absolute paths or begin with `~/`:

```xml
<codex-account-config>
  <accounts-dir>~/.local/share/codex-accounts</accounts-dir>
  <shared-home>~/.codex</shared-home>
</codex-account-config>
```

`accounts-dir` stores login credentials and must remain private; `shared-home` points to the Codex home containing the shared session history. Do not place either directory inside the Git repository. The optional `CODEX_ACCOUNT_CONFIG` environment variable selects another XML file. `CODEX_ACCOUNTS_DIR` and `CODEX_SHARED_HOME` take precedence over the corresponding XML values. The parser uses Python 3's standard library; no additional packages are required. Never put credentials in the XML file.

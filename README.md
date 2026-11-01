# Agent account switcher for macOS

Launch Codex, Claude Code, or GitHub Copilot CLI using a named account profile. Each CLI must already be installed. Bash and Python 3 are required.

Install the launcher by linking it to a directory on your PATH:

```sh
mkdir -p ~/.local/bin
ln -s "$(pwd)/agent-account" ~/.local/bin/agent-account
```

Run the commands from this repository directory or add `~/.local/bin` to your PATH. Choose the CLI when adding a profile; after that the profile name identifies it:

```sh
agent-account add personal codex
agent-account add work claude
agent-account add github-work copilot GITHUB_USERNAME
agent-account list
agent-account use personal
agent-account run
agent-account run work -- --resume
agent-account run personal -- resume --all
```

`use` changes the default for future launches; running sessions are unaffected. `run NAME` starts a named profile without changing the default. Put CLI arguments after `--`. Existing Codex profiles created by the older `codex-account` command are discovered automatically. Profile names must be unique across all agents.

Codex and Claude profiles use their CLIs' own interactive login flows. For Copilot, first authenticate the desired GitHub username with `gh auth login`; the profile stores only that username. At launch, the wrapper obtains that user's GitHub CLI token and passes it to Copilot in `COPILOT_GITHUB_TOKEN`. The token is not saved in the profile, but is present in Copilot's process environment. Copilot access depends on the account and token permissions. GitHub CLI and Copilot must be installed; GitHub Enterprise hosts are not currently supported. Copilot provider environment variables can override GitHub authentication for model requests.

## Sessions

Each CLI has its own conversation format; sessions cannot be resumed across different CLIs. Codex profiles share the existing `~/.codex` session files and SQLite state, while keeping credentials separate. Exit a session before resuming it with another profile. Codex shared-history resumption was tested with an isolated old session; simultaneous authenticated turns across accounts have not been verified.

Claude profiles use separate `CLAUDE_CONFIG_DIR` directories and link their `projects` directory to `~/.claude/projects`, or to the `projects` directory under `CLAUDE_SHARED_HOME` if set to an absolute path. Start Claude normally first to create the directory. This sharing arrangement is experimental and has not been verified with authenticated Claude sessions or all versions. If a profile already has separate project history, the launcher stops rather than overwrite it. API key or provider environment variables can override the profile login.

Copilot retains its normal configuration and session storage. Copilot's built-in `/user list` and `/user switch` are also available. Avoid running two processes against the same conversation simultaneously, and take care when separate sessions edit the same files.

## Configuration and security

The tracked `config.xml` has portable defaults. On first use, the launcher creates the Git-ignored `config.local.xml` from those defaults. Edit it to customize directories. Existing local files are never overwritten; if creation fails, defaults are used. Paths must be absolute or start with `~/`.

`accounts-dir` stores profile data and credentials; `shared-home` points to the shared Codex home. Keep both outside this repository and never put credentials into XML. `CODEX_ACCOUNT_CONFIG` selects an alternative XML file; `CODEX_ACCOUNTS_DIR` and `CODEX_SHARED_HOME` override the corresponding values. `CLAUDE_SHARED_HOME` separately overrides Claude's shared home. Credentials, histories, account configurations, and local overrides must not be committed or synced to Git.

See [Claude Code environment variables](https://code.claude.com/docs/en/env-vars) and [Copilot authentication](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli).

## Login status and reauthentication

`agent-account list` shows each profile's agent and a basic login check. `credential available` means the underlying CLI reported a saved login, or `gh` returned a token for a Copilot profile. It does not confirm that a live request will succeed or that an account has an active subscription. `check login` means the check could not establish that credentials are available; the CLI or keychain could also be unavailable. Environment credentials can affect the underlying CLI's status.

For more detail, run `agent-account status NAME`. If a Codex or Claude profile needs a new login, run `agent-account login NAME` and complete its normal login flow. For Copilot, run `gh auth login`, authenticate the GitHub username associated with the profile, then run `agent-account status NAME`. These steps retain the profile name and session history. The tool does not yet provide commands to rename, edit, or remove profiles.

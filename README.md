# Note Watcher

A tool that detects `@` mentions in Obsidian markdown notes stored in Git and dispatches instructions to configured agents — like [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — that can read, modify, and reorganize your notes directly.

Write `@agent_name do something` in any note, and Note Watcher dispatches the instruction to the named agent. The agent can edit files, create new notes, restructure content, or make any other changes to your vault. The original instruction is then replaced with a completion marker (an HTML comment, invisible in rendered markdown) so it is never reprocessed:

```markdown
<!-- @done agent_name: do something
Agent response summary goes here.
/@done -->
```

The real work happens in the commit: the agent's changes to your vault are committed back to Git. The completion comment is just a record that the instruction was processed.

## Modes of Operation

| Mode | Use case |
|------|----------|
| **Daemon** | Real-time file watching on macOS via a LaunchAgent |
| **GitHub Action** | One-shot batch processing on every push that changes `.md` files |

## Requirements

- Python 3.10+

## Installation

```bash
pip install notes-watcher
```

For development:

```bash
pip install -e ".[dev]"
```

## Configuration

Copy the example config and edit it:

```bash
mkdir -p ~/.config/note-watcher
cp config.example.yml ~/.config/note-watcher/config.yml
```

The default config location is `~/.config/note-watcher/config.yml`. You can override it with `--config`:

```bash
note-watcher watch --config /path/to/config.yml
```

### Config reference

```yaml
# Path to your Obsidian vault
vault: ~/Obsidian/MyVault

# Seconds to wait before processing after a file change
debounce_seconds: 1.0

# File patterns to ignore (glob syntax)
ignore_patterns:
  - "*.excalidraw.md"
  - ".trash/**"

# Agent definitions
agents:
  summarizer:
    type: echo        # Returns instruction text unchanged
  uppercase:
    type: uppercase   # Returns instruction text in uppercase
  word_count:
    type: command
    command: "wc -w"  # Runs a shell command, passes instruction via stdin
```

### Agent types

| Type | Behavior |
|------|----------|
| `echo` | Returns the instruction text unchanged |
| `uppercase` | Returns the instruction text in uppercase |
| `command` | Runs a shell command with instruction text on stdin, returns stdout |

### Example: Using Claude Code as an agent

Configure a `command` agent that dispatches instructions to [Claude Code](https://docs.anthropic.com/en/docs/claude-code):

```yaml
agents:
  claude:
    type: command
    command: "claude -p"   # Dispatches instruction to Claude Code CLI
```

Claude Code runs with full access to your vault, so it can edit notes, create new files, and reorganize content — not just respond in a comment. Write `@claude` instructions in your notes:

```markdown
@claude Summarize the key points of this meeting and add action items to my Tasks note
```

## Daemon Mode

Daemon mode continuously watches your Obsidian vault for changes and processes `@` mentions in real time.

### Running manually

```bash
# Watch the vault specified in your config
note-watcher watch

# Override the vault path
note-watcher watch --vault ~/Obsidian/MyVault

# Enable verbose logging
note-watcher -v watch --vault ~/Obsidian/MyVault
```

Stop the daemon with `Ctrl+C` (`SIGINT`) or `SIGTERM`.

### Installing as a macOS LaunchAgent

The included install script sets up Note Watcher as a LaunchAgent that starts on login and restarts on crash:

```bash
./scripts/install.sh
```

The script is idempotent and safe to run multiple times. It will:

1. Detect the `note-watcher` executable on your system
2. Generate a LaunchAgent plist from the included template
3. Install it to `~/Library/LaunchAgents/`
4. Start the daemon

Logs are written to `~/Library/Logs/note-watcher/`.

### Uninstalling the LaunchAgent

```bash
./scripts/uninstall.sh
```

To also remove the log directory:

```bash
./scripts/uninstall.sh --clean
```

## GitHub Action Mode

GitHub Action mode processes all pending `@` instructions across the entire vault in a single batch run. This is useful for vaults stored in a Git repository.

### CLI usage

```bash
note-watcher process --all --vault /path/to/vault
```

### Setting up the GitHub Actions workflow

See [`examples/github-action/`](examples/github-action/) for a complete, ready-to-copy example that uses [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as the AI agent.

To set it up:

1. Copy `examples/github-action/.github/` into your notes repository
2. Add a `config.yml` to your notes repo (see `examples/github-action/config.example.yml`)
3. Add your `ANTHROPIC_API_KEY` as a repository secret

The example workflow already includes `permissions: contents: write`, which is required for the action to push processed results back to your repository. If you write your own workflow, make sure to include this permission block.

The workflow triggers on any push that modifies `.md` files, processes all unprocessed `@` instructions, and commits the agent's changes back to your repository. It uses `[skip ci]` to prevent infinite loops.

See the [Claude Code GitHub Actions documentation](https://docs.anthropic.com/en/docs/claude-code/github-actions) for more on setting up Claude Code in CI.

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=note_watcher
```

## License

[MIT](LICENSE)

# Note Watcher

A daemon that detects `@` mentions in Obsidian markdown notes, dispatches instructions to configured agents, and writes results back as HTML comments.

Write `@agent_name do something` in any note, and Note Watcher replaces it with the agent's output wrapped in a single HTML comment (invisible in rendered markdown):

```markdown
<!-- @done agent_name: do something
Agent output goes here.
/@done -->
```

Processed instructions are wrapped in `<!-- @done ... /@done -->` comment blocks so they are never reprocessed and stay hidden when the note is rendered.

## Modes of Operation

| Mode | Use case |
|------|----------|
| **Daemon** | Real-time file watching on macOS via a LaunchAgent |
| **GitHub Action** | One-shot batch processing on every push that changes `.md` files |

## Requirements

- Python 3.10+

## Installation

```bash
pip install .
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

Then write `@claude` instructions in your notes:

```markdown
@claude Summarize the key points of this meeting
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

Add the following workflow to your repository at `.github/workflows/note-watcher.yml`. This example uses [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as the AI agent:

```yaml
name: Note Watcher
on:
  push:
    paths:
      - '**.md'
jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: anthropics/anthropic-cookbook/.github/actions/claude-code@main
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
      - run: pip install .
      - run: note-watcher process --all --vault .
      - name: Commit results
        run: |
          git config user.name 'Note Watcher Bot'
          git config user.email 'note-watcher@users.noreply.github.com'
          git add -A
          git diff --staged --quiet || git commit -m "Process note instructions [skip ci]"
          git push
```

This workflow:

- Triggers on any push that modifies `.md` files
- Sets up Claude Code via the [Claude Code GitHub Action](https://docs.anthropic.com/en/docs/claude-code/github-actions) for AI-powered processing
- Installs Note Watcher and processes all unprocessed instructions
- Commits the results back to the repository using a bot identity
- Uses `[skip ci]` in the commit message to prevent infinite workflow loops

> **Tip:** For AI-powered processing, configure a Claude Code agent (e.g., `command: "claude -p"`). See the [Claude Code GitHub Actions documentation](https://docs.anthropic.com/en/docs/claude-code/github-actions) for setup details.

**Note:** The repository's default `GITHUB_TOKEN` must have write permissions for the commit step to succeed. Under **Settings > Actions > General**, set "Workflow permissions" to "Read and write permissions".

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

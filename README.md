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

### System prompts

Command agents include a default system prompt that tells the agent about the vault, the note being processed, and how to respond. The default prompt is:

> You are working in an Obsidian vault at {vault_path}.
> The user has left an instruction in the note at {file_path}.
> Read the note, then modify it as requested by the instruction.
> If the user asks for changes to a note without specifying which one, apply the changes to the same note that contains the instruction.
> After making your changes, commit them to git.
> Respond with a brief summary of what you did.

This works out of the box — you only need to configure a system prompt if you want different behavior.

#### Overriding the default prompt

To replace the default, set `system_prompt` inline or load it from a file with `system_prompt_file`. Setting either one **completely replaces** the default prompt.

```yaml
agents:
  claude:
    type: command
    command: "claude --print"
    # Inline — replaces the default prompt entirely
    system_prompt: |
      You are a note-taking assistant working in {vault_path}.
      Edit the note at {file_path} as instructed.
      Do not commit changes — the caller will handle that.

  claude-from-file:
    type: command
    command: "claude --print"
    # Load from a file (path relative to the config file's directory)
    # Also replaces the default prompt entirely
    system_prompt_file: prompts/claude.md
```

You cannot set both `system_prompt` and `system_prompt_file` on the same agent — Note Watcher will raise an error if you do.

#### Template variables

System prompts (including the default) support template variables that are interpolated at dispatch time:

| Variable | Value |
|----------|-------|
| `{vault_path}` | Absolute path to the Obsidian vault |
| `{file_path}` | Path to the note containing the `@` instruction |

#### Environment variables

The resolved prompt is always passed to the command via the `NOTE_WATCHER_SYSTEM_PROMPT` environment variable. The following environment variables are always set for command agents:

| Environment variable | Value |
|----------------------|-------|
| `NOTE_WATCHER_VAULT_PATH` | Absolute path to the vault |
| `NOTE_WATCHER_FILE_PATH` | Path to the note being processed |
| `NOTE_WATCHER_SYSTEM_PROMPT` | Resolved system prompt (default or custom) |

### Example: Using Claude Code as an agent

Configure a `command` agent that dispatches instructions to [Claude Code](https://docs.anthropic.com/en/docs/claude-code). The default system prompt works well for Claude Code, so you only need to set the command:

```yaml
agents:
  claude:
    type: command
    command: "claude --print --system-prompt \"$NOTE_WATCHER_SYSTEM_PROMPT\""
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

## Arcade MCP Integration

Note Watcher can use [Arcade](https://arcade.dev) as an MCP gateway to give Claude Code access to external services like Gmail, Google Drive, Google Calendar, Google Sheets, Google Docs, GitHub, and Slack. This lets your `@claude` instructions interact with services beyond the vault — for example, checking email, creating calendar events, or posting to Slack.

Arcade handles OAuth on your behalf: you authorize each service once from your local machine, and Arcade caches the tokens server-side. After that, the GitHub Action runner can use the same tokens without any interactive auth flow.

### Setting up an Arcade MCP gateway

1. Create an [Arcade account](https://api.arcade.dev/dashboard/register) and note your API key
2. Go to the [MCP Gateways dashboard](https://api.arcade.dev/dashboard/mcp-gateways) and click **Create MCP Gateway**
3. Configure the gateway:
   - **Name**: A descriptive name (e.g. "Obsidian Note Watcher")
   - **Slug**: This becomes your gateway URL path (e.g. `obsidian-notes-watcher` gives you `https://api.arcade.dev/mcp/obsidian-notes-watcher`)
   - **Authentication Mode**: Use **Arcade Headers** for production — this requires an `Authorization` header with your API key and an `Arcade-User-ID` header with the user's email
4. Add the tools your agents need from the Arcade tool catalog. The following toolkits are supported:

| Service | Example tools |
|---------|--------------|
| **GitHub** | `Github.GetRepository`, `Github.CreateIssue`, `Github.ListPullRequests` |
| **Gmail** | `Gmail.ListEmails`, `Gmail.SendEmail` |
| **Google Drive** | `GoogleDrive.SearchFiles`, `GoogleDrive.GetFileContents` |
| **Google Calendar** | `GoogleCalendar.ListEvents`, `GoogleCalendar.CreateEvent` |
| **Google Sheets** | `GoogleSheets.GetSpreadsheet` |
| **Google Docs** | `GoogleDocs.SearchDocuments` |
| **Slack** | `Slack.ListConversations`, `Slack.SendMessage`, `Slack.GetMessages` |

You don't need to add every tool — only the ones your agents will use. You can always add more later from the dashboard.

### Pre-authorizing OAuth tokens

Arcade uses a just-in-time OAuth flow: the first time a tool needs access to a service, the user must visit a URL in a browser to grant consent. Since GitHub Action runners are headless, you need to complete this authorization once from your local machine before the action can use those services.

The included `scripts/authorize_arcade.py` script handles this. It walks through each service, triggers the OAuth flow, opens your browser for consent, and waits for completion. Arcade then caches the tokens server-side, keyed by your email address.

#### Prerequisites

```bash
pip install arcadepy
export ARCADE_API_KEY=your-api-key
```

#### Authorize all services

```bash
python scripts/authorize_arcade.py you@example.com
```

The email address is your Arcade account email. It's used as the `user_id` for token storage — the same identity must be used when the MCP gateway is called from CI.

The script will open your browser for each service that hasn't been authorized yet. Grant consent for each one, and the script will detect completion automatically.

#### Authorize specific services only

```bash
python scripts/authorize_arcade.py you@example.com --services gmail slack google-calendar
```

Available services: `github`, `gmail`, `google-drive`, `google-calendar`, `google-sheets`, `google-docs`, `slack`.

#### Without auto-opening the browser

```bash
python scripts/authorize_arcade.py you@example.com --no-browser
```

This prints the authorization URLs instead of opening them, useful for remote machines or SSH sessions.

#### Re-authorization

You'll need to re-run the script if:

- An OAuth token is revoked or expires
- You add new services to your gateway
- Your Google Cloud OAuth app is in "testing" mode (tokens expire after 7 days — publish the app or set it to "internal" for Google Workspace orgs to avoid this)

### Configuring the MCP server for Claude Code

Once your gateway is set up and tokens are cached, configure Claude Code to use it. In the GitHub Action workflow, add the MCP server before running Note Watcher:

```yaml
- name: Configure Arcade MCP gateway
  run: |
    claude mcp add --transport http arcade \
      https://api.arcade.dev/mcp/your-gateway-slug \
      --header "Authorization: Bearer ${{ secrets.ARCADE_API_KEY }}" \
      --header "Arcade-User-ID: ${{ secrets.ARCADE_USER_ID }}"
```

Add these secrets to your repository:

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (for Claude Code) |
| `ARCADE_API_KEY` | Your Arcade API key |
| `ARCADE_USER_ID` | The email you used when running `authorize_arcade.py` |

Claude Code will then have access to all the tools in your gateway when processing `@claude` instructions. For example:

```markdown
@claude Check my Gmail for any emails from the team about the Q4 report and summarize them here

@claude Create a Google Calendar event for our standup tomorrow at 10am

@claude Post a message in the #notes channel on Slack saying the weekly review is ready
```

## Installing Skills for Claude Code

[Skills](https://docs.anthropic.com/en/docs/claude-code/skills) are markdown files that teach Claude Code reusable behaviors — how to format notes, apply templates, follow your conventions, etc. Skills are checked into your notes repository, so they work automatically in both daemon mode and the GitHub Action.

### Writing your own skills

Create a `SKILL.md` file inside a named directory under `.claude/skills/`:

```
your-notes-repo/
├── .claude/
│   └── skills/
│       ├── organize-notes/
│       │   └── SKILL.md
│       └── daily-journal/
│           ├── SKILL.md
│           └── templates/
│               └── journal-entry.md
├── Notes/
│   └── ...
└── config.yml
```

Each `SKILL.md` has YAML frontmatter and markdown instructions:

```markdown
---
name: organize-notes
description: Organize notes into folders by topic and add backlinks
---

When asked to organize notes:
1. Group related notes into topic folders
2. Add `[[backlinks]]` between related notes
3. Update any broken links after moving files
```

Claude Code automatically discovers skills in `.claude/skills/` and uses them when relevant. You can also reference one explicitly:

```markdown
@claude Use the daily-journal skill to format today's standup notes
```

### Installing plugins from a marketplace

You can install community-contributed plugins from a [plugin marketplace](https://docs.anthropic.com/en/docs/claude-code/plugins) instead of writing skills by hand. Run these commands locally from your notes repository:

```bash
# Install from the official Anthropic marketplace into the project
claude plugin install plugin-name@claude-plugins-official --scope project

# Commit and push so the GitHub Action picks it up
git add .claude/
git commit -m "Add plugin-name plugin"
git push
```

The `--scope project` flag writes the plugin configuration into the repo's `.claude/` directory. Once committed and pushed, the plugin is available when the GitHub Action runs — no extra workflow steps needed.

To install from a third-party marketplace, add it first:

```bash
claude plugin marketplace add https://github.com/someone/their-marketplace
claude plugin install note-helper@their-marketplace --scope project
```

Then commit and push `.claude/` as above.

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

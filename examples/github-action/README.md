# Note Watcher GitHub Action Example

This example shows how to set up Note Watcher as a GitHub Action in your Obsidian notes repository. It uses [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as the agent, but Note Watcher can run any command — `claude -p` is just one option. Any program that reads from stdin and writes to stdout works as a `command` agent (see the [agent types](../../README.md#agent-types) in the main README).

## Setup

1. Copy `.github/workflows/note-watcher.yml` into your notes repository
2. Copy `config.example.yml` to `config.yml` in your notes repository root and configure your agents
3. Add your `ANTHROPIC_API_KEY` as a repository secret under **Settings > Secrets and variables > Actions** (only needed for the Claude agent — swap in your own command and secrets as needed)
4. Under **Settings > Actions > General**, set "Workflow permissions" to "Read and write permissions"

## How it works

When you push changes to `.md` files, the workflow:

1. Checks out your repository
2. Sets up Claude Code (only needed for the Claude agent in this example)
3. Runs the `britt/obsidian-note-watcher` action, which installs Note Watcher, processes all unprocessed `@` instructions, and commits the results back
4. Uses `[skip ci]` to prevent infinite workflow loops

## Action inputs

| Input | Default | Description |
|-------|---------|-------------|
| `vault` | `.` | Path to the Obsidian vault (relative to repo root) |
| `config` | `config.yml` | Path to the Note Watcher config file |
| `python-version` | `3.11` | Python version to use |
| `version` | latest | Note Watcher package version to install |
| `commit` | `true` | Whether to commit and push results automatically |
| `commit-message` | `Process note instructions [skip ci]` | Commit message to use |

## Example

Write `@claude` instructions in your notes:

```markdown
@claude Summarize the key points of this meeting
```

After the workflow runs, it becomes:

```markdown
<!-- @done claude: Summarize the key points of this meeting
The key points of this meeting are...
/@done -->
```

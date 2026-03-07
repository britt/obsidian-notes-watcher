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
3. Runs the `britt/obsidian-note-watcher` action, which installs Note Watcher and processes all unprocessed `@` instructions
4. The agent (e.g. Claude Code) can read, edit, create, and reorganize notes across your vault — not just reply in a comment
5. All changes are committed and pushed back to your repository
6. Uses `[skip ci]` to prevent infinite workflow loops

## Action inputs

| Input | Default | Description |
|-------|---------|-------------|
| `vault` | `.` | Path to the Obsidian vault (relative to repo root) |
| `config` | `config.yml` | Path to the Note Watcher config file |
| `python-version` | `3.11` | Python version to use |
| `version` | latest | Note Watcher package version to install |
| `commit` | `true` | Whether to commit and push results automatically |
| `commit-message` | `Process note instructions [skip ci]` | Commit message to use |

## System prompts

You can give your agent a system prompt to control its behavior. Define it inline in `config.yml` or load it from a file:

```yaml
agents:
  claude:
    type: command
    command: "claude --print --system-prompt \"$NOTE_WATCHER_SYSTEM_PROMPT\""
    system_prompt: |
      You are working in an Obsidian vault at {vault_path}.
      The user has left an instruction in the note at {file_path}.
      Read the note, then modify it as requested.
      Respond with a brief summary of what you did.
```

Or load from a file (path relative to the config file):

```yaml
agents:
  claude:
    type: command
    command: "claude --print --system-prompt \"$NOTE_WATCHER_SYSTEM_PROMPT\""
    system_prompt_file: prompts/claude.md
```

The `{vault_path}` and `{file_path}` template variables are replaced at dispatch time. The resolved prompt is set as the `NOTE_WATCHER_SYSTEM_PROMPT` environment variable. See the [system prompts section](../../README.md#system-prompts) in the main README for full details.

## Example

Write `@claude` instructions in your notes:

```markdown
@claude Summarize the key points of this meeting and add action items to my Tasks note
```

After the workflow runs, Claude Code edits your vault (creating or updating notes as needed), and the original instruction is replaced with a completion marker:

```markdown
<!-- @done claude: Summarize the key points of this meeting and add action items to my Tasks note
Added summary and extracted 3 action items to Tasks.md.
/@done -->
```

The completion comment is just a record — the real work is in the commit, where the agent's changes to your notes are pushed back to the repository.

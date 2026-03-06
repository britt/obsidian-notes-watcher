# Note Watcher GitHub Action Example

This example shows how to set up Note Watcher as a GitHub Action in your Obsidian notes repository.

## Setup

1. Copy `.github/workflows/note-watcher.yml` into your notes repository
2. Copy `config.example.yml` to `config.yml` in your notes repository root and configure your agents
3. Add your `ANTHROPIC_API_KEY` as a repository secret under **Settings > Secrets and variables > Actions**
4. Under **Settings > Actions > General**, set "Workflow permissions" to "Read and write permissions"

## How it works

When you push changes to `.md` files, the workflow:

1. Checks out your repository
2. Sets up Python and Claude Code
3. Installs Note Watcher and processes all unprocessed `@` instructions
4. Commits the results back using a bot identity
5. Uses `[skip ci]` to prevent infinite workflow loops

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

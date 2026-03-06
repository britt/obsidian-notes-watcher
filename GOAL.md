---
flow: |
  "general-purpose" -> "stpa-analyst"
  "shell-script-coder" -> "shell-script-reviewer"
  "shell-script-reviewer" -> "stpa-analyst"
models:
  "coordinator": "anthropic/claude-opus-4-6 (max)"
  "general-purpose": "anthropic/claude-opus-4-6"
  "shell-script-coder": "anthropic/claude-opus-4-6"
  "shell-script-reviewer": "anthropic/claude-opus-4-6"
  "stpa-analyst": "anthropic/claude-opus-4-6"
interactive: yes
completionGateScript: pytest
---

Build Note Watcher, a Python daemon that detects @ mentions in Obsidian notes, dispatches instructions to AI agents, and writes results back inline. Supports both real-time daemon mode and batch GitHub Action mode.

## Success Criteria

- [x] File watcher detects changes to .md files in the vault directory
- [x] Parser extracts @ mention instructions (e.g., `@summarizer Summarize this`)
- [x] Agent dispatcher routes instructions to configured AI agents
- [x] Results are written back inline, replacing the instruction with output
- [x] Completed markers prevent reprocessing of finished instructions
- [x] Daemon mode runs as macOS LaunchAgent with crash recovery
- [x] Batch mode processes all pending instructions via `note-watcher process --all`
- [x] GitHub Action workflow triggers on push and commits results with `[skip ci]`
- [x] Configuration via YAML supports custom agents and ignore patterns
- [x] Debouncing prevents duplicate processing during rapid file changes

## Context

See `Ideas/Note Watcher/Design.md` for architecture diagrams and implementation details.
See `Ideas/Note Watcher/Decisions.md` for architectural decision records.

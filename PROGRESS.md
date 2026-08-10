# Progress

## Task: Fix Multi-Mention Commenting (Issue #24) - COMPLETE
- Started: 2026-03-23
- Tests: 109 passing, 1 failing (pre-existing: `test_batch_process_multiple_files` fails due to missing `arcadepy` module, unrelated to this change)
- Coverage: Lines: 72% (TOTAL), writer.py: 100%, parser.py: 100%, config.py: 100%, dispatcher.py: 97%, watcher.py: 66% (uncovered lines are daemon/watch mode code and arcade_check/cli modules missing arcadepy dependency)
- Build: Successful
- Linting: 22 pre-existing ruff errors (line length, import sorting, unused import); none introduced by this change
- Completed: 2026-03-23
- Notes: Fixed _replace_instruction_line to use text-based search instead of line-number matching. Removed dead process_file function. Added integration test for agent file modification during dispatch.

## Task: Fix Done Comments Not Being Added (Issue #12) - COMPLETE
- Started: 2026-06-15
- Tests: 138 passing, 0 failing
- Coverage: Lines: 90% (TOTAL), writer.py: 100%, parser.py: 100%, dispatcher.py: 97%, watcher.py: 75% (remaining misses are the `start_watcher` daemon loop and an `_should_ignore` branch, both pre-existing and unrelated)
- Build: Successful
- Linting: 19 pre-existing ruff errors on origin/main (line length, import sorting); none introduced by this change. Repo is not ruff-format-clean on main, so existing multi-line style was preserved to keep the fix focused.
- Completed: 2026-06-15
- Notes: Root cause — when a command agent (e.g. Claude Code) followed its instruction and rewrote the note, it removed the original `@agent` line; `_replace_instruction_line` could then no longer find its anchor, raised ValueError, and `process_file_reparse` swallowed it and broke, so no `@done` marker was written. The #24 text-search fallback only handled the line *moving*, not being *removed*.
  Fix — "replace-before-dispatch": `process_file_reparse` now writes a parser-neutral sentinel (`<!-- note-watcher: processing @agent ... -->`) in place of the instruction *before* dispatch (while the line is guaranteed present), then swaps the sentinel for the `@done`/`@error` marker after dispatch. The swap anchors on the sentinel and appends at EOF if the agent removed it, so the response is never lost. Unknown-agent and unexpected-error paths restore the original instruction for retry. New writer helpers: `format_pending`, `write_pending`, `finalize_result`, `finalize_error`, `restore_instruction` (refactored shared `_replace_line` core). Verified end-to-end via the real CLI with a command agent, including VERIFICATION_PLAN Scenario 6 (2 markers, agent edits preserved, idempotent on re-run).

## Task: Handle Multiple Agent Invocations Per Run - COMPLETE
- Started: 2026-06-15
- Tests: 151 passing, 0 failing
- Coverage: Lines: 91% (TOTAL), parser.py: 100%, writer.py: 100%, dispatcher.py: 97%, watcher.py: 76% (remaining misses are the `start_watcher` daemon loop and an `_should_ignore` branch, both pre-existing and unrelated)
- Build: Successful
- Linting: pre-existing ruff-version artifacts only (parser.py I001, format diffs on untouched files like config.py); my diff introduces zero new ruff errors vs origin/main. CI runs `pytest --cov` only (no ruff gate).
- Completed: 2026-06-15
- Notes: After #26 fixed self-editing agents, two failure modes remained for multi-mention notes: (1) an `UnknownAgentError` or generic dispatch error `break` the loop, abandoning every later instruction (reproduced: `@ghost` before `@echo` → 0 processed); (2) siblings were exposed as raw `@agent` lines to the running agent, which could clobber them.
  Fix — claim-all-then-dispatch (design in design/plans/2026-06-15-multiple-invocations-design.md). `process_file` (renamed from `process_file_reparse`) now: recovers stale sentinels from crashed runs; claims every known-agent instruction up front (replacing each line with a sentinel) so siblings are protected during dispatch; then dispatches over a fixed list and NEVER breaks — generic errors and recovered-unknown-agents are recorded as `@error`, unknown fresh agents are left raw. Sentinels now carry a unique token (`uuid4().hex[:8]`) so duplicate identical instructions can't collide. Added parser `parse_pending`/`PendingInstruction` for recovery; tokened `format_pending`; removed now-dead `restore_instruction`. Hardened `DEFAULT_SYSTEM_PROMPT` to tell agents to leave `<!-- ... -->` markers intact. Verified end-to-end: Case 2 (unknown-before-valid) and VERIFICATION_PLAN Scenario 6 (2 markers, agent edits preserved, idempotent on re-run).

## Task: Fail the Run on Agent Timeout - COMPLETE
- Started: 2026-08-08
- Tests: 158 passing, 0 failing (5 new: 2 in test_watcher.py, 3 in test_cli.py)
- Coverage: Lines: 90% (TOTAL), writer.py: 100%, parser.py: 100%, config.py: 100%, dispatcher.py: 97%, watcher.py: 76% (remaining misses are the pre-existing `start_watcher` daemon loop, unrelated), cli.py: 86%
- Build: Successful
- Linting: zero new ruff errors on files I touched (note_watcher/watcher.py, note_watcher/cli.py, tests/test_watcher.py, tests/test_cli.py all clean); pre-existing errors/format drift on untouched files (config.py, parser.py, debouncer.py, test_integration.py, etc.) left as-is, consistent with prior entries' policy
- Completed: 2026-08-08
- Notes: `command`-type agents (e.g. Claude Code) enforce `agent_config.timeout` (default 900s) via `subprocess.run(..., timeout=...)`, which raises `subprocess.TimeoutExpired`. That was already caught by `process_file`'s generic `except Exception` and turned into an `@error` marker in the note — but `process_file` always returned normally afterward, and `note-watcher process --all` never checked for errors, so the CLI (and the GitHub Action step running it) always exited 0 even when an agent timed out.
  Fix — `process_file` now catches `subprocess.TimeoutExpired` specifically (still writing the `@error` marker, still processing every other instruction in the file — "never abort the others" is preserved), and after the loop raises a new `AgentTimeoutError` carrying the processed count if any instruction timed out. The CLI's `process` command catches `AgentTimeoutError` per-file so later files still get processed, then calls `sys.exit(1)` once all files are done if any timeout occurred. The daemon (`start_watcher`) catches and logs `AgentTimeoutError` instead of letting it escape the debounce-timer thread, since there's no exit code to fail in watch mode. Verified end-to-end via the real CLI with a `command` agent (`sleep 2`, `timeout: 1`): exit code is non-zero, the `@error` marker names the timeout, and a second file after the timed-out one still gets processed and marked `@done`.

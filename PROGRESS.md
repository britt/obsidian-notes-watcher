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

# Design: Handle Multiple Agent Invocations in a Single Run

Date: 2026-06-15
Status: Approved, ready for implementation plan

## Problem

When a note contains more than one `@agent` instruction, the processor can stop
after the first one and abandon the rest.

Commit #26 ("write @done marker even when agent removes the instruction line")
fixed the case where a self-editing command agent deletes its own instruction
line: a sentinel is now written in place of the instruction *before* dispatch,
and the result is anchored on the sentinel afterward. Verified — a note with two
mentions processed by a line-deleting agent now yields 2 done markers.

Two failure modes remain (both confirmed by reproduction):

1. **A failing instruction aborts the whole loop.** In `process_file_reparse`,
   both `UnknownAgentError` and any generic `Exception` call `restore_instruction`
   and then `break`. A note with `@ghost ...` (unknown) followed by `@echo ...`
   (valid) processes 0 instructions — the valid one is never dispatched.

2. **Siblings are exposed raw to the running agent.** Instructions are claimed one
   at a time, so while the agent runs for instruction 1, instructions 2..N are
   still raw `@agent` lines in the note. A whole-note-reading agent (e.g. Claude
   Code) can act on or clobber them before the processor reaches them.

Two latent issues also need addressing for robustness:

3. **Duplicate instructions collide.** The #26 sentinel has no unique id, so two
   identical instructions (`@echo hi` twice) produce identical sentinels; results
   can be swapped or mis-matched on finalize.

4. **No crash recovery.** A run that dies mid-dispatch leaves a sentinel that the
   parser ignores forever, stranding that instruction.

## Approach: claim-all-then-dispatch

Invert the model. Instead of dispatch-then-find-the-line, **claim every
instruction up front** (replace each with a note-watcher-owned sentinel), then
dispatch each claimed item over a fixed list. The sentinel is the stable anchor,
immune to however the agent rewrites the surrounding note.

This reuses #26's primitives (`write_pending`, `finalize_result`,
`finalize_error`, `restore_instruction`, `_replace_line`) and changes how they
are orchestrated.

### Sentinel format (add a unique token)

```
<!-- note-watcher: processing [ab12cd34] @agent instruction text -->
```

`ab12cd34` is `uuid.uuid4().hex[:8]`. The token disambiguates duplicate
instruction texts and lets finalize locate the exact sentinel regardless of line
shifts. Single line, parser-neutral, invisible in rendered markdown.

### `process_file` flow (renamed from `process_file_reparse`)

1. Read the file content.
2. **Recover** stale sentinels from a crashed prior run: a new parser pattern
   extracts `(token, agent, text)` from any `<!-- note-watcher: processing ... -->`
   lines. These are already-claimed work items.
3. **Parse** fresh `@agent` instructions (existing `parse_instructions`).
4. **Claim pass.** For each fresh instruction:
   - If its agent is not configured, leave the raw line untouched and log a
     warning (preserves Verification Scenario 2). Do not claim it.
   - Otherwise generate a token and call `write_pending(...)` to replace the line
     with a sentinel. Collect `(token, instruction, sentinel)`.
   - Line numbers stay valid through the pass: one line in, one line out.
5. **Dispatch loop** over `recovered + claimed`, **never breaking**:
   - Success → `finalize_result` (swaps sentinel for `@done`, appends at EOF if
     the agent removed it). `processed += 1`.
   - `AuthFailureError` → `finalize_error` with the Arcade re-auth message.
     `processed += 1`.
   - Any other `Exception` → `finalize_error` with the error text, then
     `continue`. Recorded visibly as `@error`; not silently retried forever.
6. Return `processed`.

Because the loop iterates a fixed captured list (no re-parse, no re-pick of
`[0]`), every item is processed exactly once and there is no infinite-loop risk.

### Decisions (confirmed)

- **(a) Generic dispatch error → write `@error`** and continue. Consistent with
  the existing auth-failure path; visible; no infinite retry.
- **(b) Crash recovery → included.** Stale sentinels are re-dispatched on the
  next run. Trade-off: an instruction that crashed mid-dispatch may re-run its
  side effects. Accepted for robustness; agents should be roughly idempotent.
- **(c) Rename the function** `process_file_reparse` → `process_file`. Update the
  daemon callback in `start_watcher` and `cli.py`. Keep `watcher.py` named as-is
  so the `watcher.py` ↔ `test_watcher.py` mapping holds.

### System prompt hardening

Update `DEFAULT_SYSTEM_PROMPT` in `dispatcher.py` to instruct agents to leave
`<!-- ... -->` HTML comment markers intact. Reduces the residual risk that an
agent deletes a sentinel for a sibling instruction (which would force the EOF
append fallback).

## Component changes

- **`parser.py`**
  - Add `PENDING_PATTERN` matching the tokened sentinel.
  - Add `parse_pending(content) -> list[...]` returning `(token, agent, text)` for
    recovery.
  - Confirm `parse_instructions` continues to skip sentinel lines (it already
    does — they start with `<!--`, not `@`).

- **`writer.py`**
  - `format_pending(agent, text, token)` — add the `[token]` segment.
  - `write_pending(...)` — accept/generate a token, return `(sentinel, token)` (or
    keep returning the sentinel string, which already embeds the token).
  - `finalize_result` / `finalize_error` already anchor on the sentinel string;
    no change beyond the new format flowing through.

- **`watcher.py`**
  - Rename `process_file_reparse` → `process_file`; rewrite as claim-all-then-
    dispatch with recovery; never break. Update `start_watcher`'s callback.
  - Add a small helper to check whether an agent is configured
    (`dispatcher.config.agents`).

- **`dispatcher.py`**
  - Harden `DEFAULT_SYSTEM_PROMPT`.

- **`cli.py`**
  - Call `process_file` instead of `process_file_reparse`.

## Testing (TDD — RED first)

- **parser**: sentinel with token is not parsed as an instruction; `parse_pending`
  extracts `(token, agent, text)` from one and from multiple sentinels.
- **writer**: `format_pending` includes the token; round-trip pending → finalize
  locates by the tokened sentinel; duplicate identical instructions get distinct
  tokens and finalize to the correct positions.
- **watcher** (`process_file`):
  - Unknown agent before a valid one → the valid one is still processed; unknown
    left raw. (Regression for Case 2.)
  - Generic dispatch error mid-list → `@error` written, later instructions still
    processed.
  - Two mentions, self-editing agent → both `@done` (regression for #26 / #24,
    still green).
  - Sibling protection: agent that would consume a raw `@agent` line cannot,
    because siblings are sentinels during dispatch.
  - Crash recovery: a file pre-seeded with a stale sentinel is re-dispatched to
    `@done`.
  - Idempotency: a fully processed file yields 0 on a second run.
- **integration**: end-to-end multi-mention run via the `process` command path.

Coverage must stay >= 90% lines / 85% branches per project rules.

## Out of scope

- Parallel dispatch of instructions (kept sequential).
- Cross-file ordering changes.
- Changing the `@done` / `@error` block format.

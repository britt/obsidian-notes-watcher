# Verification Plan

## Prerequisites

- Python 3.10+ installed
- Project installed in dev mode: `pip install -e ".[dev]"`
- A test Obsidian vault (or any directory with markdown files) backed by Git
- A config.yml pointing to the test vault with at least one agent configured (e.g., `echo` type)

## Scenarios

### Scenario 1: Basic @ Mention Processing

**Context**: A test vault with a markdown note containing an unprocessed `@` instruction. The vault is a Git repository with a clean working tree.

**Steps**:
1. Create a markdown file in the test vault with the content: `@echo hello world`
2. Run `note-watcher process --all --vault /path/to/test-vault --config /path/to/config.yml`
3. Read the markdown file after processing

**Success Criteria**:
- [ ] The `@echo hello world` instruction is replaced with a `<!-- @done echo: hello world ... /@done -->` completion marker
- [ ] The agent response is included inside the completion marker
- [ ] The change is committed to Git

**If Blocked**: Ask developer for help with config or vault setup.

### Scenario 2: Unknown Agent Handling

**Context**: A test vault with a markdown note referencing a non-existent agent.

**Steps**:
1. Create a markdown file in the test vault with the content: `@nonexistent do something`
2. Run `note-watcher process --all --vault /path/to/test-vault --config /path/to/config.yml`
3. Check logs and the markdown file after processing

**Success Criteria**:
- [ ] The application does not crash
- [ ] An error is logged indicating the agent is unknown
- [ ] The original note content is not corrupted (the `@nonexistent` instruction remains or is marked as failed)

**If Blocked**: Check error handling in dispatcher.py for `UnknownAgentError`.

### Scenario 3: Daemon Mode (Real-Time Watching)

**Context**: A test vault with the daemon running. The vault is a Git repository.

**Steps**:
1. Start the daemon: `note-watcher watch --vault /path/to/test-vault --config /path/to/config.yml`
2. Create or edit a markdown file in the vault, adding `@echo live test`
3. Wait for the debounce period (default 1 second) plus processing time
4. Read the file to check for the completion marker
5. Stop the daemon with Ctrl+C

**Success Criteria**:
- [ ] The daemon starts without errors
- [ ] The `@echo live test` instruction is detected and processed automatically
- [ ] The completion marker replaces the instruction
- [ ] The daemon shuts down cleanly on SIGINT

**If Blocked**: Check watcher.py and ensure watchdog is detecting file system events correctly.

### Scenario 4: Ignore Patterns

**Context**: A test vault with ignore patterns configured (e.g., `*.excalidraw.md`).

**Steps**:
1. Configure `ignore_patterns` in config.yml to include `"*.excalidraw.md"`
2. Create a file named `test.excalidraw.md` in the vault with the content: `@echo should be ignored`
3. Run `note-watcher process --all --vault /path/to/test-vault --config /path/to/config.yml`
4. Read the file after processing

**Success Criteria**:
- [ ] The `@echo should be ignored` instruction is NOT processed
- [ ] The file remains unchanged
- [ ] No errors are logged for the ignored file

**If Blocked**: Check config.py for ignore pattern handling.

### Scenario 5: Multiple @ Mentions All Get Commented Out (Issue #24)

**Context**: A test vault with a markdown note containing two or more `@` instructions in the same file. The vault is a Git repository with a clean working tree. At least one agent is a `command` type that modifies the file during processing (e.g., a Claude Code agent). If no command agent is available, use `echo` to verify the basic multi-mention flow.

**Steps**:
1. Create a markdown file in the test vault with this content:
   ```
   # Weekly Review

   @echo reformat the meetings column

   Some notes between instructions.

   @echo summarize the review section
   ```
2. Run `note-watcher process --all --vault /path/to/test-vault --config /path/to/config.yml`
3. Read the markdown file after processing

**Success Criteria**:
- [ ] Both `@echo` instructions are replaced with `<!-- @done echo: ... /@done -->` completion markers
- [ ] The file contains exactly 2 `<!-- @done` markers and 2 `/@done -->` markers
- [ ] The text between the instructions ("Some notes between instructions.") is preserved outside both @done blocks
- [ ] No instructions remain as raw `@echo` lines
- [ ] Running the command a second time processes 0 instructions (idempotent)

**If Blocked**: Check writer.py `_replace_instruction_line` — the fix uses text-based search instead of line-number matching.

### Scenario 6: Multiple @ Mentions With File-Modifying Agent (Issue #24 exact scenario)

**Context**: A test vault with a `command`-type agent configured that modifies the note file during dispatch (e.g., a Claude Code agent with a system prompt telling it to edit the note). This is the exact scenario from issue #24.

**Steps**:
1. Configure a command agent in config.yml that modifies the note file during processing. For example, a shell script that prepends a line to the file:
   ```yaml
   agents:
     modifier:
       type: command
       command: |
         FILE="$NOTE_WATCHER_FILE_PATH"
         sed -i '' '1i\
         <!-- agent modified this file -->' "$FILE"
         echo "Done modifying"
   ```
2. Create a markdown file with:
   ```
   @modifier first task
   @modifier second task
   ```
3. Run `note-watcher process --all --vault /path/to/test-vault --config /path/to/config.yml`
4. Read the markdown file after processing

**Success Criteria**:
- [ ] Both instructions are wrapped in `<!-- @done modifier: ... /@done -->` markers
- [ ] The file contains exactly 2 `<!-- @done` markers and 2 `/@done -->` markers
- [ ] The agent's file modifications are preserved (e.g., the prepended comment lines exist)
- [ ] Running the command a second time processes 0 instructions (no double-processing)
- [ ] The application does not crash or log errors about line numbers changing

**If Blocked**: Verify the command agent actually modifies the file during dispatch. Check that `_replace_instruction_line` falls back to text-based search when line numbers shift.

## Verification Rules

- Never use mocks or fakes
- Test environments must be fully running copies of real systems
- If any success criterion fails, verification fails
- Ask developer for help if blocked, don't guess

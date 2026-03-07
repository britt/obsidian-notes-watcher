# CLAUDE.md

## Project Overview

**Note Watcher**: A tool that detects `@` mentions in Obsidian markdown notes stored in Git and dispatches instructions to configured agents -- like Claude Code -- that can read, modify, and reorganize your notes directly.

### Problem

Obsidian users want to trigger AI agents from within their notes without leaving the editor. Existing solutions don't integrate with Git-backed vaults or allow agents to modify files directly.

### Approach

Watch for `@agent_name` instructions in markdown files, dispatch to the named agent, and replace the instruction with a completion marker. The agent's changes are committed back to Git. Supports real-time daemon mode (macOS LaunchAgent) and one-shot GitHub Action mode.

## Tech Stack

- **Language**: Python 3.10+
- **Package Manager**: pip / setuptools
- **Testing**: pytest + pytest-cov
- **Linting**: Ruff
- **Build**: setuptools + wheel
- **Key Libraries**: watchdog, pyyaml, click, pdoc (dev)

## Test File Structure

For every production file, there must be a corresponding test file:
- `note_watcher/config.py` -> `tests/test_config.py`
- `note_watcher/dispatcher.py` -> `tests/test_dispatcher.py`
- `note_watcher/watcher.py` -> `tests/test_watcher.py`

## Commands

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=note_watcher

# Lint
ruff check .

# Format
ruff format .

# Build docs
pdoc note_watcher -o docs
```

## ABSOLUTE RULES - NO EXCEPTIONS

### 1. Test-Driven Development is MANDATORY

**The Iron Law**: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST

Every single line of production code MUST follow this cycle:
1. **RED**: Write failing test FIRST
2. **Verify RED**: Run test, watch it fail for the RIGHT reason
3. **GREEN**: Write MINIMAL code to pass the test
4. **Verify GREEN**: Run test, confirm it passes
5. **REFACTOR**: Clean up with tests staying green

### 2. Violations = Delete and Start Over

If ANY of these occur, you MUST delete the code and start over:
- Wrote production code before test -> DELETE CODE, START OVER
- Test passed immediately -> TEST IS WRONG, FIX TEST FIRST
- Can't explain why test failed -> NOT TDD, START OVER
- "I'll add tests later" -> DELETE CODE NOW
- "Just this once without tests" -> NO. DELETE CODE.
- "It's too simple to test" -> NO. TEST FIRST.
- "Tests after achieve same goal" -> NO. DELETE CODE.

### 3. Test Coverage Requirements

- **Minimum 90%** coverage on ALL metrics:
  - Lines: 90%+
  - Functions: 90%+
  - Branches: 85%+
  - Statements: 90%+
- Coverage below threshold = Implementation incomplete
- Untested code = Code that shouldn't exist

### 4. Before Writing ANY Code

Ask yourself:
1. Did I write a failing test for this?
2. Did I run the test and see it fail?
3. Did it fail for the expected reason?

If ANY answer is "no" -> STOP. Write the test first.

### 5. Task Completion Requirements

**MANDATORY RULE**: NO TASK IS COMPLETE until:
- ALL tests pass (100% green)
- Build succeeds with ZERO errors
- NO linter errors or warnings
- Coverage meets minimum thresholds (90%+)
- Progress documented in PROGRESS.md

A task with failing tests, build errors, or linter warnings is INCOMPLETE. Period.

### 6. Progress Documentation

**MANDATORY RULE**: YOU MUST REPORT YOUR PROGRESS IN `PROGRESS.md`

After completing EACH task:
1. Create `PROGRESS.md` if it doesn't exist
2. Document:
   - Task completed
   - Tests written/passed
   - Coverage achieved
   - Any issues encountered
   - Timestamp

Format:
```markdown
## Task X: [Name] - [COMPLETE/IN PROGRESS]
- Started: [timestamp]
- Tests: X passing, 0 failing
- Coverage: Lines: X%, Functions: X%, Branches: X%, Statements: X%
- Build: Successful / Failed
- Linting: Clean / X errors
- Completed: [timestamp]
- Notes: [any relevant notes]
```

## Git Commit Rules

**COMMIT EARLY, COMMIT OFTEN** - This is mandatory.

- Commit after every successful TDD cycle (RED-GREEN-REFACTOR)
- Commit after completing any discrete unit of work
- Commit before switching context or taking breaks
- Never have more than 30 minutes of uncommitted work
- Each commit should be atomic: one logical change per commit

Why this matters:
- Small commits are easier to review and revert
- Frequent commits prevent loss of work
- Atomic commits make git history useful for debugging
- Regular commits force you to think in small, testable increments

### Branching Strategy

- Feature branches off `main`
- Branch naming convention: `<type>/<description>`
  - `feature/add-new-agent-type`
  - `fix/broken-dispatch`
  - `chore/update-deps`
  - `docs/add-api-reference`

### Commit Message Format

```
type(scope): brief description

- RED: What tests were written first
- GREEN: What minimal code was added
- Status: X tests passing, build successful
- Coverage: X% (if applicable)
```

## Development Workflow

For EACH feature/function:

```
1. Write test file or add test case
2. Run: pytest
3. See RED (test fails)
4. Understand WHY it fails
5. Write minimal production code
6. Run: pytest
7. See GREEN (test passes)
8. Refactor if needed
9. Run: pytest (stays green)
10. Check coverage: pytest --cov=note_watcher
11. Repeat for next feature
```

## Red Flags - STOP Immediately

If you catch yourself:
- Opening a code file before a test file
- Writing function implementation before test
- Thinking "I know this works"
- Copying code from examples without tests
- Skipping test runs
- Ignoring failing tests
- Writing multiple features before testing

**STOP. DELETE. START WITH TEST.**

## Verification

See @VERIFICATION_PLAN.md for acceptance testing procedures.

"""File watcher that monitors an Obsidian vault for changes to .md files.

Uses watchdog to detect file modifications, applies debouncing, and triggers
the parse → dispatch → write pipeline for each changed file.
"""

from __future__ import annotations

import fnmatch
import logging
import signal
import time
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from note_watcher.debouncer import Debouncer
from note_watcher.dispatcher import AgentDispatcher, UnknownAgentError
from note_watcher.parser import Instruction, parse_instructions, parse_pending
from note_watcher.result_validator import AuthFailureError
from note_watcher.writer import (
    finalize_error,
    finalize_result,
    format_pending,
    write_pending,
)

AUTH_ERROR_MESSAGE = (
    "Arcade authorization required. Re-run scripts/authorize_arcade.py "
    "to refresh tokens."
)

if TYPE_CHECKING:
    from note_watcher.config import Config

logger = logging.getLogger(__name__)


class NoteEventHandler(FileSystemEventHandler):
    """Handles file system events for .md files in the vault."""

    def __init__(self, debouncer: Debouncer, ignore_patterns: list[str]) -> None:
        """Initialize the event handler.

        Args:
            debouncer: Debouncer instance to throttle rapid file changes.
            ignore_patterns: Glob patterns for files to skip.
        """
        super().__init__()
        self.debouncer = debouncer
        self.ignore_patterns = ignore_patterns

    def on_modified(self, event: FileModifiedEvent) -> None:  # type: ignore[override]
        """Handle a file modification event.

        Filters for .md files not matching ignore patterns, then triggers
        the debouncer for further processing.

        Args:
            event: The file system event from watchdog.
        """
        if event.is_directory:
            return

        src_path = str(event.src_path)

        # Only process .md files
        if not src_path.endswith(".md"):
            return

        # Check ignore patterns
        if self._should_ignore(src_path):
            logger.debug("Ignoring %s (matches ignore pattern)", src_path)
            return

        logger.info("Detected change: %s", src_path)
        self.debouncer.trigger(src_path)

    def _should_ignore(self, file_path: str) -> bool:
        """Check if a file matches any of the ignore patterns."""
        path = Path(file_path)
        for pattern in self.ignore_patterns:
            # Check against the filename and the full path
            if fnmatch.fnmatch(path.name, pattern):
                return True
            if fnmatch.fnmatch(str(path), pattern):
                return True
        return False


def _claim_instructions(
    file_path: str, dispatcher: AgentDispatcher, instructions: list[Instruction]
) -> list[tuple[str, Instruction]]:
    """Replace each instruction line with a sentinel before any dispatch.

    Claiming every instruction up front means that while one agent runs, the
    others are already parser-neutral sentinels rather than raw ``@agent`` lines
    a whole-note-editing agent could act on or clobber.

    Instructions whose agent is not configured are left untouched (no sentinel)
    so the original line remains for the user; they are logged and skipped.

    Returns:
        A list of ``(sentinel, instruction)`` pairs for the claimed work.
    """
    claimed: list[tuple[str, Instruction]] = []
    for instruction in instructions:
        if instruction.agent_name not in dispatcher.config.agents:
            logger.warning(
                "Unknown agent @%s — leaving instruction for later",
                instruction.agent_name,
            )
            continue
        try:
            sentinel = write_pending(file_path, instruction)
        except Exception as e:
            logger.error(
                "Could not claim instruction @%s: %s", instruction.agent_name, e
            )
            continue
        claimed.append((sentinel, instruction))
    return claimed


def process_file(file_path: str, dispatcher: AgentDispatcher) -> int:
    """Process every @ mention instruction in a file in a single run.

    The flow is claim-all-then-dispatch:

    1. Recover any stale sentinels left by a crashed prior run.
    2. Parse fresh instructions and claim each one (replace its line with a
       sentinel) before dispatching anything.
    3. Dispatch each claimed item, swapping its sentinel for a @done/@error
       marker. A failure on one instruction never aborts the others.

    Args:
        file_path: Path to the markdown file to process.
        dispatcher: The agent dispatcher to use.

    Returns:
        Number of instructions processed (including those recorded as errors).
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning("File no longer exists: %s", file_path)
        return 0

    content = path.read_text()

    # Recover sentinels from a previous run that crashed mid-dispatch. These are
    # already claimed; reconstruct their exact sentinel line to anchor on.
    worklist: list[tuple[str, Instruction]] = [
        (
            format_pending(p.agent_name, p.instruction_text, p.token),
            Instruction(
                agent_name=p.agent_name,
                instruction_text=p.instruction_text,
                line_number=p.line_number,
                original_text=p.original_text,
            ),
        )
        for p in parse_pending(content)
    ]

    # Claim fresh instructions, then process recovered + freshly claimed work.
    worklist += _claim_instructions(
        file_path, dispatcher, parse_instructions(content)
    )

    processed = 0
    for sentinel, instruction in worklist:
        logger.info(
            "Dispatching @%s: %s",
            instruction.agent_name,
            instruction.instruction_text[:50],
        )
        try:
            result = dispatcher.dispatch(instruction, file_path=file_path)
            finalize_result(file_path, sentinel, instruction, result)
            logger.info("Wrote result for @%s", instruction.agent_name)
        except AuthFailureError:
            logger.warning(
                "Auth failure for @%s: writing error marker",
                instruction.agent_name,
            )
            finalize_error(file_path, sentinel, instruction, AUTH_ERROR_MESSAGE)
        except UnknownAgentError as e:
            # Only reachable for recovered sentinels whose agent is no longer
            # configured (fresh unknown agents are filtered before claiming).
            logger.warning("Unknown agent for recovered instruction: %s", e)
            finalize_error(
                file_path,
                sentinel,
                instruction,
                f"Unknown agent: {instruction.agent_name!r}",
            )
        except Exception as e:
            logger.error("Error processing @%s: %s", instruction.agent_name, e)
            finalize_error(
                file_path, sentinel, instruction, f"Unexpected error: {e}"
            )
        processed += 1

    return processed


def start_watcher(config: Config) -> None:
    """Start the file watcher daemon.

    Watches the configured vault directory for .md file changes,
    processes them through the parse → dispatch → write pipeline.

    Handles SIGTERM and SIGINT for graceful shutdown.

    Args:
        config: Application configuration.
    """
    dispatcher = AgentDispatcher(config)

    def on_file_changed(file_path: str) -> None:
        process_file(file_path, dispatcher)

    debouncer = Debouncer(
        interval=config.debounce_seconds,
        callback=on_file_changed,
    )

    handler = NoteEventHandler(
        debouncer=debouncer,
        ignore_patterns=config.ignore_patterns,
    )

    observer = Observer()
    observer.schedule(handler, str(config.vault), recursive=True)

    # Signal handling for graceful shutdown
    shutdown_event = False

    def handle_signal(signum: int, frame: object) -> None:
        nonlocal shutdown_event
        logger.info("Received signal %d, shutting down...", signum)
        shutdown_event = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("Starting watcher on vault: %s", config.vault)
    observer.start()

    try:
        while not shutdown_event:
            time.sleep(0.5)
    finally:
        logger.info("Stopping watcher...")
        debouncer.cancel_all()
        observer.stop()
        observer.join(timeout=5)
        logger.info("Watcher stopped.")

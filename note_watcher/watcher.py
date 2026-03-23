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
from note_watcher.parser import parse_instructions
from note_watcher.result_validator import AuthFailureError
from note_watcher.writer import write_error, write_result

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


def process_file_reparse(file_path: str, dispatcher: AgentDispatcher) -> int:
    """Parse a file, dispatch instructions one at a time, re-parsing after each.

    This handles the line-number shift problem by re-parsing after each write.

    Args:
        file_path: Path to the markdown file to process.
        dispatcher: The agent dispatcher to use.

    Returns:
        Number of instructions processed.
    """
    path = Path(file_path)
    processed = 0

    while True:
        if not path.exists():
            logger.warning("File no longer exists: %s", file_path)
            break

        content = path.read_text()
        instructions = parse_instructions(content)

        if not instructions:
            break

        instruction = instructions[0]
        try:
            logger.info(
                "Dispatching @%s: %s",
                instruction.agent_name,
                instruction.instruction_text[:50],
            )
            result = dispatcher.dispatch(instruction, file_path=file_path)
            write_result(file_path, instruction, result)
            processed += 1
            logger.info("Wrote result for @%s", instruction.agent_name)
        except AuthFailureError:
            logger.warning(
                "Auth failure for @%s: writing error marker",
                instruction.agent_name,
            )
            write_error(
                file_path,
                instruction,
                "Arcade authorization required. Re-run scripts/authorize_arcade.py "
                "to refresh tokens.",
            )
            processed += 1
        except UnknownAgentError as e:
            logger.warning("Skipping unknown agent: %s", e)
            break
        except Exception as e:
            logger.error("Error processing instruction: %s", e)
            break

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
        process_file_reparse(file_path, dispatcher)

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

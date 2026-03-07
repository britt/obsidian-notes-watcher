"""Tests for the file watcher module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from note_watcher.config import AgentConfig, Config
from note_watcher.dispatcher import AgentDispatcher
from note_watcher.watcher import NoteEventHandler, process_file_reparse


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        vault=tmp_path,
        agents={
            "echo": AgentConfig(name="echo", type="echo"),
            "uppercase": AgentConfig(name="uppercase", type="uppercase"),
        },
    )


@pytest.fixture
def dispatcher(config: Config) -> AgentDispatcher:
    return AgentDispatcher(config)


class TestNoteEventHandler:
    """Tests for NoteEventHandler."""

    def test_ignores_non_md_files(self) -> None:
        debouncer = MagicMock()
        handler = NoteEventHandler(debouncer=debouncer, ignore_patterns=[])

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/vault/file.txt"

        handler.on_modified(event)
        debouncer.trigger.assert_not_called()

    def test_ignores_directories(self) -> None:
        debouncer = MagicMock()
        handler = NoteEventHandler(debouncer=debouncer, ignore_patterns=[])

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/vault/subdir"

        handler.on_modified(event)
        debouncer.trigger.assert_not_called()

    def test_triggers_for_md_files(self) -> None:
        debouncer = MagicMock()
        handler = NoteEventHandler(debouncer=debouncer, ignore_patterns=[])

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/vault/note.md"

        handler.on_modified(event)
        debouncer.trigger.assert_called_once_with("/vault/note.md")

    def test_ignores_excalidraw_files(self) -> None:
        debouncer = MagicMock()
        handler = NoteEventHandler(
            debouncer=debouncer,
            ignore_patterns=["*.excalidraw.md"],
        )

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/vault/drawing.excalidraw.md"

        handler.on_modified(event)
        debouncer.trigger.assert_not_called()


class TestProcessFileReparse:
    """Tests for process_file_reparse()."""

    def test_processes_single_instruction(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        note = tmp_path / "note.md"
        note.write_text("# Title\n\n@echo Hello world\n")

        count = process_file_reparse(str(note), dispatcher)
        assert count == 1

        content = note.read_text()
        assert "<!-- @done echo: Hello world" in content
        assert "Hello world" in content
        assert "/@done -->" in content
        assert "@echo Hello world" not in content

    def test_processes_multiple_instructions(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        note = tmp_path / "note.md"
        note.write_text(
            "@echo First instruction\n"
            "\n"
            "@uppercase Second instruction\n"
        )

        count = process_file_reparse(str(note), dispatcher)
        assert count == 2

        content = note.read_text()
        assert "First instruction" in content
        assert "SECOND INSTRUCTION" in content
        # Both should be wrapped in done markers
        assert content.count("<!-- @done") == 2
        assert content.count("/@done -->") == 2

    def test_skips_already_processed(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        note = tmp_path / "note.md"
        note.write_text(
            "<!-- @done echo: Previous task\n"
            "Already done\n"
            "/@done -->\n"
            "\n"
            "@uppercase Process me\n"
        )

        count = process_file_reparse(str(note), dispatcher)
        assert count == 1

        content = note.read_text()
        assert "PROCESS ME" in content
        # Original done block should still be there
        assert "Already done" in content

    def test_handles_nonexistent_file(self, dispatcher: AgentDispatcher) -> None:
        count = process_file_reparse("/nonexistent/file.md", dispatcher)
        assert count == 0

    def test_handles_no_instructions(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        note = tmp_path / "note.md"
        note.write_text("# Just a note\n\nNo instructions here.\n")

        count = process_file_reparse(str(note), dispatcher)
        assert count == 0

    def test_passes_file_path_to_dispatcher(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """process_file_reparse passes the file path to dispatch()."""
        note = tmp_path / "note.md"
        note.write_text("@echo test\n")

        with patch.object(
            dispatcher, "dispatch", wraps=dispatcher.dispatch
        ) as mock_dispatch:
            process_file_reparse(str(note), dispatcher)
            mock_dispatch.assert_called_once()
            _, kwargs = mock_dispatch.call_args
            assert kwargs.get("file_path") == str(note)

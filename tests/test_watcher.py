"""Tests for the file watcher module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from note_watcher.config import AgentConfig, Config
from note_watcher.dispatcher import AgentDispatcher
from note_watcher.parser import parse_instructions
from note_watcher.result_validator import AuthFailureError
from note_watcher.watcher import NoteEventHandler, process_file


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


class TestProcessFile:
    """Tests for process_file()."""

    def test_processes_single_instruction(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        note = tmp_path / "note.md"
        note.write_text("# Title\n\n@echo Hello world\n")

        count = process_file(str(note), dispatcher)
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

        count = process_file(str(note), dispatcher)
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

        count = process_file(str(note), dispatcher)
        assert count == 1

        content = note.read_text()
        assert "PROCESS ME" in content
        # Original done block should still be there
        assert "Already done" in content

    def test_handles_nonexistent_file(self, dispatcher: AgentDispatcher) -> None:
        count = process_file("/nonexistent/file.md", dispatcher)
        assert count == 0

    def test_handles_no_instructions(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        note = tmp_path / "note.md"
        note.write_text("# Just a note\n\nNo instructions here.\n")

        count = process_file(str(note), dispatcher)
        assert count == 0

    def test_passes_file_path_to_dispatcher(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """process_file passes the file path to dispatch()."""
        note = tmp_path / "note.md"
        note.write_text("@echo test\n")

        with patch.object(
            dispatcher, "dispatch", wraps=dispatcher.dispatch
        ) as mock_dispatch:
            process_file(str(note), dispatcher)
            mock_dispatch.assert_called_once()
            _, kwargs = mock_dispatch.call_args
            assert kwargs.get("file_path") == str(note)

    def test_auth_failure_writes_error_marker(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """When dispatch raises AuthFailureError, an @error marker is written."""
        note = tmp_path / "note.md"
        note.write_text("@echo Check my calendar\n")

        with patch.object(
            dispatcher,
            "dispatch",
            side_effect=AuthFailureError("Visit https://cloud.arcade.dev/auth"),
        ):
            count = process_file(str(note), dispatcher)

        assert count == 1
        content = note.read_text()
        assert "<!-- @error echo: Check my calendar" in content
        assert "/@error -->" in content
        assert "<!-- @done" not in content

    def test_auth_failure_continues_processing(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """After an auth failure, processing continues to the next instruction."""
        note = tmp_path / "note.md"
        note.write_text("@echo First task\n\n@echo Second task\n")

        call_count = 0
        original_dispatch = dispatcher.dispatch

        def side_effect(instruction, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AuthFailureError("auth url here")
            return original_dispatch(instruction, **kwargs)

        with patch.object(dispatcher, "dispatch", side_effect=side_effect):
            count = process_file(str(note), dispatcher)

        assert count == 2
        content = note.read_text()
        assert "<!-- @error echo: First task" in content
        assert "<!-- @done echo: Second task" in content

    def test_unknown_agent_leaves_instruction_for_retry(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """Unknown agents leave the instruction intact (no sentinel/marker)."""
        note = tmp_path / "note.md"
        note.write_text("# Title\n\n@nonexistent do a thing\n")

        count = process_file(str(note), dispatcher)

        assert count == 0
        content = note.read_text()
        assert "@nonexistent do a thing" in content
        assert "note-watcher: processing" not in content
        assert "<!-- @done" not in content

    def test_dispatch_error_writes_error_marker(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """An unexpected dispatch error is recorded as an @error marker."""
        note = tmp_path / "note.md"
        note.write_text("@echo do a thing\n")

        with patch.object(dispatcher, "dispatch", side_effect=RuntimeError("boom")):
            count = process_file(str(note), dispatcher)

        assert count == 1
        content = note.read_text()
        assert "<!-- @error echo: do a thing" in content
        assert "boom" in content
        assert "note-watcher: processing" not in content
        assert "@echo do a thing" not in content

    def test_pending_write_failure_skips_instruction(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """If the sentinel can't be written, that instruction is skipped."""
        note = tmp_path / "note.md"
        note.write_text("@echo do a thing\n")

        with patch(
            "note_watcher.watcher.write_pending",
            side_effect=ValueError("cannot write"),
        ):
            count = process_file(str(note), dispatcher)

        assert count == 0

    def test_unknown_agent_does_not_abort_later_valid_instructions(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """An unknown agent before a valid one must not abort the valid one."""
        note = tmp_path / "note.md"
        note.write_text("@nonexistent do something\n\n@echo hello world\n")

        count = process_file(str(note), dispatcher)

        assert count == 1
        content = note.read_text()
        # The valid instruction was processed...
        assert "<!-- @done echo: hello world" in content
        # ...while the unknown agent's line is left intact for the user.
        assert "@nonexistent do something" in content

    def test_dispatch_error_does_not_abort_later_instructions(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """A generic error on one instruction must not abort the rest."""
        note = tmp_path / "note.md"
        note.write_text("@echo first\n\n@uppercase second\n")

        original_dispatch = dispatcher.dispatch

        def side_effect(instruction, **kwargs):
            if instruction.agent_name == "echo":
                raise RuntimeError("boom")
            return original_dispatch(instruction, **kwargs)

        with patch.object(dispatcher, "dispatch", side_effect=side_effect):
            count = process_file(str(note), dispatcher)

        assert count == 2
        content = note.read_text()
        assert "<!-- @error echo: first" in content
        assert "<!-- @done uppercase: second" in content

    def test_siblings_are_claimed_before_dispatch(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """While one instruction runs, siblings are sentinels, never raw @lines."""
        note = tmp_path / "note.md"
        note.write_text("@echo first\n\n@echo second\n")

        live_during_dispatch = []
        original_dispatch = dispatcher.dispatch

        def side_effect(instruction, **kwargs):
            # When any instruction runs, no raw @agent line may remain — every
            # sibling must already be a claimed sentinel the agent can't clobber.
            live_during_dispatch.append(parse_instructions(note.read_text()))
            return original_dispatch(instruction, **kwargs)

        with patch.object(dispatcher, "dispatch", side_effect=side_effect):
            process_file(str(note), dispatcher)

        assert live_during_dispatch == [[], []]

    def test_recovers_stale_pending_sentinel(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """A sentinel left by a crashed run is re-dispatched and finalized."""
        note = tmp_path / "note.md"
        note.write_text(
            "# Note\n"
            "<!-- note-watcher: processing [tok12345] @echo recovered task -->\n"
            "More text\n"
        )

        count = process_file(str(note), dispatcher)

        assert count == 1
        content = note.read_text()
        assert "<!-- @done echo: recovered task" in content
        assert "note-watcher: processing" not in content
        assert "More text" in content

    def test_recovered_sentinel_with_unknown_agent_becomes_error(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """A stale sentinel whose agent is no longer configured → @error."""
        note = tmp_path / "note.md"
        note.write_text(
            "<!-- note-watcher: processing [tok99999] @ghost vanished task -->\n"
        )

        count = process_file(str(note), dispatcher)

        assert count == 1
        content = note.read_text()
        assert "<!-- @error ghost: vanished task" in content
        assert "Unknown agent" in content
        assert "note-watcher: processing" not in content

    def test_idempotent_on_second_run(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """A fully processed file yields zero on a second run."""
        note = tmp_path / "note.md"
        note.write_text("@echo first\n\n@uppercase second\n")

        assert process_file(str(note), dispatcher) == 2
        assert process_file(str(note), dispatcher) == 0

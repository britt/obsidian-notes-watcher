"""Tests for the inline writer."""

import pytest

from note_watcher.parser import Instruction, parse_instructions
from note_watcher.writer import (
    finalize_error,
    finalize_result,
    format_error,
    format_pending,
    format_result,
    restore_instruction,
    write_error,
    write_pending,
    write_result,
)


class TestFormatResult:
    """Tests for format_result()."""

    def test_basic_format(self) -> None:
        result = format_result("summarizer", "Do something", "This is the summary.")
        assert result == (
            "<!-- @done summarizer: Do something\n"
            "This is the summary.\n"
            "/@done -->"
        )

    def test_multiline_result(self) -> None:
        result = format_result("agent", "Task", "Line 1\nLine 2\nLine 3")
        assert "Line 1\nLine 2\nLine 3" in result
        assert result.startswith("<!-- @done agent: Task")
        assert result.endswith("/@done -->")

    def test_empty_result(self) -> None:
        result = format_result("agent", "Task", "")
        assert result == "<!-- @done agent: Task\n\n/@done -->"


class TestWriteResult:
    """Tests for write_result()."""

    def test_replaces_instruction_with_result(self, tmp_path) -> None:
        note = tmp_path / "note.md"
        note.write_text("# Title\n\n@summarizer Do something\n\nMore text\n")

        instruction = Instruction(
            agent_name="summarizer",
            instruction_text="Do something",
            line_number=3,
            original_text="@summarizer Do something",
        )

        write_result(str(note), instruction, "The result")

        content = note.read_text()
        assert "@summarizer Do something" not in content
        assert "<!-- @done summarizer: Do something" in content
        assert "The result" in content
        assert "/@done -->" in content
        assert "# Title" in content
        assert "More text" in content

    def test_preserves_surrounding_content(self, tmp_path) -> None:
        note = tmp_path / "note.md"
        note.write_text("Before\n@agent Task\nAfter\n")

        instruction = Instruction(
            agent_name="agent",
            instruction_text="Task",
            line_number=2,
            original_text="@agent Task",
        )

        write_result(str(note), instruction, "Done")

        content = note.read_text()
        lines = content.split("\n")
        assert lines[0] == "Before"
        assert "<!-- @done agent: Task" in content
        assert "Done" in content
        assert "After" in lines[-2] or "After" in lines[-1]

    def test_raises_on_changed_line(self, tmp_path) -> None:
        note = tmp_path / "note.md"
        note.write_text("# Title\nDifferent content\n")

        instruction = Instruction(
            agent_name="agent",
            instruction_text="Original",
            line_number=2,
            original_text="@agent Original",
        )

        with pytest.raises(ValueError, match="not found in file"):
            write_result(str(note), instruction, "Result")

    def test_raises_on_out_of_range_line(self, tmp_path) -> None:
        note = tmp_path / "note.md"
        note.write_text("Short file\n")

        instruction = Instruction(
            agent_name="agent",
            instruction_text="Task",
            line_number=100,
            original_text="@agent Task",
        )

        with pytest.raises(ValueError, match="not found in file"):
            write_result(str(note), instruction, "Result")

    def test_write_result_with_multiline_output(self, tmp_path) -> None:
        note = tmp_path / "note.md"
        note.write_text("@agent Do it\n")

        instruction = Instruction(
            agent_name="agent",
            instruction_text="Do it",
            line_number=1,
            original_text="@agent Do it",
        )

        write_result(str(note), instruction, "Line 1\nLine 2")

        content = note.read_text()
        assert "Line 1\nLine 2" in content
        assert "@agent Do it" not in content


class TestFormatError:
    """Tests for format_error()."""

    def test_basic_error_format(self) -> None:
        result = format_error("claude", "Check calendar", "Auth required")
        assert result == (
            "<!-- @error claude: Check calendar\n"
            "Auth required\n"
            "/@error -->"
        )

    def test_multiline_error_reason(self) -> None:
        result = format_error("agent", "Task", "Line 1\nLine 2\nLine 3")
        assert "Line 1\nLine 2\nLine 3" in result
        assert result.startswith("<!-- @error agent: Task")
        assert result.endswith("/@error -->")

    def test_empty_reason(self) -> None:
        result = format_error("agent", "Task", "")
        assert result == "<!-- @error agent: Task\n\n/@error -->"


class TestWriteError:
    """Tests for write_error()."""

    def test_replaces_instruction_with_error_marker(self, tmp_path) -> None:
        note = tmp_path / "note.md"
        note.write_text("# Title\n\n@claude Check calendar\n\nMore text\n")

        instruction = Instruction(
            agent_name="claude",
            instruction_text="Check calendar",
            line_number=3,
            original_text="@claude Check calendar",
        )

        write_error(str(note), instruction, "Auth required")

        content = note.read_text()
        assert "@claude Check calendar" not in content
        assert "<!-- @error claude: Check calendar" in content
        assert "Auth required" in content
        assert "/@error -->" in content
        assert "# Title" in content
        assert "More text" in content

    def test_preserves_surrounding_content(self, tmp_path) -> None:
        note = tmp_path / "note.md"
        note.write_text("Before\n@agent Task\nAfter\n")

        instruction = Instruction(
            agent_name="agent",
            instruction_text="Task",
            line_number=2,
            original_text="@agent Task",
        )

        write_error(str(note), instruction, "Failed")

        content = note.read_text()
        lines = content.split("\n")
        assert lines[0] == "Before"
        assert "<!-- @error agent: Task" in content
        assert "After" in lines[-2] or "After" in lines[-1]

    def test_raises_on_changed_line(self, tmp_path) -> None:
        note = tmp_path / "note.md"
        note.write_text("# Title\nDifferent content\n")

        instruction = Instruction(
            agent_name="agent",
            instruction_text="Original",
            line_number=2,
            original_text="@agent Original",
        )

        with pytest.raises(ValueError, match="not found in file"):
            write_error(str(note), instruction, "Reason")


class TestReplaceInstructionAfterFileModification:
    """Tests for writing results when file has been modified
    by agent during dispatch."""

    def test_write_result_finds_instruction_after_line_shift(self, tmp_path):
        """write_result succeeds even when instruction moved to a different line."""
        note = tmp_path / "note.md"
        # Original content when parsed — instruction is on line 2
        original_content = "# Title\n@echo Hello world\nMore content\n"
        note.write_text(original_content)

        instructions = parse_instructions(original_content)
        assert len(instructions) == 1
        instruction = instructions[0]
        assert instruction.line_number == 2  # line 2 in original

        # Simulate agent modifying the file during dispatch — adds lines above
        modified_content = (
            "# Title\nAgent added this line\nAnother new line\n"
            "@echo Hello world\nMore content\n"
        )
        note.write_text(modified_content)

        # write_result should still find and replace the instruction
        write_result(str(note), instruction, "Hello world")

        final = note.read_text()
        assert "<!-- @done echo: Hello world" in final
        assert "/@done -->" in final
        assert "@echo Hello world" not in final
        # Surrounding content preserved
        assert "# Title" in final
        assert "Agent added this line" in final
        assert "More content" in final

    def test_write_result_when_instruction_no_longer_in_file(self, tmp_path):
        """write_result raises when instruction text is completely gone from file."""
        note = tmp_path / "note.md"
        original_content = "# Title\n@echo Hello world\n"
        note.write_text(original_content)

        instructions = parse_instructions(original_content)
        instruction = instructions[0]

        # Agent removed the instruction line entirely
        note.write_text("# Title\nSomething completely different\n")

        with pytest.raises(ValueError, match="not found in file"):
            write_result(str(note), instruction, "Hello world")

    def test_write_error_finds_instruction_after_line_shift(self, tmp_path):
        """write_error succeeds even when instruction moved to a different line."""
        note = tmp_path / "note.md"
        original_content = "@echo Hello world\n"
        note.write_text(original_content)

        instructions = parse_instructions(original_content)
        instruction = instructions[0]

        # Simulate line shift
        note.write_text("New first line\n@echo Hello world\n")

        write_error(str(note), instruction, "Auth required")

        final = note.read_text()
        assert "<!-- @error echo: Hello world" in final
        assert "/@error -->" in final
        assert "@echo Hello world" not in final


class TestFormatPending:
    """Tests for format_pending()."""

    def test_sentinel_is_a_single_line_comment(self) -> None:
        sentinel = format_pending("echo", "do something")
        assert sentinel == "<!-- note-watcher: processing @echo do something -->"
        assert "\n" not in sentinel

    def test_sentinel_is_not_parsed_as_instruction(self) -> None:
        """The pending sentinel must be ignored by the parser."""
        sentinel = format_pending("echo", "do something")
        assert parse_instructions(sentinel) == []


class TestPendingLifecycle:
    """Tests for write_pending / finalize_result / finalize_error / restore."""

    def _instruction(self) -> Instruction:
        return Instruction(
            agent_name="echo",
            instruction_text="Hello world",
            line_number=2,
            original_text="@echo Hello world",
        )

    def test_write_pending_replaces_instruction_with_sentinel(self, tmp_path):
        note = tmp_path / "note.md"
        note.write_text("# Title\n@echo Hello world\nMore\n")

        sentinel = write_pending(str(note), self._instruction())

        content = note.read_text()
        assert sentinel in content
        # The original instruction line is gone, and the sentinel that replaced
        # it must not be re-parsed as a live instruction.
        assert "\n@echo Hello world\n" not in content
        assert parse_instructions(content) == []

    def test_finalize_result_replaces_sentinel_in_place(self, tmp_path):
        note = tmp_path / "note.md"
        instruction = self._instruction()
        note.write_text("# Title\n@echo Hello world\nMore\n")
        sentinel = write_pending(str(note), instruction)

        finalize_result(str(note), sentinel, instruction, "THE RESULT")

        content = note.read_text()
        assert sentinel not in content
        assert "<!-- @done echo: Hello world" in content
        assert "THE RESULT" in content
        assert "/@done -->" in content
        # Result lands where the instruction was, surrounding text preserved.
        assert "# Title" in content
        assert "More" in content

    def test_finalize_result_appends_when_sentinel_removed(self, tmp_path):
        """If the agent deleted the sentinel, the result is appended, not lost."""
        note = tmp_path / "note.md"
        instruction = self._instruction()
        note.write_text("@echo Hello world\n")
        write_pending(str(note), instruction)
        sentinel = format_pending("echo", "Hello world")

        # Agent rewrote the whole file, removing the sentinel.
        note.write_text("Completely new content from the agent.\n")

        finalize_result(str(note), sentinel, instruction, "THE RESULT")

        content = note.read_text()
        assert "Completely new content from the agent." in content
        assert "<!-- @done echo: Hello world" in content
        assert "THE RESULT" in content
        assert "/@done -->" in content

    def test_finalize_error_replaces_sentinel(self, tmp_path):
        note = tmp_path / "note.md"
        instruction = self._instruction()
        note.write_text("@echo Hello world\n")
        sentinel = write_pending(str(note), instruction)

        finalize_error(str(note), sentinel, instruction, "Auth required")

        content = note.read_text()
        assert sentinel not in content
        assert "<!-- @error echo: Hello world" in content
        assert "Auth required" in content
        assert "/@error -->" in content

    def test_restore_instruction_puts_original_back(self, tmp_path):
        note = tmp_path / "note.md"
        instruction = self._instruction()
        note.write_text("@echo Hello world\n")
        sentinel = write_pending(str(note), instruction)

        restore_instruction(str(note), sentinel, instruction)

        content = note.read_text()
        assert sentinel not in content
        assert "@echo Hello world" in content

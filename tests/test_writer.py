"""Tests for the inline writer."""

import pytest

from note_watcher.parser import Instruction, parse_instructions
from note_watcher.writer import format_error, format_result, write_error, write_result


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

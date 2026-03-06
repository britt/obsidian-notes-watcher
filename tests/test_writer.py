"""Tests for the inline writer."""

import pytest

from note_watcher.parser import Instruction
from note_watcher.writer import format_result, write_result


class TestFormatResult:
    """Tests for format_result()."""

    def test_basic_format(self) -> None:
        result = format_result("summarizer", "This is the summary.")
        assert result == (
            "<!-- @done summarizer -->\n"
            "This is the summary.\n"
            "<!-- /@done -->"
        )

    def test_multiline_result(self) -> None:
        result = format_result("agent", "Line 1\nLine 2\nLine 3")
        assert "Line 1\nLine 2\nLine 3" in result
        assert result.startswith("<!-- @done agent -->")
        assert result.endswith("<!-- /@done -->")

    def test_empty_result(self) -> None:
        result = format_result("agent", "")
        assert result == "<!-- @done agent -->\n\n<!-- /@done -->"


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
        assert "<!-- @done summarizer -->" in content
        assert "The result" in content
        assert "<!-- /@done -->" in content
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
        assert "<!-- @done agent -->" in content
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

        with pytest.raises(ValueError, match="has changed"):
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

        with pytest.raises(IndexError, match="out of range"):
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

"""Tests for the @ mention parser."""

from note_watcher.parser import Instruction, parse_instructions


class TestParseInstructions:
    """Tests for parse_instructions()."""

    def test_extracts_single_instruction(self) -> None:
        content = "@summarizer Summarize this paragraph"
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].agent_name == "summarizer"
        assert instructions[0].instruction_text == "Summarize this paragraph"
        assert instructions[0].line_number == 1

    def test_extracts_multiple_instructions(self) -> None:
        content = (
            "# My Note\n"
            "\n"
            "@summarizer Summarize this\n"
            "\n"
            "Some text\n"
            "\n"
            "@uppercase Make this uppercase\n"
        )
        instructions = parse_instructions(content)
        assert len(instructions) == 2
        assert instructions[0].agent_name == "summarizer"
        assert instructions[0].line_number == 3
        assert instructions[1].agent_name == "uppercase"
        assert instructions[1].line_number == 7

    def test_skips_completed_markers(self) -> None:
        content = (
            "<!-- @done summarizer: Summarize this\n"
            "Already processed result\n"
            "/@done -->\n"
            "\n"
            "@uppercase Still pending\n"
        )
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].agent_name == "uppercase"
        assert instructions[0].instruction_text == "Still pending"

    def test_empty_content(self) -> None:
        instructions = parse_instructions("")
        assert instructions == []

    def test_no_instructions(self) -> None:
        content = "# Just a note\n\nWith some text\n"
        instructions = parse_instructions(content)
        assert instructions == []

    def test_preserves_original_text(self) -> None:
        content = "  @summarizer Summarize this  "
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].original_text == "  @summarizer Summarize this  "

    def test_agent_name_with_underscores(self) -> None:
        content = "@my_agent Do something"
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].agent_name == "my_agent"

    def test_instruction_with_special_characters(self) -> None:
        content = "@summarizer Summarize: 'this' & \"that\" (100% done!)"
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].instruction_text == "Summarize: 'this' & \"that\" (100% done!)"

    def test_skips_lines_without_space_after_agent(self) -> None:
        """@agentname with no instruction text should not match."""
        content = "@summarizer\n"
        instructions = parse_instructions(content)
        assert instructions == []

    def test_multiple_done_blocks(self) -> None:
        content = (
            "<!-- @done summarizer: Task 1\n"
            "Result 1\n"
            "/@done -->\n"
            "\n"
            "<!-- @done uppercase: Task 2\n"
            "Result 2\n"
            "/@done -->\n"
            "\n"
            "@echo Still here\n"
        )
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].agent_name == "echo"

    def test_nested_at_symbols_in_done_block(self) -> None:
        """@ mentions inside done blocks should be ignored."""
        content = (
            "<!-- @done summarizer: Summarize this\n"
            "@uppercase This is inside done block\n"
            "/@done -->\n"
        )
        instructions = parse_instructions(content)
        assert instructions == []

    def test_line_numbers_are_one_indexed(self) -> None:
        content = "line 1\nline 2\n@summarizer On line 3\n"
        instructions = parse_instructions(content)
        assert instructions[0].line_number == 3

    def test_handles_windows_line_endings_in_content(self) -> None:
        """The parser splits on \\n but content may have been normalized."""
        content = "# Note\n\n@summarizer Do this\n"
        instructions = parse_instructions(content)
        assert len(instructions) == 1

    def test_agent_name_with_trailing_colon(self) -> None:
        """@agent: should match agent name 'agent', ignoring the colon."""
        content = "@echo: hello world"
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].agent_name == "echo"
        assert instructions[0].instruction_text == "hello world"

    def test_agent_name_with_trailing_punctuation(self) -> None:
        """Trailing punctuation like comma, semicolon, period should be stripped."""
        for punct in [":", ",", ";", "."]:
            content = f"@echo{punct} hello world"
            result = parse_instructions(content)
            msg = f"Failed for punctuation: {punct}"
            assert len(result) == 1, msg
            assert result[0].agent_name == "echo", msg
            assert result[0].instruction_text == "hello world", msg

    def test_at_mention_in_middle_of_line_not_extracted(self) -> None:
        """Only @ mentions at the start of a line are extracted."""
        content = "Contact me at @summarizer for details"
        instructions = parse_instructions(content)
        # The pattern requires the @ to be at the start of the stripped line,
        # but "Contact me at @summarizer for details" doesn't start with @
        assert instructions == []

    def test_skips_error_markers(self) -> None:
        """Content inside @error blocks should be skipped."""
        content = (
            "<!-- @error claude: Do something\n"
            "Arcade authorization required.\n"
            "/@error -->\n"
            "\n"
            "@echo Still pending\n"
        )
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].agent_name == "echo"

    def test_error_and_done_blocks_coexist(self) -> None:
        """Both @done and @error blocks are skipped correctly."""
        content = (
            "<!-- @done summarizer: Task 1\n"
            "Result 1\n"
            "/@done -->\n"
            "\n"
            "<!-- @error claude: Task 2\n"
            "Auth failed\n"
            "/@error -->\n"
            "\n"
            "@echo Still here\n"
        )
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].agent_name == "echo"

    def test_nested_at_in_error_block_ignored(self) -> None:
        """@ mentions inside error blocks should be ignored."""
        content = (
            "<!-- @error claude: Check calendar\n"
            "@uppercase This is inside error block\n"
            "/@error -->\n"
        )
        instructions = parse_instructions(content)
        assert instructions == []

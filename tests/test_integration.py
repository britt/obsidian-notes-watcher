"""Integration tests for the full Note Watcher pipeline.

Tests the end-to-end flow: file content → parse → dispatch → write.
"""

from pathlib import Path

import pytest

from note_watcher.config import AgentConfig, Config
from note_watcher.dispatcher import AgentDispatcher
from note_watcher.parser import parse_instructions
from note_watcher.watcher import process_file_reparse
from note_watcher.writer import write_result


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


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_pipeline_single_instruction(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """Full flow: write file → parse → dispatch → write result."""
        note = tmp_path / "note.md"
        note.write_text(
            "# My Note\n"
            "\n"
            "Here is some context.\n"
            "\n"
            "@echo Repeat this back to me\n"
            "\n"
            "More content below.\n"
        )

        # Parse
        content = note.read_text()
        instructions = parse_instructions(content)
        assert len(instructions) == 1
        assert instructions[0].agent_name == "echo"

        # Dispatch
        result = dispatcher.dispatch(instructions[0])
        assert result == "Repeat this back to me"

        # Write
        write_result(str(note), instructions[0], result)

        # Verify final state
        final = note.read_text()
        assert "# My Note" in final
        assert "Here is some context." in final
        assert "More content below." in final
        assert "<!-- @done echo -->" in final
        assert "Repeat this back to me" in final
        assert "<!-- /@done -->" in final
        assert "@echo Repeat this back to me" not in final

    def test_full_pipeline_multiple_instructions(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """Process multiple instructions, results written correctly."""
        note = tmp_path / "note.md"
        note.write_text(
            "@echo First\n"
            "@uppercase Second\n"
        )

        count = process_file_reparse(str(note), dispatcher)
        assert count == 2

        final = note.read_text()
        assert "First" in final
        assert "SECOND" in final
        assert final.count("<!-- @done") == 2
        assert final.count("<!-- /@done -->") == 2

    def test_reprocessing_skips_completed(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """Running process twice doesn't reprocess completed instructions."""
        note = tmp_path / "note.md"
        note.write_text("@echo Process me once\n")

        # First run
        count1 = process_file_reparse(str(note), dispatcher)
        assert count1 == 1

        content_after_first = note.read_text()
        assert "<!-- @done echo -->" in content_after_first

        # Second run - should find nothing to process
        count2 = process_file_reparse(str(note), dispatcher)
        assert count2 == 0

        # Content should be unchanged after second run
        assert note.read_text() == content_after_first

    def test_mixed_completed_and_pending(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """File with both completed and pending instructions."""
        note = tmp_path / "note.md"
        note.write_text(
            "<!-- @done echo -->\n"
            "Already processed\n"
            "<!-- /@done -->\n"
            "\n"
            "@uppercase Process this new one\n"
        )

        count = process_file_reparse(str(note), dispatcher)
        assert count == 1

        final = note.read_text()
        assert "Already processed" in final
        assert "PROCESS THIS NEW ONE" in final
        assert final.count("<!-- @done") == 2

    def test_batch_process_multiple_files(
        self, tmp_path: Path, config: Config
    ) -> None:
        """Batch mode processes instructions across multiple files."""
        from click.testing import CliRunner
        from note_watcher.cli import main

        # Create multiple notes
        (tmp_path / "note1.md").write_text("@echo From file 1\n")
        (tmp_path / "note2.md").write_text("@uppercase From file 2\n")
        (tmp_path / "note3.md").write_text("# No instructions here\n")

        config_file = tmp_path / "config.yml"
        config_file.write_text(
            f"vault: {tmp_path}\n"
            "agents:\n"
            "  echo:\n"
            "    type: echo\n"
            "  uppercase:\n"
            "    type: uppercase\n"
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["process", "--all", "--vault", str(tmp_path), "--config", str(config_file)],
        )
        assert result.exit_code == 0
        assert "Processed 2 instruction" in result.output

        # Verify both files were processed
        assert "<!-- @done echo -->" in (tmp_path / "note1.md").read_text()
        assert "<!-- @done uppercase -->" in (tmp_path / "note2.md").read_text()
        # Untouched file should be unchanged
        assert (tmp_path / "note3.md").read_text() == "# No instructions here\n"

    def test_idempotent_processing(
        self, tmp_path: Path, dispatcher: AgentDispatcher
    ) -> None:
        """Processing a file multiple times is idempotent."""
        note = tmp_path / "note.md"
        note.write_text("@echo Idempotent test\n")

        # Process three times
        process_file_reparse(str(note), dispatcher)
        content1 = note.read_text()

        process_file_reparse(str(note), dispatcher)
        content2 = note.read_text()

        process_file_reparse(str(note), dispatcher)
        content3 = note.read_text()

        # All should be identical
        assert content1 == content2 == content3
        assert content1.count("<!-- @done") == 1

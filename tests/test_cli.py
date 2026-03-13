"""Tests for the CLI commands."""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from note_watcher.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestProcessCommand:
    """Tests for the 'process' CLI command."""

    def test_process_all_with_vault(self, runner: CliRunner, tmp_path: Path) -> None:
        """Process command finds and processes instructions in .md files."""
        # Create a note with an instruction
        note = tmp_path / "test.md"
        note.write_text("@uppercase hello world\n")

        # Create a minimal config
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            f"vault: {tmp_path}\n"
            "agents:\n"
            "  uppercase:\n"
            "    type: uppercase\n"
        )

        result = runner.invoke(
            main,
            ["process", "--all", "--vault", str(tmp_path), "--config", str(config_file)],
        )
        assert result.exit_code == 0
        assert "Processed 1 instruction" in result.output

        # Verify the file was updated
        content = note.read_text()
        assert "HELLO WORLD" in content
        assert "<!-- @done uppercase: hello world" in content

    def test_process_no_instructions(self, runner: CliRunner, tmp_path: Path) -> None:
        """Process command with no pending instructions."""
        note = tmp_path / "clean.md"
        note.write_text("# Just a note\n\nNo instructions here.\n")

        config_file = tmp_path / "config.yml"
        config_file.write_text(f"vault: {tmp_path}\nagents: {{}}\n")

        result = runner.invoke(
            main,
            ["process", "--all", "--vault", str(tmp_path), "--config", str(config_file)],
        )
        assert result.exit_code == 0
        assert "Processed 0 instruction" in result.output

    def test_process_requires_all_flag(self, runner: CliRunner) -> None:
        """Process command requires --all flag."""
        result = runner.invoke(main, ["process"])
        assert result.exit_code != 0


class TestWatchCommand:
    """Tests for the 'watch' CLI command."""

    def test_watch_nonexistent_vault(self, runner: CliRunner, tmp_path: Path) -> None:
        """Watch command errors on nonexistent vault."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("vault: /nonexistent/path\nagents: {}\n")

        result = runner.invoke(
            main,
            ["watch", "--vault", str(tmp_path / "nonexistent"), "--config", str(config_file)],
        )
        assert result.exit_code != 0


class TestMainGroup:
    """Tests for the main CLI group."""

    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Note Watcher" in result.output

    def test_process_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["process", "--help"])
        assert result.exit_code == 0
        assert "--all" in result.output

    def test_watch_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["watch", "--help"])
        assert result.exit_code == 0
        assert "--vault" in result.output

    def test_check_arcade_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check-arcade", "--help"])
        assert result.exit_code == 0
        assert "--user-id" in result.output


class TestCheckArcadeCommand:
    """Tests for the 'check-arcade' CLI command."""

    def test_all_authorized(self, runner: CliRunner) -> None:
        """Reports all authorized services and exits 0."""
        with patch("note_watcher.cli.check_tokens") as mock_check:
            mock_check.return_value = (["gmail", "slack"], [])
            result = runner.invoke(
                main,
                [
                    "check-arcade", "--user-id", "user@example.com",
                    "--services", "gmail", "--services", "slack",
                ],
            )
        assert result.exit_code == 0
        assert "gmail" in result.output
        assert "slack" in result.output

    def test_some_unauthorized(self, runner: CliRunner) -> None:
        """Reports unauthorized services, still exits 0."""
        with patch("note_watcher.cli.check_tokens") as mock_check:
            mock_check.return_value = (["gmail"], ["slack"])
            result = runner.invoke(
                main,
                [
                    "check-arcade", "--user-id", "user@example.com",
                    "--services", "gmail", "--services", "slack",
                ],
            )
        assert result.exit_code == 0
        assert "slack" in result.output

    def test_requires_user_id(self, runner: CliRunner) -> None:
        """Missing --user-id gives an error."""
        result = runner.invoke(main, ["check-arcade"])
        assert result.exit_code != 0

    def test_services_filter(self, runner: CliRunner) -> None:
        """--services flag filters which services to check."""
        with patch("note_watcher.cli.check_tokens") as mock_check:
            mock_check.return_value = (["gmail"], [])
            runner.invoke(
                main,
                [
                    "check-arcade",
                    "--user-id", "user@example.com",
                    "--services", "gmail",
                ],
            )
            mock_check.assert_called_once_with(
                "user@example.com", ["gmail"]
            )

    def test_always_exits_zero(self, runner: CliRunner) -> None:
        """Even with all services unauthorized, exits 0."""
        with patch("note_watcher.cli.check_tokens") as mock_check:
            mock_check.return_value = (
                [], ["gmail", "slack", "google-calendar"]
            )
            result = runner.invoke(
                main,
                [
                    "check-arcade",
                    "--user-id", "user@example.com",
                ],
            )
        assert result.exit_code == 0

"""Shared pytest fixtures for Note Watcher tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from note_watcher.config import AgentConfig, Config


@pytest.fixture
def sample_config(tmp_path: Path) -> Config:
    """A Config with echo and uppercase agents pointing at a temporary vault."""
    return Config(
        vault=tmp_path,
        debounce_seconds=0.1,
        ignore_patterns=["*.excalidraw.md", ".trash/**"],
        agents={
            "summarizer": AgentConfig(name="summarizer", type="echo"),
            "uppercase": AgentConfig(name="uppercase", type="uppercase"),
        },
    )


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """A temporary directory acting as an Obsidian vault."""
    return tmp_path


@pytest.fixture
def sample_note(vault_dir: Path) -> Path:
    """A sample markdown note with @ instructions."""
    note = vault_dir / "test_note.md"
    note.write_text(
        "# Test Note\n"
        "\n"
        "Some intro text.\n"
        "\n"
        "@summarizer Summarize the following paragraph\n"
        "\n"
        "More content here.\n"
        "\n"
        "@uppercase Make this text uppercase\n"
    )
    return note


@pytest.fixture
def processed_note(vault_dir: Path) -> Path:
    """A markdown note where some instructions are already processed."""
    note = vault_dir / "processed_note.md"
    note.write_text(
        "# Processed Note\n"
        "\n"
        "<!-- @done summarizer -->\n"
        "Summarize the following paragraph\n"
        "<!-- /@done -->\n"
        "\n"
        "@uppercase Make this new text uppercase\n"
    )
    return note

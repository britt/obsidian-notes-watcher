"""Tests for configuration loading."""

from pathlib import Path

import pytest

from note_watcher.config import (
    AgentConfig,
    Config,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_IGNORE_PATTERNS,
    load_config,
)


class TestConfig:
    """Tests for Config dataclass."""

    def test_defaults(self) -> None:
        config = Config.defaults()
        assert config.vault == Path(".")
        assert config.debounce_seconds == DEFAULT_DEBOUNCE_SECONDS
        assert config.ignore_patterns == DEFAULT_IGNORE_PATTERNS
        assert config.agents == {}

    def test_from_dict_full(self) -> None:
        data = {
            "vault": "/tmp/test-vault",
            "debounce_seconds": 2.5,
            "ignore_patterns": ["*.tmp"],
            "agents": {
                "echo": {"type": "echo"},
                "upper": {"type": "uppercase"},
            },
        }
        config = Config.from_dict(data)
        assert config.vault == Path("/tmp/test-vault")
        assert config.debounce_seconds == 2.5
        assert config.ignore_patterns == ["*.tmp"]
        assert "echo" in config.agents
        assert config.agents["echo"].type == "echo"
        assert config.agents["upper"].type == "uppercase"

    def test_from_dict_minimal(self) -> None:
        data = {"vault": "/tmp/vault"}
        config = Config.from_dict(data)
        assert config.vault == Path("/tmp/vault")
        assert config.debounce_seconds == DEFAULT_DEBOUNCE_SECONDS
        assert config.ignore_patterns == DEFAULT_IGNORE_PATTERNS

    def test_from_dict_expands_tilde(self) -> None:
        data = {"vault": "~/my-vault"}
        config = Config.from_dict(data)
        assert "~" not in str(config.vault)
        assert config.vault == Path.home() / "my-vault"

    def test_from_dict_simple_agent_value(self) -> None:
        """Agent config as a simple string value (just the type)."""
        data = {
            "vault": ".",
            "agents": {"myagent": "echo"},
        }
        config = Config.from_dict(data)
        assert config.agents["myagent"].type == "echo"

    def test_from_dict_empty(self) -> None:
        data: dict = {}
        config = Config.from_dict(data)
        assert config.vault == Path(".")


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_from_dict(self) -> None:
        agent = AgentConfig.from_dict("test", {"type": "echo"})
        assert agent.name == "test"
        assert agent.type == "echo"
        assert agent.command is None

    def test_from_dict_with_command(self) -> None:
        agent = AgentConfig.from_dict("cmd", {"type": "command", "command": "echo hello"})
        assert agent.type == "command"
        assert agent.command == "echo hello"

    def test_from_dict_with_system_prompt(self) -> None:
        agent = AgentConfig.from_dict(
            "claude",
            {
                "type": "command",
                "command": "claude --print",
                "system_prompt": "You are helpful.",
            },
        )
        assert agent.system_prompt == "You are helpful."
        assert agent.system_prompt_file is None

    def test_from_dict_with_system_prompt_file(self) -> None:
        agent = AgentConfig.from_dict(
            "claude",
            {
                "type": "command",
                "command": "claude --print",
                "system_prompt_file": "prompts/claude.md",
            },
        )
        assert agent.system_prompt is None
        assert agent.system_prompt_file == "prompts/claude.md"

    def test_from_dict_both_system_prompt_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot set both"):
            AgentConfig.from_dict(
                "claude",
                {
                    "type": "command",
                    "system_prompt": "inline",
                    "system_prompt_file": "file.md",
                },
            )


class TestLoadConfig:
    """Tests for load_config()."""

    def test_load_existing_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "vault: /tmp/test\n"
            "debounce_seconds: 3.0\n"
            "agents:\n"
            "  echo:\n"
            "    type: echo\n"
        )
        config = load_config(config_file)
        assert config.vault == Path("/tmp/test")
        assert config.debounce_seconds == 3.0
        assert "echo" in config.agents

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.yml")
        assert config.vault == Path(".")
        assert config.agents == {}

    def test_load_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "empty.yml"
        config_file.write_text("")
        config = load_config(config_file)
        assert config.vault == Path(".")

    def test_load_none_uses_default_path(self) -> None:
        """Passing None uses the default config path (which likely doesn't exist)."""
        config = load_config(None)
        # Should return defaults since ~/.config/note-watcher/config.yml likely doesn't exist
        assert isinstance(config, Config)

"""Configuration loading and management for Note Watcher.

Loads YAML configuration from a file, applies sensible defaults,
and validates required fields.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "note-watcher" / "config.yml"

DEFAULT_DEBOUNCE_SECONDS = 1.0

DEFAULT_IGNORE_PATTERNS: list[str] = [
    "*.excalidraw.md",
    ".trash/**",
]


@dataclass
class AgentConfig:
    """Configuration for a single agent."""

    name: str
    type: str
    command: str | None = None
    callable: str | None = None
    system_prompt: str | None = None
    system_prompt_file: str | None = None

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> AgentConfig:
        """Create an AgentConfig from a parsed YAML dictionary.

        Args:
            name: The agent's identifier.
            data: Dictionary of agent settings from the config file.

        Returns:
            A new AgentConfig instance.
        """
        system_prompt = data.get("system_prompt")
        system_prompt_file = data.get("system_prompt_file")
        if system_prompt and system_prompt_file:
            raise ValueError(
                f"Cannot set both 'system_prompt' and "
                f"'system_prompt_file' for agent {name!r}"
            )
        return cls(
            name=name,
            type=data.get("type", "echo"),
            command=data.get("command"),
            callable=data.get("callable"),
            system_prompt=system_prompt,
            system_prompt_file=system_prompt_file,
        )


@dataclass
class Config:
    """Application configuration."""

    vault: Path
    debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS
    ignore_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    config_dir: Path | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create a Config from a parsed YAML dictionary."""
        vault_str = data.get("vault", ".")
        # Expand ~ and environment variables in the vault path
        vault = Path(os.path.expanduser(os.path.expandvars(vault_str)))

        debounce = data.get("debounce_seconds", DEFAULT_DEBOUNCE_SECONDS)

        ignore = data.get("ignore_patterns", list(DEFAULT_IGNORE_PATTERNS))

        agents: dict[str, AgentConfig] = {}
        for name, agent_data in data.get("agents", {}).items():
            if isinstance(agent_data, dict):
                agents[name] = AgentConfig.from_dict(name, agent_data)
            else:
                # Simple string value treated as the type
                agents[name] = AgentConfig(name=name, type=str(agent_data))

        return cls(
            vault=vault,
            debounce_seconds=float(debounce),
            ignore_patterns=ignore,
            agents=agents,
        )

    @classmethod
    def defaults(cls, vault: str | Path = ".") -> Config:
        """Create a Config with default values."""
        return cls(vault=Path(vault))


def load_config(config_path: str | Path | None = None) -> Config:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the config file. If None, uses the default path.

    Returns:
        A Config instance. If the config file doesn't exist, returns defaults.
    """
    if config_path is None:
        path = DEFAULT_CONFIG_PATH
    else:
        path = Path(config_path)

    if not path.exists():
        return Config.defaults()

    with open(path) as f:
        data = yaml.safe_load(f)

    if data is None:
        return Config.defaults()

    config = Config.from_dict(data)
    config.config_dir = path.parent
    return config

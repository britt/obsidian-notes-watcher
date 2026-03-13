"""Tests for the agent dispatcher."""

import json

import pytest

from note_watcher.config import AgentConfig, Config
from note_watcher.dispatcher import AgentDispatcher, UnknownAgentError
from note_watcher.parser import Instruction
from note_watcher.result_validator import AuthFailureError


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(
        vault=tmp_path,
        agents={
            "echo_agent": AgentConfig(name="echo_agent", type="echo"),
            "upper_agent": AgentConfig(name="upper_agent", type="uppercase"),
        },
    )


@pytest.fixture
def dispatcher(config: Config) -> AgentDispatcher:
    return AgentDispatcher(config)


def _make_instruction(agent_name: str, text: str = "Test text") -> Instruction:
    return Instruction(
        agent_name=agent_name,
        instruction_text=text,
        line_number=1,
        original_text=f"@{agent_name} {text}",
    )


class TestAgentDispatcher:
    """Tests for AgentDispatcher."""

    def test_echo_agent_returns_text(self, dispatcher: AgentDispatcher) -> None:
        instruction = _make_instruction("echo_agent", "Hello world")
        result = dispatcher.dispatch(instruction)
        assert result == "Hello world"

    def test_uppercase_agent_returns_uppercased(self, dispatcher: AgentDispatcher) -> None:
        instruction = _make_instruction("upper_agent", "make me big")
        result = dispatcher.dispatch(instruction)
        assert result == "MAKE ME BIG"

    def test_unknown_agent_raises_error(self, dispatcher: AgentDispatcher) -> None:
        instruction = _make_instruction("nonexistent")
        with pytest.raises(UnknownAgentError) as exc_info:
            dispatcher.dispatch(instruction)
        assert "nonexistent" in str(exc_info.value)

    def test_unknown_agent_error_has_name(self) -> None:
        err = UnknownAgentError("test_agent")
        assert err.agent_name == "test_agent"

    def test_echo_preserves_special_characters(self, dispatcher: AgentDispatcher) -> None:
        text = "Hello! @world #test $100"
        instruction = _make_instruction("echo_agent", text)
        result = dispatcher.dispatch(instruction)
        assert result == text

    def test_uppercase_handles_empty_instruction(self, dispatcher: AgentDispatcher) -> None:
        """Uppercase agent with minimal text."""
        instruction = _make_instruction("upper_agent", "a")
        result = dispatcher.dispatch(instruction)
        assert result == "A"

    def test_command_agent(self, tmp_path) -> None:
        """Test command agent type."""
        config = Config(
            vault=tmp_path,
            agents={
                "cat_agent": AgentConfig(name="cat_agent", type="command", command="cat"),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("cat_agent", "hello from command")
        result = dispatcher.dispatch(instruction)
        assert "hello from command" in result

    def test_command_agent_uses_configured_timeout(self, tmp_path) -> None:
        """Command agent uses the timeout from AgentConfig."""
        config = Config(
            vault=tmp_path,
            agents={
                "slow_agent": AgentConfig(
                    name="slow_agent",
                    type="command",
                    command="sleep 2 && echo done",
                    timeout=1,
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("slow_agent", "wait")
        import subprocess
        with pytest.raises(subprocess.TimeoutExpired):
            dispatcher.dispatch(instruction)

    def test_unsupported_agent_type_raises(self, tmp_path) -> None:
        """An agent with an unrecognized type should raise."""
        config = Config(
            vault=tmp_path,
            agents={
                "bad_agent": AgentConfig(name="bad_agent", type="teleport"),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("bad_agent")
        with pytest.raises(UnknownAgentError):
            dispatcher.dispatch(instruction)


class TestCommandAgentEnvVars:
    """Tests for environment variables passed to command agents."""

    def test_command_receives_file_path_env(self, tmp_path) -> None:
        """Command agent receives NOTE_WATCHER_FILE_PATH env var."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_FILE_PATH",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(instruction, file_path="/tmp/notes/test.md")
        assert result == "/tmp/notes/test.md"

    def test_command_receives_vault_path_env(self, tmp_path) -> None:
        """Command agent receives NOTE_WATCHER_VAULT_PATH env var."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_VAULT_PATH",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(instruction, file_path="/tmp/notes/test.md")
        assert result == str(tmp_path)

    def test_command_receives_system_prompt_env(self, tmp_path) -> None:
        """Command agent receives NOTE_WATCHER_SYSTEM_PROMPT env var."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_SYSTEM_PROMPT",
                    system_prompt="You are helpful.",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(instruction, file_path="/tmp/notes/test.md")
        assert "You are helpful." in result
        assert "file path" in result.lower()

    def test_system_prompt_interpolates_vault_path(self, tmp_path) -> None:
        """System prompt template variables are interpolated."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_SYSTEM_PROMPT",
                    system_prompt="Vault: {vault_path}",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(instruction, file_path="/tmp/notes/test.md")
        assert f"Vault: {tmp_path}" in result

    def test_system_prompt_interpolates_file_path(self, tmp_path) -> None:
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_SYSTEM_PROMPT",
                    system_prompt="File: {file_path}",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(instruction, file_path="/tmp/notes/test.md")
        assert "File: /tmp/notes/test.md" in result

    def test_system_prompt_file_loaded(self, tmp_path) -> None:
        """System prompt loaded from file relative to config_dir."""
        prompt_file = tmp_path / "prompts" / "test.md"
        prompt_file.parent.mkdir(parents=True)
        prompt_file.write_text("Prompt from file: {vault_path}")

        config = Config(
            vault=tmp_path,
            config_dir=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_SYSTEM_PROMPT",
                    system_prompt_file="prompts/test.md",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(instruction, file_path="/tmp/notes/test.md")
        assert f"Prompt from file: {tmp_path}" in result

    def test_system_prompt_with_curly_braces_not_crashed(self, tmp_path) -> None:
        """System prompt containing curly braces (e.g. JSON) should not crash."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_SYSTEM_PROMPT",
                    system_prompt='Use JSON like {"key": "value"} in responses.',
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(instruction, file_path="/tmp/notes/test.md")
        assert 'Use JSON like {"key": "value"} in responses.' in result

    def test_command_stdin_includes_file_path(self, tmp_path) -> None:
        """Command agent receives file path as part of stdin message."""
        config = Config(
            vault=tmp_path,
            agents={
                "cat_agent": AgentConfig(
                    name="cat_agent",
                    type="command",
                    command="cat",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("cat_agent", "do something")
        result = dispatcher.dispatch(
            instruction, file_path="/tmp/notes/test.md"
        )
        assert "File: /tmp/notes/test.md" in result
        assert "do something" in result

    def test_command_stdin_file_path_before_instruction(self, tmp_path) -> None:
        """File path appears before instruction text in stdin."""
        config = Config(
            vault=tmp_path,
            agents={
                "cat_agent": AgentConfig(
                    name="cat_agent",
                    type="command",
                    command="cat",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("cat_agent", "fix the typos")
        result = dispatcher.dispatch(
            instruction, file_path="/vault/note.md"
        )
        file_pos = result.index("File: /vault/note.md")
        instruction_pos = result.index("fix the typos")
        assert file_pos < instruction_pos

    def test_system_prompt_mentions_file_path_in_message(self, tmp_path) -> None:
        """System prompt should indicate the user message contains the file path."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_SYSTEM_PROMPT",
                    system_prompt="You are helpful.",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(instruction, file_path="/tmp/notes/test.md")
        assert "file path" in result.lower()

    def test_default_system_prompt_when_not_configured(
        self, tmp_path
    ) -> None:
        """Default system prompt is used when none is configured."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_SYSTEM_PROMPT",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(
            instruction, file_path="/tmp/notes/test.md"
        )
        # Should contain key phrases from the default prompt
        assert "Obsidian vault" in result
        assert str(tmp_path) in result
        assert "/tmp/notes/test.md" in result
        # Should instruct agent to default to the same note
        assert "same note" in result.lower() or "that note" in result.lower()

    def test_default_prompt_env_always_set(self, tmp_path) -> None:
        """NOTE_WATCHER_SYSTEM_PROMPT env var is always set."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command=(
                        "python3 -c \"import os, json;"
                        " print(json.dumps(dict(os.environ)))\""
                    ),
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(
            instruction, file_path="/tmp/notes/test.md"
        )
        env = json.loads(result)
        assert "NOTE_WATCHER_SYSTEM_PROMPT" in env
        assert env["NOTE_WATCHER_FILE_PATH"] == "/tmp/notes/test.md"

    def test_custom_prompt_overrides_default(self, tmp_path) -> None:
        """Custom system_prompt replaces the default, not appends."""
        config = Config(
            vault=tmp_path,
            agents={
                "env_agent": AgentConfig(
                    name="env_agent",
                    type="command",
                    command="printenv NOTE_WATCHER_SYSTEM_PROMPT",
                    system_prompt="Custom prompt only.",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("env_agent")
        result = dispatcher.dispatch(
            instruction, file_path="/tmp/notes/test.md"
        )
        assert "Custom prompt only." in result
        # Should NOT contain the default prompt text
        assert "Obsidian vault at" not in result


class TestAuthFailureDetection:
    """Tests for Arcade auth failure detection in command agents."""

    def test_command_agent_raises_on_arcade_auth_url(
        self, tmp_path
    ) -> None:
        """Command output with Arcade auth URL raises AuthFailureError."""
        # Use echo to simulate an agent outputting an auth URL
        auth_output = (
            "I need authorization. Visit: "
            "https://accounts.google.com/o/oauth2/v2/auth?"
            "redirect_uri=https%3A%2F%2Fcloud.arcade.dev%2Fapi%2Fv1%2Foauth%2Fcallback"
        )
        config = Config(
            vault=tmp_path,
            agents={
                "auth_agent": AgentConfig(
                    name="auth_agent",
                    type="command",
                    command=f"echo '{auth_output}'",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("auth_agent", "check calendar")
        with pytest.raises(AuthFailureError) as exc_info:
            dispatcher.dispatch(instruction, file_path="/tmp/note.md")
        assert "arcade.dev" in exc_info.value.result

    def test_command_agent_returns_normal_result(self, tmp_path) -> None:
        """Normal command output is returned without raising."""
        config = Config(
            vault=tmp_path,
            agents={
                "normal_agent": AgentConfig(
                    name="normal_agent",
                    type="command",
                    command="echo 'Updated the note successfully.'",
                ),
            },
        )
        dispatcher = AgentDispatcher(config)
        instruction = _make_instruction("normal_agent", "update note")
        result = dispatcher.dispatch(instruction, file_path="/tmp/note.md")
        assert "Updated the note successfully." in result

    def test_echo_agent_not_validated(self, dispatcher: AgentDispatcher) -> None:
        """Built-in agents (echo) do not go through auth validation."""
        instruction = _make_instruction("echo_agent", "https://api.arcade.dev/auth/start")
        # Should return the text as-is, not raise AuthFailureError
        result = dispatcher.dispatch(instruction)
        assert result == "https://api.arcade.dev/auth/start"

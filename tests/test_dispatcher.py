"""Tests for the agent dispatcher."""

import pytest

from note_watcher.config import AgentConfig, Config
from note_watcher.dispatcher import AgentDispatcher, UnknownAgentError
from note_watcher.parser import Instruction


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
        assert result == "hello from command"

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

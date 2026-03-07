"""Agent dispatcher that routes instructions to configured agent handlers.

Supports built-in agent types (echo, uppercase) and extensible configuration
for command-based or callable-based agents.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from note_watcher.config import AgentConfig, Config
    from note_watcher.parser import Instruction


class UnknownAgentError(Exception):
    """Raised when an instruction references an agent that isn't configured."""

    def __init__(self, agent_name: str) -> None:
        """Initialize with the name of the unrecognized agent.

        Args:
            agent_name: The agent name that was not found in configuration.
        """
        self.agent_name = agent_name
        super().__init__(f"Unknown agent: {agent_name!r}")


class AgentDispatcher:
    """Routes instructions to the appropriate agent handler."""

    def __init__(self, config: Config) -> None:
        """Initialize the dispatcher with application configuration.

        Args:
            config: Application configuration containing agent definitions.
        """
        self.config = config

    def dispatch(self, instruction: Instruction) -> str:
        """Dispatch an instruction to the appropriate agent and return the result.

        Args:
            instruction: The parsed instruction to process.

        Returns:
            The agent's result as a string.

        Raises:
            UnknownAgentError: If the agent isn't configured.
        """
        agent_config = self.config.agents.get(instruction.agent_name)
        if agent_config is None:
            raise UnknownAgentError(instruction.agent_name)

        return self._handle(agent_config, instruction)

    def _handle(self, agent_config: AgentConfig, instruction: Instruction) -> str:
        """Route to the correct handler based on agent type."""
        handler_type = agent_config.type

        if handler_type == "echo":
            return self._handle_echo(instruction)
        elif handler_type == "uppercase":
            return self._handle_uppercase(instruction)
        elif handler_type == "command":
            return self._handle_command(agent_config, instruction)
        else:
            raise UnknownAgentError(
                f"{instruction.agent_name} (unsupported type: {handler_type})"
            )

    def _handle_echo(self, instruction: Instruction) -> str:
        """Echo agent: returns the instruction text unchanged."""
        return instruction.instruction_text

    def _handle_uppercase(self, instruction: Instruction) -> str:
        """Uppercase agent: returns the instruction text in uppercase."""
        return instruction.instruction_text.upper()

    def _handle_command(
        self, agent_config: AgentConfig, instruction: Instruction
    ) -> str:
        """Command agent: runs a shell command with the instruction as input.

        The instruction text is passed via stdin.
        """
        if not agent_config.command:
            raise ValueError(f"Agent {agent_config.name!r} has type 'command' but no command configured")

        result = subprocess.run(
            agent_config.command,
            input=instruction.instruction_text,
            capture_output=True,
            text=True,
            shell=True,
            timeout=30,
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()

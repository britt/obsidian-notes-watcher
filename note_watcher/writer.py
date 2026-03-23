"""Inline writer that replaces instructions with agent results.

Wraps results in completed markers to prevent reprocessing.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from note_watcher.parser import Instruction


def format_result(agent_name: str, instruction_text: str, result: str) -> str:
    """Format an agent result with completed markers.

    The entire result is enclosed in a single HTML comment so it is hidden
    from rendered markdown.  The original instruction text is preserved on
    the opening line after the agent name.

    Args:
        agent_name: Name of the agent that produced the result.
        instruction_text: The original instruction text from the @ mention.
        result: The agent's output text.

    Returns:
        The result wrapped in a single HTML comment block.
    """
    return f"<!-- @done {agent_name}: {instruction_text}\n{result}\n/@done -->"


def format_error(agent_name: str, instruction_text: str, reason: str) -> str:
    """Format an error with error markers.

    Args:
        agent_name: Name of the agent that failed.
        instruction_text: The original instruction text from the @ mention.
        reason: The reason for the error.

    Returns:
        The error wrapped in a single HTML comment block.
    """
    return f"<!-- @error {agent_name}: {instruction_text}\n{reason}\n/@error -->"


def _replace_instruction_line(
    file_path: str | Path,
    instruction: Instruction,
    replacement: str,
) -> None:
    """Replace an instruction line in a file with a replacement string.

    First attempts line-number match (fast path). If the file has been
    modified since parsing (e.g., by an agent during dispatch), falls back
    to searching for the instruction text on any line.

    Args:
        file_path: Path to the markdown file.
        instruction: The original instruction that was processed.
        replacement: The formatted text to replace the instruction line.

    Raises:
        ValueError: If the instruction text is not found anywhere in the file.
    """
    path = Path(file_path)
    content = path.read_text()
    lines = content.split("\n")

    target_text = instruction.original_text.strip()

    # Fast path: check original line number
    line_idx = instruction.line_number - 1
    if 0 <= line_idx < len(lines) and lines[line_idx].strip() == target_text:
        lines[line_idx] = replacement
        path.write_text("\n".join(lines))
        return

    # Fallback: search all lines for the instruction text
    for i, line in enumerate(lines):
        if line.strip() == target_text:
            lines[i] = replacement
            path.write_text("\n".join(lines))
            return

    raise ValueError(f"Instruction {target_text!r} not found in file {file_path}")


def write_result(
    file_path: str | Path,
    instruction: Instruction,
    result: str,
) -> None:
    """Write an agent result back into a file, replacing the original instruction.

    Args:
        file_path: Path to the markdown file.
        instruction: The original instruction that was processed.
        result: The agent's output text.
    """
    formatted = format_result(
        instruction.agent_name, instruction.instruction_text, result
    )
    _replace_instruction_line(file_path, instruction, formatted)


def write_error(
    file_path: str | Path,
    instruction: Instruction,
    reason: str,
) -> None:
    """Write an error back into a file, replacing the original instruction.

    Args:
        file_path: Path to the markdown file.
        instruction: The original instruction that failed.
        reason: The reason for the error.
    """
    formatted = format_error(
        instruction.agent_name, instruction.instruction_text, reason
    )
    _replace_instruction_line(file_path, instruction, formatted)

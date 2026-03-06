"""Inline writer that replaces instructions with agent results.

Wraps results in completed markers to prevent reprocessing.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from note_watcher.parser import Instruction


def format_result(agent_name: str, result: str) -> str:
    """Format an agent result with completed markers.

    Args:
        agent_name: Name of the agent that produced the result.
        result: The agent's output text.

    Returns:
        The result wrapped in completed marker comments.
    """
    return f"<!-- @done {agent_name} -->\n{result}\n<!-- /@done -->"


def write_result(
    file_path: str | Path,
    instruction: Instruction,
    result: str,
) -> None:
    """Write an agent result back into a file, replacing the original instruction.

    Reads the file, finds the instruction line, replaces it with the formatted
    result block, and writes the file back.

    Args:
        file_path: Path to the markdown file.
        instruction: The original instruction that was processed.
        result: The agent's output text.
    """
    path = Path(file_path)
    content = path.read_text()
    lines = content.split("\n")

    # Find the instruction line (0-indexed)
    line_idx = instruction.line_number - 1

    if line_idx < 0 or line_idx >= len(lines):
        raise IndexError(
            f"Instruction line {instruction.line_number} out of range "
            f"(file has {len(lines)} lines)"
        )

    # Verify the line still matches the original instruction
    if lines[line_idx].strip() != instruction.original_text.strip():
        raise ValueError(
            f"Line {instruction.line_number} has changed since parsing. "
            f"Expected: {instruction.original_text.strip()!r}, "
            f"Got: {lines[line_idx].strip()!r}"
        )

    # Replace the instruction line with the formatted result
    formatted = format_result(instruction.agent_name, result)
    lines[line_idx] = formatted

    # Write back
    path.write_text("\n".join(lines))

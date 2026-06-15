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


def format_pending(agent_name: str, instruction_text: str) -> str:
    """Format a pending marker written in place of an instruction while it runs.

    The marker is intentionally parser-neutral (it is not a @done, @error, or
    @agent line) so the parser ignores it, and it carries the agent name and
    instruction text so it can be located again after dispatch.

    Args:
        agent_name: Name of the agent that is processing the instruction.
        instruction_text: The original instruction text from the @ mention.

    Returns:
        A single-line HTML comment sentinel.
    """
    return f"<!-- note-watcher: processing @{agent_name} {instruction_text} -->"


def _replace_line(
    file_path: str | Path,
    target_text: str,
    replacement: str,
    line_number_hint: int | None = None,
    append_if_missing: bool = False,
) -> None:
    """Replace a single line matching ``target_text`` with ``replacement``.

    First attempts a line-number match (fast path) when a hint is given. If the
    file has been modified since parsing (e.g., by an agent during dispatch),
    falls back to searching for the target text on any line.

    Args:
        file_path: Path to the markdown file.
        target_text: The exact (stripped) line text to replace.
        replacement: The text to replace the matched line with.
        line_number_hint: Optional 1-indexed line to check first.
        append_if_missing: If True, append the replacement at the end of the
            file when no matching line is found instead of raising.

    Raises:
        ValueError: If the target text is not found and ``append_if_missing``
            is False.
    """
    path = Path(file_path)
    content = path.read_text()
    lines = content.split("\n")

    target = target_text.strip()

    # Fast path: check the hinted line number.
    if line_number_hint is not None:
        idx = line_number_hint - 1
        if 0 <= idx < len(lines) and lines[idx].strip() == target:
            lines[idx] = replacement
            path.write_text("\n".join(lines))
            return

    # Fallback: search all lines for the target text.
    for i, line in enumerate(lines):
        if line.strip() == target:
            lines[i] = replacement
            path.write_text("\n".join(lines))
            return

    if append_if_missing:
        # The line is gone (an agent rewrote it away). Append the replacement
        # at the end of the file so the result is never lost.
        prefix = content if content.endswith("\n") or content == "" else content + "\n"
        path.write_text(prefix + replacement + "\n")
        return

    raise ValueError(f"Instruction {target!r} not found in file {file_path}")


def _replace_instruction_line(
    file_path: str | Path,
    instruction: Instruction,
    replacement: str,
) -> None:
    """Replace an instruction line in a file with a replacement string.

    Args:
        file_path: Path to the markdown file.
        instruction: The original instruction that was processed.
        replacement: The formatted text to replace the instruction line.

    Raises:
        ValueError: If the instruction text is not found anywhere in the file.
    """
    _replace_line(
        file_path,
        instruction.original_text,
        replacement,
        line_number_hint=instruction.line_number,
    )


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


def write_pending(file_path: str | Path, instruction: Instruction) -> str:
    """Replace an instruction with a pending sentinel before dispatch.

    This is done *before* the agent runs, while the instruction line is still
    guaranteed to be present. The returned sentinel is later swapped for the
    final result or error marker, which is robust even if the agent rewrites
    the surrounding note content (issue #12).

    Args:
        file_path: Path to the markdown file.
        instruction: The instruction about to be dispatched.

    Returns:
        The sentinel string written into the file.
    """
    sentinel = format_pending(instruction.agent_name, instruction.instruction_text)
    _replace_instruction_line(file_path, instruction, sentinel)
    return sentinel


def finalize_result(
    file_path: str | Path,
    sentinel: str,
    instruction: Instruction,
    result: str,
) -> None:
    """Replace a pending sentinel with the agent's completed result marker.

    Falls back to appending at the end of the file if the agent removed the
    sentinel during dispatch, so the result is never lost.

    Args:
        file_path: Path to the markdown file.
        sentinel: The sentinel previously written by ``write_pending``.
        instruction: The original instruction that was processed.
        result: The agent's output text.
    """
    formatted = format_result(
        instruction.agent_name, instruction.instruction_text, result
    )
    _replace_line(file_path, sentinel, formatted, append_if_missing=True)


def finalize_error(
    file_path: str | Path,
    sentinel: str,
    instruction: Instruction,
    reason: str,
) -> None:
    """Replace a pending sentinel with an error marker.

    Falls back to appending at the end of the file if the sentinel is gone.

    Args:
        file_path: Path to the markdown file.
        sentinel: The sentinel previously written by ``write_pending``.
        instruction: The original instruction that failed.
        reason: The reason for the error.
    """
    formatted = format_error(
        instruction.agent_name, instruction.instruction_text, reason
    )
    _replace_line(file_path, sentinel, formatted, append_if_missing=True)


def restore_instruction(
    file_path: str | Path,
    sentinel: str,
    instruction: Instruction,
) -> None:
    """Restore the original instruction in place of a pending sentinel.

    Used when dispatch fails in a way that should leave the instruction for a
    later retry (e.g. an unknown agent) rather than marking it complete.

    Args:
        file_path: Path to the markdown file.
        sentinel: The sentinel previously written by ``write_pending``.
        instruction: The original instruction to restore.
    """
    _replace_line(
        file_path, sentinel, instruction.original_text, append_if_missing=True
    )

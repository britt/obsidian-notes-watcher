"""Parser for extracting @ mention instructions from markdown content.

Extracts instructions like `@agent_name instruction text` from markdown files,
while skipping content that has already been processed (wrapped in completed markers).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Pattern to match @ mention instructions: @agent_name followed by instruction text
INSTRUCTION_PATTERN = re.compile(r"^@(\w+)\s+(.+)$")

# Markers for completed instructions
# New format: <!-- @done agent_name: instruction text  (no closing -->)
# Old format: <!-- @done agent_name -->  (kept for backwards compatibility)
DONE_START_PATTERN = re.compile(r"^<!--\s*@done\s+(\w+).*$")
DONE_END_PATTERN = re.compile(r"^.*/@done\s*-->$")


@dataclass
class Instruction:
    """A parsed @ mention instruction."""

    agent_name: str
    instruction_text: str
    line_number: int
    original_text: str


def parse_instructions(content: str) -> list[Instruction]:
    """Extract @ mention instructions from markdown content.

    Skips any content between `<!-- @done ... -->` and `<!-- /@done -->`
    markers, which indicate already-processed instructions.

    Args:
        content: The full markdown file content.

    Returns:
        A list of Instruction objects for each unprocessed @ mention found.
    """
    instructions: list[Instruction] = []
    lines = content.split("\n")
    in_done_block = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check for start of a completed block
        if DONE_START_PATTERN.match(stripped):
            in_done_block = True
            continue

        # Check for end of a completed block
        if DONE_END_PATTERN.match(stripped):
            in_done_block = False
            continue

        # Skip lines inside completed blocks
        if in_done_block:
            continue

        # Try to match an instruction
        match = INSTRUCTION_PATTERN.match(stripped)
        if match:
            instructions.append(
                Instruction(
                    agent_name=match.group(1),
                    instruction_text=match.group(2),
                    line_number=i + 1,  # 1-indexed
                    original_text=line,
                )
            )

    return instructions

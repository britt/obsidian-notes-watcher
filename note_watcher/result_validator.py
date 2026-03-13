"""Validates agent results for known failure patterns.

Detects Arcade authorization URLs in agent output, which indicate that
the agent could not complete the task due to missing or expired OAuth tokens.
"""

from __future__ import annotations

import re

# Matches arcade.dev in URL contexts — either as a direct URL or URL-encoded
# in a redirect_uri parameter.
ARCADE_AUTH_PATTERN = re.compile(
    r"(?:https?://|%2F%2F)[^\s]*arcade\.dev", re.IGNORECASE
)


def contains_arcade_auth_url(result: str) -> bool:
    """Check if agent output contains an Arcade authorization URL.

    Args:
        result: The agent's output text.

    Returns:
        True if the output contains an Arcade auth URL.
    """
    return bool(ARCADE_AUTH_PATTERN.search(result))


class AuthFailureError(Exception):
    """Raised when agent output contains an auth URL instead of a real result."""

    def __init__(self, result: str) -> None:
        self.result = result
        super().__init__("Agent response contains Arcade authorization URL")

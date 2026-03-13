"""Pre-flight check for Arcade OAuth token status.

Verifies that Arcade tokens are cached and valid for configured services
without triggering interactive authorization flows.
"""

from __future__ import annotations

import logging

from arcadepy import Arcade

logger = logging.getLogger(__name__)

# Same mapping as scripts/authorize_arcade.py — one representative tool per service.
SERVICE_TOOLS = {
    "github": "Github.GetRepository",
    "gmail": "Gmail.ListEmails",
    "google-drive": "GoogleDrive.SearchFiles",
    "google-calendar": "GoogleCalendar.ListEvents",
    "google-sheets": "GoogleSheets.GetSpreadsheet",
    "google-docs": "GoogleDocs.SearchDocuments",
    "slack": "Slack.ListConversations",
}


def check_tokens(
    user_id: str,
    services: list[str] | None = None,
    client: Arcade | None = None,
) -> tuple[list[str], list[str]]:
    """Check which Arcade services have valid cached tokens.

    Args:
        user_id: The Arcade user ID (email) to check tokens for.
        services: List of service names to check. Defaults to all known services.
        client: Optional Arcade client instance (for testing).

    Returns:
        A tuple of (authorized, unauthorized) service name lists.
    """
    if client is None:
        client = Arcade()

    if services is None:
        services = list(SERVICE_TOOLS.keys())

    authorized: list[str] = []
    unauthorized: list[str] = []

    for service in services:
        tool_name = SERVICE_TOOLS.get(service)
        if tool_name is None:
            logger.warning("Unknown service: %s", service)
            unauthorized.append(service)
            continue

        try:
            response = client.tools.authorize(
                tool_name=tool_name, user_id=user_id
            )
            if response.status == "completed":
                authorized.append(service)
            else:
                unauthorized.append(service)
        except Exception as e:
            logger.warning("Error checking %s: %s", service, e)
            unauthorized.append(service)

    return authorized, unauthorized

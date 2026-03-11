#!/usr/bin/env python3
"""Pre-authorize Arcade OAuth tokens for headless CI usage.

Walks through each configured service (GitHub, Gmail, Google Drive, etc.)
and triggers the Arcade authorization flow. You'll be prompted to visit
a URL in your browser for each service that hasn't been authorized yet.

Once authorized, Arcade caches the tokens server-side keyed by user_id,
so the GitHub Action runner can use them without interactive auth.

Usage:
    python scripts/authorize_arcade.py user@example.com
    python scripts/authorize_arcade.py user@example.com --services gmail slack
"""

import argparse
import sys
import webbrowser

from arcadepy import Arcade

# One representative tool per service — authorizing any tool for a service
# grants the OAuth token that covers all tools in that service.
SERVICE_TOOLS = {
    "github": "Github.GetRepository",
    "gmail": "Gmail.ListEmails",
    "google-drive": "GoogleDrive.SearchFiles",
    "google-calendar": "GoogleCalendar.ListEvents",
    "google-sheets": "GoogleSheets.GetSpreadsheet",
    "google-docs": "GoogleDocs.SearchDocuments",
    "slack": "Slack.ListConversations",
}


def authorize_service(
    client: Arcade, tool_name: str, user_id: str, *, open_browser: bool = True
) -> bool:
    """Authorize a single Arcade tool/service for the given user.

    Returns True if authorization completed successfully.
    """
    auth_response = client.tools.authorize(tool_name=tool_name, user_id=user_id)

    if auth_response.status == "completed":
        return True

    print(f"  Authorize here: {auth_response.url}")
    if open_browser:
        webbrowser.open(auth_response.url)

    print("  Waiting for authorization...")
    result = client.auth.wait_for_completion(auth_response)
    return result.status == "completed"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-authorize Arcade OAuth tokens for CI usage.",
    )
    parser.add_argument(
        "user_id",
        help="Your Arcade account email (used as user_id for token storage)",
    )
    parser.add_argument(
        "--services",
        nargs="*",
        choices=list(SERVICE_TOOLS.keys()),
        default=list(SERVICE_TOOLS.keys()),
        help="Services to authorize (default: all)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open URLs in browser",
    )
    args = parser.parse_args()

    client = Arcade()  # Uses ARCADE_API_KEY env var

    print(f"Authorizing services for user: {args.user_id}")
    print(f"Services: {', '.join(args.services)}\n")

    failed = []
    for service in args.services:
        tool_name = SERVICE_TOOLS[service]
        print(f"[{service}] Authorizing via {tool_name}...")

        try:
            ok = authorize_service(
                client, tool_name, args.user_id, open_browser=not args.no_browser
            )
            if ok:
                print(f"[{service}] Authorized\n")
            else:
                print(f"[{service}] Authorization failed or timed out\n")
                failed.append(service)
        except Exception as e:
            print(f"[{service}] Error: {e}\n")
            failed.append(service)

    if failed:
        print(f"Failed services: {', '.join(failed)}")
        return 1

    print("All services authorized successfully.")
    print(f"User ID for CI config: {args.user_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

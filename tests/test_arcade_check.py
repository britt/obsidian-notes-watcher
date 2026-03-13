"""Tests for the Arcade token check module."""

from unittest.mock import MagicMock

from note_watcher.arcade_check import check_tokens


class TestCheckTokens:
    """Tests for check_tokens()."""

    def test_all_services_authorized(self) -> None:
        """When all services return completed, unauthorized list is empty."""
        client = MagicMock()
        client.tools.authorize.return_value = MagicMock(status="completed")

        authorized, unauthorized = check_tokens(
            "user@example.com",
            services=["gmail", "slack"],
            client=client,
        )
        assert authorized == ["gmail", "slack"]
        assert unauthorized == []

    def test_one_service_unauthorized(self) -> None:
        """Unauthorized service appears in the unauthorized list."""
        client = MagicMock()

        def authorize_side_effect(tool_name, user_id):
            mock = MagicMock()
            if "Gmail" in tool_name:
                mock.status = "completed"
            else:
                mock.status = "pending"
                mock.url = "https://arcade.dev/auth/..."
            return mock

        client.tools.authorize.side_effect = authorize_side_effect

        authorized, unauthorized = check_tokens(
            "user@example.com",
            services=["gmail", "slack"],
            client=client,
        )
        assert authorized == ["gmail"]
        assert unauthorized == ["slack"]

    def test_api_error_handled_gracefully(self) -> None:
        """Network errors add service to unauthorized, don't crash."""
        client = MagicMock()
        client.tools.authorize.side_effect = Exception("Network error")

        authorized, unauthorized = check_tokens(
            "user@example.com",
            services=["gmail"],
            client=client,
        )
        assert authorized == []
        assert unauthorized == ["gmail"]

    def test_defaults_to_all_services(self) -> None:
        """When services is None, all known services are checked."""
        client = MagicMock()
        client.tools.authorize.return_value = MagicMock(status="completed")

        authorized, unauthorized = check_tokens(
            "user@example.com",
            client=client,
        )
        # Should check all services in SERVICE_TOOLS
        assert len(authorized) >= 5  # at least github, gmail, google-*, slack
        assert unauthorized == []

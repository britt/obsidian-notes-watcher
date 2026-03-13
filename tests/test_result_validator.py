"""Tests for the result validator."""

from note_watcher.result_validator import AuthFailureError, contains_arcade_auth_url


class TestContainsArcadeAuthUrl:
    """Tests for contains_arcade_auth_url()."""

    def test_detects_arcade_auth_url_in_redirect(self) -> None:
        """Detects Arcade OAuth URL in a Google redirect_uri."""
        result = (
            "I need your authorization to access your Google Calendar.\n\n"
            "**[Authorize](https://accounts.google.com/o/oauth2/v2/auth?"
            "access_type=offline&client_id=826965503-xxx.apps.googleusercontent.com"
            "&redirect_uri=https%3A%2F%2Fcloud.arcade.dev%2Fapi%2Fv1%2Foauth%2F"
            "f4c6b_aps_arcade-google%2Fcallback&response_type=code)**"
        )
        assert contains_arcade_auth_url(result) is True

    def test_detects_direct_arcade_auth_url(self) -> None:
        result = "Please authorize at https://api.arcade.dev/auth/start?token=abc123"
        assert contains_arcade_auth_url(result) is True

    def test_normal_result_passes(self) -> None:
        result = "I updated the note with today's events."
        assert contains_arcade_auth_url(result) is False

    def test_empty_result_passes(self) -> None:
        assert contains_arcade_auth_url("") is False

    def test_result_with_non_arcade_urls_passes(self) -> None:
        result = (
            "Check out https://google.com and https://example.com/auth/login"
        )
        assert contains_arcade_auth_url(result) is False

    def test_detects_url_in_multiline_output(self) -> None:
        result = (
            "I tried to access your calendar but need authorization.\n"
            "\n"
            "Here is the link:\n"
            "https://accounts.google.com/o/oauth2/v2/auth?"
            "redirect_uri=https%3A%2F%2Fcloud.arcade.dev%2Fapi%2Fv1%2Foauth"
            "%2Fcallback&response_type=code\n"
            "\n"
            "Once authorized, let me know!"
        )
        assert contains_arcade_auth_url(result) is True


class TestAuthFailureError:
    """Tests for AuthFailureError."""

    def test_stores_result_text(self) -> None:
        err = AuthFailureError("some output with auth url")
        assert err.result == "some output with auth url"

    def test_is_exception(self) -> None:
        assert issubclass(AuthFailureError, Exception)

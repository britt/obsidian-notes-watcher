"""Tests for the composite GitHub Action metadata in action.yml.

The action pip-installs the ``notes-watcher`` package at runtime. If the
version it installs is not tied to the action release, a consumer pinned to
``@v0.4.3`` silently runs whatever is newest on PyPI.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def _package_version() -> str:
    """Read the package version from pyproject.toml.

    Parsed with a regex rather than ``tomllib`` so the test also runs on
    Python 3.10, which the CI matrix still covers.
    """
    text = (REPO_ROOT / "pyproject.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "no version found in pyproject.toml"
    return match.group(1)


def _action_metadata() -> dict:
    return yaml.safe_load((REPO_ROOT / "action.yml").read_text())


def test_action_version_input_defaults_to_package_version() -> None:
    """The action installs its own release version by default."""
    default = _action_metadata()["inputs"]["version"]["default"]

    assert default == _package_version()


def _install_step_script() -> str:
    steps = _action_metadata()["runs"]["steps"]
    install = next(s for s in steps if s.get("name") == "Install Note Watcher")
    return install["run"]


def test_install_step_treats_latest_as_unpinned() -> None:
    """Consumers can opt out of the pin and track the newest release."""
    script = _install_step_script()

    assert "latest" in script, "install step has no 'latest' opt-out branch"


def test_install_step_pins_the_requested_version() -> None:
    """Any other version value installs that exact release."""
    script = _install_step_script()

    assert "notes-watcher==$VERSION" in script

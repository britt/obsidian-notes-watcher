"""Note Watcher - Detect @ mentions in Obsidian notes and dispatch to AI agents."""

from pathlib import Path as _Path

__version__ = "0.3.2"

# Use README.md as the module docstring so pdoc shows it on the index page.
_readme = _Path(__file__).parent.parent / "README.md"
if _readme.is_file():
    __doc__ = _readme.read_text(encoding="utf-8")

"""Tests for the debouncer."""

import threading
import time

from note_watcher.debouncer import Debouncer


class TestDebouncer:
    """Tests for the Debouncer class."""

    def test_fires_callback_after_interval(self) -> None:
        results: list[str] = []
        event = threading.Event()

        def callback(path: str) -> None:
            results.append(path)
            event.set()

        debouncer = Debouncer(interval=0.05, callback=callback)
        debouncer.trigger("/test/file.md")

        event.wait(timeout=2.0)
        assert results == ["/test/file.md"]

    def test_deduplicates_rapid_changes(self) -> None:
        """Rapid triggers for the same file should result in a single callback."""
        results: list[str] = []
        event = threading.Event()

        def callback(path: str) -> None:
            results.append(path)
            event.set()

        debouncer = Debouncer(interval=0.1, callback=callback)

        # Trigger multiple times rapidly
        for _ in range(5):
            debouncer.trigger("/test/file.md")
            time.sleep(0.01)

        # Wait for the debounce to fire
        event.wait(timeout=2.0)
        # Give a bit more time for any additional callbacks
        time.sleep(0.15)

        assert len(results) == 1
        assert results[0] == "/test/file.md"

    def test_different_files_tracked_independently(self) -> None:
        results: list[str] = []
        event = threading.Event()

        def callback(path: str) -> None:
            results.append(path)
            if len(results) >= 2:
                event.set()

        debouncer = Debouncer(interval=0.05, callback=callback)
        debouncer.trigger("/test/file1.md")
        debouncer.trigger("/test/file2.md")

        event.wait(timeout=2.0)
        assert set(results) == {"/test/file1.md", "/test/file2.md"}

    def test_cancel_all_stops_pending(self) -> None:
        results: list[str] = []

        def callback(path: str) -> None:
            results.append(path)

        debouncer = Debouncer(interval=0.5, callback=callback)
        debouncer.trigger("/test/file.md")

        # Cancel before the timer fires
        debouncer.cancel_all()
        time.sleep(0.7)

        assert results == []

    def test_fires_again_after_interval(self) -> None:
        """A second trigger after the interval should fire again."""
        results: list[str] = []
        event1 = threading.Event()
        event2 = threading.Event()

        def callback(path: str) -> None:
            results.append(path)
            if len(results) == 1:
                event1.set()
            elif len(results) == 2:
                event2.set()

        debouncer = Debouncer(interval=0.05, callback=callback)

        debouncer.trigger("/test/file.md")
        event1.wait(timeout=2.0)

        # Trigger again after the first one fired
        debouncer.trigger("/test/file.md")
        event2.wait(timeout=2.0)

        assert len(results) == 2

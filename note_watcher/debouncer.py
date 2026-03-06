"""Debounce logic for rapid file changes.

Prevents duplicate processing when a file is modified multiple times
in quick succession (e.g., editors that write temp files then rename).
"""

from __future__ import annotations

import threading
from typing import Callable


class Debouncer:
    """Debounces file change events by path.

    When a file change is triggered, the callback is delayed by the configured
    interval. If another trigger arrives before the interval expires, the timer
    resets. This ensures the callback fires only once after the last change
    within a burst of rapid changes.
    """

    def __init__(
        self,
        interval: float,
        callback: Callable[[str], None],
    ) -> None:
        """Initialize the debouncer.

        Args:
            interval: Seconds to wait after the last trigger before firing.
            callback: Function to call with the file path when debounce fires.
        """
        self.interval = interval
        self.callback = callback
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self._cancelled = False

    def trigger(self, file_path: str) -> None:
        """Signal that a file has changed.

        Resets the debounce timer for this file. The callback will fire
        after ``interval`` seconds of no further triggers for this file.

        Args:
            file_path: Absolute path to the changed file.
        """
        with self._lock:
            if self._cancelled:
                return

            # Cancel any existing timer for this file
            existing = self._timers.pop(file_path, None)
            if existing is not None:
                existing.cancel()

            # Schedule the callback after the full interval
            timer = threading.Timer(self.interval, self._fire, args=(file_path,))
            timer.daemon = True
            self._timers[file_path] = timer
            timer.start()

    def _fire(self, file_path: str) -> None:
        """Execute the callback if not cancelled."""
        with self._lock:
            if self._cancelled:
                return
            self._timers.pop(file_path, None)

        self.callback(file_path)

    def cancel_all(self) -> None:
        """Cancel all pending timers. No further callbacks will fire."""
        with self._lock:
            self._cancelled = True
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()

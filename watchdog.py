import threading
import time
from typing import Callable, Optional


class Watchdog:
    """A simple watchdog timer that triggers a callback on timeout."""

    def __init__(self, timeout_seconds: float, on_timeout: Callable[[], None]):
        if timeout_seconds <= 0:
            raise ValueError("Watchdog timeout must be greater than zero")
        self.timeout_seconds = timeout_seconds
        self.on_timeout = on_timeout
        self._last_feed: Optional[float] = None
        self._active = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the watchdog timer in a background thread."""
        if self._active:
            return
        self._active = True
        self._stop_event.clear()
        self._last_feed = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def feed(self) -> None:
        """Reset the watchdog timer."""
        if not self._active:
            self.start()
        self._last_feed = time.monotonic()

    def stop(self) -> None:
        """Stop the watchdog thread."""
        if not self._active:
            return
        self._active = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if self._last_feed is None:
                break
            elapsed = time.monotonic() - self._last_feed
            if elapsed >= self.timeout_seconds:
                self._active = False
                self.on_timeout()
                break
            time.sleep(0.1)

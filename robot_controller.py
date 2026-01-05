import itertools
import time
from typing import Iterable, List, Sequence

from watchdog import Watchdog


class RobotController:
    """Iterates through waypoints and stops on communication loss."""

    def __init__(self, waypoints: Sequence[str], watchdog_timeout: float = 5.0):
        if not waypoints:
            raise ValueError("At least one waypoint is required")
        self.waypoints: List[str] = list(waypoints)
        self._waypoint_cycle: Iterable[str] = itertools.cycle(self.waypoints)
        self._running = False
        self.watchdog = Watchdog(watchdog_timeout, self.stop)

    def start(self) -> None:
        """Begin cycling through waypoints until stopped."""
        if self._running:
            return
        self._running = True
        self.watchdog.start()

        for waypoint in self._waypoint_cycle:
            if not self._running:
                break
            self._move_to_waypoint(waypoint)

    def stop(self) -> None:
        """Stop robot movement and watchdog monitoring."""
        if not self._running:
            return
        self._running = False
        self.watchdog.stop()
        print("Robot stopped due to communication loss or manual stop.")

    def receive_heartbeat(self) -> None:
        """Receive a communication heartbeat to keep the watchdog alive."""
        self.watchdog.feed()

    def _move_to_waypoint(self, waypoint: str) -> None:
        print(f"Moving to waypoint: {waypoint}")
        time.sleep(1)
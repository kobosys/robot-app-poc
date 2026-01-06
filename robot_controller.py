import itertools
import os
import time
from typing import Iterable, List, Sequence, Set

import requests

from watchdog import Watchdog


class RobotController:
    """Iterates through waypoints and stops on communication loss."""

    def __init__(
        self,
        waypoints: Sequence[str],
        watchdog_timeout: float = 5.0,
        *,
        base_url: str | None = None,
        auth_token: str | None = None,
        request_timeout: float = 5.0,
        poll_interval: float = 0.5,
    ):
        if not waypoints:
            raise ValueError("At least one waypoint is required")
        self.waypoints: List[str] = list(waypoints)
        self._waypoint_cycle: Iterable[str] = itertools.cycle(self.waypoints)
        self._running = False
        self._current_action_id: str | None = None
        self.watchdog = Watchdog(watchdog_timeout, self.stop)

        self.base_url = (base_url or os.getenv("SLAMWARE_BASE_URL", "http://localhost:1445")).rstrip(
            "/"
        )
        self.auth_token = auth_token or os.getenv("SLAMWARE_AUTH_TOKEN")
        self.request_timeout = request_timeout
        self.poll_interval = poll_interval
        self.session = requests.Session()

    def start(self) -> None:
        """Begin cycling through waypoints until stopped."""
        if self._running:
            return
        self._validate_waypoints()
        self._running = True
        self.watchdog.start()

        try:
            for waypoint in self._waypoint_cycle:
                if not self._running:
                    break
                self._move_to_waypoint(waypoint)
        finally:
            self._running = False
            self.watchdog.stop()
            self._current_action_id = None

    def stop(self) -> None:
        """Stop robot movement and watchdog monitoring."""
        self._stop_current_action()
        if not self._running:
            return
        self._running = False
        self.watchdog.stop()
        print("Robot stopped due to communication loss or manual stop.")

    def receive_heartbeat(self) -> None:
        """Receive a communication heartbeat to keep the watchdog alive."""
        self.watchdog.feed()

    def _move_to_waypoint(self, waypoint: str) -> None:
        action_id = self._create_move_action(waypoint)
        self._current_action_id = action_id
        print(f"Moving to waypoint: {waypoint} (action: {action_id})")

        while self._running:
            status = self._get_action_status(action_id)
            if self._is_action_complete(status):
                print(f"Reached waypoint {waypoint} (status: {status}).")
                break
            if self._is_action_failed(status):
                raise RuntimeError(f"Movement to {waypoint} failed (status: {status}).")
            time.sleep(self.poll_interval)

        self._current_action_id = None

    def _create_move_action(self, waypoint: str) -> str:
        payload = {
            "action_type": "slamtec.agent.actions.MultiFloorMoveAction",
            "params": {"target": {"poi_name": waypoint}},
        }
        response = self._request("POST", "/api/core/motion/v1/actions", json=payload)

        data = response.json()
        action_id = data.get("action_id") or data.get("id")
        if not action_id:
            raise RuntimeError("Action creation response did not include an action id.")
        return str(action_id)

    def _get_action_status(self, action_id: str) -> str:
        response = self._request("GET", f"/api/core/motion/v1/actions/{action_id}")
        data = response.json()
        return str(data.get("status") or data.get("state") or "").lower()

    def _stop_current_action(self) -> None:
        try:
            self._request("DELETE", "/api/core/motion/v1/actions/:current")
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to stop current action: {exc}")

    def _validate_waypoints(self) -> None:
        response = self._request("GET", "/api/multi-floor/map/v1/pois")
        try:
            poi_data = response.json()
        except ValueError as exc:  # noqa: B902
            raise RuntimeError("Failed to decode POI list from Slamware.") from exc

        available = self._extract_poi_names(poi_data)
        missing = [name for name in self.waypoints if name not in available]
        if missing:
            raise ValueError(f"Waypoints not found on robot: {', '.join(missing)}")

    def _extract_poi_names(self, data: object) -> Set[str]:
        names: Set[str] = set()
        if isinstance(data, dict):
            for key, value in data.items():
                if key in {"name", "poi_name", "poiName"} and isinstance(value, str):
                    names.add(value)
                names.update(self._extract_poi_names(value))
        elif isinstance(data, list):
            for item in data:
                names.update(self._extract_poi_names(item))
        return names

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Content-Type", "application/json")
        if self.auth_token:
            headers.setdefault("Authorization", f"Bearer {self.auth_token}")

        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=self.request_timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def _is_action_complete(self, status: str) -> bool:
        return status in {"succeeded", "completed", "finished", "done"}

    def _is_action_failed(self, status: str) -> bool:
        return status in {"failed", "error", "canceled", "cancelled"}

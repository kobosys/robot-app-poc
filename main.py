import threading
import time

from robot_controller import RobotController


def send_heartbeats(controller: RobotController, duration: float, interval: float = 1.0) -> None:
    """Send heartbeats for a duration to keep the robot running."""
    end_time = time.monotonic() + duration
    while time.monotonic() < end_time:
        controller.receive_heartbeat()
        time.sleep(interval)
    print("Communication lost: stopping heartbeats.")


def main() -> None:
    waypoints = ["A", "B", "C"]
    controller = RobotController(waypoints, watchdog_timeout=3.0)

    # Heartbeats are simulated in a background thread. When they stop, the
    # watchdog will call stop() and halt movement.
    threading.Thread(
        target=send_heartbeats, args=(controller, 7), daemon=True
    ).start()

    try:
        controller.start()
    except KeyboardInterrupt:
        controller.stop()


if __name__ == "__main__":
    main()
    ##추가변경
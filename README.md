# robot-app-poc

Python-based proof of concept for a robot controller that cycles through waypoints and stops when communication is lost.

## Structure
- `main.py`: Application entry point that boots the controller and simulates communication heartbeats.
- `robot_controller.py`: `RobotController` class that iterates over waypoints and interfaces with the watchdog.
- `watchdog.py`: Watchdog timer that stops the robot if heartbeats stop.

## Running
Requires Python 3.9+.

```bash
python main.py
```

The example run will cycle through waypoints A, B, and C. A background thread sends periodic heartbeats; once they stop, the watchdog triggers `stop()` to halt the controller.

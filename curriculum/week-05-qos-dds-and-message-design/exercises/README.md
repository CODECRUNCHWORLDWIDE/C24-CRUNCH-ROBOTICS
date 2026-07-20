# Week 5 — Exercises

Three focused drills on a running ROS2 graph. Each takes 30–60 minutes. Do them in order — exercise 3 reuses the mental model you build in 1 and 2. Run everything against your **week-3 differential-drive robot** in Gz Sim (or, if your sim is broken, the standalone publishers each exercise provides).

## Index

1. **[Exercise 1 — Sensor QoS on the week-3 robot](exercise-01-sensor-qos.md)** — set the robot's `/scan` and `/imu/data` to `BEST_EFFORT` / `KEEP_LAST` / depth 5, and verify with `ros2 topic info -v` that both endpoints agree. (~45 min, guided)
2. **[Exercise 2 — The latched map](exercise-02-latched-map.py)** — a `RELIABLE` / `TRANSIENT_LOCAL` / depth-1 map publisher and a *late* subscriber that still receives the map. Prove durability works. (~40 min, runnable)
3. **[Exercise 3 — The mismatch probe](exercise-03-mismatch-probe.py)** — deliberately mismatch publisher and subscriber QoS, register the rmw incompatible-QoS event callback, and capture the silent failure in your own logs. (~45 min, runnable)

## How to work the exercises

- Have your **week-3 robot** spawning in Gz Sim before you start. `ros2 topic echo /scan` should show data. If it doesn't, the standalone `LaserScan` publisher in Exercise 1 is your fallback.
- Source your overlay every new terminal: `source install/setup.bash`. Half of all "node not found" pain is an unsourced terminal.
- **Read `ros2 topic info -v` before and after every change.** The two QoS blocks are your ground truth. Train the habit of diffing them by eye.
- When a subscriber "isn't working," run the §4 decision tree from Lecture 2 before you touch code. Discovery first, QoS second, version third, semantics last.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match, you're not done.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package required. Source ROS2 Jazzy and run them directly:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-02-latched-map.py
```

Each runs both a publisher and a subscriber under a `MultiThreadedExecutor` so you can see the full handshake in one process, then in two terminals for the realistic late-join case. Instructions are in the file headers.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-05` to compare.

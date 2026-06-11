# Week 43 — Exercises

Three focused exercises that build the dashboard and the takeover plumbing piece by piece. Do them in order; later ones assume earlier ones. Together they are most of the mini-project's substance, so do them on your real capstone workspace, not a throwaway.

## Index

1. **[Exercise 1 — Wire the Foxglove telemetry dashboard](exercise-01-foxglove-telemetry-dashboard.md)** — stand up `foxglove_bridge`, build the layout, and stream live pose, costmap, the policy's chosen action, and the latched safety-filter banner. Recolor the policy-action arrow red when the safety filter overrides. (~60 min)
2. **[Exercise 2 — Add the CPU/GPU load panel](exercise-02-cpu-gpu-load-panel.py)** — a runnable `rclpy` node that publishes CPU/GPU/thermal load as a `diagnostic_msgs/DiagnosticArray`, rendered as Foxglove Gauge + Indicator panels. Works on a Jetson (via `jtop`/`tegrastats`), a dGPU box (via `nvidia-smi`), or CPU-only (via `psutil`). (~60 min)
3. **[Exercise 3 — The teleop-takeover arbiter](exercise-03-teleop-takeover-arbiter.py)** — a runnable lifecycle-managed `/cmd_vel` arbiter implementing the one-click takeover: atomic authority flips, a one-cycle safe-stop, a teleop-link watchdog, and the latched `/control/authority` topic that drives the dashboard banner. (~60 min)

## How to work the exercises

- Read the prompt. Skim, don't memorize.
- **Type the code yourself.** Do not copy-paste. The muscle memory of writing a lifecycle node and a latched publisher is the point.
- Run it against your capstone (or sim). See the panels light up. Watch the banner change.
- If you get stuck for more than 10 minutes, peek at the inline hints at the bottom of each file.
- Every exercise ends with the **"operator can see it"** marker visible on your dashboard:

  ```
  [ops] heartbeat OK · authority=AUTONOMY · cycle p99=27ms · gpu=61% · thermal=58°C
  ```

  If a field on that line is not live on your dashboard after the relevant exercise, you are not done.

## Running the runnable exercises

Exercises 2 and 3 are real `rclpy` nodes. Build and source your capstone workspace first, then run them as plain scripts (they call `rclpy.init()` themselves):

```bash
colcon build --packages-select capstone_ops capstone_msgs
source install/setup.bash
python3 exercises/exercise-02-cpu-gpu-load-panel.py
# in another terminal:
python3 exercises/exercise-03-teleop-takeover-arbiter.py --ros-args -p control_period:=0.05
```

Both assume the `capstone_msgs` package (with `SafetyTrigger.msg`, `Heartbeat.msg`, and `PolicyAction.msg` from the lecture notes) builds in your workspace. If it does not yet, define those three messages first — Lecture 2 §5 has the full `Heartbeat.msg`.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-43` to compare.

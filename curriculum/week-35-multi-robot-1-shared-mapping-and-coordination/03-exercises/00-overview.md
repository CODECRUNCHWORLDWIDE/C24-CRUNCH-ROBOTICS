# Week 35 — Exercises

Three focused drills on a multi-robot ROS2 graph. Each takes 40–60 minutes. Do them in order — exercise 3 reuses the merger you build in exercise 2, and both assume the namespaced bring-up from exercise 1. Run everything against two copies of your **week-8 `crunchbot_bringup`** robot in Gz Sim (or, where noted, the standalone grid publishers the exercise provides).

## Index

1. **[Exercise 1 — Namespaced two-robot bring-up](./exercise-01-namespaced-bringup.md)** — bring up two robots from one launch file under `robotA`/`robotB` namespaces, prove zero topic and TF collisions, and verify both resolve into a shared `world` frame. (~50 min, guided)
2. **[Exercise 2 — Merge two grids](./exercise-02-merge-two-grids.py)** — a runnable merger that fuses two `OccupancyGrid`s with a known relative transform into one `/shared_map`, using the occupied-wins fusion rule. Prove the merge is correct. (~45 min, runnable)
3. **[Exercise 3 — The stale-transform probe](./exercise-03-stale-transform-probe.py)** — inject a wrong/stale inter-robot transform, watch the merged map double-wall, and quantify the error against the correct merge. (~45 min, runnable)

## How to work the exercises

- Have **two robots** spawnable in Gz Sim before you start. The week-8 `crunchbot_bringup` launched twice under two namespaces is the target; exercise 1 builds exactly that.
- Source your overlay in every new terminal: `source install/setup.bash`. Half of all "node not found" pain is an unsourced terminal — and in a multi-robot graph it's twice as confusing.
- **Run `ros2 run tf2_ros tf2_echo world robotB/base_link` before and after every change.** If it throws `LookupException`, your shared `world` frame isn't tied to robot B, and nothing downstream will be right. This is your primary multi-robot diagnostic, the `ros2 topic info -v` of this week.
- When the shared map "looks wrong," run the §5 decision tree from Lecture 2 before you touch code. Transform first, then missing-region, then fusion, then drift.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match, you're not done.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package required, and they fabricate their own grids so they run with or without a working sim. Source ROS2 Jazzy and run them directly:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-02-merge-two-grids.py
```

Instructions are in each file's header. Exercise 2 prints a PASS/FAIL and exits accordingly; exercise 3 prints a quantified double-wall error.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-35` to compare.

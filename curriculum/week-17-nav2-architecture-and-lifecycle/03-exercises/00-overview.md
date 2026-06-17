# Week 17 — Exercises

Three focused drills on a running Nav2 stack. Each takes 30–60 minutes. Do them in order — exercise 3 reuses the costmap mental model you build in 1 and 2. Run everything against your **week-7 map** with the **week-3 diff-drive robot** in Gz Sim.

## Index

1. **[Exercise 1 — Bring up Nav2 and introspect it](./exercise-01-bringup-and-introspect.md)** — launch the full stack on your week-7 map, set the AMCL initial pose, send a goal from rviz2, and read the lifecycle states and both costmaps live. (~45 min, guided)
2. **[Exercise 2 — A `NavigateToPose` client with a fail-safe](./exercise-02-navigate-to-pose-client.py)** — a Python action client that sends goals, streams feedback, cancels, and stops the base when the planner crashes (the syllabus fail-safe). (~45 min, runnable)
3. **[Exercise 3 — The costmap monitor](./exercise-03-costmap-monitor.py)** — subscribe to both costmaps, decode the `OccupancyGrid`, report inflation coverage, and watch it change as you re-tune `inflation_radius` live. (~40 min, runnable)

## How to work the exercises

- Have your **week-7 map** loadable and your **week-3 robot** spawning in Gz Sim before you start. `ros2 topic echo /scan` should show data and AMCL should be able to localize.
- Source your overlay every new terminal: `source install/setup.bash`. Half of all "node not found" pain is an unsourced terminal.
- **Run `ros2 lifecycle get` on every server before you debug anything.** If a server isn't `active [3]`, that is your bug — stop and fix it before touching goals.
- When the robot "won't navigate," run the §4 decision tree from Lecture 2 before you touch code. Lifecycle first, TF second, costmap third, planner/controller last.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match, you're not done.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package required. Source ROS2 Jazzy (and your overlay so the Nav2 message types resolve) and run them directly:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-02-navigate-to-pose-client.py --x 1.5 --y 0.5
```

Exercise 2 talks to a *running* Nav2 stack (bring it up first, per Exercise 1). Exercise 3 only needs the costmaps published, which any Nav2 bring-up provides.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-17` to compare.

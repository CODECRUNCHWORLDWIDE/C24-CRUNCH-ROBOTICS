# Week 2 — Exercises

Three focused drills that take you from an empty workspace to a live, debuggable tf2 tree. Do them in order. Exercise 2 broadcasts the joint that Exercise 3 looks up, and the mini-project composes all three into one launch file.

## Index

1. **[Exercise 1 — Build the four-link static tree](exercise-01-four-link-static-tree.md)** — stand up `base → shoulder → elbow → wrist` with one `static_transform_publisher` per joint, verify the tree is connected with `view_frames`, and read it back with `tf2_echo`. (~45 min)
2. **[Exercise 2 — Add a dynamic broadcaster](exercise-02-dynamic-broadcaster.py)** — replace the static `shoulder → elbow` edge with a `rclpy` `TransformBroadcaster` that rotates the elbow at a steady rate, and confirm the moving frame in `rviz2`. (~40 min)
3. **[Exercise 3 — A lookup listener that fails loudly](exercise-03-lookup-listener.py)** — write a listener that looks up `wrist` in `base`, prints the pose, and logs a precise, actionable error for each of the three tf2 exceptions when you break the tree. (~45 min)

## Before you start

You need ROS2 Jazzy sourced in every terminal you open:

```bash
source /opt/ros/jazzy/setup.bash
```

Install the tf2 tooling and Python bindings once:

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-tf2-ros \
  ros-jazzy-tf2-tools \
  ros-jazzy-tf-transformations \
  ros-jazzy-tf2-geometry-msgs
```

`view_frames` renders a PDF, so it needs Graphviz:

```bash
sudo apt install -y graphviz
```

## How to work the exercises

- **Type the code yourself.** Do not copy-paste the Python files. The muscle memory of `TransformBroadcaster`, `Buffer`, and `lookup_transform` is the entire point.
- Keep **three terminals** open: one for the broadcaster(s), one for the listener, one for `tf2_echo` / `view_frames`. tf2 is a multi-process subsystem; you debug it by watching several processes at once.
- Every exercise ends with a **clean tree**: `ros2 run tf2_tools view_frames` must produce a `frames.pdf` showing a single connected `base → shoulder → elbow → wrist` chain — no orphan frames, no second root, no `NO_PARENT` in the console. If it doesn't, you are not done.
- If a lookup throws, **read which exception it is** before you change anything. `LookupException`, `ConnectivityException`, and `ExtrapolationException` mean three different things and have three different fixes (see lecture 1, §1.7).

## The two runnable files

Exercises 2 and 3 are real `rclpy` nodes (`.py`), not Markdown. Run each with `python3`, after sourcing ROS2:

```bash
python3 exercise-02-dynamic-broadcaster.py
# in another terminal:
python3 exercise-03-lookup-listener.py
```

They have no package dependencies beyond what `apt` installed above, so you can run them directly without building a colcon workspace. The mini-project promotes them into a proper package.

There are no solutions checked in. The course is open source — solutions live in forks. When you finish, search GitHub for `c24-week-02` to compare against other learners.

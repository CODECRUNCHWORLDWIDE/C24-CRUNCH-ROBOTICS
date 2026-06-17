# Week 33 — Exercises

Three drills that build from "swap the engine under one sim" to "stand the robot up in the other sim." Do them in order — Exercise 2's metrics node is the measurement tool the challenge and mini-project both reuse. Run everything against your **week-3 differential-drive robot** so every comparison holds the robot fixed.

## Index

1. **[Exercise 1 — Swap the physics engine under Gz Sim](./exercise-01-physics-engine-swap.md)** — run the same robot in Gz Sim under two engines (DART vs Bullet), and observe that contact and step-time *change* though the robot didn't. (~45 min, guided)
2. **[Exercise 2 — Measure a simulator from ROS2](./exercise-02-sim-metrics.py)** — a node that subscribes to `/clock` and a sensor topic and computes real-time factor, step-time, and sensor-rate fidelity — the sim-agnostic measurement tool for the whole week. (~50 min, runnable)
3. **[Exercise 3 — Stand the robot up in Isaac Sim](./exercise-03-isaac-scene-setup.py)** — set up the robot in Isaac Sim via the Python API and bridge it to ROS2 (Path A); or, Path B, run the documented Gz-engine substitution and reason about the Isaac equivalent. (~60 min, runnable)

## How to work the exercises

- **Keep the ROS2 stack sim-agnostic.** Your behavior/measurement nodes subscribe to `/scan`, `/clock`, `/cmd_vel` and must not care which sim is upstream. That's the property that makes the comparison fair (Lecture 2 §3.1).
- **Exercise 2 needs no special hardware** — it's a plain `rclpy` node and works against *any* simulator that bridges `/clock` and a sensor topic. Do it early; you'll lean on it all week.
- **Exercise 3 is the Path A/B fork.** With an NVIDIA GPU + Isaac Sim, do the real Isaac scene setup. Without one, the file's `--path-b` mode runs the Gz-engine substitution and prints the Isaac concepts you'd be exercising, so you still complete the comparison with two Gz engines.
- Each runnable exercise (`.py`) ends with an **expected output** block. The exact numbers depend on your machine; the *shape* (a metrics table, a scene that steps) is what must match.

## Running the Python exercises

Exercise 2 is a ROS2 node — source your overlay and run it while a sim publishes:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-02-sim-metrics.py --duration 30 --sensor /scan
```

Exercise 3 (Path A) runs *inside* Isaac Sim's Python (`SimulationApp`); Path B runs standalone:

```bash
# Path A (Isaac Sim present):  ./python.sh exercise-03-isaac-scene-setup.py
# Path B (no NVIDIA GPU):      python3 exercise-03-isaac-scene-setup.py --path-b
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-33` to compare.

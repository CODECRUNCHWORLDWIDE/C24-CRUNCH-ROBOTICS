# Week 46 — Exercises

Three drills that build the gameday machinery before the live gameday. Do them in order — exercise 1 designs the experiment, exercise 2 builds the detection-and-degradation half, exercise 3 builds the deadlock-recovery half. Run the Python against your capstone if you can; both `.py` files ship a self-contained simulator so the logic is exercisable even if your robot is down.

## Index

1. **[Exercise 1 — Design the drill](./exercise-01-design-the-drill.md)** — write the steady-state hypothesis, the injection, the blast radius (and the proof your E-stop is outside it), the predicted response, and the abort plan, for *both* drills. No code — this is the science that makes the live drill more than a demo. (~50 min)
2. **[Exercise 2 — The sensor watchdog + health aggregator](./exercise-02-sensor-watchdog.py)** — a runnable watchdog that detects a `/scan` dropout via staleness + deadline, fuses per-sensor status into one robot-health signal, and emits DEGRADED vs FAULT. Fill in the TODOs; the checks must pass. (~50 min)
3. **[Exercise 3 — The deadlock detector + recovery ladder](./exercise-03-deadlock-detector.py)** — a runnable detector that recognizes the replan-without-progress signature and walks the recovery ladder (relax → clear → operator-assist → stop). Fill in the TODOs; the checks must pass. (~50 min)

## How to work the exercises

- **Write the hypothesis before you break anything** (Exercise 1). A drill with no prediction teaches nothing, because anything that happens can be rationalized after the fact (Lecture 1 §6).
- **Test the safety path first.** Before either drill, confirm the E-stop still latches when you inject the fault (Lecture 2 §1). A safety path you haven't chaos-tested is a hope.
- **Detection, then response.** The first question is never "did it crash" — it's "did it *notice*" (Lecture 2 §6). The exercises grade detection latency and the correctness of the degraded/recovery action.
- **Bag everything** when you run against the real robot. The postmortem timeline must come from data (`ros2 bag record -a`), not memory.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match its shape, you're not done.

## Running the Python exercises

Pure-Python simulators — no ROS2 required to exercise the logic, so they run anywhere.

```bash
python3 -c "import numpy; print('numpy', numpy.__version__)"
python3 exercise-02-sensor-watchdog.py
python3 exercise-03-deadlock-detector.py
```

When you wire the real versions into your capstone, the watchdog becomes a ROS2 node with QoS deadline callbacks (Lecture 1 §3) and the deadlock detector subscribes to your planner's replan count and `/odom`.

There are no solutions checked in. After you finish, search GitHub for `c24-week-46` to compare with other learners' forks.

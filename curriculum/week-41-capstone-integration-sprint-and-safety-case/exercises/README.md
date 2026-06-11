# Week 41 — Exercises

Three exercises that build directly into the graded mini-project. The first is a writing drill (the hardest kind for engineers — that's the point). The second and third are runnable code: a `rclpy` safety node and a YAML-driven FMEA tool. Do them in order; the mini-project assembles all three.

## Index

1. **[Exercise 1 — Intended use & foreseeable misuse](exercise-01-intended-use-and-misuse.md)** — draft the two sections that bound your entire safety case: what the robot is *for* (intended use + ODD) and what people will *actually do* (reasonably foreseeable misuse). (~50 min)
2. **[Exercise 2 — Watchdog + confidence gate](exercise-02-watchdog-and-confidence-gate.py)** — a runnable `rclpy` software watchdog that latches a software E-stop when a sensor goes silent, plus a perception confidence gate. Fill in the TODOs; run the included self-test. (~60 min)
3. **[Exercise 3 — Hazard log + FMEA tool](exercise-03-hazard-log-fmea.py)** — a runnable tool that loads hazard-log and FMEA rows from YAML, computes risk ratings and RPN, applies the criticality cutoff, sorts, and emits a Markdown table for your safety case. (~50 min)

## How to work the exercises

- **Type the code yourself.** Do not copy-paste. The watchdog and the gate are patterns you will reuse on every robot you ever ship; build the muscle memory now.
- Exercises 2 and 3 are *runnable* and ship with a `--selftest` / `pytest`-style check. They must pass before you call the exercise done. Green test, or it isn't finished.
- Exercise 1 has no compiler to satisfy — its acceptance test is harsher: *a peer reads it and cannot find a hazard you failed to bound.* Trade drafts with someone in your cohort.
- Everything you write here feeds the mini-project. The intended-use section *is* the mini-project's intended-use section. The FMEA tool *generates* the mini-project's FMEA table. Don't throw any of it away.

## Environment

These assume a working **ROS2 Jazzy** workspace on **Ubuntu 24.04**, Python 3.12, with `rclpy` and `PyYAML` available (both ship in the Jazzy dev image). Exercise 2 runs as a standalone `rclpy` node — no hardware required; it self-tests with simulated heartbeats. Exercise 3 is pure Python + PyYAML and runs anywhere.

```bash
# Confirm your environment before starting.
source /opt/ros/jazzy/setup.bash
python3 -c "import rclpy, yaml; print('rclpy + yaml OK')"
```

There are no solutions checked in. Solutions live in your capstone repo, under `safety-case/`. After you finish, your hazard log and FMEA should regenerate from YAML on every commit — that is the senior-engineer outcome this week is training.

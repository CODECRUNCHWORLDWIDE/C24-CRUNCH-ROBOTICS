# Week 19 — Exercises

Three focused drills on behavior trees, from tracing to a full patrol simulation. Each takes 30–60 minutes. Do them in order — exercise 3 (the patrol) reuses the tick engine and reactivity you build in 1 and 2. The tracing and tick-engine exercises are pure Python (no ROS2 needed); the patrol simulation is also pure Python so you can verify the *logic* before wiring it to Nav2 in the mini-project.

## Index

1. **[Exercise 1 — Read and trace trees](./exercise-01-read-and-trace-trees.md)** — trace five small trees by hand, predict the exact tick sequence and the robot's behavior, then verify your predictions (against the tick engine and, optionally, Groot 2). (~50 min, guided)
2. **[Exercise 2 — The tick engine](./exercise-02-tick-engine.py)** — a runnable, correct minimal BT tick engine (`Sequence`, `Fallback`, `Parallel`, `ReactiveSequence`, decorators) with a self-checking harness that proves the control-node semantics. (~45 min, runnable)
3. **[Exercise 3 — The patrol with yield and retreat](./exercise-03-patrol-blackboard.py)** — a runnable patrol-with-yield simulation using the engine: reactive yielding to a (simulated) person, a 60 s retreat timeout, and a blackboard, with self-checks for all three scenarios. (~50 min, runnable)

## How to work the exercises

- The exercises need only **Python 3.12** (no third-party packages). The point is to learn the *semantics* cheaply before the C++ mini-project.
- **Run the self-checks.** Each `.py` ends with assertions that prove the control-node semantics and the patrol scenarios. If an assertion fails, you have a bug — read the message, it names the property that broke.
- When a tree "does the wrong thing," check whether you used a **reactive** vs **memory** control node (Lecture 1 §3.4) — it's the #1 cause of subtly-wrong behavior.
- For the optional Groot 2 verification in Exercise 1, you can author the tiny trees in Groot 2's editor and reason about them visually even without a running C++ tree.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match the *shape*, you're not done.

## Running the Python exercises

The two `.py` files are standalone:

```bash
python3 exercise-02-tick-engine.py
python3 exercise-03-patrol-blackboard.py --person-at 5 --person-leaves 12
```

Exercise 3 accepts flags to script when a (simulated) person appears and leaves, so you can drive all three scenarios (no person, person leaves in time, person stays past the timeout). Read the file headers for the full flag list.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-19` to compare.

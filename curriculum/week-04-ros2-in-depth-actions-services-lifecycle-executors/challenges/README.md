# Week 4 — Challenges

One challenge this week, and it is the bridge between the exercises and the mini-project. The exercises gave you a correct, preemptible, multi-threaded `Spin90` action server. The challenge wraps that server in a **managed lifecycle node** and makes you *prove* — not assert, prove — that it refuses goals while inactive. That property is the entire reason safety-critical robotics uses lifecycle nodes, and it is the property the mini-project and the capstone bring-up depend on.

| # | File | What you build | Est. time |
|---|------|----------------|-----------|
| 1 | [challenge-01-lifecycle-spin90.md](./challenge-01-lifecycle-spin90.md) | Convert the `Spin90` action server into a `LifecycleNode` with clean `configure` / `activate` / `deactivate` / `cleanup` transitions, and an automated test that proves goals are rejected while `inactive`. | ~2h |

## How challenges differ from exercises

Exercises are guided — they hand you the structure and most of the code. A challenge hands you a spec and acceptance criteria and expects you to architect the solution yourself. There is no starter file. You will reuse your Exercise 3 server as the *active* behavior, but the lifecycle scaffolding, the state-aware goal rejection, and the proof-of-rejection test are yours to write.

The acceptance criteria are testable. If you cannot run a command that demonstrates each checkbox, you have not met it.

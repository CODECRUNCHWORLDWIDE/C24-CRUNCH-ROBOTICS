# Week 40 — Exercises

Three exercises, in order. They build the kickoff ritual from Lecture 2 and the contract-reading from Lecture 1 into runnable artifacts you carry into the mini-project. Exercise 1 turns the capstone spec into a requirements-traceability table and a "what I heard" restatement — the document that defends the rest of your milestone. Exercise 2 writes the pre-flight check node that proves your composed graph is healthy before any goal is sent. Exercise 3 writes the telemetry spine that makes every layer of the stack observable on a Foxglove dashboard, plus the `/fleet/heartbeat` the spec requires.

Do them in order. Do not skip Exercise 1 because it "is just writing" — the traceability table is the artifact a reviewer reads your milestone against, and the mini-project's acceptance criteria assume you can point at the row that owns each requirement. Exercises 2 and 3 are the two nodes the mini-project's launch graph cannot run without.

| # | File | Type | What you build | Est. time |
|---|------|------|----------------|-----------|
| 1 | [exercise-01-read-the-spec-and-write-it-back.md](./exercise-01-read-the-spec-and-write-it-back.md) | Guided (Markdown) | Turn the capstone spec into a requirements-traceability table (requirement → restatement → owning artifact → acceptance test) and a one-page "what I heard" restatement with explicit non-goals. | 90 min |
| 2 | [exercise-02-preflight-check-node.py](./exercise-02-preflight-check-node.py) | Runnable (`rclpy`) | A pre-flight check node that verifies the clock is advancing, every required topic publishes at its expected rate, every required transform is resolvable and recent, and every managed node reports `active` — and exits non-zero (aborting the run) on any failure. | 120 min |
| 3 | [exercise-03-telemetry-spine.py](./exercise-03-telemetry-spine.py) | Runnable (`rclpy`) | A telemetry aggregator that republishes every layer's state onto `/telemetry/*` for a Foxglove dashboard (pose, detections, planned path, policy action, safety-filter status) and publishes a schema-conformant `/fleet/heartbeat` at 1 Hz. | 120 min |

## Prerequisites for all three

- ROS2 Jazzy on Ubuntu 24.04, sourced (`source /opt/ros/jazzy/setup.bash`).
- The composed capstone stack from earlier weeks, or enough of it that the topics the exercises reference exist. Both `.py` exercises ship a `--demo` mode that publishes synthetic versions of every topic, so you can run and verify them headless before you have the full stack live.
- `tf2_ros`, `lifecycle_msgs`, `nav_msgs`, `vision_msgs`, `geometry_msgs`, and `std_msgs` available (all part of a standard Jazzy desktop install).
- A Foxglove account (free tier) for Exercise 3's dashboard half. The node publishes standard ROS2 messages, so Foxglove (via the `foxglove_bridge`) or `rviz2` both visualize them.

## How to run a `.py` exercise

These files run two ways:

1. **Against your live stack** (the real way): source your workspace, bring up the composed graph, then `python3 exercise-02-preflight-check-node.py`. The node introspects the live graph.
2. **Standalone in `--demo` mode** (for fast iteration and CI): `python3 exercise-02-preflight-check-node.py --demo`. The node spawns synthetic publishers for every topic, transform, and lifecycle service it checks, so you can verify the *check logic* without the full robot. Flip a `--break <check>` flag to make one check fail and confirm the abort path.

Each file's header block has the exact commands and the expected output.

# Week 24 — Exercises

Three exercises, in order. They build the integration discipline from Lecture 1 and the safety stance from Lecture 2 into runnable artifacts you carry into the mini-project. Exercise 1 composes Nav2 and MoveIt2 into one graph and produces the integration interface table that catches the four defects. Exercise 2 writes the pre-flight check node that proves the composed graph is healthy before any goal is sent. Exercise 3 writes the software E-stop that cancels both the base and the arm on latch, with a latch-to-stop latency measurement.

Do them in order. Do not skip Exercise 1 because it "is just composition and a table" — the interface table is the artifact the milestone is debugged against, and Exercises 2 and 3 assume the composed graph it produces. Exercises 2 and 3 are the two nodes the mini-project's launch graph cannot run without.

| # | File | Type | What you build | Est. time |
|---|------|------|----------------|-----------|
| 1 | [exercise-01-compose-and-trace.md](./exercise-01-compose-and-trace.md) | Guided (Markdown) | Bring Nav2 + MoveIt2 up in one graph, build the integration interface table (topic / type / frame / rate / QoS per seam), and diagnose the four integration defects on your own graph. | 90 min |
| 2 | [exercise-02-preflight-check.py](./exercise-02-preflight-check.py) | Runnable (`rclpy`) | A pre-flight check node that verifies the clock advances, every required topic publishes at rate, every required transform resolves and is recent, every managed node is `active`, and command topics have exactly one publisher — and exits non-zero (aborting the run) on any failure. | 120 min |
| 3 | [exercise-03-estop-latch.py](./exercise-03-estop-latch.py) | Runnable (`rclpy`) | A software E-stop monitor that, on `/safety/estop` latch, cancels the Nav2 navigation action and the MoveIt2 trajectory and zeroes `/cmd_vel`, plus a latch-to-stop latency measurement against the 200 ms budget. | 120 min |

## Prerequisites for all three

- ROS2 Jazzy on Ubuntu 24.04, sourced (`source /opt/ros/jazzy/setup.bash`).
- The composed base+arm stack from Lecture 1 / Exercise 1, or enough of it that the topics, transforms, and actions the exercises reference exist. Both `.py` exercises ship a `--demo` mode that publishes synthetic versions of every topic, transform, lifecycle service, and action, so you can run and verify them headless before you have the full stack live.
- `tf2_ros`, `lifecycle_msgs`, `nav2_msgs`, `control_msgs`, `geometry_msgs`, `nav_msgs`, and `std_msgs` available (all part of a standard Jazzy desktop + Nav2/MoveIt2 install).
- Groot 2 (optional, for visualizing the top-level behavior tree).

## How to run a `.py` exercise

These files run two ways:

1. **Against your live stack** (the real way): source your workspace, bring up the composed graph, then `python3 exercise-02-preflight-check.py`. The node introspects the live graph and the live actions.
2. **Standalone in `--demo` mode** (for fast iteration and CI): `python3 exercise-02-preflight-check.py --demo`. The node spawns synthetic publishers, transforms, lifecycle services, and action servers for everything it checks, so you can verify the *logic* without the full robot. Flip a `--break <check>` flag to make one check fail and confirm the abort path.

Each file's header block has the exact commands and the expected output. The `.py` exercises end with an **expected output** block — if your output doesn't match the *shape*, you're not done.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-24` to compare.

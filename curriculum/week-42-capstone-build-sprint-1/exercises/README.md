# Week 42 — Exercises

Three exercises, split by path. Exercises 1 and 2 are **Path A** (hardware). Exercise 3 is **Path B** (hardened sim deployment). Do the two that match your path; read the third so you can speak to it in the Week 48 defense.

These are integration exercises, not syntax drills, so they run longer than the usual week. Protect a real block of time and run them with your hands on the robot (A) or at the deployment target (B), not on your dev laptop in passing.

## Index

1. **[Exercise 1 — Bring up and verify](exercise-01-bring-up-and-verify.md)** *(Path A, ~75 min)* — Bring the robot up from cold metal, confirm every sensor publishes at rate with sane values, confirm every actuator responds with the correct sign, and assert the TF tree is fully connected. Produces a scripted, repeatable bring-up gate.
2. **[Exercise 2 — Trajectory drive and drift](exercise-02-trajectory-drive-and-drift.py)** *(Path A, ~90 min)* — Drive a 20-meter trajectory under the full stack, record a rosbag, and log the terminal drift of the fused estimate against a taped ground-truth endpoint.
3. **[Exercise 3 — Telemetry and cold boot](exercise-03-telemetry-and-cold-boot.py)** *(Path B, ~90 min)* — Add a telemetry heartbeat subscriber to the hardened launch graph and verify a clean cold boot in under 60 seconds, with a script that times boot-to-ready and asserts every node, sensor, and actuator is nominal.

## How to work the exercises

- **Read the prompt fully before touching anything.** Integration exercises punish improvisation.
- **Type the code yourself.** Do not copy-paste. The point of a bring-up script is that you understand every check it makes.
- **Run the verification before you trust the layer above it.** If Exercise 1's gate does not exit 0, do not start Exercise 2.
- **Record everything.** Every run this week produces a rosbag or a journal log. The number without the artifact is not a result.
- **Every exercise must end with a measured number and a PASS/FAIL**, in the `[capstone]` format from the week README. "It looked right" is not a result.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-42` to compare.

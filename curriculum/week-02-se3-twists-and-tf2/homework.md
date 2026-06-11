# Week 2 Homework

Six practice problems that revisit the week's topics — three of math (SE(3), twists, adjoints) and three of tooling (tf2). The full set should take about **5 hours** in total. Work in your Week 2 Git repository so each problem produces at least one commit you can point to later.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

Keep a Python REPL with `numpy` open for the math problems and three sourced ROS2 terminals open for the tf2 problems.

---

## Problem 1 — Invert a transform by hand, then by code

**Problem statement.** Take this SE(3) element (a +90° rotation about z, translated 2 m in x):

```python
import numpy as np

T = np.array([
    [0.0, -1.0, 0.0, 2.0],
    [1.0,  0.0, 0.0, 0.0],
    [0.0,  0.0, 1.0, 0.0],
    [0.0,  0.0, 0.0, 1.0],
])
```

1. On paper, compute `T_inv` using the block formula `[[R.T, -R.T @ t], [0, 1]]`. Write out the 4×4 result.
2. In code, write `invert_transform(T)` using the block formula (no `numpy.linalg.inv`).
3. Verify `invert_transform(T) @ T` is the identity to `1e-9`, and that your code result matches your paper result.
4. In a comment, state how many floating-point multiplies the block form does versus what a general 4×4 LU inverse would cost, and why the block form is also more numerically honest for an SE(3) element.

**Acceptance criteria.**

- A file `homework/p1_invert.py` that prints `T_inv`, prints `invert_transform(T) @ T`, and asserts the latter is `≈ I`.
- Your hand-computed `T_inv` appears as a comment and matches the code output.
- No `numpy.linalg.inv` anywhere in the file.
- Committed.

**Hint.** `R.T` of a +90°-about-z rotation is a −90°-about-z rotation. `-R.T @ t` with `t = [2, 0, 0]` gives `[0, 2, 0]`. So `T_inv` translates `[0, 2, 0]` after rotating −90° about z. Sanity-check: `T` maps the origin to `[2, 0, 0]`; `T_inv` must map `[2, 0, 0]` back to the origin.

**Estimated time.** 35 minutes.

---

## Problem 2 — Compose a chain and check non-commutativity

**Problem statement.** Define two transforms: `A` = drive forward 1 m in x (identity rotation, `t = [1, 0, 0]`), and `B` = turn +90° about z (no translation).

1. Compute `A @ B` and `B @ A`. Show they differ.
2. Interpret each in one sentence: which one is "drive forward, then turn" and which is "turn, then drive forward," and where does the robot end up in each case (give the resulting position of a point that started at the origin)?
3. Compose the full week-2 arm chain in code from the link parameters (`shoulder_z = 0.10`, `upper_arm = 0.25`, `forearm = 0.20`, all identity rotation) and confirm `T_base_wrist` has translation `[0.45, 0, 0.10]`. Then set the `shoulder → elbow` edge to a +90°-about-z rotation and recompute; predict the new wrist position **before** you run it.

**Acceptance criteria.**

- A file `homework/p2_compose.py` that prints `A @ B`, `B @ A`, asserts they differ, and prints both arm-chain results.
- A comment stating the physical interpretation of `A @ B` vs `B @ A` and the resulting origin positions.
- Your prediction for the rotated-elbow wrist position appears as a comment **above** the code that computes it, and matches.
- Committed.

**Hint.** `A @ B` applies `B` first (it is nearest the point). So `A @ B` = turn then drive = robot ends facing +y, displaced 1 m along its new heading. With the elbow rotated +90° about z, the forearm now points in +y from the elbow, so the wrist moves to roughly `[0.25, 0.20, 0.10]`.

**Estimated time.** 45 minutes.

---

## Problem 3 — Exponentiate a twist and round-trip the log

**Problem statement.** Implement the SE(3) exponential map `exp_se3(twist)` for a twist in **ROS order** `[v, ω]` (a 6-vector), using the closed-form expansion from lecture 2 (Rodrigues for the rotation, the `V` matrix for the translation). Then:

1. Take the pure-rotation twist `[0, 0, 0, 0, 0, π/2]` (no linear, +90° about z) and confirm `exp_se3` produces a +90°-about-z rotation with zero translation.
2. Take the screw twist `[1, 0, 0, 0, 0, π/2]` (unit linear along x, +90° about z) and confirm the result against a hand calculation of where a point at the origin lands.
3. Implement `log_se3(T)` (the inverse) and verify `log_se3(exp_se3(twist)) ≈ twist` to `1e-9` for ten random twists.

**Acceptance criteria.**

- A file `homework/p3_exp_log.py` with `exp_se3` and `log_se3`.
- The two named test cases print and match a comment stating the expected result.
- The round-trip assertion passes for ten random twists.
- Committed.

**Hint.** For the rotation, `R = I + sin(θ)/θ · [ω]× + (1 − cos θ)/θ² · [ω]×²` where `θ = ||ω||` and `[ω]×` is the skew matrix. The translation is `V @ v` where `V = I + (1 − cos θ)/θ² · [ω]× + (θ − sin θ)/θ³ · [ω]×²`. Guard the `θ → 0` case with the small-angle limit (`R → I`, `V → I`) to avoid dividing by zero.

**Estimated time.** 1 hour.

---

## Problem 4 — Build the static tree in a launch file

**Problem statement.** Reproduce Exercise 1's four-link tree, but as a single launch file `homework/p4_static_tree.launch.py` instead of three terminals. Use three `Node` entries for `tf2_ros`'s `static_transform_publisher`, each with `arguments=[...]` carrying the named flags (`--x`, `--z`, `--frame-id`, `--child-frame-id`, etc.).

1. Launch it with `ros2 launch homework/p4_static_tree.launch.py` (or after a `colcon build` if you package it).
2. Confirm `ros2 run tf2_tools view_frames` shows one connected `base → shoulder → elbow → wrist` tree.
3. Confirm `ros2 run tf2_ros tf2_echo base wrist` reports `[0.450, 0.000, 0.100]`.

**Acceptance criteria.**

- A working launch file that starts all three static publishers.
- `view_frames` produces a single connected tree (include the `frames.pdf` in the repo).
- `tf2_echo base wrist` reports the expected translation.
- Committed.

**Hint.** A minimal launch file is `from launch import LaunchDescription` / `from launch_ros.actions import Node` / `def generate_launch_description(): return LaunchDescription([Node(package='tf2_ros', executable='static_transform_publisher', arguments=['--z', '0.10', '--frame-id', 'base', '--child-frame-id', 'shoulder']), ...])`. You can run a standalone launch file directly with `ros2 launch ./p4_static_tree.launch.py`.

**Estimated time.** 40 minutes.

---

## Problem 5 — Time-travel: where was the wrist when the shutter fired?

**Problem statement.** Run the Exercise 2 dynamic broadcaster (rotating elbow). Write a listener `homework/p5_time_travel.py` that uses `lookup_transform_full` to answer: "Where was the `wrist`, expressed in the `base` frame, **0.5 seconds ago**?" Compare it to where the wrist is **now**. Print both and the difference.

`lookup_transform_full(target_frame, target_time, source_frame, source_time, fixed_frame)` is the time-travel API: it lets you ask for the source frame at one time and the target at another, bridged through a fixed frame. Here use `fixed_frame="base"`, `source_time = now - 0.5s`, `target_time = now`.

**Acceptance criteria.**

- A listener that prints the wrist-in-base position now and 0.5 s ago, and their difference.
- The difference is nonzero (the elbow is rotating) and consistent with the rotation rate (at 0.5 rad/s, the wrist sweeps a measurable arc in 0.5 s).
- A comment explaining, in one sentence, why time-travel needs a *fixed* frame argument.
- Committed.

**Hint.** Build the times from `self.get_clock().now()` and `rclpy.duration.Duration(seconds=0.5)`. The fixed frame is the frame assumed not to move between the two times; `base` is the natural choice here because the base is stationary. This is exactly the API you use in week 14 to project a depth image into the map frame at the instant the camera captured it.

**Estimated time.** 45 minutes.

---

## Problem 6 — Mini reflection essay

**Problem statement.** Write a 300–400 word reflection at `notes/week-02-reflection.md` answering:

1. Which clicked faster: the SE(3) math (transforms, twists, adjoints) or the tf2 tooling (buffers, lookups, exceptions)? Why do you think that is?
2. Before this week, did you think of tf2 as "magic that usually works"? What is one specific mental-model change that now lets you debug a tf2 error in minutes instead of hours?
3. Explain, to a teammate who only knows linear algebra, why a velocity transforms with the adjoint while a point transforms with the homogeneous matrix — in one paragraph, no equations.
4. Which of the three tf2 exceptions do you expect to hit most in the rest of C24, and what is your one-sentence diagnostic question for it?

**Acceptance criteria.**

- File exists, 300–400 words.
- Each numbered question is addressed in its own paragraph.
- File is committed.

**Hint.** This is for *you*, not for a grade. Be honest. Future-you, staring at an `ExtrapolationException` in the Nav2 costmap in week 17, will be grateful you wrote down your diagnostic question now.

**Estimated time.** 30 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 | 35 min |
| 2 | 45 min |
| 3 | 1 h 0 min |
| 4 | 40 min |
| 5 | 45 min |
| 6 | 30 min |
| **Total** | **~4 h 35 min** |

When you've finished all six, push your repo and open the [mini-project](./mini-project/README.md).

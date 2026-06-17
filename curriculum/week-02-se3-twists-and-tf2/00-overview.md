# Week 2 — SE(3), Twists, and tf2

Welcome to week 2 of **C24 · Crunch Robotics**. Week 1 gave you rotations — SO(3), quaternions, axis-angle, and a `rclpy` publisher spinning a pose in `rviz2`. This week we promote rotation to full rigid-body motion. A robot arm is not a stack of orientations; it is a stack of *poses* — rotation plus translation — and the mathematics that handles both together is the group **SE(3)**.

Two things have to land by Friday. First, the math: you must be able to write a homogeneous transform by hand, compose two of them in the right order, invert one without a `numpy.linalg.inv` call, and explain what a twist and an adjoint are without hand-waving. Second, the tooling: you must understand **tf2** — ROS2's transform library — as a living, timestamped representation of SE(3) at every joint of every robot. tf2 is the single most-used and most-misunderstood subsystem in ROS2. Half of all "my robot is in the wrong place" bugs are tf2 bugs. By the end of the week, when somebody pastes an `ExtrapolationException` into your team channel, you will know exactly what broke and how to fix it.

The thesis of the week, which we will repeat until it is reflexive: **every transform problem is a tree problem.** tf2 maintains a forest of frames connected by transforms. A lookup is a walk up the tree from the source frame to a common ancestor and back down to the target frame. When a lookup fails, it failed for one of three reasons — the frames are not connected, the buffer does not have data for the requested time, or the requested time is outside the buffered window. Learn to diagnose which of the three, and tf2 stops being magic.

## Learning objectives

By the end of this week, you will be able to:

- **Construct** a 4×4 homogeneous transform from a rotation matrix and a translation vector, and explain why the bottom row is `[0 0 0 1]`.
- **Compose** transforms in the correct order (`T_a_c = T_a_b @ T_b_c`) and **invert** an SE(3) element by hand using the block-transpose formula, not a generic matrix inverse.
- **Derive** a twist as the element of the Lie algebra se(3), and **exponentiate** a twist into a transform with the closed-form SE(3) exponential map.
- **Apply** the adjoint to transform a twist from one frame into another, and explain why velocity transforms differently than a point.
- **Explain** the tf2 architecture: the `Buffer`, the `TransformListener`, the `TransformBroadcaster`, the `StaticTransformBroadcaster`, and how a lookup walks the tree.
- **Distinguish** static transforms (published once, latched, on `/tf_static`) from dynamic transforms (re-published continuously on `/tf`) and choose the right one for each joint.
- **Build** a four-link manipulator tf2 tree — `base → shoulder → elbow → wrist` — using a `static_transform_publisher` per joint and visualize it in `rviz2`.
- **Add** a dynamic broadcaster for one rotating joint and confirm the moving frame in `rviz2`.
- **Write** a listener node that looks up `wrist` in the `base` frame, and **diagnose** `LookupException`, `ConnectivityException`, and `ExtrapolationException` correctly.
- **Reproduce, then fix,** a tf2 `ExtrapolationException` caused by timestamp mismatch, using correct stamping and a buffer timeout.

## Prerequisites

This week assumes you have completed **Week 1 — Rigid-body math and ROS2 first contact**, or have equivalent fluency. Specifically:

- You have ROS2 Jazzy installed on Ubuntu 24.04 (or WSL2), sourced in your shell, and you can run `ros2 topic list` and `rviz2`.
- You can write a `rclpy` node with a publisher, a timer, and a `main()` that calls `rclpy.init()` and `rclpy.spin()`.
- You understand SO(3): rotation matrices, quaternions, axis-angle, and why ZYX Euler angles are a debugging hazard. We build directly on the small rotation library you wrote in week 1.
- You can read NumPy: `@` for matrix multiply, `.T` for transpose, broadcasting, slicing.
- You can read enough C++ to follow a `tf2_ros::Buffer::lookupTransform` call. We write the bulk of the week in Python; one exercise touches C++ because that is what the BT.CPP and Nav2 stacks use, and you will read tf2 C++ all year.

You do **not** need any prior Lie-theory exposure. We define every term we use. The math is concrete and you will check every formula against `tf_transformations` and `numpy` in code.

## Topics covered

- Homogeneous coordinates: why we append a 1 to a point, and what appending a 0 means instead.
- The 4×4 homogeneous transform `T = [[R, t], [0, 1]]`; the meaning of each block.
- The SE(3) group: closure, identity, inverse, associativity; why SE(3) is *not* commutative.
- Frame-naming discipline: the `T_target_source` convention and how it makes composition a "cancel the middle index" operation.
- Inverting a transform the cheap way: `R.T` and `-R.T @ t`, never a 4×4 `inv`.
- The Lie algebra se(3): twists as `[v, ω]`, the `wedge` (`^`) and `vee` (`∨`) operators, the 4×4 twist matrix.
- The SE(3) exponential and logarithm maps; the closed-form Rodrigues-style expansion for the translation part (the `V` matrix).
- Body twist vs. spatial twist; what "this twist is expressed in frame X" actually means.
- The adjoint `Ad_T`, the 6×6 matrix that transforms a twist between frames; why points use `T` but twists use `Ad_T`.
- The tf2 mental model: a forest of frames, transforms as edges, a `Buffer` that stores a time-windowed history per edge.
- `TransformBroadcaster` (dynamic, `/tf`), `StaticTransformBroadcaster` (latched, `/tf_static`), `TransformListener`, and the `Buffer`.
- The `static_transform_publisher` command-line tool and its launch-file form.
- `lookup_transform(target, source, time)`: tree walk, time interpolation, and the `Time(0)` "latest available" sentinel.
- tf2 time-travel: `lookup_transform_full` with two times and a fixed frame, for asking "where was the gripper, in the map frame, at the instant the camera shutter fired."
- The three tf2 exceptions — `LookupException`, `ConnectivityException`, `ExtrapolationException` — and how to tell them apart.
- Buffer cache duration, `Duration` timeouts on lookups, and why a lookup with a timeout blocks.
- Debugging tools: `ros2 run tf2_tools view_frames`, `ros2 run tf2_ros tf2_echo`, `ros2 topic echo /tf`, the rviz2 TF display.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract. The independent-build hours are where the learning happens.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | SE(3): homogeneous transforms, composition, inversion  |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Tuesday   | Twists, exponential coordinates, adjoints              |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Wednesday | tf2 architecture; static vs. dynamic; building the tree|    1h    |    2h     |     0.5h   |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Thursday  | Listeners, lookups, time-travel, exceptions            |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     1.5h     |    0h      |     6.5h    |
| Friday    | Mini-project: launch + tree-health monitor            |    0h    |    0.5h   |     0.5h   |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work + challenge                     |    0h    |    0h     |     0.5h   |    0h     |   0h     |     2h       |    0h      |     2.5h    |
| Sunday    | Quiz, review, polish                                   |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7.5h**  | **3.5h**   | **3.5h**  | **5h**   | **10.5h**    | **2h**     | **35h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Curated SE(3) references, the tf2 docs, Modern Robotics, real talks |
| [lecture-notes/01-every-transform-problem-is-a-tree-problem.md](./02-lecture-notes/01-every-transform-problem-is-a-tree-problem.md) | The tf2 mental model: buffers, lookups, time-travel, broadcasters, the three exceptions |
| [lecture-notes/02-se3-twists-and-adjoints.md](./02-lecture-notes/02-se3-twists-and-adjoints.md) | Rigid-body motion as exponential coordinates: SE(3), twists, the exp/log maps, adjoints |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-four-link-static-tree.md](./03-exercises/exercise-01-four-link-static-tree.md) | Build a `base → shoulder → elbow → wrist` tf2 tree with `static_transform_publisher` per joint |
| [exercises/exercise-02-dynamic-broadcaster.py](./03-exercises/exercise-02-dynamic-broadcaster.py) | Add a dynamic broadcaster for one rotating joint; confirm the moving frame in rviz2 |
| [exercises/exercise-03-lookup-listener.py](./exercises/exercise-03-lookup-listener.py) | A listener that looks up `wrist` in `base` and logs a clear error when the tree breaks |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-induce-and-fix-extrapolation.md](./04-challenges/challenge-01-induce-and-fix-extrapolation.md) | Deliberately trigger an `ExtrapolationException`, then fix it; document before/after |
| [quiz.md](./05-quiz.md) | 12 multiple-choice questions with an answer key |
| [homework.md](./06-homework.md) | Six practice problems for the week |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for the reusable launch file + tree-health monitor node |

## The "clean tree" promise

C24 uses a recurring marker for any tf2 lab that ends in a working tree. When you run:

```bash
ros2 run tf2_tools view_frames
```

the generated `frames.pdf` must show a **single connected tree** — `base → shoulder → elbow → wrist`, no orphan frames, no two roots, no `NO_PARENT` warnings in the console. If `view_frames` reports more than one tree, or a frame with no broadcaster, you are not done. A disconnected TF tree is the robotics equivalent of a `NullReferenceException`: everything downstream — Nav2, MoveIt2, your perception stack — silently produces wrong answers until you fix it.

## A note on conventions

Robotics has two competing twist conventions and they fight all year. *Modern Robotics* (Lynch & Park) writes a twist as `[ω, v]` (angular first). The Featherstone / spatial-vector community and much of the screw-theory literature agree. ROS2, `geometry_msgs/Twist`, and most ROS code write it as `[v, ω]` (linear first). **We use the ROS ordering `[v, ω]` in code** because that is what `geometry_msgs/Twist` gives you and what you will debug all year, and we flag the swap every time we cite *Modern Robotics* so you can cross-reference the textbook without a sign error. When you read a paper, the first thing you check is which ordering it uses. The adjoint's 6×6 block structure changes accordingly; we show both.

## Stretch goals

If you finish the regular work early and want to push further:

- Read *Modern Robotics* (Lynch & Park) Chapter 3 in full: <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>. It is the canonical treatment of SE(3), twists, and the exponential map, and it is free.
- Skim the tf2 design paper, "tf: The Transform Library" (Foote, 2013): <https://ieeexplore.ieee.org/document/6556373>. It explains *why* tf2 caches a time window and interpolates.
- Read the `tf2` source for `BufferCore::lookupTransform` — the actual tree walk — in `geometry2` on GitHub: <https://github.com/ros2/geometry2>.
- Implement the SE(3) `log` map (the inverse of `exp`) yourself and verify `log(exp(twist)) == twist` round-trips to 1e-9 for ten random twists.
- Write a one-paragraph note for your future self: in your own words, why does a velocity (twist) transform with the adjoint while a point transforms with the homogeneous matrix?

## Up next

Continue to **Week 3 — URDF, xacro, and the first simulated robot** once you have pushed the mini-project to your GitHub. Week 3 replaces your hand-written `static_transform_publisher` tree with a URDF that the `robot_state_publisher` turns into a TF tree automatically — and the mental model you build this week is exactly what makes that node legible instead of magic.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

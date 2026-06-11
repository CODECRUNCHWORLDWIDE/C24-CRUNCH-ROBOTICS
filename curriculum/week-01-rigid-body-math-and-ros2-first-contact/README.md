# Week 1 — Rigid-Body Math and ROS2 First Contact

Welcome to Crunch Robotics. This is the first week of a year, and it sets two foundations you will stand on for the next forty-seven: the **mathematics of rotation** and your **first running ROS2 graph**. By Friday you will be able to rotate a vector in 3D by hand and in code, explain why your engineering instincts about Euler angles will betray you, and watch a `geometry_msgs/PoseStamped` you published in `rclpy` tumble in `rviz2` at 50 Hz with a quaternion you computed yourself.

We assume nothing about ROS. We assume you can write Python from memory (C1 or industry), that you have shipped *something*, and that you remember enough linear algebra to multiply two matrices without panicking. Everything else — what a quaternion *is*, what a node *is*, why ROS1 is dead — we build from the ground up this week.

The one thing to internalize before you read another line: **a rotation is an element of a group, not a bag of three numbers.** The three-number representations you reach for first — roll, pitch, yaw — are a *chart* on that group, and like every chart, it has places where it lies to you. The discipline this week teaches is to treat orientation as a first-class mathematical object (a rotation matrix in SO(3), a unit quaternion in the double cover of SO(3)) and to convert to three numbers only at the very edge, for a human to read. Every drift bug, every gimbal-lock surprise, every "my robot spun the long way around" failure in the next year traces back to someone who forgot this.

This week is where you stop forgetting it.

## Learning objectives

By the end of this week, you will be able to:

- **Rotate** a 3D vector three ways — by a rotation matrix, by an axis-angle pair, and by a unit quaternion — and prove the three agree to numerical precision.
- **Explain** why the rotation matrices form the group SO(3): closure, identity, inverse (the transpose), and why `det(R) = +1` separates a rotation from a reflection.
- **Convert** fluently among rotation matrix ↔ quaternion ↔ axis-angle ↔ Euler (ZYX), and state which conversions are exact and which (Euler) are ambiguous.
- **Diagnose** gimbal lock: demonstrate the rank drop in the ZYX Euler Jacobian at pitch = ±90° and explain why a real robot's attitude estimator never represents state as Euler angles.
- **Compose** rotations in the correct order, and articulate why quaternion multiplication is non-commutative and what the order means physically (intrinsic vs. extrinsic, body vs. world).
- **Install** ROS2 Jazzy on Ubuntu 24.04 (or WSL2 / container) with clean hygiene — sourced overlays, a `colcon` workspace, a working `ros2 doctor`.
- **Write** a `rclpy` publisher node that emits `geometry_msgs/PoseStamped` at 50 Hz with a correctly stamped, correctly framed, rotating quaternion, and visualize it in `rviz2`.
- **Verify** your own quaternion-to-matrix conversion against `tf_transformations` (and `scipy.spatial.transform.Rotation`) so you trust your math before you trust a library.

## Prerequisites

This is Week 1; the prerequisites are the track's, not a prior week's:

- **Fluent Python** (C1 or equivalent). You can write a class, a generator, and a NumPy expression without a reference open.
- **Linear algebra at the level of "I can multiply matrices and I know what a dot and cross product are."** We re-derive the rotation-specific parts; we do not re-teach what a matrix is.
- A **laptop you can run Ubuntu 24.04 on** — native, dual-boot, a VM, or **WSL2** on Windows. 16 GB RAM, 256 GB free disk. A discrete GPU helps `rviz2` but is not required this week.
- Comfort on a **Linux command line**: `apt`, environment variables, `source`, editing a `~/.bashrc`.

You do **not** need any prior ROS, DDS, or robotics experience. You do not need C++ this week (it arrives properly in Week 4). If the words "quaternion" and "node" are both unfamiliar, you are exactly the intended reader.

## Topics covered

- **2D rotation** as the warm-up: the 2×2 rotation matrix `R(θ)`, why `R(θ)ᵀ = R(−θ)`, and the special-orthogonal group SO(2) as the circle.
- **3D rotation matrices and SO(3):** orthogonality (`RᵀR = I`), the determinant test (`det R = +1`), the three elementary rotations `Rx, Ry, Rz`, and right-handed convention with the right-hand rule.
- **Axis-angle and the exponential map:** Euler's rotation theorem (every 3D rotation is a single rotation about some axis), the skew-symmetric matrix `[ω]×`, and Rodrigues' formula `R = I + sin θ [k]× + (1−cos θ)[k]×²`.
- **Quaternions:** the algebra (`i² = j² = k² = ijk = −1`), unit quaternions as the double cover of SO(3), the rotation action `v' = q v q⁻¹`, why `q` and `−q` are the same rotation, composition by Hamilton product, and SLERP at a glance.
- **Euler angles and their failure modes:** the ZYX (yaw-pitch-roll) convention, intrinsic vs. extrinsic composition, and **gimbal lock** — the rank-deficiency at pitch = ±90° demonstrated numerically.
- **The ROS2 architecture overview:** nodes, topics, the publish/subscribe model, the DDS layer beneath `rmw`, the `rclpy`/`rclcpp`/`rcl`/`rmw` stack, and the colcon workspace. Why ROS1's master + TCP model is dead and what replaced it.
- **First contact in code:** a minimal `rclpy` publisher, the `geometry_msgs/PoseStamped` message, `std_msgs/Header` stamping, `frame_id` discipline, a wall timer at 50 Hz, and `rviz2` as your first visualization tool.
- **Trust-but-verify:** validating your hand-written quaternion math against `tf_transformations` and `scipy.spatial.transform.Rotation` so the library is a *check* on your understanding, not a substitute for it.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | SO(2)/SO(3), rotation matrices, axis-angle, Rodrigues  |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Tuesday   | Quaternions: algebra, action, composition, SLERP       |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Wednesday | Euler angles, gimbal lock; ROS2 install + first node   |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    1h      |     6.5h    |
| Thursday  | ROS2 architecture; the PoseStamped publisher; rviz2    |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Verify against tf_transformations; mini-project deep work |  0h    |    0h     |     1h     |    0.5h   |   1h     |     2.5h     |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                 |    0h    |    0h     |     0h     |    0h     |   0h     |     2h       |    0h      |     2h      |
| Sunday    | Quiz, review, math write-up polish                     |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7h**    | **4h**     | **4h**    | **5h**   | **7.5h**     | **2.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The rotation-math references, the ROS2 install docs, and the talks worth your time |
| [lecture-notes/01-rotations-are-a-group.md](./lecture-notes/01-rotations-are-a-group.md) | SO(3), rotation matrices, axis-angle, Rodrigues, quaternions, and why Euler lies |
| [lecture-notes/02-ros2-first-contact.md](./lecture-notes/02-ros2-first-contact.md) | ROS2 architecture, the install, the colcon workspace, and the 50 Hz PoseStamped publisher |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-rotation-by-hand.md](./exercises/exercise-01-rotation-by-hand.md) | Rotate a vector three ways on paper; verify in NumPy |
| [exercises/exercise-02-quaternion-toolkit.py](./exercises/exercise-02-quaternion-toolkit.py) | Implement quaternion multiply, conjugate, rotate, and quat↔matrix from scratch; test against scipy |
| [exercises/exercise-03-pose-publisher.py](./exercises/exercise-03-pose-publisher.py) | A 50 Hz `PoseStamped` publisher with a rotating quaternion, ready for rviz2 |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-gimbal-lock-demonstrator.md](./challenges/challenge-01-gimbal-lock-demonstrator.md) | Reproduce gimbal lock numerically and prove quaternions don't suffer it |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the rotation-conversion library write-up |
| [mini-project/README.md](./mini-project/README.md) | The `crunch_rotations` library + a `tumbling_pose` ROS2 publisher you visualize in rviz2 |

## The "it tumbles in rviz2" promise

C24 uses a recurring marker for every exercise that ends in something visible. This week's is a coordinate frame tumbling in `rviz2`:

```
$ ros2 run crunch_pose tumbling_pose
[INFO] [tumbling_pose]: publishing PoseStamped on /tumbling_pose at 50 Hz, frame_id=world
```

Open `rviz2`, set the **Fixed Frame** to `world`, add a **Pose** display on `/tumbling_pose`, and watch the axis triad rotate smoothly — no jumps, no flips, no gimbal stutter. If it jumps or snaps, your quaternion isn't normalized or you stamped it wrong. The point of Week 1 is to make that smooth tumble ordinary, and to make a *jerky* one a signal you can immediately read.

## Stretch goals

If you finish the regular work early and want to push further:

- Implement **SLERP** (spherical linear interpolation) between two quaternions and animate a pose that eases from one orientation to another. Confirm the path is a great-circle arc on the unit sphere, not a straight line through it.
- Derive **Rodrigues' rotation formula** from the matrix exponential `exp([ω]×θ)` by hand, using the fact that `[k]×³ = −[k]×` for a unit axis. Confirm your derivation matches the closed form you used in the exercises.
- Read the **`tf2` design rationale** (you meet `tf2` properly in Week 2) and predict why it stores orientation internally as quaternions and converts to Euler only for display.
- Benchmark your hand-written quaternion-rotate against `scipy.spatial.transform.Rotation.apply` over a million vectors. Note the constant-factor gap and why production code uses the optimized path.

## Up next

Week 2 takes the SO(3) fluency you built here and lifts it to **SE(3)** — full rigid-body transforms (rotation *and* translation) — and introduces **tf2**, the transform tree that is the backbone of every ROS2 robot. The `crunch_rotations` library you write this week becomes the rotation core of that work. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

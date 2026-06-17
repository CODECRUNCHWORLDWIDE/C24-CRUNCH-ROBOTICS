# Week 8 — Phase 1 Integration and Architecture Review

Welcome to the last week of **Phase 1 · Foundations**. The previous seven weeks each left you with a node, a config, a URDF, a tuning session — useful fragments, scattered across seven directories, each launched with a different ad-hoc command you half-remember. This week you collapse all of it into one package and one command, and then you defend the result in front of a reviewer.

This is not busywork. The single most common reason a junior robotics engineer's work does not survive contact with a team is that **only they can run it**. The robot comes up because they typed four terminals' worth of commands in the right order, with the right environment variables, with one `ros2 run` they forgot to write down. The week they go on vacation, the robot is dead. A senior engineer's work comes up with `ros2 launch crunchbot_bringup robot.launch.py` and a one-page README, and it comes up the same way on every machine in the building. That difference — reproducible bring-up versus folklore — is the difference between a demo and a product.

So Week 8 has two halves. The first half is **construction**: you build the `crunchbot_bringup` package, the foundation package that every subsequent phase (Nav2 in Phase 3, MoveIt2 in Phase 4, the fleet stack in Phase 5) will extend rather than replace. The second half is **defense**: you sit the Phase 1 milestone architecture review, where a reviewer reads your `launch/` directory the way a senior engineer reads a stranger's codebase, and asks you to justify your TF tree, your QoS choices, your odometry, and your map against a written rubric.

By Friday you should be able to: bring up the robot, its sensors, `slam_toolbox`, and `rviz2` with a saved layout from a single launch file; map a brand-new world end-to-end in under fifteen minutes; and walk a reviewer through every architectural decision in your stack without reaching for "I don't know, it was in the tutorial."

## Learning objectives

By the end of this week, you will be able to:

- **Compose** a multi-node robot bring-up from a single top-level Python launch file using `IncludeLaunchDescription`, `GroupAction`, and composable-node containers.
- **Manage** parameters as files, not as `ros2 param set` incantations — one YAML per node, loaded declaratively, overridable from the command line.
- **Apply** namespaces and topic/frame remapping correctly so the same launch file can bring up `robot1` and `robot2` without a single hard-coded topic name.
- **Read** an unfamiliar `launch/` directory the way a senior engineer does — find the entry point, trace the includes, and reconstruct the runtime graph in your head before running anything.
- **Defend** a TF tree as a single connected graph rooted at `map`, with no duplicate broadcasters, no extrapolation errors, and a documented static/dynamic split.
- **Justify** every QoS profile on every topic against the week-5 rules — sensor streams `BEST_EFFORT`, latched maps `RELIABLE`/`TRANSIENT_LOCAL` — and explain what breaks when they are wrong.
- **Quantify** odometry drift and map quality with numbers, not adjectives, and state the conditions under which each degrades.
- **Package** the whole stack as `crunchbot_bringup`, the reusable foundation every later phase depends on, with documented parameters and a `README` an operator can follow.
- **Pass** the Phase 1 milestone architecture review against the rubric in `homework.md`.

## Prerequisites

This week assumes you have completed **C24 weeks 1–7** and have the artifacts they produced. Specifically, you must arrive with:

- A working **differential-drive URDF in xacro** (week 3) that spawns cleanly in Gz Sim with a 2D LiDAR and an IMU plugin.
- A **diff-drive odometry node** (week 6) consuming `/joint_states` and publishing `/odom` plus the `odom → base_link` transform.
- A **`slam_toolbox` configuration** (week 7) you have driven through at least one multi-room world and saved a map from.
- The **QoS literacy** from week 5 — you can state, for any topic, whether it should be `RELIABLE` or `BEST_EFFORT` and why.
- The **tf2 mental model** from week 2 — you can read a `tf2` tree, run `ros2 run tf2_tools view_frames`, and spot a disconnected frame.
- A working **ROS2 Jazzy** install on Ubuntu 24.04 (or WSL2), with `colcon`, `Gz Sim` (Harmonic), `slam_toolbox`, and `rviz2` all functional.

If any of those is missing or broken, fix it before Monday. This week composes existing pieces; it does not teach you to build them. A broken week-6 odometry node will fail the milestone review no matter how clean your launch file is.

## Topics covered

- The anatomy of a ROS2 Python launch file: `LaunchDescription`, `Node`, `IncludeLaunchDescription`, `DeclareLaunchArgument`, `LaunchConfiguration`, `PathJoinSubstitution`, `FindPackageShare`.
- Launch-file composition: one top-level file that includes per-subsystem launch files (robot, sensors, SLAM, visualization) instead of one monolithic file.
- The `ros2 launch` argument system: declaring arguments with defaults, overriding them from the command line, and threading them down into includes via `launch_arguments`.
- Parameter management as files: one YAML per node, the `parameters=[...]` list, the `use_sim_time` discipline, and command-line parameter overrides.
- Namespaces with `PushRosNamespace` / `GroupAction`, and why a namespaced launch file is the foundation of the multi-robot work in Phase 5.
- Topic and frame remapping: the `remappings=[...]` list, the `tf` / `tf_static` remap that namespacing requires, and the difference between remapping a topic and renaming a frame.
- Composable nodes and `ComposableNodeContainer`: running multiple nodes in one process with intra-process zero-copy communication, and when it is worth it.
- The "minimal robot bring-up" pattern: the canonical structure of a `*_bringup` package that senior teams converge on.
- Reading a `launch/` directory cold: entry-point identification, include-tracing, and reconstructing the node graph and TF tree before you run anything.
- The Phase 1 milestone architecture review: the rubric, the four defenses (TF tree, QoS, odometry, map), and how to prepare evidence for each.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract; the milestone review on Sunday is the only fixed point.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Reading a `launch/` directory like a senior engineer   |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | The minimal bring-up pattern: composition + params     |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | Namespaces, remapping, composable containers           |    1h    |    2h     |     1h     |    0.5h   |   0h     |     1.5h     |    0.5h    |     6.5h    |
| Thursday  | Package weeks 3–7 into one bringup; rviz2 layout        |    0h    |    1.5h   |     1h     |    0.5h   |   0h     |     2.5h     |    0h      |     5.5h    |
| Friday    | End-to-end map of a new world; time the run            |    0h    |    1h     |     1h     |    0.5h   |   1h     |     2.5h     |    0.5h    |     6.5h    |
| Saturday  | Milestone prep: TF/QoS/odom/map evidence pack          |    0h    |    0h     |     0h     |    0h     |   2h     |     1.5h     |    0h      |     3.5h    |
| Sunday    | Quiz, architecture review, retro                       |    0h    |    0h     |     0h     |    1h     |   1h     |     0.5h     |    0h      |     2.5h    |
| **Total** |                                                        | **5h**   | **8h**    | **4h**     | **3.5h**  | **6h**   | **11h**      | **1.5h**   | **35.5h**   |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Curated, current (2026) ROS2 Jazzy launch, parameter, and `slam_toolbox` references |
| [lecture-notes/01-reading-a-launch-directory.md](./02-lecture-notes/01-reading-a-launch-directory.md) | Your launch file is your README for operators: reading a `launch/` directory like a senior engineer |
| [lecture-notes/02-minimal-robot-bringup-pattern.md](./02-lecture-notes/02-minimal-robot-bringup-pattern.md) | The minimal robot bring-up pattern: composition, parameters, namespaces, remapping |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-package-weeks-3-7.md](./03-exercises/exercise-01-package-weeks-3-7.md) | Guided: package weeks 3–7 into one bringup package with a single top-level launch file |
| [exercises/exercise-02-bringup-launch.py](./03-exercises/exercise-02-bringup-launch.py) | Runnable: the top-level launch file that brings up robot + sensors + `slam_toolbox` + `rviz2` with a saved layout |
| [exercises/exercise-03-map_a_new_world.py](./03-exercises/exercise-03-map_a_new_world.py) | Runnable: map a brand-new world end-to-end and time the run with a `rclpy` stopwatch node |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-cold-start-map-under-15.md](./04-challenges/challenge-01-cold-start-map-under-15.md) | Map an unseen multi-room world from cold start to saved map in under fifteen minutes, single command |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for the `crunchbot_bringup` package and the Phase 1 milestone review |
| [quiz.md](./05-quiz.md) | 13 questions with an answer key |
| [homework.md](./06-homework.md) | The milestone evidence pack and the architecture-review rubric |

## The "one command" promise

C24 uses a recurring marker for any bring-up that is done right. By the end of this week, your robot must come up with exactly one line:

```bash
ros2 launch crunchbot_bringup robot.launch.py world:=warehouse slam:=true rviz:=true
```

No second terminal. No `ros2 run` you forgot to write down. No "oh, you also have to set `GZ_SIM_RESOURCE_PATH` first." If your robot needs anything beyond that one line and what is documented in your package `README`, you are not done. The point of Week 8 is to make that line ordinary — and to make it survive being run by someone who is not you, on a machine that is not yours.

## A note on the milestone

The Phase 1 milestone is a **hard gate** in the C24 assessment matrix. You do not advance to Phase 2 (Perception) with an unsigned milestone. The review is not adversarial for its own sake — the reviewer wants you to pass — but it is genuinely rigorous. "It works on my machine" is not a defense; "here is the `view_frames` PDF, here is the `ros2 topic info -v` output for every topic, here is the drift number over a 10 m square, here is the map at three lidar rates" is a defense. Spend Saturday building the evidence pack. The learners who fail the milestone are almost never the ones whose robot does not work; they are the ones who cannot *explain why it works*.

## Up next

**Phase 2 — Perception** begins at Week 9 (IMU calibration and integration). Phase 2 assumes the `crunchbot_bringup` package exists and works, because you will add a Jetson, a depth camera, and a fused state estimator *on top of it*. Do not start Week 9 until the Phase 1 milestone is signed.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

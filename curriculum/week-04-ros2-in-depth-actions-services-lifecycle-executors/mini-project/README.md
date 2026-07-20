# Mini-Project — The `crunch_motion` Motion-Primitives Package

> Build a production-shaped ROS2 package of **motion primitives** — `RotateByAngle` and `DriveStraightDistance` — implemented as preemptible, lifecycle-managed action servers, composed into a single process. This is the package the crunchbot bring-up dispatches in later weeks; the capstone's behavior tree will tick these primitives as its leaves. You are not building a toy this week. You are building a load-bearing component of the rest of the course.

**Estimated time:** ~15 hours (split across Thursday, Friday, Saturday, Sunday in the suggested schedule).

This mini-project **compounds**. The syllabus is explicit: *"the crunchbot bring-up will later dispatch these primitives."* Week 6 (kinematics) refines the `DriveStraightDistance` controller; Week 17 (Nav2) brings these primitives up under a lifecycle manager; Week 19 (behavior trees) ticks them as BT leaves. Build the interfaces and the lifecycle discipline right now and the rest of the course inherits a clean foundation. Cut corners — non-cancellable loops, ambiguous terminal status, a node that commands motors while inactive — and you will pay for it in every downstream week.

---

## What you will build

A single ROS2 package, `crunch_motion`, exposing two action servers in one composed process:

```bash
# Rotate in place by a relative angle (radians, + = CCW), closed-loop on IMU yaw.
ros2 action send_goal /rotate_by_angle crunch_motion_interfaces/action/RotateByAngle \
  "{target_relative_yaw: 1.5708, max_angular_speed: 0.8}" --feedback

# Drive straight a relative distance (metres, + = forward), closed-loop on odometry.
ros2 action send_goal /drive_straight crunch_motion_interfaces/action/DriveStraightDistance \
  "{target_distance: 1.0, max_linear_speed: 0.25}" --feedback
```

Both servers:

- run as **lifecycle nodes** (boot `unconfigured`, refuse goals until `active`),
- are **preemptible** (a cancel mid-execution stops the robot within one control tick and returns `CANCELED`),
- **stream feedback** (remaining angle / distance and current error),
- **always stop the robot on every exit path** (the clean-shutdown promise),
- are **composed into one process** via a `ComposableNodeContainer` running a multi-threaded executor,
- come up under a small **lifecycle manager** that drives them `unconfigured → inactive → active` in order.

By the end you have a public repo, ~600–800 lines across interfaces and nodes, that a teammate can clone, build, bring up with one launch file, and dispatch primitives against.

---

## Why "motion primitives"

A motion primitive is a parameterized, self-contained, cancellable motion: "rotate by θ," "drive d metres," "back up," "spin in place." Mobile robots are built from a small alphabet of these. Nav2's recovery behaviors are motion primitives. A behavior tree's leaves are motion primitives. The reason to package them as **actions** rather than topics or services is the entire Lecture 1 argument: they take seconds, the caller wants feedback, and they *must* be cancellable. The reason to make them **lifecycle nodes** is the entire Lecture 2 argument: a supervisor must be able to bring them up after the sensors are ready and refuse work before that.

You already wrote `Spin90` (a fixed-angle rotate). `RotateByAngle` generalizes it to any angle with a speed cap. `DriveStraightDistance` is its translational sibling, closing the loop on integrated odometry distance instead of IMU yaw. The architecture is identical; only the controlled variable changes. That symmetry is the point — once you have the action + lifecycle + callback-group skeleton right, a new primitive is an afternoon.

---

## Package layout

Two packages (interfaces separate from nodes, as in Exercise 1):

```
crunch_ws/src/
├── crunch_motion_interfaces/            # ament_cmake
│   ├── action/
│   │   ├── RotateByAngle.action
│   │   └── DriveStraightDistance.action
│   ├── CMakeLists.txt
│   └── package.xml
└── crunch_motion/                       # ament_python
    ├── crunch_motion/
    │   ├── __init__.py
    │   ├── rotate_by_angle.py           # LifecycleNode + RotateByAngle action server
    │   ├── drive_straight.py            # LifecycleNode + DriveStraightDistance action server
    │   ├── motion_math.py               # shared yaw/distance helpers (tested in isolation)
    │   └── lifecycle_manager.py         # supervisor: drives both nodes to active
    ├── launch/
    │   └── motion_primitives.launch.py  # ComposableNodeContainer (mt) + lifecycle manager
    ├── test/
    │   ├── test_motion_math.py          # pytest unit tests for the math
    │   └── test_preemption.py           # integration: cancel takes effect in budget
    ├── setup.py
    └── package.xml
```

### Interface definitions

`RotateByAngle.action`:

```
# Goal
float64 target_relative_yaw    # radians, relative to start, + = CCW
float64 max_angular_speed      # rad/s cap; <= 0 means use the node default
---
# Result
float64 final_error_deg        # residual heading error, degrees
bool reached                   # true iff within tolerance
float64 elapsed_seconds        # wall time spent executing
---
# Feedback
float64 remaining_deg
float64 current_error_deg
```

`DriveStraightDistance.action`:

```
# Goal
float64 target_distance        # metres, relative to start, + = forward
float64 max_linear_speed       # m/s cap; <= 0 means use the node default
---
# Result
float64 final_error_m          # residual distance error, metres
bool reached
float64 elapsed_seconds
---
# Feedback
float64 remaining_m
float64 current_error_m
```

---

## Functional requirements

### R1 — Both primitives are lifecycle action servers

Each node subclasses `rclpy.lifecycle.LifecycleNode`. The action server is created in `on_configure` (so it is discoverable while `inactive`) and gated on an `self._active` flag set in `on_activate` / cleared in `on_deactivate`. A goal arriving while not `active` is rejected with a logged reason. `cmd_vel` is published through a `create_lifecycle_publisher`, so even a stray publish while inactive is silently dropped.

### R2 — Closed-loop control

- `RotateByAngle` subscribes to `/imu`, extracts yaw, and runs a proportional controller on heading error (your Exercise 3 loop), clamped by `min(node_default, goal.max_angular_speed)`. Terminate within 1° tolerance.
- `DriveStraightDistance` subscribes to `/odom` (`nav_msgs/Odometry`), integrates travelled distance from the start pose, and runs a proportional controller on remaining distance, clamped by the speed cap. Terminate within 2 cm tolerance. Hold heading with a small yaw-rate correction so the robot does not drift (a P term on the heading deviation from the start heading is sufficient this week).

### R3 — Preemption

A cancel request, accepted in a `cancel_callback` that lives in a `ReentrantCallbackGroup`, must be noticed by the control loop within one tick. On cancel: stop the robot, call `goal_handle.canceled()`, return `CANCELED`. The integration test (`test_preemption.py`) asserts a cancel takes effect within 0.5 s of the request.

### R4 — The clean-shutdown promise

Every exit path of every control loop publishes a zero `Twist` in a `finally`. Success, cancel, abort, exception, `deactivate`, `shutdown` — the robot is always left stopped. A reviewer running `ros2 topic echo /cmd_vel` must never see motion after a goal terminates.

### R5 — Composition into one process

A `launch/motion_primitives.launch.py` loads both primitives into a single `ComposableNodeContainer` using the **multi-threaded** container executable (`component_container_mt`), with `use_intra_process_comms: True`. Both servers share one process and one executor. The multi-threaded container is mandatory, not optional — your action servers need the cancel-path concurrency from Lecture 2.

> **Note on language for composition.** True component composition (a node loaded as a plugin into a generic container) is a `rclcpp` feature; the `component_container_mt` loads C++ components. You have two honest paths, and either earns full marks:
> 1. **Python path (default this week):** launch both lifecycle nodes as separate `LifecycleNode` actions inside one launch file under a multi-threaded executor each, and document that "composition into one *process*" in pure Python uses a shared-process launch pattern rather than the C++ plugin container. This is what most Python ROS2 shops actually do.
> 2. **C++ stretch path:** implement the two primitives as `rclcpp_lifecycle::LifecycleNode` components registered with `RCLCPP_COMPONENTS_REGISTER_NODE` and load them into `component_container_mt`. This is the production form and the form the capstone uses. Do this if you want the full composition experience.
>
> The mini-project is graded on the lifecycle + preemption + clean-shutdown discipline either way. Choose the Python path to ship on time; choose the C++ path if you have the hours.

### R6 — Ordered bring-up via a lifecycle manager

`lifecycle_manager.py` is a small supervisor node that, on startup, drives both primitive nodes from `unconfigured → inactive → active` by calling their `change_state` services in order, logging each transition, and refusing to declare the system "ready" until both report `active`. This is the Nav2 pattern in miniature, and it is exactly the shape the crunchbot bring-up uses to dispatch these primitives later.

### R7 — Tests

- `test_motion_math.py` — pure `pytest` unit tests for the shared helpers in `motion_math.py`: `shortest_angular_distance` across the ±π wrap, distance integration, the speed-cap clamp. No ROS spin needed; these are fast.
- `test_preemption.py` — a `launch_testing` integration test that brings up `rotate_by_angle`, activates it, sends a large goal, cancels after 0.5 s, and asserts the result status is `CANCELED` within budget and that the final `cmd_vel` is zero.

---

## Rules

- **You may** read the ROS2 Jazzy docs, the design articles, your own Exercise 2/3/challenge code, and `ros2/demos`.
- **You must** target ROS2 **Jazzy** on **Ubuntu 24.04**. `rclpy` for the Python path; `rclcpp_lifecycle` + `rclcpp_action` for the C++ stretch path.
- **You must not** put a `sleep` or a blocking I/O in a `goal_callback` or `cancel_callback`. Those callbacks decide; the `execute_callback` does the long work.
- **You must** run the composed process under a multi-threaded executor / `component_container_mt`. A single-threaded executor is an automatic fail — your cancel will deadlock.
- **You must** treat "robot moves after a goal is dead" as a build-breaking defect, the same way C9 treats a compiler warning as a bug.
- Use the Week 3 robot in Gz Sim, or the `--fake-imu` / `--fake-odom` synthetic-sensor flags (carry them forward from the exercises) so the project runs headless in CI.

---

## Acceptance criteria

- [ ] A public repo named `c24-week-04-crunch-motion-<yourhandle>`.
- [ ] `colcon build` of both packages succeeds with no errors.
- [ ] `ros2 launch crunch_motion motion_primitives.launch.py` brings up one process containing both servers; the lifecycle manager drives both to `active` and logs `system ready`.
- [ ] `ros2 action list` shows `/rotate_by_angle` and `/drive_straight`.
- [ ] `RotateByAngle` rotates the robot to within 1° of target and reports `reached: true`.
- [ ] `DriveStraightDistance` drives to within 2 cm of target, holds heading, reports `reached: true`.
- [ ] Cancelling either primitive mid-execution stops the robot within 0.5 s and returns `CANCELED`.
- [ ] Before `activate`, both servers **reject** goals (the lifecycle property).
- [ ] `ros2 topic echo /cmd_vel` shows zero after every terminal event — no creeping robot.
- [ ] `colcon test` runs `test_motion_math.py` and `test_preemption.py`, both green.
- [ ] A `README.md` in the repo documents the design: which rung of the ladder and why, the callback-group assignment and why, the lifecycle states, and which composition path (Python vs C++) you chose.

---

## Grading rubric (100 points)

| Area | Points | What earns them |
|------|-------:|-----------------|
| **Interfaces** | 10 | Both `.action` files correct, build cleanly, fields sensible (relative targets, speed caps, elapsed time). |
| **Closed-loop control** | 20 | Both primitives reach target within tolerance; `DriveStraight` holds heading; the proportional controllers are clamped and stable. |
| **Preemption** | 20 | Cancel stops the robot within budget, returns `CANCELED`, control loop checks `is_cancel_requested` every tick. |
| **Executor + callback groups** | 15 | Multi-threaded executor; execute in a mutually-exclusive group, cancel + sensor in a reentrant group; the cancel deadlock is demonstrably absent. |
| **Lifecycle** | 15 | All five transitions implemented; goals rejected while inactive; `deactivate` stops the robot; lifecycle publisher used for `cmd_vel`. |
| **Composition + bring-up** | 10 | Both servers in one process under a multi-threaded container/executor; lifecycle manager drives ordered bring-up. |
| **Clean-shutdown discipline** | 5 | Every exit path stops the robot; `try/finally` everywhere; verified via `cmd_vel` echo. |
| **Tests + docs** | 5 | Unit tests for the math, integration test for preemption, a design README. |

A submission that rotates and drives perfectly but cannot be cancelled, or commands the robot while `inactive`, **caps at 50 points** regardless of polish. Cancellability and the lifecycle gate are safety properties, not features — the rubric weights them accordingly.

---

## How this compounds

| Week | What it does with `crunch_motion` |
|------|-----------------------------------|
| **6 — Kinematics** | Replaces the proportional `DriveStraight` controller with a kinematically-aware one; the action interface is unchanged. |
| **17 — Nav2** | Brings these primitives up under Nav2's `lifecycle_manager` alongside the planner and controller servers; your ordered bring-up was the rehearsal. |
| **19 — Behavior trees** | Wraps each primitive as a BT leaf node; your clean terminal statuses (`SUCCEEDED`/`CANCELED`/`ABORTED`) map directly to BT `SUCCESS`/`FAILURE`. |
| **Capstone** | The crunchbot bring-up dispatches `RotateByAngle` and `DriveStraightDistance` as recovery and maneuvering primitives. |

Build it once, build it right, and it carries you to graduation. That is why this is a 15-hour mini-project in Week 4 and not a throwaway.

---

## Submission

Push to your public repo, tag it `week-04-submission`, and open the repo's README with the design write-up. In your cohort channel, post the repo link and a 30-second screen capture (or an asciinema) of: launch → lifecycle manager reports ready → a `RotateByAngle` goal running with feedback → a cancel mid-rotation → the robot stopping. That capture is the proof; the rubric is the checklist.

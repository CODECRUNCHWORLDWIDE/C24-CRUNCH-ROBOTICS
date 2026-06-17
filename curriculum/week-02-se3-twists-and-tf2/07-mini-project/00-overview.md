# Mini-Project — `arm_tf_bringup`: one launch file, a live tree, and a health monitor that refuses to lie

> Compose the four-link `base → shoulder → elbow → wrist` tf2 tree into a single, reusable launch file — static edges where the geometry is fixed, a dynamic broadcaster for the one rotating joint — and add a monitoring node that continuously validates the full `base → wrist` chain and reports tree health on a topic. The monitor must turn the three tf2 failure modes from last-resort exceptions into first-class, machine-readable health signals. By Friday you have a `colcon`-buildable package any robotics team would recognize: a tree you can bring up with one command, and a watchdog that tells an operator the tree is healthy before anything downstream trusts it.

This is the canonical "make the tree real" mini-project for C24. In every later week — URDF in week 3, SLAM in week 7, Nav2 in week 17, MoveIt2 in week 23 — the *first* thing you do is bring up a tf tree and the *first* thing that goes wrong is a broken tree. A health monitor that watches `base → wrist` and publishes "healthy / degraded / broken" is the single most reused diagnostic node in a robotics codebase. You are building it once, here, and you will copy it into every project for the rest of the track.

**Estimated time:** ~10.5 hours (split across Thursday, Friday, Saturday in the suggested schedule).

---

## What you will build

A ROS2 Jazzy package named `arm_tf_bringup` that ships:

1. **A `se3` Python module** that *extends your Week 1 rotation library* into full SE(3). Week 1 gave you `quat_to_matrix`, `matrix_to_quat`, and `axis_angle_to_matrix`. This week you add `make_transform(R, t)`, `invert_transform(T)` (block-transpose, **not** `numpy.linalg.inv`), `compose(T_a_b, T_b_c)`, and `transform_to_msg` / `msg_to_transform` converters to and from `geometry_msgs/Transform`. The broadcaster and the monitor both import this module — the math lives in one place.
2. **A `arm_tree_broadcaster` node** that broadcasts the full tree: `base → shoulder` and `elbow → wrist` as static transforms on `/tf_static`, and `shoulder → elbow` as a dynamic transform on `/tf` that rotates at a configurable rate. The link lengths and the rotation rate are ROS parameters.
3. **A `tree_health_monitor` node** that, at a configurable rate, attempts `lookup_transform("base", "wrist", Time(0))`, classifies the result as `HEALTHY`, `DEGRADED`, or `BROKEN`, and publishes a `diagnostic_msgs/DiagnosticArray` plus a simple `std_msgs/String` summary on `/tree_health`. It distinguishes the three tf2 exceptions and reports *which* one fired and a human-readable hint.
4. **A single launch file** `arm_bringup.launch.py` that starts the broadcaster, the monitor, and (optionally) `rviz2` with a saved config showing the TF display. One command brings up the whole system.
5. **A README** at the package root documenting how to run it, what healthy output looks like, and how to break the tree and watch the monitor catch it.

You ship **one colcon package** with this layout:

```text
arm_tf_bringup/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/arm_tf_bringup
├── arm_tf_bringup/
│   ├── __init__.py
│   ├── se3.py                  # SE(3) helpers; extends the week-1 rotation lib
│   ├── arm_tree_broadcaster.py # the broadcaster node
│   └── tree_health_monitor.py  # the watchdog node
├── launch/
│   └── arm_bringup.launch.py
├── config/
│   └── arm.rviz                # saved rviz2 layout with the TF display on
├── test/
│   └── test_se3.py             # pytest unit tests for the SE(3) math
└── README.md
```

---

## Rules

- **You may** read the ROS2 Jazzy docs, the tf2 tutorials, lecture notes 1 and 2, your week-1 rotation library, the `tf2_ros` API, and the `diagnostic_msgs` docs.
- **You may NOT** use a generic 4×4 matrix inverse anywhere in `se3.py`. `invert_transform` must use the block formula `R.T` and `-R.T @ t`. A unit test will check that your inverse is correct *and* you will be asked to explain in the README why the block form is both faster and more numerically honest than `numpy.linalg.inv` for an SE(3) element.
- **You may NOT** depend on any third-party package beyond what ships with Jazzy plus `numpy` and `transforms3d` (both already in the ROS2 Python environment). No `robot_state_publisher`, no URDF — that is week 3's job. The point of this week is to do by hand what `robot_state_publisher` will later do for you, so the magic is legible when it arrives.
- Target distro: **ROS2 Jazzy** on **Ubuntu 24.04**. Python via `ament_python`.
- The package must build clean: `colcon build` with **zero warnings**, and `colcon test` green.
- The broadcaster's link lengths and rotation rate, and the monitor's check rate and staleness threshold, must be **ROS parameters** with sane defaults — not hard-coded constants. An operator must be able to retune from the launch file without editing Python.

---

## The health classification — the heart of the project

The monitor must implement exactly this state machine, because it maps the three tf2 exceptions onto operator-meaningful states:

| State | Condition | What the operator does |
|-------|-----------|------------------------|
| `HEALTHY` | `lookup_transform` succeeds **and** the result's stamp is within the staleness threshold (default 0.5 s) of now. | Nothing. Downstream may trust the tree. |
| `DEGRADED` | The lookup succeeds but the transform is **stale** (older than the threshold) — the broadcaster is slow or hiccuping but not dead. | Investigate the broadcaster's rate; downstream should treat poses as suspect. |
| `BROKEN` | The lookup throws `LookupException`, `ConnectivityException`, or `ExtrapolationException`. | Stop trusting the tree immediately. The report names which exception and the likely cause. |

The published `DiagnosticArray` must carry:

- A `DiagnosticStatus` with `name = "base->wrist chain"`, `level` set to `OK` / `WARN` / `ERROR` for `HEALTHY` / `DEGRADED` / `BROKEN`, and a `message` that is human-readable.
- Key/value pairs in `status.values` for: `state`, `latest_stamp`, `staleness_s`, and (on `BROKEN`) `exception_type` and `hint`.

The `std_msgs/String` on `/tree_health` is a one-line summary for quick `ros2 topic echo` debugging, e.g. `HEALTHY base->wrist t=[+0.450,+0.000,+0.100] staleness=0.012s`.

---

## Acceptance criteria

The grading rubric is below. Each box maps to a specific deliverable.

### SE(3) math (25%)

- [ ] `se3.make_transform(R, t)` returns a valid 4×4 SE(3) element; a test asserts the bottom row is `[0, 0, 0, 1]` and `R` is orthonormal.
- [ ] `se3.invert_transform(T)` uses the block-transpose formula (no `numpy.linalg.inv`); a test asserts `invert_transform(T) @ T ≈ I` to `1e-9` for ten random transforms.
- [ ] `se3.compose(A, B)` equals `A @ B`; a test asserts associativity `compose(compose(A,B),C) ≈ compose(A,compose(B,C))`.
- [ ] `se3.transform_to_msg` / `se3.msg_to_transform` round-trip a `geometry_msgs/Transform` to `1e-9`; a test asserts the round-trip.
- [ ] `se3.py` imports and reuses the Week 1 rotation functions (quaternion↔matrix), not a fresh copy. (Vendoring the week-1 file into the package is fine; copy-pasting the *bodies* inline is not.)

### Broadcaster (20%)

- [ ] `arm_tree_broadcaster` publishes `base→shoulder` and `elbow→wrist` on `/tf_static` (latched) and `shoulder→elbow` on `/tf` (dynamic, rotating).
- [ ] Link lengths (`shoulder_z`, `upper_arm_len`, `forearm_len`) and `elbow_rate_rad_s` are ROS parameters with defaults `0.10`, `0.25`, `0.20`, `0.50`.
- [ ] `ros2 run tf2_tools view_frames` shows **one connected** `base→shoulder→elbow→wrist` tree.

### Monitor (30%)

- [ ] `tree_health_monitor` checks `base→wrist` at a configurable rate (default 5 Hz) and publishes a `DiagnosticArray` and a `String` on `/tree_health`.
- [ ] It classifies `HEALTHY` / `DEGRADED` / `BROKEN` exactly per the table above.
- [ ] On `BROKEN`, the report names which of the three exceptions fired and gives a one-line, *accurate* hint (future vs past extrapolation, split tree, missing frame).
- [ ] Killing the broadcaster moves the monitor to `DEGRADED` (stale) and then `BROKEN` (aged out), observable on `ros2 topic echo /tree_health`.
- [ ] Running only part of the tree (omit the `shoulder→elbow` edge) makes the monitor report `BROKEN` with `ConnectivityException`.

### Launch + docs (25%)

- [ ] `ros2 launch arm_tf_bringup arm_bringup.launch.py` brings up the broadcaster and monitor; a launch argument `use_rviz:=true` also opens `rviz2` with the saved config.
- [ ] All four parameters above are overridable from the launch command line (e.g. `elbow_rate_rad_s:=1.0`).
- [ ] `colcon build` is warning-free; `colcon test` is green.
- [ ] The package `README.md` documents: how to run; a screenshot or text capture of `HEALTHY` output; the three ways to break the tree and the matching `BROKEN` reports; and the one-paragraph explanation of why `invert_transform` uses the block form, not `numpy.linalg.inv`.

---

## Suggested implementation outline

The order matters: get the math and its tests right first, then the broadcaster, then the monitor, then wrap it in launch.

### Day 1 (Thursday — ~3 hours): the SE(3) module and its tests

1. `ros2 pkg create --build-type ament_python arm_tf_bringup --dependencies rclpy geometry_msgs tf2_ros diagnostic_msgs std_msgs`. This scaffolds `package.xml`, `setup.py`, and the folders.
2. Vendor your Week 1 rotation functions into `arm_tf_bringup/rotations.py` (or import them if you packaged them). Write `se3.py` on top: `make_transform`, `invert_transform`, `compose`, `transform_to_msg`, `msg_to_transform`.
3. Write `test/test_se3.py` *first* for `invert_transform` and `compose` — TDD the math. Use `pytest`; run with `colcon test --packages-select arm_tf_bringup` then `colcon test-result --verbose`.
4. Prove the inverse: generate ten random `SE(3)` elements (random axis-angle for `R`, random `t`), assert `invert_transform(T) @ T ≈ I`. This is the test that will save you a sign error later.

### Day 2 (Friday — ~4.5 hours): the broadcaster and the monitor

5. Write `arm_tree_broadcaster.py`. Declare the four parameters with `declare_parameter`. Build the static edges from the parameters with `se3.make_transform` + `se3.transform_to_msg`, latch them once on a `StaticTransformBroadcaster`. Tick the dynamic `shoulder→elbow` edge on a 50 Hz timer with a fresh stamp every tick. (Exercise 2 is your starting point — promote it into the package and parameterize it.)
6. `ros2 run arm_tf_bringup arm_tree_broadcaster` and confirm `view_frames` shows one tree and `tf2_echo base wrist` sweeps. Do not move on until this is clean.
7. Write `tree_health_monitor.py`. A `Buffer` + `TransformListener`; a timer that calls `lookup_transform("base", "wrist", Time(0), timeout=...)`; the classification state machine; the `DiagnosticArray` + `String` publishers. (Exercise 3 is your starting point — promote it and add the diagnostics.)
8. Run broadcaster + monitor; `ros2 topic echo /tree_health` should stream `HEALTHY`. Kill the broadcaster and watch `DEGRADED` → `BROKEN`. Run a split tree and watch `ConnectivityException`.

### Day 3 (Saturday — ~3 hours): launch, rviz, docs, polish

9. Write `arm_bringup.launch.py`. Use `DeclareLaunchArgument` for `use_rviz` and the four tuning parameters; pass parameters into the nodes; conditionally start `rviz2` with `IfCondition(LaunchConfiguration('use_rviz'))` and `arguments=['-d', <config/arm.rviz>]`.
10. Save the rviz2 layout (`File → Save Config As → config/arm.rviz`) with Fixed Frame `base` and the TF display on, names and axes shown.
11. Write the package `README.md`: run instructions, a `HEALTHY` capture, the three break-and-catch demonstrations, and the block-inverse explanation.
12. `colcon build`, `colcon test`, final `view_frames` for the clean-tree check. Push.

---

## What "done" looks like

A single command:

```bash
ros2 launch arm_tf_bringup arm_bringup.launch.py use_rviz:=true elbow_rate_rad_s:=0.8
```

brings up the rotating arm in rviz2 with the TF display showing four frames, the elbow and wrist orbiting the shoulder. In a second terminal:

```bash
ros2 topic echo /tree_health --field data
```

streams a line several times a second:

```text
HEALTHY base->wrist t=[+0.450,+0.000,+0.100] staleness=0.011s
HEALTHY base->wrist t=[+0.447,+0.058,+0.100] staleness=0.009s
```

`Ctrl+C` the broadcaster, and within a second the monitor flips:

```text
DEGRADED base->wrist stale by 0.62s (broadcaster slow or stopped)
BROKEN   base->wrist ExtrapolationException: latest data older than cache (broadcaster dead?)
```

That transition — from a confident `HEALTHY` to a precise, named `BROKEN` — is the artifact. It is the difference between a robot that knows its tree is broken and one that silently drives into a wall because every downstream node trusted a stale transform.

---

## How this compounds

This package is **directly reused** in the rest of Phase 1:

- **Week 3 (URDF):** you replace `arm_tree_broadcaster` with `robot_state_publisher` driven by a URDF. The `tree_health_monitor` carries over unchanged — it does not care *who* publishes the tree, only that `base → wrist` resolves. You will appreciate having written it once.
- **Week 7 (SLAM):** the monitor pattern becomes a `map → base_link` health check. Same node, different frames.
- **Week 8 (integration):** the `bringup` package pattern you practice here — one launch file, parameters, a saved rviz config — is exactly the deliverable for the Phase 1 milestone.
- **The capstone:** a fleet-readiness `/fleet/heartbeat` is a generalization of `/tree_health`. The instinct to publish machine-readable health, not just throw exceptions, is the instinct that gets a robot through a chaos drill.

The `se3.py` module is the foundation for week 6 (odometry composes `odom → base_link` transforms), week 11 (GTSAM factor graphs optimize over SE(3)), and week 23 (manipulator FK is a chain of SE(3) products). The block-inverse and `compose` you write today are called thousands of times per second in those weeks. Write them correctly now.

---

## Submission

Commit `arm_tf_bringup` to your Week 2 GitHub repo under `mini-project/arm_tf_bringup/`. The grader clones fresh and runs:

```bash
colcon build --packages-select arm_tf_bringup
colcon test --packages-select arm_tf_bringup && colcon test-result --verbose
source install/setup.bash
ros2 launch arm_tf_bringup arm_bringup.launch.py
ros2 run tf2_tools view_frames
```

It must build clean, test green, launch without error, and produce a single connected `frames.pdf`. Include the `frames.pdf` and a `/tree_health` capture in your README so the grader can see your result without a full setup.

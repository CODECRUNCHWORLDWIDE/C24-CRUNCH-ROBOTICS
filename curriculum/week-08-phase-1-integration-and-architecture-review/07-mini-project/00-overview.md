# Mini-Project — `crunchbot_bringup`: the foundation package + the Phase 1 milestone review

> Deliver the `crunchbot_bringup` package: one command that brings up the robot, its sensors, `slam_toolbox`, and `rviz2` with a saved layout, every parameter documented, namespace-ready, with exactly one TF broadcaster per edge. Then sit the Phase 1 milestone architecture review and defend your TF tree, your QoS choices, your odometry, and your map against the rubric. This package is not a throwaway exercise — it is the foundation every subsequent phase extends. Phase 2 adds perception *on top of it*; Phase 3 adds Nav2 *as an include in it*; Phase 5 namespaces *this exact package* for two robots. Build it like you will live in it for forty more weeks, because you will.

This is the capstone of Phase 1. Everything from weeks 1 through 7 — the rigid-body math, the tf2 tree, the URDF, the actions and lifecycle, the QoS literacy, the diff-drive kinematics, the SLAM — converges here into one installable, operable, defensible package. The deliverable is two things: the package itself, and your passing the milestone review.

**Estimated time:** ~11 hours (split across Wednesday, Thursday, Friday, Saturday, Sunday in the suggested schedule).

> **Compounds forward:** The syllabus is explicit that this is "the foundation package every subsequent phase extends." Do not treat it as disposable. Phase 2 (week 9+) assumes `crunchbot_bringup` exists and works, and adds a Jetson, a depth camera, and a fused state estimator by *including new subsystem launch files in this package*. A throwaway mini-project here becomes technical debt you carry for the rest of the track.

---

## What you will build

A single ament-Python package, `crunchbot_bringup`, that satisfies the bring-up contract from lecture 2, section 2.8. Concretely:

1. **One top-level launch file** — `launch/robot.launch.py` — that composes per-subsystem includes and exposes a documented operator interface (`world`, `slam`, `rviz`, `use_sim_time`, `namespace`).
2. **Per-subsystem launch files** — `description.launch.py`, `gz_sim.launch.py`, `slam.launch.py`, `rviz.launch.py` — each independently runnable and independently testable.
3. **One YAML parameter file per node** under `config/`, keyed by the node's runtime name, with every non-default parameter commented to explain *why* it has that value.
4. **A saved rviz2 layout** — `rviz/bringup.rviz` — that opens showing the map, the laser scan, the TF tree, the robot model, and the odometry, with sensible fixed frame and view.
5. **The `map_run_timer` node** from exercise 3, wired as a console entry point, so any mapping run is timed and reported.
6. **A package `README.md`** that documents the one command, every argument, and the bring-up topology — the operator-facing documentation that co-evolves with the launch file.
7. **A milestone evidence pack** — the artifacts (`view_frames` PDF, `ros2 topic info -v` dumps, the drift measurement, the map at three lidar rates) that you bring to the architecture review.

You ship **one package** with this structure (the layout from lecture 2, section 2.1):

```text
crunchbot_bringup/
├── package.xml
├── setup.py
├── resource/crunchbot_bringup
├── crunchbot_bringup/
│   ├── __init__.py
│   └── map_run_timer.py          ← exercise 3, wired as an entry point
├── launch/
│   ├── robot.launch.py           ← top-level entry point
│   ├── description.launch.py
│   ├── gz_sim.launch.py
│   ├── slam.launch.py
│   └── rviz.launch.py
├── config/
│   ├── slam_toolbox.yaml
│   └── ros_gz_bridge.yaml
├── rviz/bringup.rviz
├── worlds/{warehouse.sdf, house.sdf}
├── urdf/crunchbot.urdf.xacro
├── maps/.gitkeep
└── README.md
```

---

## Rules

- **You may** read the ROS2 Jazzy docs, the REPs (especially REP 105), the `slam_toolbox` README, `turtlebot4_bringup` and `nav2_bringup` source, the lecture notes, and your own weeks 1–7 artifacts.
- **You may NOT** depend on any third-party package beyond the ROS2 Jazzy desktop install plus `slam_toolbox`, `ros_gz_sim`, `ros_gz_bridge`, and `robot_state_publisher`. No `turtlebot*_bringup` as a runtime dependency — you may *read* it, not *depend* on it. The point is to build your own.
- **Target distro:** ROS2 Jazzy Jalisco on Ubuntu 24.04 (or WSL2). **Gz Sim:** Harmonic.
- **Every parameter lives in a YAML file**, keyed by node name. Inline parameter dicts are reserved for `use_sim_time` and at most one or two launch-controlled overrides per node.
- **No absolute paths.** Every asset is resolved through `FindPackageShare` + `PathJoinSubstitution`. A single `/home/` in any launch file is an automatic documentation fail.
- **Exactly one TF broadcaster per edge.** The Gz `DiffDrive` plugin owns `odom → base_link`; `robot_state_publisher` owns the static joints; `slam_toolbox` owns `map → odom`. No duplicates.
- **The package must build with `colcon build --symlink-install` with zero warnings** and come up with one command on a clean checkout.

---

## Acceptance criteria

The grading rubric is below. Each box maps to a deliverable. The milestone review (Documentation + Defense, 40% combined) is the hard gate — you do not advance to Phase 2 without it signed.

### Bring-up correctness (30%)

- [ ] `ros2 launch crunchbot_bringup robot.launch.py` brings up `robot_state_publisher`, Gz Sim + the spawn + `ros_gz_bridge`, `slam_toolbox`, and `rviz2` from a clean checkout, with no second terminal required.
- [ ] `ros2 launch crunchbot_bringup robot.launch.py --show-args` lists all five arguments with descriptions.
- [ ] `slam:=false` starts no `slam_toolbox` and publishes no `/map`; the launch still comes up cleanly.
- [ ] `rviz:=false` starts no `rviz2`; the launch still comes up cleanly (useful for headless runs).
- [ ] `namespace:=robot1` namespaces the whole stack — `ros2 node list` shows `/robot1/...` nodes — while `/tf` and `/tf_static` remain global and frame ids are prefixed `robot1/...`.
- [ ] `rviz/bringup.rviz` opens with the map, scan, robot model, TF, and odometry already configured; no manual display setup needed.

### TF tree (defended at review) (15%)

- [ ] `ros2 run tf2_tools view_frames` produces a single connected tree rooted at `map`: `map → odom → base_link → {laser, imu, wheels...}`.
- [ ] No edge has two broadcasters. `ros2 run tf2_ros tf2_monitor odom base_link` reports a single authority and a stable rate.
- [ ] The static/dynamic split is documented: which edges are static (URDF fixed joints) and which are dynamic (`odom → base_link`, `map → odom`), and which node owns each.
- [ ] No `extrapolation` or `lookup would require extrapolation into the future` errors during a 60-second run.

### QoS (defended at review) (10%)

- [ ] Every sensor stream (`/scan`, `/imu/data`, odometry) uses `BEST_EFFORT` + `KEEP_LAST` and you can state why.
- [ ] The `/map` topic uses `RELIABLE` + `TRANSIENT_LOCAL` and you can state why (a late-joining subscriber must still receive the latched map).
- [ ] `ros2 topic info -v <topic>` for every topic is captured in the evidence pack, showing matching publisher/subscriber QoS.
- [ ] `ros2 doctor` reports no QoS-mismatch warnings during a full bring-up.

### Odometry (defended at review) (10%)

- [ ] You can state where `odom → base_link` comes from (the Gz `DiffDrive` plugin in sim) and how it would come from your week-6 node on hardware.
- [ ] A documented drift measurement: drive a 10×10 m square (or a known closed loop), and report the position error on return-to-origin, with the conditions stated.
- [ ] You can explain *why* the odometry drifts (wheel slip, radius error, integration) and what Phase 2 will do about it (IMU + wheel fusion via `robot_localization`).

### Map (defended at review) (5%)

- [ ] A saved map of at least one multi-room world, with a visible resolved loop closure.
- [ ] A documented comparison of map quality at (at least) two lidar update rates, with a one-paragraph conclusion.

### Documentation + milestone (30%)

- [ ] The package `README.md` documents the one command, every argument (matching `--show-args`), and the bring-up topology (a short include tree and a TF-tree sketch).
- [ ] The `config/*.yaml` files have a comment on every non-default parameter explaining the value.
- [ ] The milestone evidence pack (`docs/milestone/`) contains: the `view_frames` PDF, the `ros2 topic info -v` dumps, the drift measurement with plot, and the map-quality comparison.
- [ ] **The Phase 1 milestone architecture review is passed and the rubric in `homework.md` is signed by a reviewer.**

---

## Suggested implementation outline

The order matters. Build the package, get one command working, *then* assemble the evidence pack, *then* rehearse the defense.

### Wednesday (~1.5 h) — namespace and composition skeleton

1. Start from the `crunchbot_bringup` package you built in exercise 1.
2. Write `gz_sim.launch.py`: start the Gz Sim server with your world, spawn the robot from `/robot_description` with `ros_gz_sim create`, and start `ros_gz_bridge` from `config/ros_gz_bridge.yaml` (bridging `/clock`, `/scan`, `/imu/data`, `/cmd_vel`, `/odom`, `/joint_states`). Configure the Gz `DiffDrive` plugin in your URDF to publish `odom → base_link` at 50 Hz with the correct frame names.
3. Confirm `ros2 launch crunchbot_bringup robot.launch.py slam:=false rviz:=false` brings up the robot in Gz and you can drive it with `ros2 topic pub /cmd_vel`.

### Thursday (~2.5 h) — SLAM, rviz layout, one command

4. Wire in `slam.launch.py` and `rviz.launch.py` (from exercise 2). Bring the full stack up.
5. Lay out rviz2: add the Map, LaserScan, RobotModel, TF, and Odometry displays; set the fixed frame to `map`; set a sensible default view. Save as `rviz/bringup.rviz`. Re-launch and confirm it opens already configured.
6. Confirm the full one-command bring-up and run the three-command check (`ros2 node list`, `ros2 topic list`, `view_frames`).
7. Add the `namespace` argument path (the `GroupAction` + `PushRosNamespace` from exercise 2) and verify `namespace:=robot1` namespaces nodes while keeping TF global.

### Friday (~2.5 h) — map a new world, time it, capture evidence

8. Wire `map_run_timer` as a console entry point. Run the exercise-3 / challenge-1 workflow: map a new world end-to-end and capture the timed run.
9. Capture the QoS evidence: `ros2 topic info -v` for `/scan`, `/imu/data`, `/odom`, `/map`, `/tf`. Save the outputs into `docs/milestone/qos/`.
10. Capture the TF evidence: `view_frames` PDF, `tf2_monitor odom base_link` output, a 60-second run with no extrapolation errors.

### Saturday (~1.5 h) — odometry drift, map quality, evidence pack

11. Drive the documented 10×10 m square; record the return-to-origin error. Plot odometry vs. ground truth (Gz publishes ground-truth pose; subscribe and diff) in PlotJuggler. Save the plot.
12. Map the same world at two lidar rates (e.g., 5 Hz and 15 Hz); save both maps; write the one-paragraph comparison.
13. Assemble `docs/milestone/` into a coherent evidence pack and write the package `README.md`.

### Sunday (~0.5 h) — defend

14. Sit the milestone review. Walk the reviewer through the evidence pack: the `view_frames` PDF for the TF defense, the `topic info -v` dumps for the QoS defense, the drift plot for the odometry defense, the map comparison for the map defense. Answer the rubric questions (`homework.md`). Get the rubric signed.

---

## Hints

- **The Gz bridge `config/ros_gz_bridge.yaml`** is itself a parameter file. Each entry maps a Gz topic to a ROS2 topic with a message type and a direction (`GZ_TO_ROS`, `ROS_TO_GZ`, or `BIDIRECTIONAL`). Bridge `/clock` first — without it, `use_sim_time` has no clock to use and every node hangs waiting for time. This is a guaranteed "my robot won't come up" bug if you forget it.
- **`use_sim_time` everywhere or nowhere.** Set it once with `SetParameter` at the top of `robot.launch.py`. A node that misses it runs on wall time, its timestamps disagree with the sim clock, and tf2 throws extrapolation errors that look like a tf2 bug. The reviewer *will* ask "how do you guarantee every node uses sim time?" — the answer is the global `SetParameter`.
- **One broadcaster per edge.** Do not run your week-6 odometry node *and* the Gz `DiffDrive` plugin; both publish `odom → base_link` and the tree flickers. In sim, let the plugin own it. Document that on hardware (Phase 6) the week-6 node takes over.
- **The map QoS is the classic mismatch.** `slam_toolbox` publishes `/map` as `RELIABLE` + `TRANSIENT_LOCAL`. If rviz2 (or your timer node) subscribes with the default sensor QoS, it silently receives nothing. Match the QoS. This is the week-5 lesson, and it is the most common reason "rviz shows no map."
- **`view_frames` writes to the current directory.** Run it from `docs/milestone/` so the PDF lands where your evidence pack expects it.
- **Rehearse the defense out loud.** The learners who fail the milestone are almost never the ones whose robot is broken; they are the ones who cannot explain *why* it works. For each of the four defenses, prepare one sentence of claim and one artifact of evidence.

---

## Anti-goals

The following are explicitly **not** part of this mini-project. They are later phases; pursuing them now distracts from the lesson and is not graded.

- **Nav2.** Navigation is Phase 3 (week 17). Do not add a planner or controller. This package brings the robot up and maps; it does not navigate autonomously.
- **A fused state estimator.** `robot_localization` / EKF is Phase 2 (week 10). Your odometry here is raw wheel odometry from the Gz plugin. The drift you measure is *expected* and is the motivation for Phase 2.
- **Hardware bring-up.** Real motor controllers, micro-ROS, CAN — all Phase 6. This is a sim bring-up. You *document* how the hardware path would differ (your week-6 node owning `odom → base_link`), but you do not implement it.
- **Composable-node containers.** Your Phase 1 topics are low-bandwidth; separate processes are correct here. Composition earns its complexity in Phase 2's perception pipeline. Know why you are not using it; do not use it.
- **A perfect map.** The map needs to be complete and loop-closed, not survey-grade. Chasing centimeter-perfect walls is not the lesson; reproducible bring-up is.

---

## Submission

Push the package to your Week 8 GitHub repository at `mini-project/crunchbot_bringup/`. The instructor reviews by:

1. Cloning the repo onto a clean ROS2 Jazzy machine.
2. Running `colcon build --packages-select crunchbot_bringup --symlink-install` — must build clean.
3. Running `ros2 launch crunchbot_bringup robot.launch.py` — must come up with one command.
4. Running the milestone review against the rubric in `homework.md`, using your `docs/milestone/` evidence pack.

A submission that builds clean, comes up with one command, and passes the four defenses is a pass. The most common review-fails, in order: a hard-coded path that breaks on the reviewer's machine; a duplicate TF broadcaster causing flicker; a QoS mismatch that hides the map; and — most often of all — a learner who cannot explain their own odometry drift number.

---

## Stretch goals (no extra grade)

- **Cold-boot time as a metric.** Instrument your bring-up to log the wall-clock time from launch to "all nodes ready and `/map` first published." Drive it under 30 seconds. Cold-boot time is a real product metric you will see again in Phase 6 (the capstone requires a 60-second cold boot of a far larger stack).
- **A `localization.launch.py` subsystem.** Add a sibling launch file that brings `slam_toolbox` up in `localization` mode against a saved map, selected by a `mode:=mapping|localization` argument on the top level. This previews the AMCL-style localization you will lean on in Phase 3.
- **Two-robot launch.** Write a `multi_robot.launch.py` that includes `robot.launch.py` twice with `namespace:=robot1` and `namespace:=robot2`. Confirm both map the same world independently with no TF collisions. This is a direct preview of Phase 5, week 35, and it validates that your namespacing is actually correct rather than accidentally working for the single-robot case.

The stretch goals are harder than the main project. Do not attempt them until the milestone is signed.

---

**References**

- ROS2 Jazzy — Launch documentation: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html>
- `slam_toolbox` — configuration and services: <https://github.com/SteveMacenski/slam_toolbox>
- `ros_gz` — the Gz Sim ↔ ROS2 bridge: <https://github.com/gazebosim/ros_gz/tree/jazzy>
- REP 105 — "Coordinate Frames for Mobile Platforms": <https://www.ros.org/reps/rep-0105.html>
- ROS2 QoS design doc: <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html>
- `turtlebot4_bringup` — the reference `*_bringup` package: <https://github.com/turtlebot/turtlebot4>

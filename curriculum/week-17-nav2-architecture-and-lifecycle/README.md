# Week 17 — Nav2 Architecture and Lifecycle

Welcome to Phase 3 and to the most important reusable codebase in mobile robotics. By Friday you will be able to bring up the full Nav2 stack on your own map, send a goal, watch the planner and the controller take turns driving the robot, read the navigation behavior tree the way you read a stack trace, and write your own behavior plugin that hooks into the lifecycle correctly instead of fighting it. You will read `ros2 lifecycle get /controller_server` the way a backend engineer reads a health check.

We assume you finished Phase 2 — you have a fused state estimate, a perception node, and (from Week 7) a saved map. We also assume your **week-7 map** of a multi-room Gz Sim world still loads and that AMCL can localize against it. If it can't, fix that first — every exercise this week navigates *that* robot on *that* map. Nav2 is not a thing you read about; it is a thing you run.

The one idea to internalize before you read another line: **Nav2 is not a path planner. Nav2 is a navigation *framework* — a set of independently-managed lifecycle servers (planner, controller, smoother, behaviors, the BT navigator) wired together by a behavior tree, with two costmaps underneath and a lifecycle manager on top that brings them up in the right order and tears them down cleanly.** When people say "Nav2 doesn't work," they almost always mean one of four specific things: a lifecycle node that never reached `active`, a costmap layer that isn't seeing the sensor it expects, a TF frame that doesn't exist, or a BT that's looping in a recovery branch you didn't know was there. This week teaches you to tell those four apart in under five minutes.

This is where Phase 3's safety stance begins. **Every lab from here forward declares a fail-safe.** This week's fail-safe question is the one on the syllabus: *what does the robot do if the planner crashes mid-goal?* You will answer it in code, not in prose.

## Learning objectives

By the end of this week, you will be able to:

- **Name** every server in the Nav2 stack — `planner_server`, `controller_server`, `smoother_server`, `behavior_server`, `bt_navigator`, `waypoint_follower`, `velocity_smoother`, `map_server`, `amcl`, `lifecycle_manager` — and state what each one does, what plugins it loads, and what it publishes.
- **Explain** the managed-node lifecycle (`unconfigured → inactive → active → finalized`) and trace how `lifecycle_manager` walks every Nav2 server through `configure` and `activate` in a deterministic order at bring-up.
- **Distinguish** the global costmap from the local costmap — their update rates, their layer stacks (static, obstacle, voxel, inflation), their rolling-window vs. fixed-frame behavior — and introspect both live in rviz2 and on the topic.
- **Read** the default navigation behavior tree (`navigate_to_pose_w_replanning_and_recovery.xml`): the `PipelineSequence`, the `RateController`, the `RecoveryNode`, the `ComputePathToPose`/`FollowPath` action leaves, and the recovery subtree, and predict what the robot does when a leaf fails.
- **Bring up** the full stack from a launch file with your own `nav2_params.yaml`, send a goal from rviz2 and from the `NavigateToPose` action API, and confirm the robot reaches it.
- **Configure** a costmap plugin — swap the `obstacle_layer` for a `voxel_layer`, tune the `inflation_layer` radius — and observe the effect on the planned path in real time.
- **Write** a custom Nav2 behavior plugin (a `BehaviorServer` plugin) in C++ that pauses navigation when an external `/operator/hold` topic latches `true` and cleanly resumes when it clears — your first plugin against the real plugin interface.
- **Declare and implement** a fail-safe: detect a `planner_server` crash mid-goal and bring the base to a controlled stop instead of letting the last `/cmd_vel` coast.

## Prerequisites

This week assumes you have completed **C24 weeks 1–16**, or have equivalent ROS2 + perception fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or container / WSL2), with **Nav2** installed: `sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup`.
- Your **week-7 map** (`.yaml` + `.pgm`) of a multi-room world, and a Gz Sim world that matches it, so AMCL can localize.
- The **week-3 diff-drive robot** with a working TF tree: `map → odom → base_link → laser_link`, a 2D LiDAR on `/scan`, and `/odom` published honestly (Week 6).
- Fluency with **lifecycle nodes** from Week 4 — you know `configure`, `activate`, `deactivate`, `cleanup`, and you can read `ros2 lifecycle get` / `ros2 lifecycle set`.
- **QoS literacy** from Week 5 — you know `/map` is `RELIABLE` + `TRANSIENT_LOCAL` and `/scan` is `BEST_EFFORT`, and you can spot a costmap that isn't getting its sensor because of a QoS mismatch.
- You can build a **C++ `ament_cmake` package** with a `pluginlib` export — the custom-plugin exercise is C++ (`rclcpp`), because that is how Nav2 plugins are actually written.

You do **not** need prior Nav2 experience. We start at the architecture diagram and build up to a working custom plugin. If you've only ever run `nav2_bringup` and clicked "Nav2 Goal" in rviz2 without knowing what the eight servers underneath were doing, this is the week that knowledge becomes load-bearing.

## Topics covered

- The **Nav2 server inventory**: `bt_navigator` (the orchestrator), `planner_server` (global plan), `controller_server` (local control + the local costmap), `smoother_server`, `behavior_server` (recoveries: spin, back-up, wait, drive-on-heading), `waypoint_follower`, `velocity_smoother`, `map_server`, `amcl`, and the `lifecycle_manager` that owns them.
- The **managed-node lifecycle** applied to Nav2: the `unconfigured / inactive / active / finalized` states, the `configure`/`activate`/`deactivate`/`cleanup` transitions, the `bond` mechanism by which `lifecycle_manager` detects a crashed server, and the deterministic bring-up order in `lifecycle_manager`'s `node_names` list.
- **The two costmaps**: the global costmap (full map, fixed `map` frame, planner's world) vs. the local costmap (rolling window, `odom` frame, controller's world); the **layered costmap** model — `static_layer`, `obstacle_layer`, `voxel_layer`, `inflation_layer`, `range_sensor_layer` — and how layers combine into the master grid.
- **The plugin architecture**: Nav2's `pluginlib`-based extension points — planner plugins (`NavFn`, `SmacPlannerHybrid`, `ThetaStar`), controller plugins (`DWB`, `RPP`, `MPPI`), behavior plugins, costmap-layer plugins, goal-checker and progress-checker plugins — and how `nav2_params.yaml` selects and configures each.
- **The BT-driven navigation pattern**: how `bt_navigator` ticks `navigate_to_pose_w_replanning_and_recovery.xml`; the `PipelineSequence`, `RateController`, `RecoveryNode`, `RoundRobin`, and the action-node leaves (`ComputePathToPose`, `FollowPath`, `Spin`, `BackUp`, `Wait`); the blackboard; and how a leaf's `FAILURE` propagates into a recovery.
- **Costmap-plugin configuration**: enabling a `voxel_layer` for 3D obstacle marking, tuning the `inflation_layer` (`cost_scaling_factor`, `inflation_radius`), the `obstacle_layer` raytrace/mark ranges, and observing each change in the planned path.
- **Writing a Nav2 behavior plugin** in C++: the `nav2_core::Behavior` interface, `configure`/`activate`/`deactivate`/`cleanup`, the `onRun`/`onCycleUpdate` cycle, exporting it with `PLUGINLIB_EXPORT_CLASS`, the `plugin.xml`, and wiring it into the `behavior_server` plugin list.
- **The fail-safe**: detecting a crashed `planner_server` via the lifecycle `bond` and the `NavigateToPose` action result, and bringing the base to a controlled stop — the first of Phase 3's mandatory fail-safe declarations.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                               | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-----------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Nav2 server inventory; lifecycle; bring-up           |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | The two costmaps; layers; rviz2 introspection        |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | The navigation BT; plugins; the action API           |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | The custom behavior plugin; the fail-safe            |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Plugin wiring; costmap tuning; the hold plugin       |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                              |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, fail-safe write-up polish             |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                     | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The Nav2 docs, the lifecycle design docs, the BT-navigator reference, and the talks worth your time |
| [lecture-notes/01-nav2-architecture-and-lifecycle.md](./lecture-notes/01-nav2-architecture-and-lifecycle.md) | The server inventory, the managed-node lifecycle, the bring-up order, and the two costmaps |
| [lecture-notes/02-costmaps-the-navigation-bt-and-plugins.md](./lecture-notes/02-costmaps-the-navigation-bt-and-plugins.md) | The layered costmap in depth, reading the navigation BT, the plugin architecture, and writing a behavior plugin |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-bringup-and-introspect.md](./exercises/exercise-01-bringup-and-introspect.md) | Bring up Nav2 on your week-7 map, send a goal, and read the lifecycle + costmaps live |
| [exercises/exercise-02-navigate-to-pose-client.py](./exercises/exercise-02-navigate-to-pose-client.py) | A `NavigateToPose` action client with feedback, cancellation, and a planner-crash fail-safe |
| [exercises/exercise-03-costmap-monitor.py](./exercises/exercise-03-costmap-monitor.py) | Subscribe to both costmaps, decode the `OccupancyGrid`, and watch the inflation layer change as you re-tune it |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-the-stuck-stack.md](./challenges/challenge-01-the-stuck-stack.md) | A bring-up that "comes up but won't navigate" — four planted faults across lifecycle, costmap, TF, and BT |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the mandatory fail-safe declaration |
| [mini-project/README.md](./mini-project/README.md) | The `crunchbot_nav` bring-up package + the `OperatorHold` behavior plugin |

## The "it reached `active`" promise

C24 uses a recurring marker for every exercise that ends in the stack actually being up. For Nav2, that marker is the lifecycle state:

```
$ ros2 lifecycle get /bt_navigator
active [3]
$ ros2 lifecycle get /planner_server
active [3]
$ ros2 lifecycle get /controller_server
active [3]
```

If any server is stuck in `unconfigured [1]` or `inactive [2]` when you expected `active [3]`, the stack is *not* up, no matter what rviz2 shows. A server stuck in `inactive` is the canonical Nav2 silent failure: the lifecycle manager logged the problem once at startup and then went quiet, and you spend an afternoon sending goals into a `bt_navigator` that never activated. The point of Week 17 is to make `active [3]` ordinary — and to make the wrong state *loud* instead of buried in the launch log.

## Stretch goals

If you finish the regular work early and want to push further:

- Swap the default `NavfnPlanner` for `SmacPlannerHybrid` (the Hybrid-A* planner) in `nav2_params.yaml` and watch the planned path respect a minimum turning radius — a preview of Week 18, where you implement A* by hand and compare.
- Replace the `DWB` controller with `RegulatedPurePursuitController` (RPP) and then `MPPI`, and compare path-tracking on the same goal. Note which one your robot's dynamics like best. (MPPI previews Week 22.)
- Open the navigation BT in **Groot 2** (`sudo snap install groot2` or the AppImage) and watch it tick live as the robot navigates — a preview of Week 19, where Groot 2 is the main tool.
- Read the Nav2 `lifecycle_manager` source until you can explain the **bond timeout** — how the manager detects a server that crashed (not just one that returned an error) and what it does about it. This is the mechanism behind your fail-safe.

## Up next

Week 18 opens up the planner you've been treating as a black box: you implement A* and Dijkstra by hand on an occupancy grid, compare them against Nav2's `NavFn` on the same map, and drop in `SMAC Hybrid-A*` for an Ackermann-like vehicle. The costmap literacy you build this week is exactly what those planners search over. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

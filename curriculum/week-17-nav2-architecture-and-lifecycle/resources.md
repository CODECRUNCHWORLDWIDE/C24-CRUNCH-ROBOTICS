# Week 17 — Resources

Every resource here is **free** and pinned to **ROS2 Jazzy** and the matching **Nav2** release wherever the docs are versioned. The Nav2 docs (`docs.nav2.org`) are open. The ROS2 lifecycle design docs are open. No paywalled books are linked.

Nav2's docs version with the ROS2 distro. The concepts — the server inventory, the lifecycle, the layered costmap, the navigation BT — are stable across distros; only the parameter names and the occasional plugin default move. When in doubt, trust `ros2 param dump` on your running stack over any doc.

## Required reading (work it into your week)

- **Nav2 — Getting Started** — the architecture overview, the first bring-up, the rviz2 goal workflow:
  <https://docs.nav2.org/getting_started/index.html>
- **Nav2 — Navigation Concepts** — the canonical description of the planner/controller/behavior/BT split and the costmaps:
  <https://docs.nav2.org/concepts/index.html>
- **Nav2 — First-Time Robot Setup Guide** — the TF, URDF, odom, and sensor prerequisites Nav2 assumes (read this against your week-7 robot):
  <https://docs.nav2.org/setup_guides/index.html>
- **Managed nodes / lifecycle design** — the ROS2 design doc for the state machine every Nav2 server implements:
  <https://design.ros2.org/articles/node_lifecycle.html>
- **Nav2 — Behavior Trees overview** — how `bt_navigator` ticks the navigation tree, and the default trees that ship:
  <https://docs.nav2.org/behavior_trees/index.html>

## The reference docs (you'll have these open all week)

- **Nav2 — Configuration Guide** (every server's parameters, in one place — bookmark it):
  <https://docs.nav2.org/configuration/index.html>
- **Nav2 — Costmap 2D configuration** (the layers, the plugin list, the inflation/obstacle/voxel/static layer params):
  <https://docs.nav2.org/configuration/packages/configuring-costmaps.html>
- **Nav2 — `bt_navigator` configuration** (the default BT XML path, the plugin libraries it loads):
  <https://docs.nav2.org/configuration/packages/configuring-bt-navigator.html>
- **Nav2 — list of BT nodes** (every control/decorator/condition/action node you can put in a tree):
  <https://docs.nav2.org/behavior_trees/overview/nav2_specific_nodes.html>
- **Nav2 — lifecycle manager** (the `node_names` order, the `bond` timeout, autostart):
  <https://docs.nav2.org/configuration/packages/configuring-lifecycle.html>

## Plugin authoring (for the custom behavior plugin)

- **Nav2 — Writing a New Behavior Plugin** (the exact tutorial the Thursday exercise follows):
  <https://docs.nav2.org/plugin_tutorials/docs/writing_new_behavior_plugin.html>
- **Nav2 — Writing a New Costmap2D Plugin** (for the stretch costmap-layer work):
  <https://docs.nav2.org/plugin_tutorials/docs/writing_new_costmap2d_plugin.html>
- **`pluginlib` concept** (how Nav2 loads plugins at runtime from a `plugin.xml`):
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Pluginlib.html>
- **`nav2_core` interfaces** (the abstract base classes — `Behavior`, `GlobalPlanner`, `Controller`, `Layer`):
  <https://github.com/ros-navigation/navigation2/tree/main/nav2_core/include/nav2_core>

## API references

- **`NavigateToPose` action definition** (`nav2_msgs/action/NavigateToPose`) — goal, feedback, result:
  <https://github.com/ros-navigation/navigation2/blob/main/nav2_msgs/action/NavigateToPose.action>
- **`nav2_simple_commander`** (the Python API the Exercise 2 client mirrors — read it before you write your own):
  <https://docs.nav2.org/commander_api/index.html>
- **`rclcpp_lifecycle::LifecycleNode`** (what every Nav2 server inherits):
  <https://docs.ros.org/en/jazzy/p/rclcpp_lifecycle/>
- **`nav_msgs/OccupancyGrid`** (the costmap-as-grid the monitor in Exercise 3 decodes):
  <https://docs.ros2.org/latest/api/nav_msgs/msg/OccupancyGrid.html>

## Planners and controllers (preview of weeks 18, 20–22)

- **Nav2 — planner plugins** (`NavfnPlanner`, `SmacPlannerHybrid`, `SmacPlanner2D`, `ThetaStarPlanner`):
  <https://docs.nav2.org/configuration/packages/configuring-planner-server.html>
- **Nav2 — controller plugins** (`DWB`, `RegulatedPurePursuit`, `MPPI`):
  <https://docs.nav2.org/configuration/packages/configuring-controller-server.html>
- **SMAC planner deep-dive** (the Hybrid-A* you drop in this week and rebuild by hand next week):
  <https://docs.nav2.org/configuration/packages/configuring-smac-planner.html>

## Tools you'll use this week

- **`ros2 lifecycle get / set / list <node>`** — your primary diagnostic. Is the server `active [3]`?
- **`ros2 launch nav2_bringup ...`** — the reference bring-up to crib from; you'll write your own.
- **rviz2** with the Nav2 panel — send goals, visualize both costmaps, the global/local plans, the footprint.
- **`ros2 topic echo /global_costmap/costmap --once`** — the costmap as a raw `OccupancyGrid`.
- **`ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose ...`** — fire a goal from the CLI.
- **Groot 2** (optional this week, central in Week 19) — visualize the navigation BT ticking live.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **`bt_navigator`** | The orchestrator. Ticks the navigation behavior tree; exposes the `NavigateToPose` action. |
| **`planner_server`** | Computes the global path from start to goal over the global costmap. Loads a planner plugin (`NavFn`, SMAC). |
| **`controller_server`** | Follows the global path locally, avoiding obstacles in the local costmap. Loads a controller plugin (DWB, RPP, MPPI). Outputs `/cmd_vel`. |
| **`behavior_server`** | Runs recovery behaviors: spin, back up, wait, drive-on-heading. Where your custom plugin lives. |
| **`smoother_server`** | Post-processes a raw path into a smoother one. Optional. |
| **`lifecycle_manager`** | Brings every Nav2 server up (and down) in a fixed order; detects crashes via `bond`. |
| **Managed node** | A lifecycle node: `unconfigured → inactive → active → finalized`, with `configure`/`activate`/`deactivate`/`cleanup` transitions. |
| **`bond`** | A heartbeat between `lifecycle_manager` and each server; a broken bond means the server crashed. |
| **Global costmap** | Full-map, `map`-frame grid the planner searches. Static + obstacle + inflation layers. |
| **Local costmap** | Rolling-window, `odom`-frame grid the controller avoids obstacles in. |
| **Layered costmap** | The model where `static`, `obstacle`, `voxel`, `inflation` layers combine into one master grid. |
| **`inflation_layer`** | Spreads a decaying cost outward from obstacles so the planner keeps clearance. |
| **`pluginlib`** | The runtime plugin loader; every planner/controller/behavior/layer is a `pluginlib` class chosen in YAML. |
| **`PipelineSequence`** | A Nav2 BT control node: ticks children in order, re-ticking earlier ones each cycle. The spine of the nav tree. |
| **`RecoveryNode`** | A Nav2 BT control node: run child 1; on failure run child 2 (the recovery), then retry child 1. |

---

*If a link 404s, please open an issue so we can replace it.*

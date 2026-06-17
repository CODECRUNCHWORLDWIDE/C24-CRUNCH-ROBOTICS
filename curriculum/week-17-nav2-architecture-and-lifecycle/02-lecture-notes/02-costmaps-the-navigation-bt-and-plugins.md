# Lecture 2 — Costmaps in Depth, the Navigation BT, and Writing Plugins

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can read the default navigation behavior tree leaf by leaf and predict the robot's behavior when a leaf fails, configure a costmap layer plugin and see its effect on the planned path, and write a `nav2_core::Behavior` plugin in C++ that hooks into the `behavior_server` correctly.

Lecture 1 gave you the map of the territory — the servers, the lifecycle, the two costmaps. This lecture goes inside two of those: the **behavior tree** that `bt_navigator` ticks (the navigation *logic*), and the **plugin architecture** that lets you extend any server without forking Nav2 (the navigation *extensibility*). Three parts: (1) the costmap as a tunable object, (2) reading the navigation BT, (3) writing a plugin.

---

## Part 1 — The costmap as a thing you tune

In Lecture 1 you learned what the layers *are*. Here you learn to *configure* them, because 80% of "the robot won't go through that doorway" or "the robot clips the corner" bugs are costmap-tuning bugs, not planner bugs.

### 1.1 The costmap parameter block

A costmap is configured under a node namespace in `nav2_params.yaml`. Here is a real, working global-costmap block with comments:

```yaml
global_costmap:
  global_costmap:
    ros__parameters:
      update_frequency: 1.0          # how often layers re-combine (Hz)
      publish_frequency: 1.0         # how often /global_costmap/costmap is published
      global_frame: map              # the planner's fixed frame
      robot_base_frame: base_link
      robot_radius: 0.22             # circular footprint; or use 'footprint' for a polygon
      resolution: 0.05               # metres per cell — matches your week-7 map
      track_unknown_space: true      # treat unknown as not-free (conservative)
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]

      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
        map_subscribe_transient_local: true   # <-- the Week-5 QoS latch. Get this wrong and the map never loads.

      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        enabled: true
        observation_sources: scan
        scan:
          topic: /scan
          data_type: "LaserScan"
          marking: true               # mark hit cells as obstacles
          clearing: true              # raytrace-clear cells the beam passed through
          max_obstacle_height: 2.0
          obstacle_max_range: 2.5
          raytrace_max_range: 3.0

      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0      # higher = cost decays faster = hugs walls more
        inflation_radius: 0.55        # how far cost spreads from each obstacle (m)
```

Two things to burn in:

1. **`plugins:` is an ordered list and the order is the layer order.** `inflation_layer` is last because it operates on whatever the layers below it marked. Put inflation before obstacle and it inflates an empty map.
2. **`map_subscribe_transient_local: true` is the Week-5 QoS lesson in production.** The `static_layer` subscribes to `/map`, which `map_server` publishes `TRANSIENT_LOCAL`. If this flag is wrong (or you point it at a `VOLATILE` publisher), the static layer subscribes *after* the one-shot map publish and gets nothing — an empty global costmap, a planner that thinks the building is an open field, and a robot that plans straight through walls. When the costmap is mysteriously empty, this line is the first suspect.

### 1.2 The local-costmap differences

The local costmap looks similar but differs in the load-bearing ways from Lecture 1 §3.1:

```yaml
local_costmap:
  local_costmap:
    ros__parameters:
      update_frequency: 5.0
      publish_frequency: 2.0
      global_frame: odom             # <-- odom, NOT map. Local smoothness over global accuracy.
      robot_base_frame: base_link
      rolling_window: true           # <-- the window follows the robot
      width: 5                       # metres
      height: 5
      resolution: 0.05
      plugins: ["obstacle_layer", "inflation_layer"]   # NO static_layer — local cares only about now
```

`rolling_window: true` and `global_frame: odom` are the two lines that make it *local*. There is no `static_layer` because the controller does not care about the wall three rooms away — only about the obstacle two metres ahead.

### 1.3 Swapping a layer: `obstacle_layer` → `voxel_layer`

The Tuesday exercise has you swap in a `voxel_layer`. The change is mechanical:

```yaml
      plugins: ["static_layer", "voxel_layer", "inflation_layer"]
      voxel_layer:
        plugin: "nav2_costmap_2d::VoxelLayer"
        enabled: true
        publish_voxel_map: true       # so you can visualize the 3D grid in rviz2
        origin_z: 0.0
        z_resolution: 0.05
        z_voxels: 16                  # 16 layers of 5 cm = 0.8 m tall
        observation_sources: pointcloud
        pointcloud:
          topic: /points
          data_type: "PointCloud2"
          marking: true
          clearing: true
```

Now the costmap is built from a 3D point cloud, projected to 2D — which catches the table edge a 2D LiDAR slices under. Re-tune the planner and watch the path change in rviz2. This is the *point* of the plugin architecture: a one-block YAML edit changes the robot's perception of obstacles without touching a line of C++.

---

## Part 2 — Reading the navigation behavior tree

`bt_navigator` ticks an XML behavior tree. The default is `navigate_to_pose_w_replanning_and_recovery.xml`, and reading it fluently is a Week-17 skill that pays off all the way to the capstone. (Week 19 teaches you to *author* trees; this week you must *read* the one you've been running.)

### 2.1 The default tree, annotated

Here is the structure of the default tree, lightly simplified to the load-bearing nodes:

```xml
<root main_tree_to_execute="MainTree">
  <BehaviorTree ID="MainTree">
    <!-- RecoveryNode: run child 1; if it fails, run child 2 (recovery), then retry. -->
    <RecoveryNode number_of_retries="6" name="NavigateRecovery">

      <!-- PipelineSequence: tick children in order, re-ticking earlier ones each cycle. -->
      <PipelineSequence name="NavigateWithReplanning">

        <!-- RateController: throttle the planner so we replan at 1 Hz, not every tick. -->
        <RateController hz="1.0">
          <!-- Compute the global path. On failure, the RecoveryNode wrapping this
               (ComputePathToPoseRecovery) tries to clear costmaps and retries. -->
          <RecoveryNode number_of_retries="1" name="ComputePathToPoseRecovery">
            <ComputePathToPose goal="{goal}" path="{path}" planner_id="GridBased"/>
            <ClearEntireCostmap name="ClearGlobalCostmap-Context"
                                service_name="global_costmap/clear_entirely_global_costmap"/>
          </RecoveryNode>
        </RateController>

        <!-- Follow the computed path. On failure, clear the LOCAL costmap and retry. -->
        <RecoveryNode number_of_retries="1" name="FollowPathRecovery">
          <FollowPath path="{path}" controller_id="FollowPath"/>
          <ClearEntireCostmap name="ClearLocalCostmap-Context"
                              service_name="local_costmap/clear_entirely_local_costmap"/>
        </RecoveryNode>

      </PipelineSequence>

      <!-- THE RECOVERY SUBTREE: only reached if the PipelineSequence above fails
           after its own retries. Tried in round-robin: clear costmaps, spin,
           wait, back up — then the outer RecoveryNode loops back to navigation. -->
      <ReactiveFallback name="RecoveryFallback">
        <GoalUpdated/>                              <!-- bail out of recovery if a new goal arrived -->
        <RoundRobin name="RecoveryActions">
          <Sequence name="ClearingActions">
            <ClearEntireCostmap service_name="local_costmap/clear_entirely_local_costmap"/>
            <ClearEntireCostmap service_name="global_costmap/clear_entirely_global_costmap"/>
          </Sequence>
          <Spin spin_dist="1.57"/>
          <Wait wait_duration="5.0"/>
          <BackUp backup_dist="0.30" backup_speed="0.05"/>
        </RoundRobin>
      </ReactiveFallback>

    </RecoveryNode>
  </BehaviorTree>
</root>
```

### 2.2 The control nodes you must recognize

- **`PipelineSequence`** — the spine. It ticks its children in order, but unlike a plain `Sequence`, it **re-ticks the earlier children every cycle.** That's what makes navigation *reactive*: the planner (`ComputePathToPose`) keeps getting re-ticked (throttled to 1 Hz by the `RateController`) *while* the controller (`FollowPath`) runs. The path stays fresh as the robot moves. This is **replanning**, and it's a property of the tree, not a feature of the planner.
- **`RecoveryNode`** — run the first child; if it returns `FAILURE`, run the second child (the recovery); then retry the first, up to `number_of_retries`. The whole tree is wrapped in one (`NavigateRecovery`) so that if navigation fails, the recovery subtree runs before giving up.
- **`RateController`** — a decorator that ticks its child at most `hz` times per second, returning `RUNNING` in between. This is why the planner runs at 1 Hz while the controller runs at 20 Hz — they're at different points in the tree with different rate gates.
- **`RoundRobin`** — tries its children one at a time, advancing on each entry. The recovery subtree uses it so successive recovery attempts try *different* behaviors (clear, then spin, then wait, then back up) instead of the same one repeatedly.
- **`ReactiveFallback`** — ticks children left to right, returning `SUCCESS` on the first success; it's *reactive* because it re-checks earlier children (here `GoalUpdated`) every tick, so a new goal aborts recovery immediately.

### 2.3 Predicting behavior when a leaf fails

This is the skill. Trace it:

- **`ComputePathToPose` returns `FAILURE`** (no path found). Its wrapping `RecoveryNode` clears the global costmap and retries once. If it still fails, the `PipelineSequence` fails, which drops the outer `RecoveryNode` into the recovery subtree: clear both costmaps, spin to re-perceive, wait, back up — then loop back and try to plan again. **Observable behavior:** the robot stops, spins in place, maybe backs up, then tries a new route. If you didn't know the recovery subtree existed, this looks like the robot "randomly spinning."
- **`FollowPath` returns `FAILURE`** (controller stuck, progress checker tripped). Clear the *local* costmap, retry. Still failing → recovery subtree. **Observable:** the robot stalls, the local costmap clears (in case it was a sensor ghost), then recovery.
- **A *crashed* planner** (Lecture 1 §5) — the action *never returns*, so the BT leaf hangs in `RUNNING`. The tree doesn't recover, because there's no `FAILURE` to react to. This is exactly why the crash fail-safe lives *outside* the BT.

> **The interview tell:** "the robot keeps spinning and backing up for no reason" is almost never a sensor problem and almost always the recovery subtree firing because the controller's progress checker keeps tripping — often because the goal tolerance is too tight or the inflation radius is so large the goal cell is `lethal`. Read the BT, find the recovery, work backward to *why it's being entered*.

---

## Part 3 — The plugin architecture and writing a behavior plugin

Nav2's extensibility is `pluginlib` everywhere: planners, controllers, behaviors, costmap layers, goal checkers, progress checkers, smoothers, and BT nodes are all plugins selected in YAML and loaded at runtime. This is why you almost never fork Nav2 — you write a plugin against a stable interface and list it in your params.

### 3.1 The `nav2_core` interfaces

The abstract base classes live in `nav2_core`. The ones you'll meet:

| Interface | You implement it to... | Loaded by |
|---|---|---|
| `nav2_core::GlobalPlanner` | write a new global planner (your hand-rolled A*, Week 18) | `planner_server` |
| `nav2_core::Controller` | write a new local controller | `controller_server` |
| `nav2_core::Behavior` | write a new recovery/behavior (this week) | `behavior_server` |
| `nav2_costmap_2d::Layer` | write a new costmap layer | both costmaps |
| `nav2_core::GoalChecker` | redefine "close enough to the goal" | `controller_server` |

Every one of them is a lifecycle-aware class with `configure` / `activate` / `deactivate` / `cleanup`, mirroring the server that hosts it. When the `behavior_server` activates, it activates its plugins; your plugin's `activate()` runs then.

### 3.2 The `Behavior` interface

The Thursday exercise implements the syllabus's `OperatorHold`: pause navigation when `/operator/hold` latches `true`, resume cleanly when it clears. A behavior plugin implements `nav2_core::Behavior` via the convenience base `nav2_behaviors::TimedBehavior<ActionT>`, which gives you `onRun` (called once when the behavior starts) and `onCycleUpdate` (called every cycle while it runs). Here is the spine of the plugin (full version is in the mini-project):

```cpp
// operator_hold.hpp
#ifndef CRUNCHBOT_NAV__OPERATOR_HOLD_HPP_
#define CRUNCHBOT_NAV__OPERATOR_HOLD_HPP_

#include <string>
#include <memory>

#include "nav2_behaviors/timed_behavior.hpp"
#include "nav2_msgs/action/wait.hpp"          // we reuse the Wait action type
#include "std_msgs/msg/bool.hpp"
#include "rclcpp/rclcpp.hpp"

namespace crunchbot_nav
{

using HoldAction = nav2_msgs::action::Wait;   // pausing == waiting until hold clears

class OperatorHold : public nav2_behaviors::TimedBehavior<HoldAction>
{
public:
  OperatorHold();
  ~OperatorHold() override = default;

  // Called once when the behavior is invoked. Validate, set up, return RUNNING.
  nav2_behaviors::ResultStatus onRun(
    const std::shared_ptr<const HoldAction::Goal> command) override;

  // Called every cycle while the behavior runs. Return RUNNING to keep holding,
  // SUCCEEDED to resume navigation.
  nav2_behaviors::ResultStatus onCycleUpdate() override;

protected:
  // Latched subscription to the operator hold flag.
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr hold_sub_;
  std::atomic_bool hold_active_{false};
  rclcpp::Time hold_started_;
};

}  // namespace crunchbot_nav
#endif  // CRUNCHBOT_NAV__OPERATOR_HOLD_HPP_
```

```cpp
// operator_hold.cpp  (the load-bearing parts)
#include "crunchbot_nav/operator_hold.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace crunchbot_nav
{

OperatorHold::OperatorHold()
: nav2_behaviors::TimedBehavior<HoldAction>() {}

nav2_behaviors::ResultStatus
OperatorHold::onRun(const std::shared_ptr<const HoldAction::Goal> /*command*/)
{
  // node_ is provided by the TimedBehavior base (a LifecycleNode weak_ptr, locked).
  auto node = this->node_.lock();
  if (!node) {
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::FAILED, 0};
  }

  // Subscribe to the latched /operator/hold flag (TRANSIENT_LOCAL: catch the last value).
  rclcpp::QoS hold_qos(rclcpp::KeepLast(1));
  hold_qos.reliable().transient_local();
  hold_sub_ = node->create_subscription<std_msgs::msg::Bool>(
    "/operator/hold", hold_qos,
    [this](std_msgs::msg::Bool::SharedPtr msg) { hold_active_.store(msg->data); });

  hold_started_ = this->clock_->now();
  RCLCPP_INFO(this->logger_, "OperatorHold engaged: pausing until /operator/hold clears.");
  return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING, 0};
}

nav2_behaviors::ResultStatus
OperatorHold::onCycleUpdate()
{
  // Publish a zero twist each cycle so the base is actively held, not coasting.
  geometry_msgs::msg::Twist stop;          // all-zero
  this->vel_pub_->publish(std::move(stop));  // vel_pub_ comes from the base class

  if (!hold_active_.load()) {
    RCLCPP_INFO(this->logger_, "OperatorHold cleared: resuming navigation.");
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::SUCCEEDED, 0};
  }
  return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING, 0};
}

}  // namespace crunchbot_nav

// The line that makes it a plugin pluginlib can load:
PLUGINLIB_EXPORT_CLASS(crunchbot_nav::OperatorHold, nav2_core::Behavior)
```

### 3.3 Exporting and wiring the plugin

Three files make a `pluginlib` plugin discoverable:

**1. `behavior_plugin.xml`** — the manifest:

```xml
<library path="crunchbot_nav_behaviors">
  <class type="crunchbot_nav::OperatorHold" base_class_type="nav2_core::Behavior">
    <description>Pauses navigation while /operator/hold is latched true.</description>
  </class>
</library>
```

**2. `CMakeLists.txt`** — build the shared library and export the plugin description:

```cmake
add_library(crunchbot_nav_behaviors SHARED src/operator_hold.cpp)
ament_target_dependencies(crunchbot_nav_behaviors
  rclcpp nav2_core nav2_behaviors pluginlib std_msgs geometry_msgs nav2_msgs)
pluginlib_export_plugin_description_file(nav2_core behavior_plugin.xml)
install(TARGETS crunchbot_nav_behaviors LIBRARY DESTINATION lib)
```

**3. `nav2_params.yaml`** — tell the `behavior_server` to load it:

```yaml
behavior_server:
  ros__parameters:
    behavior_plugins: ["spin", "backup", "wait", "operator_hold"]
    operator_hold:
      plugin: "crunchbot_nav::OperatorHold"
    spin:
      plugin: "nav2_behaviors::Spin"
    backup:
      plugin: "nav2_behaviors::BackUp"
    wait:
      plugin: "nav2_behaviors::Wait"
```

Rebuild, restart the stack, and `ros2 action list` shows a new `/operator_hold` action your BT can call. That is the entire plugin lifecycle: implement an interface, export it, list it in YAML. No Nav2 fork, no patched binary.

> **Why C++ and not Python for the plugin?** `behavior_server` loads its plugins in-process via `pluginlib`, which is a C++ class loader. Nav2 planner/controller/behavior plugins are C++. (There *is* a Python BT-node path and `nav2_simple_commander` for clients in Python — which is what Exercise 2 uses — but in-server plugins are C++. That's why this week finally puts you in `rclcpp`.)

---

## 4. Putting it together: the diagnostic decision tree

When the robot "comes up but won't navigate," walk this tree — it covers lifecycle, costmaps, TF, and the BT:

```
Robot won't navigate.
│
├─ Is every server `active [3]`?  (ros2 lifecycle get <each>)
│   ├─ No  → a configure() threw. Read THAT server's log for the exception. (L1 §2)
│   └─ Yes ↓
│
├─ Is the TF chain map→odom→base_link complete?  (ros2 run tf2_tools view_frames)
│   ├─ No  → AMCL not publishing map→odom (set initial pose), or odom missing. (L1 §4)
│   └─ Yes ↓
│
├─ Does the global costmap contain the map?  (echo /global_costmap/costmap, or rviz2)
│   ├─ No  → static_layer QoS: map_subscribe_transient_local. Empty costmap. (Part 1 §1.1)
│   └─ Yes ↓
│
├─ Does ComputePathToPose return a path?  (send a goal, echo /plan)
│   ├─ No  → goal in a lethal/inflated cell, or unreachable. Check inflation_radius. (Part 1)
│   └─ Yes ↓
│
└─ Path computed but robot won't move → controller. Check /cmd_vel, the goal/progress
   checkers, and whether the BT is stuck in a recovery (Groot 2, or echo the BT log). (Part 2)
```

Tape this next to the costmap parameter block. Between this tree and Lecture 1's server inventory, you can diagnose the overwhelming majority of Nav2 bring-up failures in under five minutes — which is exactly the Challenge this week.

---

## 5. Recap

You should now be able to:

- Configure a costmap's layer list, frame, and rolling-window behavior, and explain why `map_subscribe_transient_local` is the Week-5 QoS lesson made load-bearing.
- Swap a costmap layer (`obstacle_layer` → `voxel_layer`) in YAML and predict the effect on the planned path.
- Read the default navigation BT — `PipelineSequence`, `RecoveryNode`, `RateController`, `RoundRobin`, `ReactiveFallback` — and predict the robot's behavior when `ComputePathToPose` or `FollowPath` fails.
- Explain that a *crashed* server hangs the BT leaf in `RUNNING` (no `FAILURE` to recover from), which is why the crash fail-safe lives outside the tree.
- Name the `nav2_core` plugin interfaces and write a `nav2_core::Behavior` plugin: implement `onRun`/`onCycleUpdate`, export with `PLUGINLIB_EXPORT_CLASS`, and wire it into `behavior_server` via `behavior_plugin.xml` + YAML.
- Walk the lifecycle → TF → costmap → planner → controller decision tree to diagnose any "comes up but won't navigate" failure.

Next: the exercises put all of this on your week-7 map. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *Configuring costmaps* — Nav2 docs: <https://docs.nav2.org/configuration/packages/configuring-costmaps.html>
- *Behavior trees overview* — Nav2 docs: <https://docs.nav2.org/behavior_trees/index.html>
- *Nav2-specific BT nodes* — Nav2 docs: <https://docs.nav2.org/behavior_trees/overview/nav2_specific_nodes.html>
- *Writing a new behavior plugin* — Nav2 docs: <https://docs.nav2.org/plugin_tutorials/docs/writing_new_behavior_plugin.html>
- *Writing a new costmap2d plugin* — Nav2 docs: <https://docs.nav2.org/plugin_tutorials/docs/writing_new_costmap2d_plugin.html>
- *`nav2_core` interfaces*: <https://github.com/ros-navigation/navigation2/tree/main/nav2_core/include/nav2_core>
- *`pluginlib` tutorial*: <https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Pluginlib.html>

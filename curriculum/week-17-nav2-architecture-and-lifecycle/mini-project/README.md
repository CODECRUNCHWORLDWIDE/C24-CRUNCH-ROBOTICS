# Mini-Project — `crunchbot_nav`: A Bring-Up Package with a Custom Behavior Plugin

> Build a reusable Nav2 bring-up package for the crunchbot that brings the whole stack up cleanly on your week-7 map, **and** ships a custom `nav2_core::Behavior` plugin — `OperatorHold` — that pauses navigation when an external `/operator/hold` topic latches `true` and cleanly resumes when it clears. This is your first real Nav2 plugin against the real interface, wired into the real `behavior_server`.

This is the artifact that turns "I ran the Nav2 tutorial" into "I can deploy and extend Nav2 on a new robot." After this week, Nav2 bring-up is a package you own — one launch file, one params file, one lifecycle manager — and the plugin architecture is something you've *used*, not just read about.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This package becomes part of your **Week 24 Phase 3 integration** (Nav2 + MoveIt2 + a small BT in one launch graph). The `OperatorHold` plugin is the seed of the capstone's safety story — an operator-commanded pause is one of the simplest, most important fail-safes a shared-space robot has. Build it well now; you'll extend it into the `/safety/estop` path in Week 24.

---

## What you will build

A `colcon` package `crunchbot_nav` (C++ `ament_cmake`, because Nav2 plugins are C++) with three deliverables:

1. **The bring-up** — `launch/crunchbot_nav.launch.py` + `config/nav2_params.yaml` that brings up the full stack (localization + navigation lifecycle managers, both costmaps, planner, controller, behaviors, `bt_navigator`) on your week-7 map, with `use_sim_time` correct for Gz Sim.
2. **The `OperatorHold` behavior plugin** — a `nav2_core::Behavior` (via `nav2_behaviors::TimedBehavior`) that subscribes to a latched `/operator/hold` (`std_msgs/Bool`), holds the base stopped while it's `true`, and returns `SUCCEEDED` (resuming navigation) when it clears. Exported with `PLUGINLIB_EXPORT_CLASS`, declared in `behavior_plugin.xml`, and listed in the `behavior_server` plugin list.
3. **A demo + a custom BT** — a navigation BT (`behavior_trees/navigate_with_hold.xml`) that inserts a check on `/operator/hold` so the hold engages mid-navigation, plus a short script that publishes `true`/`false` on `/operator/hold` so you can demonstrate the pause/resume on a live goal.

By the end you have a public repo of ~400–600 lines (C++ plugin + launch + params + BT + a test) that any future crunchbot package can launch to get a working, extensible Nav2.

---

## Why a custom behavior plugin and not a separate node

You *could* write a standalone node that subscribes to `/operator/hold` and slams `/cmd_vel` to zero. Don't — not as the primary mechanism. A behavior *plugin* gives you:

- **It runs inside the BT.** The hold is a first-class navigation behavior the tree can invoke, so navigation *knows* it's paused and resumes cleanly — instead of two nodes fighting over `/cmd_vel`.
- **Lifecycle correctness.** The plugin activates and deactivates with the `behavior_server`; it can't accidentally hold the robot while the stack is down.
- **The real interface.** You learn `nav2_core::Behavior` — the same shape as planner, controller, and costmap-layer plugins — so the next plugin (a real one, in Week 24) is muscle memory.

A standalone "panic node" that zeroes `/cmd_vel` is a fine *additional* hardware-adjacent safety layer (and you'll build one for the E-stop in Week 24). But the *operator hold* belongs in the BT, as a plugin. That's the senior-shop convention.

---

## Package layout

```
crunchbot_nav/
├── package.xml
├── CMakeLists.txt
├── behavior_plugin.xml              # the pluginlib manifest for OperatorHold
├── include/crunchbot_nav/
│   └── operator_hold.hpp
├── src/
│   └── operator_hold.cpp            # the nav2_core::Behavior plugin
├── config/
│   └── nav2_params.yaml             # the full stack config, OperatorHold in the list
├── launch/
│   └── crunchbot_nav.launch.py      # localization + navigation bring-up
├── behavior_trees/
│   └── navigate_with_hold.xml       # nav BT that checks /operator/hold
├── scripts/
│   └── toggle_hold.py               # publish true/false on /operator/hold for the demo
└── test/
    └── test_operator_hold.cpp       # unit test for the hold-active state logic
```

---

## Deliverable 1 — the bring-up

`launch/crunchbot_nav.launch.py` must:

- Start `map_server` + `amcl` under a `lifecycle_manager_localization`.
- Start `controller_server`, `smoother_server`, `planner_server`, `behavior_server`, `bt_navigator`, `waypoint_follower`, `velocity_smoother` under a `lifecycle_manager_navigation`, with `autostart: true`.
- Pass `use_sim_time: true` everywhere (Gz Sim).
- Load `config/nav2_params.yaml` and your week-7 map path (a launch argument with a sensible default).
- Point `bt_navigator` at `behavior_trees/navigate_with_hold.xml`.

Crib structure from `nav2_bringup`'s `bringup_launch.py`, but make it *yours* — your map default, your params, your BT. The acceptance bar is the Week-17 promise: every server reaches `active [3]`.

> **Watch the lifecycle order.** `bt_navigator` activates **last** in the navigation manager's `node_names` (Lecture 1 §2.3). If you put it first, it tries to orchestrate servers that aren't live yet.

---

## Deliverable 2 — the `OperatorHold` plugin

This is the heart of the project. Implement `nav2_core::Behavior` via `nav2_behaviors::TimedBehavior<nav2_msgs::action::Wait>` (reusing the `Wait` action type — pausing *is* waiting). It must:

- In `onRun()`: create a **latched** subscription (`RELIABLE` + `TRANSIENT_LOCAL` + `KeepLast(1)`) to `/operator/hold` (`std_msgs/Bool`) so it picks up the *current* hold state immediately, even if the flag was set before the behavior started. Return `RUNNING`.
- In `onCycleUpdate()`: publish a zero `Twist` each cycle (so the base is *actively* held, not coasting), and return `RUNNING` while `hold == true`, `SUCCEEDED` when it clears.
- Export with `PLUGINLIB_EXPORT_CLASS(crunchbot_nav::OperatorHold, nav2_core::Behavior)`.

The Lecture 2 §3.2 listing is your spine — fill in the parameter declaration, the namespace, and the full include set. Then declare it:

```xml
<!-- behavior_plugin.xml -->
<library path="crunchbot_nav_behaviors">
  <class type="crunchbot_nav::OperatorHold" base_class_type="nav2_core::Behavior">
    <description>Pauses navigation while /operator/hold is latched true; resumes when it clears.</description>
  </class>
</library>
```

And wire it into the `behavior_server`:

```yaml
behavior_server:
  ros__parameters:
    use_sim_time: true
    behavior_plugins: ["spin", "backup", "wait", "drive_on_heading", "operator_hold"]
    operator_hold:
      plugin: "crunchbot_nav::OperatorHold"
    spin: { plugin: "nav2_behaviors::Spin" }
    backup: { plugin: "nav2_behaviors::BackUp" }
    wait: { plugin: "nav2_behaviors::Wait" }
    drive_on_heading: { plugin: "nav2_behaviors::DriveOnHeading" }
```

After `colcon build` and a restart, `ros2 action list` must show `/operator_hold`.

---

## Deliverable 3 — the demo and the custom BT

`behavior_trees/navigate_with_hold.xml` is the default navigation tree with one addition: a reactive check that invokes the `OperatorHold` behavior whenever `/operator/hold` is `true`, so the robot pauses mid-navigation and resumes when cleared. The simplest correct structure wraps the navigation pipeline in a `ReactiveSequence` whose first child is a condition on the hold flag.

`scripts/toggle_hold.py` publishes a latched `std_msgs/Bool` on `/operator/hold`:

```bash
python3 scripts/toggle_hold.py --hold true     # latch the hold ON
python3 scripts/toggle_hold.py --hold false    # release it
```

The demo: send a goal across the room, and partway there run `toggle_hold.py --hold true`. The robot stops. Run `--hold false`. The robot resumes to the goal. That pause/resume, on a live goal, is the deliverable.

---

## Rules

- **You may** read the Nav2 docs, the `nav2_behaviors` source, the behavior-plugin tutorial, and the reference `nav2_bringup`.
- **You must not** implement the hold by spawning a node that fights `bt_navigator` for `/cmd_vel`. The hold is a `behavior_server` plugin invoked by the BT. (A separate panic node is allowed as an *additional* layer, clearly labeled, but it is not the primary mechanism.)
- **You must not** depend on anything outside the ROS2 Jazzy + Nav2 install. No third-party BT libraries.
- C++17, `rclcpp`, `ament_cmake`, `pluginlib`. Jazzy.
- Every Nav2 server must reach `active [3]` on bring-up, or the project does not pass.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-17-crunchbot-nav-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_nav` succeeds with no errors.
- [ ] `ros2 launch crunchbot_nav crunchbot_nav.launch.py` brings the stack up; `ros2 lifecycle get` reads `active [3]` for every server.
- [ ] `ros2 action list` shows `/operator_hold` (the plugin loaded).
- [ ] On a live goal, publishing `true` on `/operator/hold` stops the base; publishing `false` resumes navigation to the goal — demonstrated in the README with a GIF or a `/cmd_vel` before/after.
- [ ] The hold subscription is **latched** (`TRANSIENT_LOCAL`): set the hold `true` *before* sending the goal and confirm the robot never moves until you clear it — proving the late-join durability works.
- [ ] `colcon test --packages-select crunchbot_nav` passes, including `test_operator_hold` covering the hold-active → `RUNNING` and hold-clear → `SUCCEEDED` state logic.
- [ ] A `README.md` in the repo with the bring-up command, the plugin's place in the architecture, and a paragraph on why the hold is a plugin, not a separate node.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Bring-up correctness** | 25 | Every server reaches `active [3]`; lifecycle order correct; `use_sim_time` right; map loads; a goal navigates. |
| **Plugin correctness** | 25 | `OperatorHold` implements `nav2_core::Behavior` correctly; `onRun`/`onCycleUpdate` semantics right; zero-twist hold (no coasting); `SUCCEEDED` on clear. |
| **Plugin wiring** | 15 | `PLUGINLIB_EXPORT_CLASS` + `behavior_plugin.xml` + `pluginlib_export_plugin_description_file` + YAML list all correct; `/operator_hold` appears in `ros2 action list`. |
| **Latched-hold discipline** | 10 | The `/operator/hold` subscription is `TRANSIENT_LOCAL`; hold-before-goal works (the Week-5 durability lesson applied). |
| **Demo & BT** | 15 | The custom BT engages the hold mid-navigation; the pause/resume demo works on a live goal. |
| **Tests & hygiene** | 10 | `test_operator_hold` covers both state transitions; clean CMake; no `build/`/`install/` checked in; clear README. |

**90+** is portfolio-grade and ready to fold into Week 24's integration. **70–89** works but has a rough edge (the hold coasts, or the bring-up needs a manual lifecycle nudge). **Below 70** means the plugin isn't actually loading as a plugin — check `ros2 action list` and the `pluginlib` export first.

---

## Common pitfalls (read before you start)

A short field guide to where this mini-project usually goes wrong, so you don't lose an evening to a known trap:

- **The plugin builds but `ros2 action list` doesn't show `/operator_hold`.** The `pluginlib` export didn't take. Check three things in order: `PLUGINLIB_EXPORT_CLASS` is in the `.cpp`, `behavior_plugin.xml` declares the class with the exact namespaced type, and `pluginlib_export_plugin_description_file(nav2_core behavior_plugin.xml)` is in `CMakeLists.txt`. All three must agree on the class name.
- **The bring-up hangs with a server stuck in `inactive`.** A bad parameter or a plugin that failed to load. Run `ros2 lifecycle get` on every server (Week-17 promise) and read the stuck server's log for the `configure` exception — don't re-launch hoping it fixes itself.
- **The hold engages but the robot coasts instead of stopping.** Your `onCycleUpdate` isn't publishing a zero `Twist`, or it's publishing to the wrong topic. The hold must *actively* command zero velocity each cycle, not just stop sending commands (the last command coasts — the same lesson as the planner-crash fail-safe).
- **Hold-before-goal doesn't work.** The `/operator/hold` subscription isn't `TRANSIENT_LOCAL`, so a hold latched before the behavior started is missed. This is the Week-5 durability lesson; the subscription must be latched to catch the last value.

## Stretch goals

- **Operator dashboard hook.** Publish a `/operator/hold_status` (`std_msgs/Bool`) from the plugin so an operator UI can confirm the robot *acknowledged* the hold, not just that the command was sent. (Previews the capstone telemetry in Week 43.)
- **Hold timeout → retreat.** Add a parameter `max_hold_seconds`; if the hold exceeds it, the behavior returns `FAILURE` so the BT can route into a "retreat to a safe waiting spot" subtree. This is the syllabus's Week-19 "if pause exceeds 60 s, retreat" pattern, prototyped early.
- **Vendor sweep.** Bring the stack up under both `rmw_fastrtps_cpp` and `rmw_cyclonedds_cpp` and confirm the plugin and lifecycle behave identically — proving your bring-up is vendor-portable (Week 5).
- **CI job.** A GitHub Actions workflow that builds the package and runs `colcon test` in a headless Jazzy + Nav2 container. Green check on every push.

---

## Worked verification protocol

Don't declare the mini-project done until you've run this exact protocol — it's the shape of the Week-24 integration review:

1. **Launch** `crunchbot_nav.launch.py`; run `ros2 lifecycle get` on every server and confirm `active [3]` across the board.
2. **Localize** with a 2D Pose Estimate; confirm `tf2_echo map odom` prints a live transform.
3. **Send a goal** from rviz2; confirm the robot plans (`/plan`) and drives it.
4. **Confirm the plugin loaded:** `ros2 action list | grep operator_hold` shows the action.
5. **Hold-during-goal:** mid-goal, `toggle_hold.py --hold true`; confirm the base stops (`/cmd_vel` → 0). Then `--hold false`; confirm navigation resumes to the goal.
6. **Hold-before-goal (latched test):** set `--hold true`, *then* send a goal; confirm the robot never moves until you clear the hold — proving the `TRANSIENT_LOCAL` subscription caught the pre-set value.
7. **Capture** the `/cmd_vel` before/after (or a GIF) for the README.

If all seven pass, you have a portfolio-grade bring-up + plugin. If step 4 fails, the `pluginlib` export is wrong; if step 5 coasts, `onCycleUpdate` isn't publishing zero; if step 6 fails, the subscription isn't latched.

## How this connects to the rest of C24

- **Week 18 (path planning)** swaps the planner you brought up here for a hand-rolled A* and SMAC Hybrid-A* — your bring-up is the harness those planners plug into.
- **Week 19 (behavior trees)** makes the BT the star; your `navigate_with_hold.xml` is the warm-up, and `OperatorHold` is a behavior the Week-19 patrol tree can call.
- **Week 24 (Phase 3 integration)** folds `crunchbot_nav` into the combined Nav2 + MoveIt2 launch graph, and the hazard log grades whether your operator-hold and fail-safe are real. This mini-project is that safety seed, planted seven weeks early. Push it, keep the repo, launch it in Week 24.

When you've finished, push the repo and take the [quiz](../quiz.md).

# Challenge 1 — The Stuck Stack: Four Faults in a Bring-Up That Won't Navigate

**Time estimate:** ~90 minutes.

## Problem statement

You are on call. A teammate's Nav2 bring-up "comes up" — rviz2 shows the robot and the map — but it won't navigate. Goals do nothing, or the robot spins forever, or it plans straight through a wall. There are **four** independent planted faults, one in each of the four subsystems you must master this week: **lifecycle**, **costmap**, **TF**, and the **behavior tree**.

You will run a fault-injected params file against a reference bring-up, then **detect, diagnose, and prescribe the fix** for each fault, using only the introspection tools from this week. This mirrors the real skill: you rarely debug a Nav2 stack you just wrote — you debug one someone else launched, from the lifecycle states out.

## The faulty params

Save this as `stuck_nav2_params.yaml` and launch the reference bring-up against it and your week-7 map. The four faults are below; **do not study them before you've diagnosed each from the outside.**

```yaml
# stuck_nav2_params.yaml — four planted faults. Diagnose, then fix.
amcl:
  ros__parameters:
    use_sim_time: true
    base_frame_id: "base_link"
    global_frame_id: "map"
    odom_frame_id: "odom"
    scan_topic: /scan

bt_navigator:
  ros__parameters:
    use_sim_time: true
    global_frame: map
    robot_base_frame: base_link
    # FAULT #4: this BT path does not exist on disk. bt_navigator configure() fails,
    # so bt_navigator never reaches active — and the whole nav lifecycle hangs on it.
    default_nav_to_pose_bt_xml: "/opt/ros/jazzy/share/nav2_bt_navigator/behavior_trees/THIS_FILE_DOES_NOT_EXIST.xml"

controller_server:
  ros__parameters:
    use_sim_time: true
    controller_frequency: 20.0
    # FAULT #1 (paired): a typo'd plugin type. controller_server configure() throws
    # "failed to create controller", stays in unconfigured/inactive.
    controller_plugins: ["FollowPath"]
    FollowPath:
      plugin: "dwb_core::DWBLocalPlannerTYPO"   # <-- not a real class

planner_server:
  ros__parameters:
    use_sim_time: true
    planner_plugins: ["GridBased"]
    GridBased:
      plugin: "nav2_navfn_planner/NavfnPlanner"

global_costmap:
  global_costmap:
    ros__parameters:
      use_sim_time: true
      global_frame: map
      robot_base_frame: base_link
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]
      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
        # FAULT #2: the static layer subscribes VOLATILE, but map_server publishes
        # the map once, TRANSIENT_LOCAL. The layer joins late and gets NOTHING ->
        # empty global costmap -> planner thinks the world is open.
        map_subscribe_transient_local: false
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: scan
        scan:
          topic: /scan
          data_type: "LaserScan"
          # FAULT #3 lives in TF, not here: see sensor_frame note below.
          marking: true
          clearing: true
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        inflation_radius: 0.55

local_costmap:
  local_costmap:
    ros__parameters:
      use_sim_time: true
      global_frame: odom
      robot_base_frame: base_link
      rolling_window: true
      width: 5
      height: 5
      plugins: ["obstacle_layer", "inflation_layer"]
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: scan
        scan:
          topic: /scan
          data_type: "LaserScan"
          marking: true
          clearing: true
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        inflation_radius: 0.55
```

**FAULT #3 (TF)** is injected outside this file: launch your robot with the LiDAR publishing `/scan` stamped with `frame_id: laser_link`, but **do not publish** the `base_link → laser_link` static transform (comment it out of your robot's launch). The costmap can't transform the scan into the costmap frame, so the obstacle layer silently marks nothing — the robot is blind to obstacles even though `/scan` is full of data.

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch nav2_bringup bringup_launch.py \
  map:=$HOME/maps/my_map.yaml use_sim_time:=true \
  params_file:=$HOME/stuck_nav2_params.yaml
```

## Your task

For **each of the four faults**, produce a diagnosis with these four parts:

1. **Symptom** — what's observably wrong (which `ros2 lifecycle get` state, what `view_frames` shows, what the costmap echo shows, what the BT does).
2. **Root cause** — which subsystem and which exact line/condition is wrong, stated mechanically (e.g., "`controller_server` configure() fails because `dwb_core::DWBLocalPlannerTYPO` is not a registered plugin, so the server never leaves `unconfigured`, so the nav lifecycle manager's activate pass aborts").
3. **Subsystem** — which of the four (lifecycle / costmap / TF / BT) it belongs to.
4. **Prescription** — the exact corrected line, and how you'd *confirm* the fix with a command.

You must reach each diagnosis using **at least two** independent signals — e.g., the stuck lifecycle state *and* the server's `ERROR` log line, or an empty costmap echo *and* the `view_frames` PDF. One signal is a guess; two is a diagnosis.

## Acceptance criteria

- [ ] A file `challenge-01-diagnosis.md` with a section per fault, each containing all four parts above.
- [ ] You correctly identify each fault's subsystem and root cause:
  - **#1** — `controller_server` (and consequently `bt_navigator`) stuck below `active` due to a bad plugin type → **lifecycle**.
  - **#2** — empty global costmap because the static layer's `map_subscribe_transient_local: false` misses the latched one-shot map → **costmap** (and a Week-5 QoS lesson).
  - **#3** — obstacle layer marks nothing because `base_link → laser_link` is missing, so the scan can't be transformed → **TF**.
  - **#4** — `bt_navigator` never activates because `default_nav_to_pose_bt_xml` points at a nonexistent file → **BT** (surfacing as a lifecycle stall).
- [ ] For at least faults #1 and #4 you quote the actual `ros2 lifecycle get` state and the `ERROR` log line.
- [ ] For fault #2 you show the empty/near-empty global costmap (Exercise 3's monitor, or `ros2 topic echo /global_costmap/costmap --once`).
- [ ] For fault #3 you show the `view_frames` PDF missing `laser_link`, or a costmap warning about the transform.
- [ ] A `fixed_nav2_params.yaml` (+ the restored static TF) where all servers reach `active [3]`, the global costmap contains the map, and a goal navigates.
- [ ] Committed to your Week 17 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

Faults #1 and #4 both present as the **same symptom from rviz2**: "I send a goal and nothing happens." But they are *different servers* failing for *different reasons*, and a lifecycle manager that brings nodes up in order will stall on the first one it can't activate — which may **mask** the second. So if you fix `controller_server` (#1) and the stack *still* won't navigate, do not assume your fix was wrong; re-run `ros2 lifecycle get` across all servers and you'll now see `bt_navigator` stuck (#4) that the earlier failure was hiding. **Faults can stack. Fix one, re-diagnose the whole stack, repeat.** Prescribing "it's the controller plugin" and stopping is the wrong, incomplete diagnosis.

Also note: fault #2 (empty costmap) and fault #3 (blind obstacle layer) are *both* costmap-adjacent but have completely different root causes — one is QoS, one is TF. A junior lumps them as "costmap broken." A senior names the QoS miss and the missing transform separately, because the fixes are in different files.

## Stretch

- Add a fifth fault: set `inflation_radius: 1.5` so a doorway becomes impassable, and diagnose it purely from the *planner* refusing to produce a `/plan` through the door while producing one to an open-room goal. This is a fault with no error log at all — only the behavior reveals it.
- Re-run the whole challenge with `default_nav_to_pose_bt_xml` pointing at a *valid* but *wrong* tree (one with no recovery subtree) and explain how the robot's failure behavior changes — it gives up instead of recovering. The BT is logic; swapping it changes behavior with zero code change.
- Write a 15-line `nav2_health.sh` that runs `ros2 lifecycle get` on every Nav2 server, greps for anything not `active [3]`, checks `tf2_echo map base_link` succeeds, and confirms the global costmap is non-empty — a one-command pre-flight you can reuse for the rest of Phase 3.

## Why this matters

In Phase 3, every week stacks more onto Nav2 — planners (Week 18), controllers (Weeks 20–22), behavior trees (Week 19), and eventually MoveIt2 in the same launch graph (Week 24). The bring-ups only get bigger and the faults only get more entangled. The engineer who can take a stuck stack, run four commands, and name all four faults in order is the one who unblocks the integration. Every robotics on-call rotation eventually hands you a bring-up you didn't write that "comes up but won't navigate." This challenge *is* that page, rehearsed.

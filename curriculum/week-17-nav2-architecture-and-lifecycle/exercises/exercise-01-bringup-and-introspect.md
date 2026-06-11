# Exercise 1 — Bring Up Nav2 and Introspect It

**Goal:** Bring up the full Nav2 stack on your week-7 map, localize with AMCL, send a goal from rviz2, and then *prove you understand what came up* by reading the lifecycle states and both costmaps. You will train the single most important Nav2 diagnostic habit: `ros2 lifecycle get` before anything else.

**Estimated time:** 45 minutes. Guided.

---

## Setup

You need the **week-3 robot** spawning in Gz Sim and your **week-7 map** (`my_map.yaml` + `my_map.pgm`). Verify the prerequisites in three terminals (source your overlay in each):

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch crunchbot_bringup robot.launch.py      # your week-3 sim + week-7 world
```

```bash
ros2 topic echo /scan --once          # LiDAR is publishing
ros2 run tf2_tools view_frames        # odom -> base_link -> laser_link exists (map comes from AMCL)
```

If the LiDAR isn't publishing or the TF tree is broken, fix that before touching Nav2 — Nav2 assumes a healthy robot underneath it.

---

## Step 1 — Bring up Nav2

Use the reference `nav2_bringup` to start, with your map. (In the mini-project you write your own bring-up; here, crib the reference one.)

```bash
ros2 launch nav2_bringup bringup_launch.py \
  map:=$HOME/maps/my_map.yaml \
  use_sim_time:=true \
  params_file:=$HOME/crunchbot_ws/src/crunchbot_nav/config/nav2_params.yaml
```

If you don't have a params file yet, omit `params_file:=` and Nav2 uses its defaults — fine for this exercise. `use_sim_time:=true` is mandatory in Gz Sim; forget it and every timestamp is wrong and AMCL never converges.

---

## Step 2 — Read the lifecycle BEFORE you do anything else

This is the habit. Before you send a goal, before you touch rviz2, confirm the stack is actually up:

```bash
for n in map_server amcl controller_server planner_server behavior_server bt_navigator smoother_server velocity_smoother waypoint_follower; do
  printf "%-22s " "$n"; ros2 lifecycle get /$n
done
```

Every line should read `active [3]`. The expected output:

```
map_server             active [3]
amcl                   active [3]
controller_server      active [3]
planner_server         active [3]
behavior_server        active [3]
bt_navigator           active [3]
smoother_server        active [3]
velocity_smoother      active [3]
waypoint_follower      active [3]
```

> **If any server reads `inactive [2]` or `unconfigured [1]`:** that server's `configure()` or the lifecycle manager's activate pass failed. Find the cause in *that server's* log — scroll your launch output for `[server_name]` lines with `ERROR`. The usual culprits: a bad parameter, a missing plugin library, or a map path that doesn't exist. **Do not send a goal to a half-active stack** — you'll chase a ghost.

---

## Step 3 — Localize with AMCL

Open rviz2 (the bringup launches one, or `rviz2 -d $(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/rviz/nav2_default_view.rviz`). The robot's particle cloud is scattered — AMCL doesn't know where the robot is yet.

1. Click **"2D Pose Estimate"** in the rviz2 toolbar.
2. Click-and-drag on the map at the robot's true location, pointing the arrow in its facing direction.
3. Watch the particle cloud collapse toward the true pose as AMCL matches `/scan` against the map.

Confirm `map → odom` now exists:

```bash
ros2 run tf2_ros tf2_echo map odom
# Should print a transform, updating. If it says "could not find transform", AMCL hasn't converged.
```

---

## Step 4 — Send a goal and watch the servers take turns

Click **"Nav2 Goal"** in rviz2 and click a reachable point in another room. The robot should plan a path (you'll see the green `/plan` line) and drive it.

While it drives, in another terminal:

```bash
# The global plan the planner produced:
ros2 topic echo /plan --once | head -20

# The velocity the controller is commanding:
ros2 topic echo /cmd_vel
```

You are watching the architecture from Lecture 1: `bt_navigator` ticked `ComputePathToPose` (the `/plan` you echoed) and `FollowPath` (the `/cmd_vel` you echoed). Two servers, taking turns, orchestrated by a behavior tree.

---

## Step 5 — Introspect both costmaps in rviz2

Add two **Map** displays in rviz2:

1. Display 1: topic `/global_costmap/costmap`, color scheme **costmap**. You'll see your week-7 map with a colored inflation halo around the walls.
2. Display 2: topic `/local_costmap/costmap`, color scheme **costmap**. You'll see a small square window that *follows the robot* — the rolling local costmap in the `odom` frame.

Confirm the frame difference from the command line:

```bash
ros2 topic echo /global_costmap/costmap --field header.frame_id --once   # map
ros2 topic echo /local_costmap/costmap  --field header.frame_id --once   # odom
```

That `map` vs `odom` difference is Lecture 1 §3.1 made concrete: the global costmap is fixed to the map; the local costmap rolls with the robot in odom.

---

## Step 6 — Re-tune the inflation radius live and watch the planner react

```bash
# Make the robot keep more clearance from walls:
ros2 param set /global_costmap/global_costmap inflation_layer.inflation_radius 0.9
# Force the costmap to rebuild:
ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap "{}"
```

Send a goal through a doorway. With a 0.9 m radius on a doorway narrower than ~1.8 m, the planner may now refuse — the inflated cost makes the doorway look impassable. Set it back to `0.55` and the path returns. **This is the single most common "the robot won't go through the door" bug, reproduced on purpose.**

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `ros2 lifecycle get` reads `active [3]` for all nine listed servers.
- [ ] AMCL converges after a 2D Pose Estimate and `tf2_echo map odom` prints a live transform.
- [ ] A goal sent from rviz2 produces a `/plan` and the robot drives it (you saw `/cmd_vel` change).
- [ ] You can state the frame of each costmap (`global` = `map`, `local` = `odom`) and confirmed it from `header.frame_id`.
- [ ] You reproduced the "inflation too large blocks the doorway" effect and reverted it.

---

## Stretch

- Kill `planner_server` by hand (`ros2 lifecycle set /planner_server deactivate`) mid-goal and watch the BT leaf hang in `RUNNING` — no recovery fires, because deactivation isn't a `FAILURE`. This is the gap your Exercise 2 fail-safe fills.
- Swap the planner: set `planner_server.GridBased.plugin` to `nav2_smac_planner/SmacPlannerHybrid` in your params, restart, and watch the path respect a turning radius. (Preview of Week 18.)
- Open the navigation BT in Groot 2 and watch it tick live while the robot navigates — find the `RecoveryNode` and watch it stay green until you wall the robot in. (Preview of Week 19.)

---

When this feels comfortable, move to [Exercise 2 — The NavigateToPose client](exercise-02-navigate-to-pose-client.py).

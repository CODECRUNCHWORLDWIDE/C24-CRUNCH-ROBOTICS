# Exercise 1 — Mapping mode: drive the multi-room world and close a loop

**Goal:** Launch `slam_toolbox` in asynchronous mapping mode against a multi-room Gz Sim world, drive your Week 3 robot through it in a loop, *watch the loop close in RViz* (the map snaps into alignment), and save the result two ways — the PGM/YAML occupancy grid for Nav2/AMCL and the serialized pose graph for `slam_toolbox` localization. This is the first time your robot builds a globally-consistent map of a space larger than one room.

**Estimated time:** 75 minutes.

---

## Setup

You need, all running and talking:

- Your **Week 3 diff-drive robot** spawned in Gz Sim Harmonic, publishing `sensor_msgs/LaserScan` on `/scan` and `sensor_msgs/JointState` on `/joint_states`.
- Your **Week 6 odometry node** publishing `nav_msgs/Odometry` on `/odom` and the `odom → base_link` transform.
- **`slam_toolbox`** installed: `sudo apt install ros-jazzy-slam-toolbox`.
- **`nav2_map_server`** installed: `sudo apt install ros-jazzy-nav2-map-server`.

Confirm the inputs before you touch SLAM:

```bash
ros2 topic hz /scan          # steady ~10-30 Hz
ros2 topic echo /scan --once # ranges[] populated, frame_id is your lidar frame
ros2 run tf2_ros tf2_echo odom base_link   # transform updates as you drive
```

If `/scan` is empty or `tf2_echo` errors, fix that first. `slam_toolbox` with no scans or a broken `odom → base_link` does nothing useful.

---

## Step 1 — Create the `crunch_slam` package

```bash
cd ~/crunch_ws/src
ros2 pkg create --build-type ament_cmake crunch_slam
mkdir -p crunch_slam/config crunch_slam/launch crunch_slam/worlds crunch_slam/maps
```

Add the install rules to `crunch_slam/CMakeLists.txt` (before `ament_package()`):

```cmake
install(DIRECTORY config launch worlds maps
        DESTINATION share/${PROJECT_NAME})
```

---

## Step 2 — The multi-room world (with a real loop)

Save this as `crunch_slam/worlds/crunch_rooms.sdf`. It is a simple three-room world with a corridor that returns to the start — a genuine loop. (If you have your own multi-room world with a loop, use it instead.)

```xml
<?xml version="1.0" ?>
<sdf version="1.9">
  <world name="crunch_rooms">
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-scene-broadcaster-system"
            name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-user-commands-system"
            name="gz::sim::systems::UserCommands"/>

    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <model name="ground">
      <static>true</static>
      <link name="link">
        <collision name="c"><geometry><plane><normal>0 0 1</normal>
          <size>50 50</size></plane></geometry></collision>
        <visual name="v"><geometry><plane><normal>0 0 1</normal>
          <size>50 50</size></plane></geometry>
          <material><ambient>0.7 0.7 0.7 1</ambient></material></visual>
      </link>
    </model>

    <!-- Outer walls of a 16 x 10 m rectangle, with interior partitions that
         create three rooms joined by a corridor. The robot drives a loop:
         start room -> corridor -> far room -> corridor -> back to start. -->
    <model name="walls">
      <static>true</static>
      <link name="link">
        <!-- helper: each wall is a thin box 0.2 m thick, 2 m tall -->
        <!-- south wall -->
        <collision name="s_c"><pose>0 -5 1 0 0 0</pose><geometry><box>
          <size>16 0.2 2</size></box></geometry></collision>
        <visual name="s_v"><pose>0 -5 1 0 0 0</pose><geometry><box>
          <size>16 0.2 2</size></box></geometry></visual>
        <!-- north wall -->
        <collision name="n_c"><pose>0 5 1 0 0 0</pose><geometry><box>
          <size>16 0.2 2</size></box></geometry></collision>
        <visual name="n_v"><pose>0 5 1 0 0 0</pose><geometry><box>
          <size>16 0.2 2</size></box></geometry></visual>
        <!-- west wall -->
        <collision name="w_c"><pose>-8 0 1 0 0 0</pose><geometry><box>
          <size>0.2 10 2</size></box></geometry></collision>
        <visual name="w_v"><pose>-8 0 1 0 0 0</pose><geometry><box>
          <size>0.2 10 2</size></box></geometry></visual>
        <!-- east wall -->
        <collision name="e_c"><pose>8 0 1 0 0 0</pose><geometry><box>
          <size>0.2 10 2</size></box></geometry></collision>
        <visual name="e_v"><pose>8 0 1 0 0 0</pose><geometry><box>
          <size>0.2 10 2</size></box></geometry></visual>
        <!-- interior partition 1 (with a 2 m doorway gap at the top) -->
        <collision name="p1_c"><pose>-2.5 -1.5 1 0 0 0</pose><geometry><box>
          <size>0.2 7 2</size></box></geometry></collision>
        <visual name="p1_v"><pose>-2.5 -1.5 1 0 0 0</pose><geometry><box>
          <size>0.2 7 2</size></box></geometry></visual>
        <!-- interior partition 2 (with a 2 m doorway gap at the bottom) -->
        <collision name="p2_c"><pose>3 1.5 1 0 0 0</pose><geometry><box>
          <size>0.2 7 2</size></box></geometry></collision>
        <visual name="p2_v"><pose>3 1.5 1 0 0 0</pose><geometry><box>
          <size>0.2 7 2</size></box></geometry></visual>
      </link>
    </model>
  </world>
</sdf>
```

Spawn your Week 3 robot into this world (use your Week 3 spawn launch, pointing `gz_args` at `crunch_rooms.sdf`). Drive it once with `ros2 topic pub /cmd_vel` to confirm it moves and `/scan` shows the walls.

---

## Step 3 — The mapping parameter file

Save this as `crunch_slam/config/mapper_params_online_async.yaml` (this is the annotated file from Lecture 2, §2.2):

```yaml
slam_toolbox:
  ros__parameters:
    solver_plugin: solver_plugins::CeresSolver
    ceres_linear_solver: SPARSE_NORMAL_CHOLESKY
    ceres_preconditioner: SCHUR_JACOBI
    ceres_trust_strategy: LEVENBERG_MARQUARDT
    ceres_dogleg_type: TRADITIONAL_DOGLEG
    ceres_loss_function: None

    odom_frame: odom
    map_frame: map
    base_frame: base_link
    scan_topic: /scan
    mode: mapping

    resolution: 0.05
    map_update_interval: 1.0
    transform_publish_period: 0.02
    transform_timeout: 0.2
    tf_buffer_duration: 30.0

    minimum_travel_distance: 0.3
    minimum_travel_heading: 0.3
    max_laser_range: 12.0
    minimum_time_interval: 0.5

    use_scan_matching: true
    use_scan_barycenter: true
    scan_buffer_size: 10
    scan_buffer_maximum_scan_distance: 10.0
    link_match_minimum_response_fine: 0.1
    link_scan_maximum_distance: 1.5
    correlation_search_space_dimension: 0.5
    correlation_search_space_resolution: 0.01
    correlation_search_space_smear_deviation: 0.1

    do_loop_closing: true
    loop_search_maximum_distance: 3.0
    loop_match_minimum_chain_size: 10
    loop_match_maximum_variance_coarse: 3.0
    loop_match_minimum_response_coarse: 0.35
    loop_match_minimum_response_fine: 0.45
    loop_search_space_dimension: 8.0
    loop_search_space_resolution: 0.05
    loop_search_space_smear_deviation: 0.03
```

---

## Step 4 — The mapping launch file

Save this as `crunch_slam/launch/online_async_mapping.launch.py`:

```python
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg = get_package_share_directory("crunch_slam")
    params = os.path.join(pkg, "config", "mapper_params_online_async.yaml")
    return LaunchDescription([
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            output="screen",
            parameters=[params, {"use_sim_time": True}],
        ),
    ])
```

Build and source:

```bash
cd ~/crunch_ws
colcon build --packages-select crunch_slam
source install/setup.bash
```

---

## Step 5 — Run mapping and open RViz

In four terminals (each sourced):

```bash
# T1: Gz Sim with the crunch_rooms world + your Week 3 robot spawned
ros2 launch <your_week3_pkg> spawn_robot.launch.py world:=crunch_rooms.sdf

# T2: your Week 6 odometry node
ros2 run <your_week6_pkg> odometry_node --ros-args -p use_sim_time:=true

# T3: slam_toolbox mapping
ros2 launch crunch_slam online_async_mapping.launch.py

# T4: RViz2
rviz2
```

In RViz: set **Fixed Frame** to `map`. Add a **Map** display on `/map`, a **LaserScan** display on `/scan`, and a **TF** display. Add the **SlamToolboxPlugin** panel (Panels → Add New Panel → SlamToolboxPlugin) so you can serialize from a button later.

---

## Step 6 — Drive a loop and watch it close

Drive the robot through all three rooms and *back to where it started*, so it re-observes the first room from a different approach. The simplest reliable loop with this world: start in the west room, go through the doorway in partition 1, cross to the east room through the doorway in partition 2, come back the way you came. Drive smoothly — fast spins blow past the scan-match window.

```bash
# teleop, or a scripted drive; keep speeds modest:
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

As you drive, the map grows in RViz, room by room. **The moment to watch for:** when you return to an already-mapped area, `slam_toolbox`'s front-end recognizes it, the back-end re-optimizes, and the **map visibly snaps** — doubled walls merge into one, the whole map shifts a few centimetres. That snap is a loop closure (Lecture 1, §1.6). The `slam_toolbox` terminal logs it:

```
[slam_toolbox]: Loop closure found between scans, adding constraint...
[slam_toolbox]: ... optimization complete, ... constraints
```

If the map *doubles* a wall and never merges it, you missed the loop — drive closer to the original path, slow down, or note it for the challenge (the challenge is exactly this failure, on purpose).

---

## Step 7 — Save the map two ways

With `slam_toolbox` still running and the map looking good:

```bash
# Format 1 -- PGM + YAML occupancy grid (for Nav2/AMCL in Phase 3):
ros2 run nav2_map_server map_saver_cli -f ~/crunch_ws/src/crunch_slam/maps/crunch_world

# Format 2 -- serialized pose graph (for slam_toolbox localization, exercise 2):
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '/home/$USER/crunch_ws/src/crunch_slam/maps/crunch_world'}"
```

You now have four files in `maps/`: `crunch_world.pgm`, `crunch_world.yaml`, `crunch_world.posegraph`, `crunch_world.data`. (The PGM/YAML is the Nav2 input; the `.posegraph`/`.data` is the `slam_toolbox` input — Lecture 2, §2.4.)

Open the PGM to eyeball it:

```bash
xdg-open ~/crunch_ws/src/crunch_slam/maps/crunch_world.pgm
```

---

## Expected output

A correct run produces:

- An RViz `/map` showing three rooms and the connecting corridor, walls roughly single-cell-thick (one black pixel line, not a fuzzy band), free space white inside the rooms, unknown grey outside the walls.
- At least **one** logged `Loop closure found` line in the `slam_toolbox` terminal, with a visible map snap in RViz when it fired.
- A `view_frames` PDF (`ros2 run tf2_tools view_frames`) showing `map → odom → base_link`, with `slam_toolbox` as the `map → odom` author and your odometry node as the `odom → base_link` author, each frame singly-parented.
- Four saved files in `maps/`.

A `.pgm` that looks like *two overlapping copies of the world* offset by tens of centimetres means **no loop closed** — the front-end never recognized the revisit and the drift was never corrected. That is the challenge's subject; for this exercise, re-drive until at least one loop closes.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `slam_toolbox` runs in async mapping mode with `use_sim_time:=true` and builds a map of the three-room world in RViz.
- [ ] At least one loop closure fired (logged, and you saw the map snap).
- [ ] `view_frames` shows `map → odom → base_link` with the correct authors and no double-parented frame.
- [ ] You saved the map in **both** formats (PGM/YAML and `.posegraph`/`.data`).
- [ ] The saved `.pgm` shows single-thick walls and three distinguishable rooms — not a doubled map.
- [ ] You can explain, in your own words, *which* link in the frame chain jumped when the loop closed and why that is correct (Lecture 2, §2.7).

---

## Stretch

- Re-run with `loop_match_minimum_response_fine: 0.6` (stricter). Does the loop still close? You are previewing the challenge's failure mode.
- Re-run in **sync** mode (`sync_slam_toolbox_node`) by adding a second launch file. Drive the same path. Note whether the map lags the robot differently.
- Record a bag of this drive now (`ros2 bag record /scan /tf /tf_static /odom /joint_states /clock`). Exercise 3 needs one.

---

## Hints

<details>
<summary>The map never appears in RViz</summary>

Almost always `use_sim_time`. Confirm *every* node has it: `ros2 param get /slam_toolbox use_sim_time` must return `true`. Also confirm `/clock` is being published (`ros2 topic hz /clock`) — Gz Sim publishes it, but the bridge must carry it.

</details>

<details>
<summary>`slam_toolbox` logs "Failed to compute odom pose" or transform timeouts</summary>

Your `odom → base_link` is not arriving, is on the wrong clock, or is stale. Confirm `tf2_echo odom base_link` works and your odometry node has `use_sim_time:=true`. `transform_timeout` too small also causes this on a busy machine — bump it to `0.5`.

</details>

<details>
<summary>The map builds but no loop ever closes</summary>

Three usual causes: (1) you never actually re-drove an old area — the loop has to physically revisit a mapped place; (2) `loop_search_maximum_distance` is smaller than your accumulated drift, so the old node is "too far" to be a candidate — raise it to `5.0`; (3) `loop_match_minimum_response_fine` is too strict for your scan density — lower it to `0.4`. This is the challenge in miniature.

</details>

---

When this exercise feels comfortable, move to [Exercise 2 — Save and restart in localization mode](./exercise-02-save-and-restart-in-localization.py).

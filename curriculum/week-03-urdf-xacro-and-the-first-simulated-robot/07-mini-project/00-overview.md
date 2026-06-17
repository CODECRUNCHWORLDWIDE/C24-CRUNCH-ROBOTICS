# Mini-Project — crunchbot: the Phase-1 Platform

> Build the canonical **crunchbot** — a differential-drive robot described entirely in xacro, with two driven wheels, two casters, a 2D LiDAR, and an IMU, plus a `ros_gz_sim` launch file that spawns it *cleanly* into an empty world and bridges it to ROS2. By the end you drive it with `ros2 topic pub /cmd_vel` and watch `/odom`, `/imu`, and `/scan` populate. This robot is not a throwaway: it is the platform you reuse for the rest of Phase 1 — and it comes back in Phase 2, Phase 3, and the capstone.

This is the most important artifact of Phase 1's first half. Weeks 4 through 8 all build on *this exact robot*:

- **Week 4** writes a `Spin90Degrees` action server that rotates crunchbot using closed-loop IMU yaw — the IMU you wire this week.
- **Week 5** sets crunchbot's sensor topics to `BEST_EFFORT/KEEP_LAST` and its map topic to `RELIABLE/TRANSIENT_LOCAL`, then breaks QoS on purpose — on the topics you bridge this week.
- **Week 6** turns *off* the DiffDrive plugin's odometry and makes you publish `/odom` yourself from wheel joint states — using the wheels you size this week.
- **Week 7** drives crunchbot through a multi-room world running `slam_toolbox` — using the LiDAR you mount this week.
- **Week 8** packages weeks 3–7 into one `bringup` package whose foundation is the launch file you write this week.

So: build it like you mean it. A sloppy crunchbot is a tax you pay every week until Week 8.

**Estimated time:** ~9.5 hours (split across Thursday, Friday, Saturday, and Sunday in the suggested schedule).

---

## What you will build

A ROS2 package named **`crunchbot_description`** in a colcon workspace `crunchbot_ws`, containing:

- A modular xacro robot description (top-level file plus included macro files).
- Gz Sim system/sensor plugins for **DiffDrive**, **IMU**, and **2D LiDAR**, wired through `<gazebo>` extension blocks.
- A `ros_gz_bridge` parameter-bridge YAML that maps every Gz topic to its ROS2 counterpart.
- A single Python launch file that starts Gz Sim with an empty world, publishes the robot description, spawns crunchbot, starts the bridge, and (optionally) opens rviz2 with a saved layout.

The robot's physical parameters (the canonical crunchbot spec — do not deviate without a reason you can defend):

| Part | Shape | Dimensions | Mass | Notes |
|------|-------|------------|------|-------|
| Chassis | box | `0.40 × 0.30 × 0.10 m` | `2.0 kg` | Root is `base_link`; chassis box centered, raised so wheels reach the ground |
| Drive wheel ×2 | cylinder | `r = 0.05 m`, `l = 0.04 m` | `0.30 kg` | `continuous` joints; axle along local z after a −90° roll |
| Caster ×2 | sphere | `r = 0.025 m` | `0.05 kg` | `fixed` joint; frictionless sphere collision stands in for a real swivel |
| LiDAR | cylinder (visual) | `r = 0.03 m`, `l = 0.04 m` | `0.10 kg` | `fixed` to chassis top; `gpu_lidar` sensor, 360°, ~10 Hz |
| IMU | small box (visual) | `0.02 × 0.02 × 0.01 m` | `0.02 kg` | `fixed` near the chassis center; `imu` sensor at ~100 Hz |

Derived constants that **must** agree between the URDF and the DiffDrive plugin:

```
wheel_separation = 0.36 m   (wheel joints at ±0.18 m in y)
wheel_radius     = 0.05 m   (matches the wheel cylinder radius)
```

---

## Rules

- **You may** read the ROS2 Jazzy docs, the Gz Sim (Harmonic) docs, the `ros_gz` README, the SDFormat spec, the lecture notes, and the exercise files. The mini-project is "assemble what the exercises taught into one clean package," not "discover it from nothing."
- **You may NOT** copy a TurtleBot or other published URDF wholesale and rename it. Author crunchbot yourself. Borrowing the *pattern* of a plugin block is fine; cloning a whole robot defeats the point.
- **You must** generate every `<inertial>` block from mass and dimensions via xacro math (the macro from Exercise 1). **No hand-typed inertia tensors anywhere.**
- **You must** keep the DiffDrive plugin's `wheel_separation` and `wheel_radius` numerically identical to the URDF geometry.
- **You must** run every ROS2 node with `use_sim_time: true` and bridge `/clock`.
- Toolchain: **ROS2 Jazzy on Ubuntu 24.04**, **Gz Sim (Harmonic)**, `ros_gz` from apt. Python launch files (not XML).

---

## Package layout

This is the layout the rest of Phase 1 expects. Match it.

```
crunchbot_ws/
└── src/
    └── crunchbot_description/
        ├── package.xml
        ├── CMakeLists.txt              # ament_cmake; installs urdf/, launch/, config/, rviz/, worlds/
        ├── crunchbot_description/
        │   ├── __init__.py
        │   └── inertia.py              # the tested helper from homework P1 (reused)
        ├── urdf/
        │   ├── crunchbot.urdf.xacro    # top-level: includes the rest, sets properties
        │   ├── chassis.xacro           # base_link + materials
        │   ├── wheels.xacro            # the wheel macro (visual/collision/inertial + joint)
        │   ├── casters.xacro           # the caster macro
        │   ├── sensors.xacro           # LiDAR + IMU links and <gazebo> sensor blocks
        │   ├── actuators.xacro         # the DiffDrive <gazebo> plugin block
        │   └── inertials.xacro         # box/cylinder/sphere inertia macros (xacro math)
        ├── launch/
        │   └── crunchbot.launch.py     # start sim, publish description, spawn, bridge, rviz2
        ├── config/
        │   └── crunchbot_bridge.yaml   # ros_gz_bridge parameter-bridge config
        ├── rviz/
        │   └── crunchbot.rviz          # saved layout: RobotModel, TF, LaserScan, Odometry
        ├── worlds/
        │   └── empty.sdf               # the empty world we spawn into (ground plane + sun + physics)
        └── test/
            └── test_inertia.py         # the pytest suite from homework P1
```

---

## Acceptance criteria

- [ ] A new public GitHub repo named `c24-week-03-crunchbot-<yourhandle>` containing `crunchbot_ws/src/crunchbot_description/`.
- [ ] `colcon build` from `crunchbot_ws/` succeeds with no errors. After `source install/setup.bash`, the package is discoverable.
- [ ] `xacro $(ros2 pkg prefix crunchbot_description)/share/crunchbot_description/urdf/crunchbot.urdf.xacro` expands with no errors, and the expanded URDF passes `check_urdf`.
- [ ] **Every `<inertial>` is generated by an xacro macro from mass + dimensions.** A reviewer can grep the source and find *zero* hand-typed `ixx="..."` numeric literals outside the inertia macros themselves.
- [ ] All four inertia sanity checks pass for every link (positive mass, positive diagonals, triangle inequality, order of magnitude). Prove it by running `test/test_inertia.py` green.
- [ ] `ros2 launch crunchbot_description crunchbot.launch.py` brings up Gz Sim, spawns crunchbot, and prints:
  ```
  [create]: Spawn entity [crunchbot] in world [empty]: success
  [robot_state_publisher]: got segment base_link
  ```
- [ ] **The robot sits still on the ground plane when no command is sent.** No drift, no sink, no vibration, no explosion. This is the headline requirement.
- [ ] `ros2 topic list` shows `/cmd_vel`, `/odom`, `/imu`, `/scan`, `/clock`, and `/tf`. `ros2 topic hz /scan` and `ros2 topic hz /imu` report sane, non-zero rates.
- [ ] Publishing a forward command moves the robot in Gz Sim **and** `/odom` x/y change to track it:
  ```bash
  ros2 topic pub /cmd_vel geometry_msgs/msg/TwistStamped \
    "{twist: {linear: {x: 0.2}, angular: {z: 0.0}}}" -r 10
  ```
- [ ] `ros2 run tf2_tools view_frames` produces a single connected tree rooted at `odom → base_link → (wheels, casters, lidar_link, imu_link)`, no orphans.
- [ ] rviz2 (launched by the launch file or separately with the saved layout) shows the robot model, the TF tree, the laser scan, and the odometry trail.
- [ ] Your `README.md` includes: a one-paragraph description, the exact build + launch + drive commands, a screenshot or terminal capture of the clean spawn, and a "Things I learned" section with at least 3 specific items.

---

## Suggested order of operations

Build incrementally. The fastest way to fail this project is to write all the xacro at once and spawn it cold; you will get a detonation and no idea which of fifty lines caused it. Spawn after **every** phase.

### Phase 1 — Workspace and a body that just sits there (~1.5h)

1. Create the workspace and package:
   ```bash
   mkdir -p ~/crunchbot_ws/src && cd ~/crunchbot_ws/src
   ros2 pkg create --build-type ament_cmake crunchbot_description
   ```
2. Add the directory skeleton (`urdf/`, `launch/`, `config/`, `rviz/`, `worlds/`, `test/`) and wire `CMakeLists.txt` to install each with `install(DIRECTORY ... DESTINATION share/${PROJECT_NAME})`.
3. Write `inertials.xacro` first — the box/cylinder/sphere inertia macros that compute the tensor from mass and dimensions (this is Exercise 1's macro). Then `chassis.xacro` with just `base_link` (visual + collision + a *generated* inertial).
4. Write a minimal `empty.sdf` world (ground plane, sun, a physics plugin) and a minimal `crunchbot.launch.py` that starts Gz Sim, runs `robot_state_publisher`, and spawns the chassis-only robot.
5. **Spawn it.** A single box should fall a hair and sit flat on the ground. If it does anything else, fix it now — before adding wheels.
6. Commit: `crunchbot: chassis-only body spawns clean`.

### Phase 2 — Wheels and casters via macros (~2h)

1. Write `wheels.xacro`: a `<xacro:macro name="wheel" params="prefix reflect">` that emits the wheel link (visual cylinder, collision cylinder, generated inertial) and the `continuous` joint at `xyz="0 ${reflect*0.18} 0" rpy="-1.5708 0 0"` with `<axis xyz="0 0 1"/>`. Call it twice: `reflect=1` (left) and `reflect=-1` (right).
2. Write `casters.xacro`: a `<xacro:macro name="caster" params="prefix x">` that emits a sphere link (frictionless collision) and a `fixed` joint at the given x offset. Call it twice (front and rear, or both at the rear — your choice, document it).
3. Set the chassis height so the wheels (radius 0.05) and casters (radius 0.025) all touch the ground with the chassis level. This is a geometry puzzle; sketch it on paper.
4. **Spawn it.** The robot should sit level and still. Push it gently with the Gz GUI's force tool — the wheels should roll, the casters should slide. If it trembles or jumps, run the §1.7 differential.
5. Commit: `crunchbot: wheels + casters, sits level and still`.

### Phase 3 — The DiffDrive actuator (~1.5h)

1. Write `actuators.xacro` containing the `<gazebo>` DiffDrive plugin block from Lecture 2 §2.3. Set `<left_joint>`/`<right_joint>` to your exact wheel joint names, `<wheel_separation>0.36</wheel_separation>`, `<wheel_radius>0.05</wheel_radius>`, and the odom/tf outputs.
2. Add the `/cmd_vel` and `/odom` entries to `crunchbot_bridge.yaml` (`/cmd_vel`: `geometry_msgs/msg/TwistStamped` ↔ `gz.msgs.Twist`, `ROS_TO_GZ`; `/odom`: `nav_msgs/msg/Odometry` ↔ `gz.msgs.Odometry`, `GZ_TO_ROS`). Add `/clock` and `/tf`. Add the bridge node to the launch file.
3. **Spawn and drive.** Publish a forward `TwistStamped` and confirm the robot moves and `/odom` tracks it. If ROS publishes but Gz is silent, you have the wrong message type or bridge direction (the §2.3 "why won't it move" bug).
4. Commit: `crunchbot: DiffDrive + cmd_vel/odom bridge, drives`.

### Phase 4 — The sensors (~2h)

1. Write `sensors.xacro`: the LiDAR link (`fixed` to chassis top) with a `<gazebo reference="lidar_link">` `gpu_lidar` `<sensor>` block (360°, ~10 Hz, sane min/max range), plus the IMU link (`fixed` near center) with a `<gazebo reference="imu_link">` `imu` `<sensor>` block (~100 Hz). Add the `gz-sim-sensors-system` and `gz-sim-imu-system` plugins to the world (or model) as Lecture 2 describes.
2. Add `/scan` (`sensor_msgs/msg/LaserScan` ↔ `gz.msgs.LaserScan`, `GZ_TO_ROS`) and `/imu` (`sensor_msgs/msg/Imu` ↔ `gz.msgs.IMU`, `GZ_TO_ROS`) to the bridge YAML.
3. **Spawn and verify.** `ros2 topic hz /scan` and `/imu` report sane rates; `/imu` linear-z reads `~+9.81` at rest; `/scan` returns a full ring of ranges. (Reuse your homework P3 audit node.)
4. Commit: `crunchbot: LiDAR + IMU sensors, topics populate`.

### Phase 5 — rviz2 layout and the one-command bring-up (~1.5h)

1. Open rviz2, add **RobotModel** (source: `/robot_description`), **TF**, **LaserScan** (topic `/scan`), and **Odometry** (topic `/odom`), set the fixed frame to `odom`, and save the layout to `rviz/crunchbot.rviz`.
2. Add an optional `rviz` launch argument to the launch file that opens rviz2 with this layout (`rviz2 -d <layout>`).
3. Confirm the **whole thing comes up from one command**: `ros2 launch crunchbot_description crunchbot.launch.py rviz:=true`. Sim, spawn, bridge, rviz2 — all of it, clean.
4. Commit: `crunchbot: rviz layout + single-command bring-up`.

### Phase 6 — Smoke, docs, push (~1h)

1. Drive a small loop and confirm the laser scan, TF, and odometry trail all update live in rviz2.
2. Run the full acceptance-criteria checklist top to bottom. Capture the clean-spawn terminal output and an rviz2 screenshot.
3. Write the package `README.md`: description, build/launch/drive commands, the captures, and "Things I learned."
4. Push to GitHub. Confirm `colcon build` + launch work on a **fresh clone** in a clean workspace — that is the real test.
5. Commit: `crunchbot: docs, smoke test, ship`.

---

## Example expected output

A clean bring-up prints (interleaved, ordering varies):

```
[gz_sim]            [Msg] Loading world [empty]
[robot_state_publisher] got segment base_link
[robot_state_publisher] got segment left_wheel
[create]            Requesting list of world names.
[create]            Spawn entity [crunchbot] in world [empty]: success
[parameter_bridge]  Creating GZ->ROS Bridge: [/scan (gz.msgs.LaserScan) -> /scan (sensor_msgs/msg/LaserScan)]
[parameter_bridge]  Creating ROS->GZ Bridge: [/cmd_vel (geometry_msgs/msg/TwistStamped) -> /cmd_vel (gz.msgs.Twist)]
```

A topic audit at rest:

```
$ ros2 topic hz /scan
average rate: 10.001
$ ros2 topic hz /imu
average rate: 100.012
$ ros2 topic echo /imu --once | grep -A3 linear_acceleration
linear_acceleration:
  x: 0.001
  y: -0.002
  z: 9.806
```

A drive command and its odometry response:

```
$ ros2 topic pub /cmd_vel geometry_msgs/msg/TwistStamped \
    "{twist: {linear: {x: 0.2}, angular: {z: 0.0}}}" -r 10 &
$ ros2 topic echo /odom --once | grep -A3 position
position:
  x: 0.42
  y: 0.0
  z: 0.0
```

---

## Rubric

| Criterion | Weight | What "great" looks like |
|----------|-------:|-------------------------|
| Spawns clean and sits still | 25% | `Spawn ... success`; zero drift/sink/vibration/explosion at rest on a fresh clone |
| Inertia discipline | 20% | Every inertial generated from mass+dimensions; zero hand-typed tensors; `test_inertia.py` green |
| Drives via `/cmd_vel` | 15% | Forward + turning commands move the robot; `/odom` tracks; constants match the URDF |
| Sensors populate | 15% | `/scan` and `/imu` at sane rates; `+9.81` at rest; full LiDAR ring |
| One-command bring-up | 15% | A single `ros2 launch` starts sim + spawn + bridge + rviz2, repeatably |
| Package hygiene + README | 10% | Clean layout; builds on fresh clone; README lets a stranger run it in <5 min |

---

## Stretch (optional)

- Add a **depth camera** plugin (you need it in Phase 2). The pattern is identical to the LiDAR: a `<sensor type="rgbd_camera">` block and two bridged topics (`/camera/image`, `/camera/depth_image`). Confirm they show up; don't tune them yet.
- Render each link's inertia tensor as an **ellipsoid** in rviz2 (or with a small script) and visually confirm the ellipsoids match the link geometry — a fat disk for wheels, a slab for the chassis.
- Add a `crunchbot_state` xacro property block so the *entire* robot (every dimension, mass, offset) is parameterized at the top of `crunchbot.urdf.xacro`. Then prove you can make a "crunchbot-XL" (1.5× every dimension, mass scaled by volume) by changing only those properties — and that it *still spawns clean*, because the inertials regenerate.
- Swap `empty.sdf` for the `ros_gz` `shapes.sdf` world and drive crunchbot around the obstacles, watching the LaserScan light up in rviz2.
- Write a tiny `pytest` launch test (`launch_testing`) that asserts `/scan`, `/imu`, and `/odom` all publish within 10 seconds of launch — a real smoke test you can run in CI.

---

## What this prepares you for

- **Week 4** drives *this robot* with a `Spin90Degrees` action server closing the loop on the IMU you wired here.
- **Week 5** sets QoS on the exact topics in your `crunchbot_bridge.yaml` and shows you the silent failure of a QoS mismatch.
- **Week 6** turns off the DiffDrive odometry and makes you publish `/odom` yourself from `/joint_states`, using the wheel radius and separation you locked in here.
- **Week 7** runs `slam_toolbox` against your LiDAR through a multi-room world.
- **Week 8** wraps weeks 3–7 into one `bringup` package whose spine is this launch file. By then "new robot → this package layout" is reflex.

The crunchbot you ship this week is, with sensor and controller additions, the **same robot** that appears in the Phase-1 milestone review and again in later phases. Build it to a standard you will be glad to inherit.

---

## Resources

- ROS2 Jazzy — URDF tutorials: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/URDF-Main.html>
- ROS2 Jazzy — Simulators / Gazebo integration: <https://docs.ros.org/en/jazzy/Tutorials/Advanced/Simulators/Gazebo/Gazebo.html>
- `ros_gz` (the bridge + sim integration): <https://github.com/gazebosim/ros_gz>
- Gz Sim (Harmonic) docs: <https://gazebosim.org/docs/harmonic>
- SDFormat 1.11 spec (`<sensor>`, `<inertial>`, `<plugin>`): <http://sdformat.org/spec?ver=1.11>
- xacro documentation: <https://github.com/ros/xacro/wiki>

---

## Submission

When done:

1. Push your repo to GitHub with a public URL (`c24-week-03-crunchbot-<yourhandle>`).
2. Make sure `README.md` includes the build + launch + drive commands and the clean-spawn capture.
3. Confirm `colcon build` and `ros2 launch crunchbot_description crunchbot.launch.py` are green on a **freshly cloned** workspace — that means committing every xacro, the bridge YAML, the world, and the rviz layout, and excluding `build/`, `install/`, and `log/` with a `.gitignore`.
4. Post the repo URL in your cohort tracker. This robot is your Phase-1 platform; show it off — you will be living with it for five more weeks.

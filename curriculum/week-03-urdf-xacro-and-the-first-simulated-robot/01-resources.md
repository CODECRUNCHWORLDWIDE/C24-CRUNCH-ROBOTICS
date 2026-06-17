# Week 3 — Resources

Every resource on this page is **free**. The ROS2 and Gazebo docs are open. The SDF and URDF specifications are published openly. Open-source repos are public on GitHub. No paywalled material is linked.

A note on versions: this week targets **ROS2 Jazzy Jalisco** (the May-2024 LTS) on **Ubuntu 24.04** with **Gz Sim Harmonic** (the LTS Gazebo paired with Jazzy via `ros_gz`). If a doc page lets you pick a version, pick **Jazzy** and **Harmonic**. Many older tutorials target Humble + Gazebo Classic or Foxy + Gazebo 11; the URDF authoring transfers, but the simulator launch files and plugin names do not. When in doubt, prefer the dated 2024–2026 material below.

## Required reading (work it into your week)

- **URDF — the official ROS2 concept page**, the canonical model of links and joints:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/URDF-Main.html>
- **"Building a Visual Robot Model with URDF from Scratch"** — the ROS2 Jazzy tutorial that introduces links, joints, and the `robot_state_publisher` flow:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/Building-a-Visual-Robot-Model-with-URDF-from-Scratch.html>
- **"Using Xacro to Clean Up a URDF File"** — properties, macros, includes:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/Using-Xacro-to-Clean-Up-a-URDF-File.html>
- **Gazebo + ROS2 integration (`ros_gz`)** — the Gazebo "ROS 2 Integration" tutorials, current for Harmonic:
  <https://gazebosim.org/docs/harmonic/ros2_integration/>
- **`ros_gz_bridge` README** — the topic-type mapping table you will consult constantly:
  <https://github.com/gazebosim/ros_gz/blob/jazzy/ros_gz_bridge/README.md>

## The specifications (skim, don't memorize)

The first time a reviewer writes "your `<inertial>` violates the triangle inequality, see the SDF spec," you will want to know what they mean.

- **URDF XML specification** — the normative link/joint/inertial reference (still hosted on the ROS wiki, still authoritative):
  <https://wiki.ros.org/urdf/XML>
- **`<link>` element reference** (visual / collision / inertial in detail):
  <https://wiki.ros.org/urdf/XML/link>
- **`<joint>` element reference** (types, axis, limits, dynamics):
  <https://wiki.ros.org/urdf/XML/joint>
- **SDFormat specification (1.11, current with Harmonic)** — Gz Sim's native format; URDF is converted to SDF on spawn, so reading the target format pays off:
  <http://sdformat.org/spec?ver=1.11>
- **SDF `<inertial>`** specifically — note it supports automatic inertia computation from mesh density, which URDF does not:
  <http://sdformat.org/spec?ver=1.11&elem=link#link_inertial>

## Inertia tensors — the math you must get right

- **List of moments of inertia (Wikipedia)** — the closed-form table for box, solid cylinder, solid sphere, hollow shapes. Bookmark this; you will use it every time you add a link:
  <https://en.wikipedia.org/wiki/List_of_moments_of_inertia>
- **Moment of inertia (Wikipedia)** — the conceptual page: what the tensor *is*, the parallel-axis theorem, principal axes:
  <https://en.wikipedia.org/wiki/Moment_of_inertia>
- **`onshape-to-robot` inertia docs** — a practical engineer's explanation of how CAD-to-URDF tools compute the tensor, and the common mistakes:
  <https://onshape-to-robot.readthedocs.io/en/latest/>

## Gazebo / Gz Sim

- **Gz Sim Harmonic documentation home** — install, concepts, tutorials:
  <https://gazebosim.org/docs/harmonic/>
- **"Sensors" tutorial (Harmonic)** — how the `Sensors` system plugin and per-sensor `<sensor>` blocks work:
  <https://gazebosim.org/docs/harmonic/sensors/>
- **DiffDrive system plugin reference** — the parameters (`left_joint`, `right_joint`, `wheel_separation`, `wheel_radius`, `topic`, `odom_topic`):
  <https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1DiffDrive.html>
- **IMU system + sensor reference**:
  <https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1Imu.html>
- **GPU LiDAR sensor tutorial** — the `gpu_lidar` `<sensor>` block and its `<ray>` scan parameters:
  <https://gazebosim.org/docs/harmonic/sensors/#gpu-lidar>
- **`ros_gz` repository (jazzy branch)** — `ros_gz_sim`, `ros_gz_bridge`, `ros_gz_image`, with the demo launch files that are the best real examples you will find:
  <https://github.com/gazebosim/ros_gz/tree/jazzy>

## Tools you'll use this week

- **`xacro`** — the macro processor. `xacro model.urdf.xacro > model.urdf` expands it; `xacro --help` lists the options.
- **`check_urdf`** — from the `liburdfdom-tools` package: `sudo apt install liburdfdom-tools`. It parses a URDF and prints the link/joint tree, catching structural errors.
- **`gz sdf -p model.sdf`** — validates and pretty-prints SDF; useful after converting your URDF.
- **`ros2 run robot_state_publisher robot_state_publisher`** — publishes `/tf` and `/robot_description` from a URDF.
- **`rviz2`** — visualize the robot, the tf tree, the LiDAR scan, and (with the InertiaDisplay) the inertia ellipsoids.
- **`ros2 topic echo` / `ros2 topic hz` / `ros2 topic info -v`** — confirm sensor topics populate at the rate and QoS you expect.

## Free books and longer reads (chapter-level)

- **"A Gentle Introduction to ROS"** by Jason O'Kane — free PDF; the URDF/tf chapters are excellent foundations even though they predate ROS2 syntax:
  <https://www.cse.sc.edu/~jokane/agitr/>
- **"Programming Multiple Robots with ROS2"** (the community ROS2 book, free online) — the simulation and description chapters:
  <https://osrf.github.io/ros2multirobotbook/>
- **Articulated Robotics — URDF & Gazebo series** (Josh Newans) — the single best free video+text walkthrough of building a diff-drive robot from URDF to Gazebo for ROS2; he keeps it current:
  <https://articulatedrobotics.xyz/tutorials/mobile-robot/>

## Videos (free, no signup)

- **Articulated Robotics — "Making a Mobile Robot"** playlist — the diff-drive build, the inertia explanation, the Gazebo plugins, all current to ROS2:
  <https://www.youtube.com/playlist?list=PLunhqkrRNRhYAffV8JDiFOatQXuU-NnxT>
- **Open Robotics — Gazebo tutorials channel** — official Harmonic walkthroughs:
  <https://www.youtube.com/@OpenRoboticsOrg>
- **ROSCon talks archive** — search "URDF" or "Gazebo" on the Vimeo/YouTube archive for the deep conference talks:
  <https://roscon.ros.org/>

## Open-source robot descriptions to read this week

You learn more from one hour reading a well-written URDF than from three hours of tutorials. Each of these is a real, maintained, ROS2-Jazzy-compatible description. Pick one and read its xacro top to bottom:

- **TurtleBot 4** — the reference diff-drive base this course's capstone descends from:
  <https://github.com/turtlebot/turtlebot4>
- **`turtlebot3` (Burger / Waffle)** — smaller, simpler diff-drive descriptions; great first read:
  <https://github.com/ROBOTIS-GIT/turtlebot3>
- **`sam_bot` / `ros_gz` example robots** — minimal diff-drive robots wired for Gz Sim, the closest analog to what you build this week:
  <https://github.com/ros-navigation/navigation2/tree/main/nav2_bringup>
- **Articulated Robotics `diffdrive_arduino` / `articubot_one`** — a complete hobby diff-drive robot, sim and real, by the author of the video series above:
  <https://github.com/joshnewans/articubot_one>

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **URDF** | Unified Robot Description Format — XML describing links, joints, and their physical properties. |
| **xacro** | XML macros for URDF — properties, macros, math, includes. Expands to plain URDF. |
| **SDF / SDFormat** | Simulation Description Format — Gazebo's native XML. Your URDF is converted to SDF on spawn. |
| **link** | A rigid body in the robot. Carries visual, collision, and inertial blocks. |
| **joint** | A connection between two links. Has a type, an axis, and (sometimes) limits. |
| **inertial** | The mass, center of mass, and 3×3 inertia tensor of a link. The physics engine reads it literally. |
| **inertia tensor** | A 3×3 symmetric matrix describing how mass resists angular acceleration. Units kg·m². |
| **visual** | The geometry you *see* in rviz2/Gazebo. Can be a detailed mesh. |
| **collision** | The geometry the physics engine *touches*. Usually a coarse primitive for speed. |
| **continuous joint** | A revolute joint with no angle limit — what a wheel uses. |
| **Gz Sim** | The current Gazebo (Harmonic in 2026). Formerly "Ignition Gazebo." Not Gazebo Classic. |
| **system plugin** | A Gz Sim plugin attached to a model or world — DiffDrive, Sensors, Imu live here. |
| **`ros_gz_bridge`** | The process that translates Gz transport messages to/from ROS2 topics. |
| **`ros_gz_sim create`** | The command/launch action that spawns an entity into a running Gz world. |
| **`robot_state_publisher`** | The node that reads the URDF and publishes the `/tf` tree and `/robot_description`. |

---

*If a link 404s, please open an issue so we can replace it.*

# Week 3 — URDF, xacro, and the First Simulated Robot

Welcome to the week your robot stops being a tf2 tree you typed by hand and becomes a *thing* — a body with mass, wheels that drive, and sensors that publish. By Friday you spawn a differential-drive robot into Gz Sim and drive it around an empty world with nothing but `ros2 topic pub /cmd_vel`. By Sunday that robot — **crunchbot** — is a clean, reusable package you will carry through the rest of Phase 1 and well beyond.

This is also the week you meet the single most misunderstood file in robotics: the URDF. People treat it like a 3D model. It is not. **A URDF is a kinematic and dynamic *claim*** — a structured assertion about where the joints are, which way they rotate, how much each link weighs, and how that mass is distributed. The physics engine reads those claims literally and simulates them without mercy. Get the inertia tensor wrong by three orders of magnitude and your robot will detonate the instant it spawns: wheels fly off, the chassis launches into the skybox, and `rviz2` shows a twitching mess. We are going to make that failure mode *boring* — you will know exactly why it happens and exactly how to fix it before it happens to you.

We assume Week 1 (rotations, rclpy, rviz2) and Week 2 (SE(3), tf2 trees) are behind you. You should be able to read a quaternion without flinching and reason about a frame tree. This week we attach mass and geometry to that tree and hand it to a physics engine.

The toolchain is **ROS2 Jazzy on Ubuntu 24.04** with **Gz Sim (Harmonic)** and the `ros_gz` bridge. If you are on Path B (sim-only), everything this week runs on your laptop with no hardware. If you are on Path A, you still do everything in sim this week — the physical base does not arrive until Phase 2.

## Learning objectives

By the end of this week, you will be able to:

- **Author** a complete robot description in xacro: links, joints, materials, and `<xacro:macro>` definitions that eliminate copy-paste across symmetric parts.
- **Distinguish** the three blocks every link carries — `<visual>`, `<collision>`, and `<inertial>` — and explain why each exists and what reads it.
- **Compute** an inertia tensor for a box, a cylinder, and a sphere from closed-form equations, and **verify** it with a unit-aware sanity check before a physics engine ever sees it.
- **Diagnose** the "robot explodes on spawn" failure mode from its symptoms and trace it to one of four root causes (bad inertia, zero/negative mass, self-colliding collision geometry, or a degenerate joint).
- **Choose** the correct joint type (`fixed`, `continuous`, `revolute`, `prismatic`) for each connection and set its axis, limits, and dynamics correctly.
- **Wire** Gz Sim plugins for differential drive, an IMU, and a 2D LiDAR into the URDF via the `<gazebo>` extension block.
- **Bridge** Gz topics to ROS2 topics with `ros_gz_bridge` and confirm `/cmd_vel`, `/odom`, `/imu`, and `/scan` all populate.
- **Write** a `ros_gz_sim` launch file that starts the simulator, spawns the robot into an empty world, publishes the robot description, and starts the bridge — cleanly, every time.
- **Drive** the spawned robot with `ros2 topic pub /cmd_vel` and observe it move in both Gz Sim and rviz2.

## Prerequisites

This week assumes you have completed **C24 Weeks 1 and 2**, or have equivalent ROS2 fluency. Specifically:

- ROS2 Jazzy installed on Ubuntu 24.04 (native, WSL2, or a VM with GPU passthrough for the GUI). `ros2 --help` works; you can `colcon build` a workspace.
- You understand the tf2 tree as a representation of SE(3) at every joint (Week 2). A URDF *generates* that tree — this week closes the loop.
- You can write a small `rclpy` node and launch it (Week 1). We use Python launch files this week, not XML.
- Comfortable in a terminal: sourcing a workspace, setting `ROS_DOMAIN_ID`, reading `ros2 topic echo` output.

You do **not** need any prior URDF, Gazebo, or SDF experience. We start from the schema. If you have used **Gazebo Classic** (the version that reached end-of-life in January 2025), you will need to unlearn a few habits — Gz Sim is a different simulator with a different plugin system, and we will flag the differences as we go.

Install the Gz Sim and bridge packages before Monday:

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-ros-gz \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher-gui
gz sim --version   # expect "Gazebo Sim, version 8.x.x" (Harmonic)
```

## Topics covered

- The URDF as a *claim*, not a CAD file: what the kinematic graph asserts and who consumes it (`robot_state_publisher`, rviz2, the physics engine, MoveIt2 later).
- The URDF schema: `<robot>`, `<link>`, `<joint>`, `<material>`, and the parent/child convention.
- The three faces of a link: `<visual>` (what you see), `<collision>` (what the physics engine touches), `<inertial>` (mass + center of mass + 3×3 inertia tensor).
- Why visual and collision geometry differ — fidelity vs. simulation cost — and the "primitive collision for a detailed visual" pattern.
- Inertia tensors: the physical meaning, the closed-form equations for box/cylinder/sphere, units (kg·m²), and the sanity checks that catch errors.
- The four joint types you use in Phase 1: `fixed`, `continuous`, `revolute`, `prismatic`. Axis, limits, dynamics (damping, friction).
- xacro: properties, `<xacro:macro>`, `<xacro:include>`, math expressions in `${...}`, and how to generate two wheels from one macro.
- The "explode on spawn" failure mode: its four root causes, the smell test, and the fix workflow.
- Gz Sim (Harmonic) vs. Gazebo Classic vs. Isaac Sim — what changed and why ROS2 Jazzy pairs with Gz.
- The SDF world file and the empty world we spawn into.
- Gz Sim system plugins: `gz::sim::systems::DiffDrive`, `Sensors`, `Imu`, the LiDAR via the `<sensor>` SDF block.
- The `ros_gz_bridge`: mapping Gz transport topics to ROS2 topics, and the parameter-bridge YAML.
- The `ros_gz_sim create` spawn mechanism and the `robot_state_publisher` → `/robot_description` flow.
- Driving with `/cmd_vel` (`geometry_msgs/msg/TwistStamped` on Jazzy), and reading `/odom`, `/imu`, `/scan`.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract — the independent build is where the learning lives.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | URDF schema, links/joints, inertia tensors             |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | xacro macros; build the diff-drive body (Exercise 1)   |    1h    |    2.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Wednesday | Gz Sim plugins: diff-drive, IMU, LiDAR (Lecture 2)     |    2h    |    1.5h   |     1h     |    0.5h   |   0.5h   |     0h       |    0.5h    |     6h      |
| Thursday  | Sensors + bridge (Exercise 2); spawn & drive (Ex 3)    |    1h    |    2h     |     0h     |    0.5h   |   1h     |     1.5h     |    0h      |     6h      |
| Friday    | The explode-on-spawn challenge; mini-project kickoff   |    0h    |    0.5h   |     1.5h   |    0.5h   |   0.5h   |     2.5h     |    0.5h    |     6h      |
| Saturday  | crunchbot mini-project deep work                       |    0h    |    0h     |     0h     |    0h     |   0.5h   |     3.5h     |    0h      |     4h      |
| Sunday    | Quiz, review, push the crunchbot package               |    0h    |    0h     |     0h     |    1h     |   0h     |     1.5h     |    0h      |     2.5h    |
| **Total** |                                                        | **6h**   | **8h**    | **4h**     | **3.5h**  | **4.5h** | **9.5h**     | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Curated, current (2026) URDF / xacro / Gz Sim / inertia references |
| [lecture-notes/01-a-urdf-is-a-kinematic-claim.md](./02-lecture-notes/01-a-urdf-is-a-kinematic-claim.md) | URDF schema, links/joints, visual vs. collision, inertia tensors, the explode-on-spawn smell test |
| [lecture-notes/02-gz-sim-plugins-diff-drive-imu-lidar.md](./02-lecture-notes/02-gz-sim-plugins-diff-drive-imu-lidar.md) | How sensors and actuators get into simulation: DiffDrive, IMU, LiDAR plugins, the bridge, the launch file |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-build-the-diff-drive-body.md](./03-exercises/exercise-01-build-the-diff-drive-body.md) | Author the chassis, two driven wheels, two casters in xacro |
| [exercises/exercise-02-add-lidar-and-imu.py](./03-exercises/exercise-02-add-lidar-and-imu.py) | Generate sensor xacro and a bridge config; verify topics populate |
| [exercises/exercise-03-spawn-and-drive.py](./03-exercises/exercise-03-spawn-and-drive.py) | A launch file that spawns the robot and a node that drives it via `/cmd_vel` |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-fix-the-exploding-robot.md](./04-challenges/challenge-01-fix-the-exploding-robot.md) | Diagnose and repair a provided URDF that explodes on spawn |
| [quiz.md](./05-quiz.md) | 13 questions with an answer key |
| [homework.md](./06-homework.md) | Five practice problems with a rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for **crunchbot**, the Phase-1 platform |

## The "spawns clean" promise

C24 uses a recurring marker in every lab that ends in a working robot:

```
[ros_gz_sim]: Requesting list of world names.
[create]: Spawn entity [crunchbot] in world [empty]: success
[robot_state_publisher]: got segment base_link
```

If your spawn does not print `success` and your robot does not sit still on the ground plane when you let go of `/cmd_vel`, **you are not done**. A robot that drifts, sinks through the floor, vibrates, or explodes is a robot with a description bug — not a simulator bug. The point of this week is to make "spawns clean and sits still" ordinary.

## Stretch goals

If you finish the regular work early and want to push further:

- Read the SDF specification for `<inertial>` and compare it to URDF's: <http://sdformat.org/spec?ver=1.11&elem=link#link_inertial>.
- Add a `check_urdf` step to your build: `check_urdf <(xacro crunchbot.urdf.xacro)` and read what it reports about the tree.
- Swap the empty world for the `ros_gz` `shapes.sdf` world and drive around the obstacles.
- Add a depth camera plugin (you will need it in Phase 2) and confirm the `/camera/image` and `/camera/depth_image` topics show up. We do not require it this week, but the plugin pattern is identical to the LiDAR.
- Render your inertia tensors as ellipsoids in rviz2 and visually confirm they match the link geometry.

## Up next

Continue to **Week 4 — ROS2 in depth: actions, services, lifecycle, executors** once you have pushed the crunchbot package to your GitHub. Week 4's `Spin90Degrees` action server drives *this exact robot* using closed-loop IMU yaw, so the robot you build this week is the robot you control next week.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

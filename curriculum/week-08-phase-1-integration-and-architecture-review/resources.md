# Week 8 — Resources

Every resource on this page is **free**. The ROS2 documentation, the `ros2/launch` and `ros2/launch_ros` source repositories, `slam_toolbox`, `robot_state_publisher`, and `rviz2` are all open source (Apache-2.0 or BSD) and public on GitHub. The design articles (REPs) are part of the public ROS Enhancement Proposal process. No paywalled material is linked. Everything targets **ROS2 Jazzy Jalisco on Ubuntu 24.04** unless explicitly noted otherwise; where a doc page is version-agnostic, prefer the `jazzy` URL.

## Required reading (work it into your week)

- **ROS2 Jazzy — Launch documentation entry point**:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html>
- **ROS2 Jazzy — "Creating a launch file"** (the canonical Python-launch tutorial):
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html>
- **ROS2 Jazzy — "Using substitutions"** (`LaunchConfiguration`, `PathJoinSubstitution`, `FindPackageShare`):
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-Substitutions.html>
- **ROS2 Jazzy — "Using event handlers"** (the launch event system; you need this for the cold-start timer challenge):
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-Event-Handlers.html>
- **ROS2 Jazzy — "Launch file different formats"** (why Python launch beats XML/YAML once you need logic):
  <https://docs.ros.org/en/jazzy/How-To-Guides/Launch-file-different-formats.html>
- **ROS2 Jazzy — "Understanding parameters"**:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Parameters/Understanding-ROS2-Parameters.html>
- **ROS2 Jazzy — "Using parameters in a class (Python)"** and the YAML override mechanism:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-Python.html>
- **ROS2 Jazzy — "Composing multiple nodes in a single process"** (`ComposableNodeContainer`, intra-process comms):
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html>
- **ROS2 Jazzy — "Migrating from a node to a launch file"** (namespaces, remapping, `GroupAction`, `PushRosNamespace`):
  <https://docs.ros.org/en/jazzy/How-To-Guides/Launch-files-migration-guide.html>
- **`slam_toolbox` — README and configuration reference** (the source of truth for every parameter you will tune):
  <https://github.com/SteveMacenski/slam_toolbox>

## Authoritative deep dives

- **ROS Enhancement Proposal REP 105 — "Coordinate Frames for Mobile Platforms"** — the canonical definition of the `map → odom → base_link` frame convention. The TF defense in the milestone is graded against this document. Read it end-to-end; it is short and load-bearing:
  <https://www.ros.org/reps/rep-0105.html>
- **ROS Enhancement Proposal REP 103 — "Standard Units of Measure and Coordinate Conventions"** — right-hand rule, ENU vs NED, SI units. The reason your IMU and odometry agree on which way is "forward":
  <https://www.ros.org/reps/rep-0103.html>
- **ROS2 Design — "About Quality of Service settings"** — the definitive QoS reference: reliability, durability, history, the compatibility matrix that explains *silent* mismatches:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html>
- **ROS2 Design — "About executors"** and the composition rationale (why single-process composition exists, what intra-process comms buys you):
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html>
- **Steve Macenski et al. — "SLAM Toolbox: SLAM for the dynamic world"** (Journal of Open Source Software, 2021). The paper behind the package you are running; explains the pose-graph back-end and the lifelong-mapping mode:
  <https://joss.theoj.org/papers/10.21105/joss.02783>
- **Nav2 documentation — "Setting up the URDF" and "Setting up odometry"** — even though Nav2 itself is Phase 3, its bring-up guides are the best worked examples of the exact TF + odom + QoS contract you are defending this week:
  <https://docs.nav2.org/setup_guides/index.html>
- **`tf2` design — "tf2 and time" and the `view_frames` tooling**:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html>

## Official docs you will reference repeatedly

- **`launch_ros.actions.Node` API** (the `parameters`, `remappings`, `namespace`, `arguments` keyword arguments):
  <https://github.com/ros2/launch_ros/blob/jazzy/launch_ros/launch_ros/actions/node.py>
- **`launch.actions.IncludeLaunchDescription` API**:
  <https://github.com/ros2/launch/blob/jazzy/launch/launch/actions/include_launch_description.py>
- **`launch_ros.actions.PushRosNamespace`**:
  <https://github.com/ros2/launch_ros/blob/jazzy/launch_ros/launch_ros/actions/push_ros_namespace.py>
- **`launch_ros.actions.ComposableNodeContainer` and `LoadComposableNodes`**:
  <https://github.com/ros2/launch_ros/blob/jazzy/launch_ros/launch_ros/actions/composable_node_container.py>
- **`robot_state_publisher` source and README** (publishes `tf` from the URDF + `/joint_states`):
  <https://github.com/ros/robot_state_publisher/tree/ros2>
- **`ros_gz` (the Gz Sim ↔ ROS2 bridge) — `ros_gz_bridge` and `ros_gz_sim`**:
  <https://github.com/gazebosim/ros_gz/tree/jazzy>
- **`rviz2` — saving and loading a `.rviz` config**:
  <https://github.com/ros2/rviz>

## Source repos worth skimming

- **`ros2/launch`** — the core launch system. Read `launch/launch/actions/` for the action surface and `launch/launch/substitutions/` for every substitution you can compose:
  <https://github.com/ros2/launch>
- **`ros2/launch_ros`** — the ROS-aware launch actions (`Node`, `PushRosNamespace`, `SetParameter`, composable containers):
  <https://github.com/ros2/launch_ros>
- **TurtleBot4 — `turtlebot4_bringup`** — a production-quality `*_bringup` package. This is the single best worked example of the pattern this week teaches; read its `launch/`, `config/`, and `package.xml` end-to-end:
  <https://github.com/turtlebot/turtlebot4>
- **TurtleBot3 — `turtlebot3_bringup` and `turtlebot3_navigation2`** — the older but extremely widely-copied reference; useful for seeing how a community standardized on one launch pattern:
  <https://github.com/ROBOTIS-GIT/turtlebot3>
- **`nav2_bringup`** — the gold standard for launch composition at scale: nested includes, a lifecycle manager, namespaced multi-robot support, all from one `tb3_simulation_launch.py`. Reading this file is itself an exercise in this week's lecture 1:
  <https://github.com/ros-navigation/navigation2/tree/main/nav2_bringup>

## Talks and walkthroughs worth watching (all free, no account)

- **ROSCon — "Launch files in ROS2"** (search ROSCon's YouTube channel; the launch-system maintainers present the design rationale and the substitution model). The single best video on *why* the launch system is shaped the way it is.
- **ROSCon — "slam_toolbox" by Steve Macenski** (the package author presents the architecture and the mapping/localization/lifelong modes). Watch before the milestone; the map defense is easier when you can describe the back-end.
- **Articulated Robotics — the "Making a Mobile Robot" series** (YouTube). Josh Newans builds a diff-drive robot bring-up package from scratch on ROS2; the launch-composition and `ros_gz` bridge episodes map almost one-to-one onto this week's mini-project.
- **ROSCon — "On the Use of QoS in ROS2"** — the talk that finally makes the reliability/durability compatibility matrix intuitive. Pair it with the ROS2 QoS design doc above.

## How to use this resource list

The lectures cite specific URLs from this page at decision points. The links you should read end-to-end *this week* are:

1. **ROS2 "Creating a launch file"** and **"Using substitutions"** (Required reading). You cannot do the mini-project without them.
2. **REP 105** (Deep dives). The TF defense is graded directly against it.
3. **The ROS2 QoS design doc** (Deep dives). The QoS defense is graded against it.
4. **The `turtlebot4_bringup` `launch/` directory** (Source repos). Read it the way lecture 1 teaches you to read a `launch/` directory, before you write your own.

The rest are reference material — bookmark them and return when a specific question arises. Even senior ROS2 engineers re-read REP 105 and the QoS doc when they touch the relevant code.

---

*Bookmarks decay. If a `docs.ros.org` link rots, swap the distro segment (`jazzy`) for the current LTS, or search the page title — these are all canonical pages that survive distro bumps.*

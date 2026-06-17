# Week 35 — Resources

Every resource here is **free** and, where versioned, pinned to **ROS2 Jazzy** (the LTS we run on Ubuntu 24.04). The ROS2 docs are open. The map-merge and distributed-SLAM packages are open source. The papers are on arXiv. No paywalled books are linked.

When a link is versioned, the Jazzy URL is given. If you are on a newer distro later, swap `jazzy` for your distro name — the namespacing and map-merge concepts are stable across distros; only the API-reference URLs move.

## Required reading (work it into your week)

- **Multiple robots / namespacing** — the canonical ROS2 page on running more than one robot, namespaces, and remapping. Read it Monday:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-Substitutions.html>
- **Composing launch files & namespaces (`PushRosNamespace`)** — how a `GroupAction` pushes a namespace over a whole sub-stack:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-ROS2-Launch-For-Large-Projects.html>
- **About discovery** — `ROS_DOMAIN_ID`, `ROS_AUTOMATIC_DISCOVERY_RANGE`, multicast vs. unicast (re-read from week 5 through the multi-robot lens):
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Discovery.html>
- **`nav_msgs/OccupancyGrid`** — the message you will merge; read every field, especially `info.origin` and the row-major `int8[]` data semantics (0 free / 100 occupied / -1 unknown):
  <https://docs.ros.org/en/jazzy/p/nav_msgs/interfaces/msg/OccupancyGrid.html>
- **`slam_toolbox`** — the per-robot SLAM you will run two of; read how it sets `map` and `odom` frames so you understand why two robots have two unrelated `map` frames:
  <https://github.com/SteveMacenski/slam_toolbox>

## The map-merge & multi-robot packages (read the source)

- **`m-explore-ros2` — `multirobot_map_merge`** — the de-facto open-source ROS2 grid-merger; read how it does feature-based alignment when the relative transform is unknown:
  <https://github.com/robo-friends/m-explore-ros2>
- **Cartographer (multi-trajectory)** — Google's SLAM with multiple trajectories in one map; the "how do you merge submaps" reference implementation:
  <https://github.com/cartographer-project/cartographer_ros>
- **`tf2_ros` static & dynamic broadcasters** — you will publish `world -> robotA/map` here; read the static-transform-broadcaster latching story (it's `TRANSIENT_LOCAL`, exactly like week 5 taught):
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html>

## Distributed-SLAM papers (skim Thursday; don't memorize)

You are not implementing these this week. But when a teammate says "we need inter-robot loop closures," you want to know what they mean.

- **Kimera-Multi (Tian, Chang, Carlone et al.)** — distributed, robust, dense metric-semantic SLAM for a robot team, no central server:
  <https://arxiv.org/abs/2106.14386>
- **DOOR-SLAM (Lajoie et al.)** — distributed, online, outlier-resilient multi-robot SLAM; the pairwise-consistent-measurement-set idea for rejecting bad inter-robot loop closures:
  <https://arxiv.org/abs/1909.12198>
- **Multi-robot SLAM survey** — a 2023 survey of the landscape so you can place Cartographer, Kimera-Multi, and DOOR-SLAM relative to each other:
  <https://arxiv.org/abs/2108.08325>

## Coordination & distributed-systems vocabulary (the minimum)

- **Eventual consistency** — the only honest consistency model for a robot fleet on Wi-Fi; the AWS builders' library explainer is short and concrete:
  <https://aws.amazon.com/builders-library/>
- **The fallacies of distributed computing** — "the network is reliable," "latency is zero," "bandwidth is infinite" — print this, tape it next to the QoS table from week 5:
  <https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing>

## API references (open all week)

- **`tf2_ros` (Python)** — `StaticTransformBroadcaster`, `TransformBroadcaster`, `Buffer`, `TransformListener`:
  <https://docs.ros.org/en/jazzy/p/tf2_ros_py/>
- **`rclpy` launch namespacing** — `Node(namespace=...)`, `PushRosNamespace`, `GroupAction`:
  <https://docs.ros.org/en/jazzy/p/launch_ros/>
- **`nav_msgs`, `geometry_msgs`** — `OccupancyGrid`, `MapMetaData`, `TransformStamped`, `Pose`:
  <https://github.com/ros2/common_interfaces>

## Tools you'll use this week

- **`ros2 launch <pkg> <file> namespace:=robotA`** — bring up a stack under a namespace.
- **`ros2 run tf2_ros tf2_echo world robotA/base_link`** — confirm both robots resolve into a shared `world` frame. Your primary multi-robot diagnostic.
- **`ros2 run tf2_tools view_frames`** — dump the *entire* (now two-robot) TF tree to a PDF; the fastest way to see a frame collision.
- **`ros2 topic list | grep robotA`** — confirm namespacing actually prefixed every topic.
- **`rviz2`** — set the Fixed Frame to `world` and add two `RobotModel`s plus the `/shared_map`; this is your merge ground truth.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Namespace** | A prefix on a node's topics/services/params (`/robotA/scan`) that lets two copies of a stack coexist. |
| **TF frame prefix** | A prefix on coordinate-frame names (`robotA/base_link`) so two robots' frames don't collide in one tree. |
| **`map` frame (per robot)** | The origin of *that robot's* SLAM — robot A's `map` and robot B's `map` are unrelated until you tie them. |
| **`world` frame** | The shared root frame the merged map lives in; `world -> robotA/map` and `world -> robotB/map` tie the two. |
| **Inter-robot transform** | The relative pose `robotA/map -> robotB/map` (known by setup, or estimated by a shared landmark / loop closure). |
| **Map merge** | Fusing two occupancy grids (after transforming into a common frame) into one, with occupied-wins cell rules. |
| **Inter-robot loop closure** | Recognizing that two robots saw the *same place*, producing a constraint that aligns their maps (Kimera-Multi). |
| **Eventual consistency** | Each robot's copy of shared state converges over time, never instantaneously; the honest fleet model. |
| **Latency-bounded coordination** | Never block one robot on a synchronous call to another; exchange state periodically, best-effort. |
| **`ROS_DOMAIN_ID`** | Integer 0–232; the coarse fleet-isolation knob (same domain to coordinate, different to isolate). |
| **DDS partition** | A finer-than-domain isolation inside a shared domain; lets robots share some topics, hide others. |
| **Occupancy grid** | `nav_msgs/OccupancyGrid`: resolution, width, height, origin pose, row-major `int8[]` of 0/100/-1. |
| **Submap** | A locally-consistent chunk of map (Cartographer's unit of merging); merging at the submap level beats merging raw grids. |

---

*If a link 404s, please open an issue so we can replace it.*

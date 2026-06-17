# Week 5 — QoS, DDS, and Message Design

Welcome to the most under-taught failure mode in all of ROS2. By Friday you will be able to look at any topic on a running graph and state, without hesitation, what its Quality of Service profile *should* be, whether the publisher and subscriber actually *agree*, and what silently breaks when they don't. You will read `ros2 topic info -v` the way a backend engineer reads an HTTP status code.

We assume you finished Week 4 and have a `rclpy` action server, a multi-threaded executor, and at least a passing memory of how DDS sits under the rmw layer. We also assume your **week-3 differential-drive robot** still spawns in Gz Sim and publishes `/scan`, `/imu/data`, and `/odom`. If it doesn't, fix that first — every exercise this week runs against that robot.

The one thing to internalize before you read another line: **the default QoS profile in ROS2 is `RELIABLE` + `KEEP_LAST(10)` + `VOLATILE`, and that default is wrong for at least half of the topics on a real robot.** A 30 Hz LiDAR has no business being `RELIABLE` — retransmitting a scan that's already 33 ms stale is worse than dropping it. A latched occupancy grid has no business being `VOLATILE` — a node that subscribes after the map was published gets *nothing*, forever, and you spend an afternoon convinced your map server is broken. QoS is the contract between two nodes. The defaults sign a contract that's wrong for most sensor and map traffic, and the failure is *silent*: no exception, no error log, just two nodes that quietly never talk.

This week is where you stop being surprised by that.

## Learning objectives

By the end of this week, you will be able to:

- **Enumerate** the six QoS policies that matter in practice — reliability, durability, history, depth, deadline, liveliness — and state the default value and the legal values of each.
- **Choose** the correct QoS profile for a topic given only its *class*: sensor stream, latched map, parameter event, command, or transient diagnostic.
- **Predict** whether a given publisher QoS and subscriber QoS are *compatible* using the request–offered rule, before you ever run the graph.
- **Diagnose** a silent QoS mismatch on a live graph using `ros2 topic info -v`, `ros2 doctor`, and rmw-level introspection — and distinguish it from a topic-name typo or a node that crashed.
- **Explain** how DDS discovery works (the SPDP/SEDP handshake), why two nodes on the same `ROS_DOMAIN_ID` find each other with no master, and what `ROS_LOCALHOST_ONLY` and the discovery server change.
- **Compare** CycloneDDS and Fast-DDS — their defaults, their tuning knobs, their failure personalities — and switch between them with one environment variable.
- **Apply** ROS2 message-design idioms: stamping every message with a `std_msgs/Header`, setting `frame_id` honestly, and versioning a custom `.msg` without breaking existing subscribers.
- **Build** a reusable QoS-profile module that any bring-up launch file imports, so QoS is a decision made *once*, in one file, not copy-pasted wrong across forty nodes.

## Prerequisites

This week assumes you have completed **C24 weeks 1–4**, or have equivalent ROS2 fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or the same in a container / WSL2). `ros2 --version` works; `ros2 doctor` runs.
- You can write a `rclpy` publisher and subscriber from memory, and a minimal `rclcpp` node from a template.
- You have the **week-3 robot** (the diff-drive xacro with a 2D LiDAR and IMU) and it spawns in Gz Sim. You can `ros2 topic echo /scan` and see data.
- You understand the **rmw / rcl / rclpy** layering from Week 1 — that `rclpy` calls `rcl` which calls an `rmw` implementation which wraps a DDS vendor.
- You can read and write a `colcon` workspace, a `package.xml`, and a Python or CMake `ament` package.

You do **not** need prior DDS experience. We start at the policy table and build up to discovery and vendor internals. If you've used QoS only through `qos_profile_sensor_data` without knowing what it expands to, this is the week that knowledge becomes load-bearing.

## Topics covered

- The six QoS policies in depth: **Reliability** (`RELIABLE` / `BEST_EFFORT`), **Durability** (`VOLATILE` / `TRANSIENT_LOCAL`), **History** (`KEEP_LAST` / `KEEP_ALL`), **Depth**, **Deadline**, **Liveliness** (`AUTOMATIC` / `MANUAL_BY_TOPIC`) plus the lease duration.
- The **request–offered compatibility matrix**: which subscriber requests are satisfied by which publisher offers, and the exact rules under which a connection silently fails to form.
- The **ROS2 built-in profiles**: `qos_profile_system_default`, `qos_profile_sensor_data`, `qos_profile_parameters`, `qos_profile_parameter_events`, `qos_profile_services_default`, and the rosbag2 `TRANSIENT_LOCAL` story. What each one expands to and when to reach for it.
- **The topic-class taste test**: sensor streams (`BEST_EFFORT` / `KEEP_LAST` / small depth), latched maps and static transforms (`RELIABLE` / `TRANSIENT_LOCAL` / depth 1), parameters and parameter events, commands (`/cmd_vel`), and high-rate diagnostics.
- **DDS discovery**: the participant, the SPDP (Simple Participant Discovery Protocol) and SEDP (Simple Endpoint Discovery Protocol) handshake, multicast vs. unicast discovery, the discovery server pattern, `ROS_DOMAIN_ID`, and `ROS_LOCALHOST_ONLY`.
- **CycloneDDS vs. Fast-DDS** (a.k.a. Fast RTPS / `rmw_fastrtps_cpp`): defaults in Jazzy, switching with `RMW_IMPLEMENTATION`, the XML/JSON config files (`CYCLONEDDS_URI`, `FASTRTPS_DEFAULT_PROFILES_FILE`), shared-memory transport, and the practical reasons a shop picks one over the other in 2026.
- **rmw-level introspection**: `ros2 topic info -v`, `ros2 doctor --report`, the `RMW_IMPLEMENTATION` and `RCUTILS_LOGGING_*` environment knobs, CycloneDDS's `iox-roudi` and `ddsperf`, Fast-DDS's `fastdds discovery` CLI.
- **Message-design idioms**: the `std_msgs/Header` (stamp + `frame_id`), why every sensor message must be stamped at acquisition time, `frame_id` discipline against the tf2 tree, message *versioning* (additive fields, deprecation, the `_v2` escape hatch), and why you almost never roll your own message when a `common_interfaces` type exists.
- **The QoS-profile module pattern**: centralizing every profile in one importable Python/C++ module so the bring-up makes the QoS decision once, and an introspection script that audits the live graph against that module.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                              | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The six QoS policies; compatibility; built-ins     |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Topic-class taste test; sensor + map exercises     |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | DDS discovery; CycloneDDS vs Fast-DDS; introspection |  2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Message-design idioms; the mismatch postmortem     |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | QoS-profile module; live-graph audit               |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                             |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, postmortem polish                    |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                    | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The ROS2 QoS docs, DDS specs, vendor docs, and the talks worth your time |
| [lecture-notes/01-qos-is-not-optional.md](./02-lecture-notes/01-qos-is-not-optional.md) | The six policies, the compatibility rules, the built-in profiles, and the topic-class taste test |
| [lecture-notes/02-dds-discovery-vendors-message-design.md](./02-lecture-notes/02-dds-discovery-vendors-message-design.md) | DDS discovery, CycloneDDS vs Fast-DDS, rmw introspection, and message-design idioms |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-sensor-qos.md](./03-exercises/exercise-01-sensor-qos.md) | Set the robot's sensor topics to `BEST_EFFORT`/`KEEP_LAST`/depth 5 and verify with `ros2 topic info -v` |
| [exercises/exercise-02-latched-map.py](./03-exercises/exercise-02-latched-map.py) | A `TRANSIENT_LOCAL` map publisher + a late subscriber that still receives the latched map |
| [exercises/exercise-03-mismatch-probe.py](./03-exercises/exercise-03-mismatch-probe.py) | Introduce a deliberate QoS mismatch and capture the silent failure with rmw incompatibility events |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-diagnose-three-mismatches.md](./04-challenges/challenge-01-diagnose-three-mismatches.md) | Detect and prescribe the fix for three different QoS-mismatch scenarios on a live graph |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the one-page mismatch postmortem |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The reusable `crunchbot_qos` profile module + live-graph auditor |

## The "the connection formed" promise

C24 uses a recurring marker for every exercise that ends in two nodes actually talking:

```
$ ros2 topic info /scan -v
...
Publisher count: 1
Subscription count: 1
QoS profile:
  Reliability: BEST_EFFORT
  Durability:  VOLATILE
  History (Depth): KEEP_LAST (5)
```

If `Subscription count` is `0` when you expected `1`, or the two endpoints print *different* QoS, you are not done. A topic that exists but whose subscriber count is stuck at zero is the canonical silent QoS failure. The point of Week 5 is to make that line ordinary — and to make the zero *loud* instead of silent.

## Stretch goals

If you finish the regular work early and want to push further:

- Read the **DDS RTPS wire-protocol spec** §8.4 (the discovery section) until you can draw the SPDP/SEDP handshake from memory: <https://www.omg.org/spec/DDSI-RTPS/2.5/>.
- Run **`ddsperf`** (ships with CycloneDDS) on your robot's network and measure round-trip latency for a 1 KB sample under `RELIABLE` vs `BEST_EFFORT`. Note where the reliability tax shows up.
- Stand up a **Fast-DDS discovery server** with `fastdds discovery -i 0` and point your robot's nodes at it with `ROS_DISCOVERY_SERVER`. Measure how discovery traffic on the wire changes versus default multicast.
- Write a `.msg` for a custom `crunch_interfaces/SystemHealth` message, then *version it*: add a field, rebuild, and confirm a node built against the old definition still deserializes the new message. Document where it breaks.

## Up next

Week 6 takes the QoS literacy you built here and applies it to **odometry**: wheel kinematics, drift, and why your `/odom` topic's QoS interacts with `robot_localization`'s expectations. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

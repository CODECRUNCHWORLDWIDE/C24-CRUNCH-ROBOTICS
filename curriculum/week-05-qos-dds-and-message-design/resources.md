# Week 5 — Resources

Every resource here is **free** and pinned to **ROS2 Jazzy** (the LTS we run on Ubuntu 24.04) wherever the docs are versioned. The ROS2 docs are open. The DDS and RTPS specs are published openly by the OMG. The vendor docs (eProsima, Eclipse CycloneDDS) are public. No paywalled books are linked.

When a link is versioned, the Jazzy URL is given. If you are on a newer distro later, swap `jazzy` for your distro name — the QoS concepts are stable across distros; only the API-reference URLs move.

## Required reading (work it into your week)

- **About Quality of Service settings** — the canonical ROS2 QoS page. Read it twice, once Monday and once Thursday:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html>
- **QoS compatibility** — the request–offered table from Lecture 1, in the official words:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html#qos-compatibilities>
- **About discovery** — SPDP/SEDP, domains, multicast, the discovery server:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Discovery.html>
- **About different middleware vendors** — the rmw abstraction, what ships, how to switch:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Different-Middleware-Vendors.html>
- **About ROS2 interfaces** — message/service/action definitions and the type-hashing that makes versioning a redeploy-everything event:
  <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html>

## The specifications (skim, don't memorize)

You will not read these cover to cover. But the first time a colleague says "that's a §8.5.3 SPDP thing," you want to know what they mean.

- **DDS specification v1.4 (QoS policies live in §2.2.3)** — OMG:
  <https://www.omg.org/spec/DDS/1.4/>
- **DDSI-RTPS wire-protocol spec v2.5 (discovery is §8.5)** — the bytes on the wire:
  <https://www.omg.org/spec/DDSI-RTPS/2.5/>
- **REP 2003 — default QoS profiles for sensor and map data** — why `/scan` is `BEST_EFFORT` and `/map` is `TRANSIENT_LOCAL` as ratified policy, not folklore:
  <https://www.ros.org/reps/rep-2003.html>

## API references (the ones you'll have open all week)

- **`rclpy.qos`** — `QoSProfile`, the policy enums, and the named profiles:
  <https://docs.ros.org/en/jazzy/p/rclpy/rclpy.qos.html>
- **`rclcpp::QoS`** — the C++ builder (`KeepLast`, `.reliable()`, `.transient_local()`):
  <https://docs.ros.org/en/jazzy/p/rclcpp/generated/classrclcpp_1_1QoS.html>
- **`rmw_qos_profile_t`** — the C struct every vendor enforces:
  <https://docs.ros.org/en/jazzy/p/rmw/generated/structrmw__qos__profile__s.html>

## Vendor docs

- **Eclipse CycloneDDS — configuration reference** (`CYCLONEDDS_URI` XML, every knob):
  <https://cyclonedds.io/docs/cyclonedds/latest/config/index.html>
- **CycloneDDS — `ddsperf`** (latency/throughput benchmarking; ships with the apt package):
  <https://github.com/eclipse-cyclonedds/cyclonedds/blob/master/src/tools/ddsperf/ddsperf.1.adoc>
- **Fast-DDS — XML profiles** (`FASTRTPS_DEFAULT_PROFILES_FILE`):
  <https://fast-dds.docs.eprosima.com/en/latest/fastdds/xml_configuration/xml_configuration.html>
- **Fast-DDS — ROS2 discovery server** (`fastdds discovery`, `ROS_DISCOVERY_SERVER`):
  <https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html>

## How-to guides (the practical ones)

- **Working with multiple RMW implementations** — switching, confirming, the apt packages:
  <https://docs.ros.org/en/jazzy/How-To-Guides/Working-with-multiple-RMW-implementations.html>
- **Using `ros2 doctor`** — what the report includes and how to read it:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Ros-2-doctor.html>
- **Configuring QoS for a topic in a launch file / params** — the standard place real bring-ups set it:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html#qos-profiles>

## QoS in real stacks (read the source of code that gets QoS right)

- **Nav2 map server** — the canonical `RELIABLE` + `TRANSIENT_LOCAL` latched map publisher:
  <https://docs.nav2.org/configuration/packages/configuring-map-server.html>
- **`slam_toolbox`** — publishes `/map` latched; read how it sets QoS:
  <https://github.com/SteveMacenski/slam_toolbox>
- **`tf2_ros` `StaticTransformBroadcaster`** — why `/tf_static` is `TRANSIENT_LOCAL` with a deep history:
  <https://github.com/ros2/geometry2/tree/jazzy/tf2_ros>
- **`common_interfaces`** — `std_msgs`, `sensor_msgs`, `geometry_msgs`, `nav_msgs`, `vision_msgs`; read a `.msg` before you write your own:
  <https://github.com/ros2/common_interfaces>

## Talks worth your time (free, no signup)

- **"DDS in ROS2: the good, the bad, and the QoS"** — ROSCon talks index; search the ROSCon archive for the discovery and QoS deep-dives, all posted free:
  <https://roscon.ros.org/>
- **eProsima — Fast-DDS channel** — discovery-server and SHM walkthroughs from the maintainers:
  <https://www.youtube.com/@eProsima>
- **ROSCon 2024/2025 QoS and middleware sessions** — the OSRF posts every talk; the QoS sessions are the most-rewatched in the middleware track:
  <https://vimeo.com/osrfoundation>

## Tools you'll use this week

- **`ros2 topic info -v`** — your primary diagnostic. Prints both endpoints' full QoS.
- **`ros2 doctor --report`** — rmw implementation, middleware version, network config.
- **`ros2 topic echo --qos-reliability best_effort /scan`** — echo with an explicit QoS so you don't fight a default mismatch while debugging.
- **`ddsperf`** (CycloneDDS) — `sudo apt install cyclonedds-tools`. Latency/throughput bench.
- **`fastdds`** CLI (Fast-DDS) — `discovery`, `shm clean` (clears stale SHM after a crash).

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **QoS** | Quality of Service — the per-endpoint contract (reliability, durability, history, depth, deadline, liveliness). |
| **DDS** | Data Distribution Service — the OMG pub/sub middleware under ROS2. |
| **RTPS** | Real-Time Publish-Subscribe — the wire protocol DDS speaks. |
| **rmw** | ROS middleware interface — the abstraction layer that wraps a DDS vendor. |
| **SPDP** | Simple Participant Discovery Protocol — periodic multicast "I exist" announcements. |
| **SEDP** | Simple Endpoint Discovery Protocol — unicast exchange of topic/type/QoS; where compatibility is checked. |
| **`RELIABLE`** | Lost samples are retransmitted (TCP-like). Default. |
| **`BEST_EFFORT`** | Fire-and-forget; lost samples are gone (UDP-like). Correct for sensors. |
| **`VOLATILE`** | Late subscribers get only new samples. Default. |
| **`TRANSIENT_LOCAL`** | Late subscribers get the last `depth` cached samples — ROS2's "latched." |
| **`KEEP_LAST(n)`** | Ring buffer of the last `n` samples. |
| **`KEEP_ALL`** | Keep every sample (resource-limited). |
| **Deadline** | Max expected gap between samples; a *monitoring* policy, fires events. |
| **Liveliness** | How a writer asserts it's alive; `AUTOMATIC` vs `MANUAL_BY_TOPIC`. |
| **Request–offered rule** | A connection forms only if the publisher's offer is ≥ the subscriber's request, per policy. |
| **`ROS_DOMAIN_ID`** | Integer 0–232; nodes only discover nodes in the same domain. |
| **Discovery server** | A relay that turns N² multicast discovery into N unicast. |
| **Type hash (RIHS)** | The hash of a message definition; mismatched hashes refuse to connect. |

---

*If a link 404s, please open an issue so we can replace it.*

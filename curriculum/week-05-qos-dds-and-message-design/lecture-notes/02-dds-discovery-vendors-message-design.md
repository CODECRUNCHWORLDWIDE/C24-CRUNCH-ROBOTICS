# Lecture 2 — DDS Discovery, CycloneDDS vs Fast-DDS, and Message Design

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain how two ROS2 nodes find each other with no master, switch DDS vendors with one environment variable and articulate why a shop picks one, and design a message that you won't regret in six months.

Lecture 1 was the contract. This lecture is the courier that carries the contract across the wire — DDS — plus the discipline that keeps the *payload* sane: message design. Three parts: (1) how discovery works, (2) the two vendors you'll actually use, (3) message-design idioms.

---

## Part 1 — DDS discovery: how nodes find each other with no master

ROS1 had a master (`roscore`). Every node phoned home to the master to find every other node. Kill the master and the graph froze. ROS2 has **no master**. Nodes find each other by a fully distributed protocol baked into DDS. This is the single biggest architectural change from ROS1, and it's worth understanding because when discovery goes wrong, the symptom — "my node can't see the other node's topic" — looks identical to a QoS mismatch but has a completely different fix.

### 1.1 Participants, writers, readers

DDS organizes a process into:

- A **DomainParticipant** — one per process (one per ROS2 `Context`, usually one per node-process). It owns the discovery machinery.
- **DataWriters** — one per publisher.
- **DataReaders** — one per subscription.

Every participant lives in a **domain**, identified by an integer 0–232. In ROS2 this is `ROS_DOMAIN_ID` (default `0`). **Participants only discover participants in the same domain.** This is your first isolation knob: two robots on the same LAN that should never talk get different domain IDs, and discovery simply never introduces them. It's also a classic gotcha — you `export ROS_DOMAIN_ID=42` in one terminal, forget it in another, and the two terminals' nodes are invisible to each other. They're in different domains.

```bash
# Terminal A and Terminal B must share a domain to see each other.
export ROS_DOMAIN_ID=7
ros2 run demo_nodes_cpp talker
# ... different terminal, same export ...
export ROS_DOMAIN_ID=7
ros2 run demo_nodes_py listener
```

### 1.2 SPDP — finding participants

When a participant starts, it announces itself with **SPDP, the Simple Participant Discovery Protocol.** Concretely, it sends a periodic announcement to a well-known **multicast** address (derived from the domain ID) containing its GUID, the locators (IP + port) where it can be reached, and its lease duration. Every other participant in the domain is listening on that multicast address; when it hears the announcement, it records "participant X exists at these addresses" and replies with its own.

The key properties:

- It's **periodic** — announcements repeat (default every few seconds) so a participant that starts late still discovers everyone, and a participant that dies stops announcing and is eventually timed out by its lease.
- It's **multicast by default** — which is why discovery "just works" on a single LAN with multicast enabled, and breaks the moment you cross a router that drops multicast, or a Wi-Fi AP with multicast filtering, or a Docker bridge network. Half of all "ROS2 works on the bench but not on the robot's Wi-Fi" tickets are multicast discovery being filtered.

### 1.3 SEDP — finding endpoints

Once two participants know about each other (SPDP), they exchange the *details* of their writers and readers over **SEDP, the Simple Endpoint Discovery Protocol** — this time **unicast**, point to point. SEDP carries: topic name, topic type, and **the full QoS profile of each endpoint.**

This is the moment QoS compatibility (Lecture 1, §3) is actually evaluated. When participant A's reader for `/scan` learns about participant B's writer for `/scan` via SEDP, each side checks the request–offered rule. If they're compatible, a connection is established and data flows. If not, the endpoints are *known to each other* (which is why `ros2 topic info -v` shows both) but no data link forms. **Discovery succeeded; the QoS handshake failed.** That distinction is the whole reason `ros2 topic info -v` is useful: it shows you the SEDP-exchanged QoS of both sides.

```
Participant A starts ──SPDP(multicast)──► everyone hears it
Participant B starts ──SPDP(multicast)──► A hears it, A & B now know each other
A's reader  ◄──SEDP(unicast)── B's writer    (exchange topic, type, QoS)
                 │
                 ▼
        QoS compatible?  ──yes──► data flows
                 │
                 └────────no────► connection silently not formed
```

### 1.4 The discovery cost and the discovery server

Multicast SPDP scales poorly. With N participants, every participant announces to every other, so discovery traffic grows roughly with N². On a two-node bench that's nothing. On a 200-node graph (a real Nav2 + MoveIt2 + perception stack) it's a measurable chunk of your network and CPU at startup, and it spikes every time a node restarts.

Both vendors offer a **discovery server** to fix this: instead of N participants multicasting to each other, they all unicast to one (or a few) well-known server processes that relay endpoint information. This turns N² into N, eliminates multicast entirely (great for Wi-Fi and Docker), and is the standard pattern for any non-trivial deployment in 2026.

- **Fast-DDS:** `fastdds discovery -i 0` runs a server; clients set `ROS_DISCOVERY_SERVER=<ip>:<port>`.
- **CycloneDDS:** configured via the `<Discovery>` block in `CYCLONEDDS_URI`, using peer lists or the Cyclone discovery features.

You don't need the discovery server for this week's exercises (two-node graphs), but you must know it exists, because the first time you can't get discovery working across a Docker bridge, the answer is "turn off multicast, use a discovery server or a unicast peer list."

### 1.5 The two isolation knobs you'll actually use

- **`ROS_DOMAIN_ID`** — integer. Nodes only discover nodes in the same domain. Use it to run two independent robots/sims on one network.
- **`ROS_LOCALHOST_ONLY`** (deprecated in favor of `ROS_AUTOMATIC_DISCOVERY_RANGE` in Jazzy, but you'll still see it) — restricts discovery to `localhost`. Use it to keep your laptop's experiments off the lab network. In Jazzy the modern form is `export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`.

```bash
# Keep everything on this machine — no announcements leave localhost.
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
```

---

## Part 2 — CycloneDDS vs Fast-DDS

ROS2 abstracts the vendor behind `rmw`, so your *code* doesn't change when you switch. What changes is the defaults, the tuning files, the failure personality, and the performance under load. As of Jazzy, **`rmw_fastrtps_cpp` (Fast-DDS) is the default rmw**, but **CycloneDDS (`rmw_cyclonedds_cpp`) is what a large fraction of production shops run** because of its simpler configuration and predictable behavior. You should be fluent in switching.

### 2.1 Switching vendors

One environment variable:

```bash
# Use CycloneDDS:
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Use Fast-DDS (the Jazzy default — usually unset):
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# Confirm what you're actually running:
ros2 doctor --report | grep -A2 "middleware"
```

You must have the package installed (`sudo apt install ros-jazzy-rmw-cyclonedds-cpp`). **Every node in a graph must use the same rmw** — Cyclone and Fast-DDS can technically interoperate over RTPS, but in practice you set it once for the whole graph and don't mix. A graph where half the nodes are Cyclone and half are Fast-DDS is a debugging nightmare you create for yourself.

### 2.2 The honest comparison

| Dimension | CycloneDDS (`rmw_cyclonedds_cpp`) | Fast-DDS (`rmw_fastrtps_cpp`) |
|---|---|---|
| Jazzy status | Tier-1, widely deployed | Default rmw |
| Configuration | One XML file via `CYCLONEDDS_URI`, small and readable | XML profiles via `FASTRTPS_DEFAULT_PROFILES_FILE`, richer but more verbose |
| Shared memory | Via Iceoryx (`iox-roudi` daemon) | Built-in SHM transport, easier to enable |
| Discovery server | Peer-list / config-based | First-class `fastdds discovery` CLI + `ROS_DISCOVERY_SERVER` |
| Personality | Predictable, fewer knobs, "it does what you said" | More features, more tuning surface, occasionally more startup chatter |
| Common choice for | Mobile robots, "just make it reliable and simple" | Large feature-rich systems, teams already invested in eProsima tooling |

The honest summary a senior engineer gives a new hire in 2026: **"Default is Fast-DDS. If discovery is flaky or config is fighting you, try `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and most weird problems go away. Pick one, write it into your bring-up's environment, and make sure the whole fleet runs the same one."** Both are good. The failure mode you must avoid is *accidentally* running different vendors on different machines.

### 2.3 Tuning files

CycloneDDS reads an XML config pointed to by `CYCLONEDDS_URI`. A minimal one that disables multicast (Docker/Wi-Fi friendly) and sets a peer:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS xmlns="https://cdds.io/config"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
  <Domain Id="any">
    <General>
      <Interfaces>
        <NetworkInterface name="eth0" priority="default" multicast="false"/>
      </Interfaces>
      <AllowMulticast>false</AllowMulticast>
    </General>
    <Discovery>
      <Peers>
        <Peer Address="192.168.1.10"/>
      </Peers>
      <ParticipantIndex>auto</ParticipantIndex>
    </Discovery>
  </Domain>
</CycloneDDS>
```

```bash
export CYCLONEDDS_URI=file:///home/crunch/cyclonedds.xml
```

Fast-DDS reads XML profiles pointed to by `FASTRTPS_DEFAULT_PROFILES_FILE`. The structure differs but the idea is identical: declare transports, disable multicast, set peers/discovery-server. You won't author these from scratch this week; you must know *where they live* and *that they override the QoS you set in code only where they explicitly say so* — code-level QoS still applies per-endpoint; the XML configures the transport and discovery beneath it.

### 2.4 Vendor introspection tools

- **CycloneDDS:** `ddsperf` (latency/throughput benchmarking — ships with the package), and the `iox-roudi` daemon for shared memory.
- **Fast-DDS:** `fastdds discovery` (run a discovery server), `fastdds shm clean` (clear stale shared-memory segments after a crash — a real fix for "nodes won't restart"), and Fast-DDS Monitor (a GUI).
- **Vendor-agnostic:** `ros2 doctor --report` dumps the rmw implementation, the middleware version, network interfaces, and platform — the first command to run when "discovery is weird."

```bash
ros2 doctor --report
# Look for the "RMW MIDDLEWARE" and "NETWORK CONFIGURATION" sections.
```

---

## Part 3 — Message-design idioms

A robot is only as trustworthy as its timestamps and frames. The QoS contract gets the bytes across; message design decides whether those bytes mean anything. Three idioms separate code that works in a demo from code that works at 3 a.m.

### 3.1 Stamp every message, at acquisition time

Almost every meaningful ROS2 message carries a `std_msgs/Header`:

```
# std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
```

The `stamp` is **the time the data was *acquired*, not the time you got around to publishing it.** This is the single most violated rule in beginner ROS2 code. If your camera node reads a frame, runs 40 ms of inference, and *then* stamps the message with `now()`, every downstream consumer — tf2, the EKF, the synchronizer — thinks the detection happened 40 ms later than it did. On a robot moving 1 m/s that's 4 cm of error injected for free, and it compounds.

```python
# WRONG: stamp at publish time, after processing.
def on_image(self, img):
    result = self.run_inference(img)        # 40 ms
    msg = Detection2DArray()
    msg.header.stamp = self.get_clock().now().to_msg()  # too late!
    self.pub.publish(msg)

# RIGHT: carry the acquisition stamp through.
def on_image(self, img):
    acquired = img.header.stamp              # the camera's stamp
    result = self.run_inference(img)
    msg = Detection2DArray()
    msg.header.stamp = acquired              # preserve the truth
    self.pub.publish(msg)
```

When you *generate* data (a synthetic scan, a simulated IMU), stamp it the instant you sample the world, before any work. When you *transform* data, preserve the input's stamp. When you *fuse* data with different stamps, that's exactly what tf2's time-travel and the EKF's covariance bookkeeping are for — but they can only work if every input is stamped honestly.

### 3.2 `frame_id` discipline

The `frame_id` says *which coordinate frame the data is expressed in.* It must be a real frame in your tf2 tree (Week 2). A `LaserScan` from the LiDAR is in the `laser_link` frame; an `Odometry` message is in `odom`; a goal pose might be in `map`. Get this wrong and tf2 either throws `LookupException` (the loud failure — you'll catch it) or, worse, silently transforms with the wrong frame and your robot drives into a wall confidently.

Rules:

- Every stamped message's `frame_id` names a frame that exists in the tf tree at that `stamp`.
- Sensor data is in the sensor's frame, not `base_link`, not `map`. Let the consumer transform it.
- Never leave `frame_id` empty on a stamped message. An empty `frame_id` is a landmine — some consumers treat it as "no transform needed," others throw.
- The `child_frame_id` on `Odometry` and `TransformStamped` is the frame being *described* (e.g., `base_link`), while `header.frame_id` is the *reference* frame (e.g., `odom`). Mixing these up inverts your transform.

### 3.3 Use `common_interfaces` before you roll your own

ROS2 ships `common_interfaces`: `std_msgs`, `sensor_msgs`, `geometry_msgs`, `nav_msgs`, `vision_msgs`, `diagnostic_msgs`, and more. Before you define a custom `.msg`, check whether a standard one fits. The standard types are what every off-the-shelf tool (rviz2, Foxglove, Nav2, `robot_localization`) understands. A custom `MyRobotPose` that's structurally identical to `geometry_msgs/PoseStamped` buys you nothing and costs you every integration. Roll your own *only* when no standard type fits, and even then, **compose** standard types inside it:

```
# crunch_interfaces/msg/SystemHealth.msg  (version 1)
std_msgs/Header header
float32 battery_voltage
float32 cpu_temp_celsius
uint8 nav_state
```

### 3.4 Versioning a message without breaking subscribers

Messages are part of your API. Once a node depends on a `.msg`, changing it can break every node built against the old definition, because ROS2 uses the message's **type hash** (the RIHS hash in Jazzy) to check compatibility at discovery time. Two endpoints with different hashes for the "same" topic won't connect.

The safe-evolution rules:

- **Additive is *not* automatically safe in ROS2** the way it is in some serialization formats. Adding a field changes the type hash, so an old subscriber and a new publisher have different hashes and **will not connect**. This surprises people coming from Protobuf, where adding optional fields is backward-compatible.
- Therefore: when you add a field, **rebuild and redeploy *every* node** that uses the message in the same release. In a monorepo with one `colcon build`, that's automatic. In a fleet with mixed software versions, it is not — which is why fleet upgrades stage interface changes carefully.
- When you genuinely must support old and new simultaneously (a rolling fleet upgrade), the pragmatic escape hatch is a **new message type** — `SystemHealthV2` on a new topic — and a bridge node that translates, until the old version is fully retired. Ugly, explicit, and it works.
- Add new fields **at the end** and give them sane zero-defaults, so the *intent* is additive even though the hash changes. Never reorder or retype existing fields; that's a semantic break on top of a hash break.

```
# crunch_interfaces/msg/SystemHealth.msg  (version 2 — new field appended)
std_msgs/Header header
float32 battery_voltage
float32 cpu_temp_celsius
uint8 nav_state
float32 disk_free_gb        # appended in v2; defaults to 0.0
```

Rebuild the whole workspace, and old-vs-new endpoints will refuse to connect until both are rebuilt — which is the system *telling you* about the incompatibility loudly, instead of silently deserializing garbage. That's a feature. Respect it.

### 3.5 A note on bounded vs unbounded fields

`string` and `sequence<T>` (the `T[]` syntax) are unbounded by default, which means a malicious or buggy publisher can send an arbitrarily large message and blow up a subscriber's buffer. For anything safety- or resource-sensitive, bound them: `string<=32 name` and `float32[<=360] ranges`. Bounded fields let DDS preallocate, which also helps real-time determinism. For a research robot it's optional; for a shipping product it's table stakes.

---

## 3.6 The deadline and liveliness contract in the wild

Lecture 1 introduced **deadline** and **liveliness** as policies. Here is where they earn their keep, because they only matter once data is crossing DDS and a node has to decide "is the other side still alive, and is it keeping its promise?"

**Deadline** is a publisher's promise — "I will publish at least this often" — and a subscriber's expectation. Set a 100 ms deadline on a 30 Hz LiDAR subscriber, and the moment two consecutive scans are more than 100 ms apart, DDS fires a `requested_deadline_missed` event on the reader. That is your dropout detector, for free, at the middleware layer — no watchdog timer in your node, no manual "when did I last hear a scan" bookkeeping. The chaos-drill in Week 46 ("the LiDAR is killed mid-task") is exactly this event firing.

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from rclpy.duration import Duration
from rclpy.qos_event import SubscriptionEventCallbacks, QoSRequestedDeadlineMissedInfo

def on_deadline_missed(info: QoSRequestedDeadlineMissedInfo) -> None:
    # Fires when the publisher misses its promised period.
    node.get_logger().warn(
        f"/scan deadline missed: total={info.total_count} "
        f"delta={info.total_count_change}"
    )

scan_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
    deadline=Duration(seconds=0, nanoseconds=100_000_000),  # 100 ms
)

callbacks = SubscriptionEventCallbacks(deadline=on_deadline_missed)
node.create_subscription(
    LaserScan, "/scan", on_scan, scan_qos, event_callbacks=callbacks
)
```

The compatibility rule for deadline is the same request–offered logic as everything else, in the direction that protects the subscriber: a subscriber's *requested* deadline must be **greater than or equal to** the publisher's *offered* deadline. Ask for a tighter deadline than the publisher promises and the connection is rejected at SEDP — the publisher cannot guarantee what you demand, so DDS refuses to lie about it. Practically: set the subscriber's deadline to a little more than the publisher's nominal period (a 30 Hz / 33 ms stream gets a ~100 ms deadline, not 33 ms) so normal jitter doesn't spam the event.

**Liveliness** answers a different question: "is the publisher's *process* still alive, even if it has nothing to say right now?" `AUTOMATIC` liveliness is asserted by the DDS stack as long as the participant exists, so a publisher that's connected but silent still counts as live. `MANUAL_BY_TOPIC` requires the publisher to actively assert liveliness (by publishing, or by calling `assert_liveliness()`) within the lease duration — useful for a heartbeat where "I'm running but idle" must be distinguished from "I crashed." The capstone's `/fleet/heartbeat` at 1 Hz is the canonical `MANUAL_BY_TOPIC` topic: if the node wedges but the process survives, `AUTOMATIC` would still report it live and lie to the fleet manager; `MANUAL_BY_TOPIC` with a 2 s lease catches the wedge.

The honest field guidance for 2026: **most topics need neither.** Reach for deadline on sensor streams where dropout is a safety event you must detect, and for liveliness on heartbeats and on any topic where a wedged-but-not-dead publisher is a real hazard. Setting deadline on every topic "to be safe" just generates event noise nobody reads — and noise nobody reads is worse than no signal at all.

## 3.7 QoS and rosbag2: the recording gotcha

The first time you `ros2 bag record /scan /map` and then play it back, you will hit a QoS surprise, so internalize it now. `rosbag2` records the QoS profile that was offered on each topic at record time and stores it in the bag's metadata. On **playback**, the bag *re-publishes* with a QoS chosen by the player, and a few things bite:

- A `TRANSIENT_LOCAL` topic (your `/map`) recorded fine, but on playback the player defaults to `VOLATILE` unless you override it — so a node that joins the playback late gets no latched map, and you re-learn Lecture 1's durability lesson against a bag instead of a robot.
- A `BEST_EFFORT` publisher recorded into a bag plays back, by default, as `RELIABLE` unless you pass `--qos-profile-overrides-path`, which can change timing characteristics on a busy graph.

The fix is an override YAML handed to record or play:

```yaml
# qos_overrides.yaml — force /map back to TRANSIENT_LOCAL on playback
/map:
  history: keep_last
  depth: 1
  reliability: reliable
  durability: transient_local
```

```bash
ros2 bag play my_bag --qos-profile-overrides-path qos_overrides.yaml
```

This is not an edge case; it is the standard reason "my recorded map doesn't show up when I replay the bag in rviz2." The same `crunchbot_qos` module you build in the mini-project should be the thing that *generates* this override file — one source of truth for live QoS and for bag QoS.

---

## 4. Putting it together: the failure-mode decision tree

When a subscriber isn't receiving, walk this tree — it covers discovery *and* QoS *and* message design:

```
Subscriber gets nothing.
│
├─ Does `ros2 topic list` show the topic at all?
│   ├─ No  → discovery problem. Check ROS_DOMAIN_ID match,
│   │        multicast on the network, RMW_IMPLEMENTATION match.
│   └─ Yes ↓
│
├─ Does `ros2 topic info /t -v` show BOTH a publisher and subscriber?
│   ├─ No  → the other node isn't running, or topic name typo / remap.
│   └─ Yes ↓
│
├─ Do the publisher and subscriber QoS blocks MATCH (compatible)?
│   ├─ No  → QoS mismatch. Apply the request–offered rule. (Lecture 1 §3)
│   └─ Yes ↓
│
├─ Do `ros2 topic info` types / hashes match?
│   ├─ No  → message-version mismatch. Rebuild both ends. (§3.4)
│   └─ Yes ↓
│
└─ Data flows but is wrong → check `frame_id` and `stamp`. (§3.1, §3.2)
```

Tape this next to the QoS taste-test table. Between the two, you can diagnose almost any "my nodes won't talk" problem on a ROS2 graph in under five minutes — which is the whole point of this week.

---

## 5. Recap

You should now be able to:

- Explain SPDP (multicast participant discovery) and SEDP (unicast endpoint + QoS exchange) and where QoS compatibility is actually evaluated.
- Use `ROS_DOMAIN_ID` and `ROS_AUTOMATIC_DISCOVERY_RANGE` to isolate graphs, and explain why multicast filtering breaks discovery.
- Switch between CycloneDDS and Fast-DDS with `RMW_IMPLEMENTATION`, name the practical trade-offs, and avoid mixing vendors.
- Stamp messages at acquisition time, set `frame_id` against the tf tree, and reuse `common_interfaces` before rolling your own.
- Evolve a message safely and know why ROS2's type hash makes "additive" changes a redeploy-everything event.
- Walk the discovery → QoS → version → semantics decision tree to diagnose any silent failure.

Next: the exercises put all of this on your week-3 robot. Continue to [the exercises](../exercises/README.md).

---

## References

- *About discovery* — ROS2 docs: <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Discovery.html>
- *Working with multiple RMW implementations* — ROS2 docs: <https://docs.ros.org/en/jazzy/How-To-Guides/Working-with-multiple-RMW-implementations.html>
- *DDS implementations* — ROS2 docs: <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Different-Middleware-Vendors.html>
- *CycloneDDS configuration*: <https://cyclonedds.io/docs/cyclonedds/latest/config/index.html>
- *Fast-DDS discovery server*: <https://fast-dds.docs.eprosima.com/en/latest/fastdds/ros2/discovery_server/ros2_discovery_server.html>
- *DDSI-RTPS wire protocol spec* (discovery, §8.5): <https://www.omg.org/spec/DDSI-RTPS/2.5/>
- *`common_interfaces` repository*: <https://github.com/ros2/common_interfaces>
- *About ROS2 interfaces (message hashing)*: <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html>
- *rosbag2 QoS profile overrides*: <https://github.com/ros2/rosbag2#overriding-qos-profiles>
- *QoS deadline, liveliness, lifespan demo*: <https://docs.ros.org/en/jazzy/Tutorials/Demos/Quality-of-Service.html>

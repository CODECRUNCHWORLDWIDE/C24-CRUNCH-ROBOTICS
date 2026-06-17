# Lecture 1 — Namespacing, Discovery, and the Two-`map`-Frames Problem

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can namespace a full robot stack so two copies coexist in one graph with zero collisions, decide when two robots should share or isolate a DDS domain, and explain why two `slam_toolbox` robots have two unrelated `map` frames and what frame the shared map must live in.

If you remember one sentence from this lecture, remember this one:

> **Two robots in one graph collide on three axes — topic names, TF frame names, and discovery — and a namespace fixes the first, a frame prefix fixes the second, and a domain decision fixes the third. Confusing the three is the source of every "why can't robot A see its own scan" bug you will file this week.**

For thirty-four weeks your robot has been alone. There was one `/scan`, one `/map`, one TF tree rooted at `map`, one `ROS_DOMAIN_ID` you never thought about. This week there are two robots, and every one of those singletons becomes a plural. The good news: ROS2 was designed for this — the namespace machinery is first-class, not bolted on. The bad news: the defaults assume you are alone, so every default is now a trap.

---

## 1. The three collisions

Spawn two copies of your week-8 `crunchbot_bringup` in one graph with no changes and watch what breaks. Both robots publish `/scan`. Both publish a TF from `odom` to `base_link`. Both run a node literally named `robot_state_publisher`. The result is a graph where:

1. **Topics collide.** Two publishers on `/scan` means a subscriber gets an interleaved stream of *both* robots' LiDAR, with no way to tell which beam came from which robot. Garbage.
2. **TF frames collide.** Two transforms `odom -> base_link` in one tf2 buffer means the tree has two parents fighting for `base_link`. tf2 will use whichever arrived last; your robots teleport between each other's poses.
3. **Node names collide.** Two nodes named `robot_state_publisher` is a warning at best and undefined behavior at worst; ROS2 nodes are supposed to have unique fully-qualified names.

Each collision has its own fix. Learn them as three separate tools, because using the wrong one — a namespace where you needed a frame prefix — fixes half the problem and leaves you debugging the other half for an hour.

---

## 2. Namespacing: the topic-and-node fix

A **namespace** is a prefix applied to a node's name and to every *relative* topic, service, and parameter it touches. Give robot A the namespace `robotA` and its node `scan_publisher` becomes `/robotA/scan_publisher`, its `scan` topic becomes `/robotA/scan`, its `cmd_vel` becomes `/robotA/cmd_vel`. Robot B under `robotB` gets `/robotB/scan`. No collision. A subscriber that wants robot A's LiDAR subscribes to `/robotA/scan` and knows exactly whose beams it's reading.

The load-bearing word is **relative**. ROS2 topic names come in three flavors:

- **Relative** — `scan`. Resolved against the node's namespace. Under namespace `robotA` it becomes `/robotA/scan`. **This is what you want almost always.**
- **Absolute** — `/scan`. The leading slash means "ignore my namespace; this is the global name." It resolves to `/scan` regardless of namespace. **This is the trap.** A node that hard-codes `/scan` defeats namespacing — both robots' nodes will use the global `/scan` and collide exactly as if you'd done nothing.
- **Private** — `~/scan`. Resolved against the node's *fully-qualified name*, becoming `/robotA/scan_publisher/scan`. Rare for data topics; used for per-node config topics.

> **Rule:** inside a node that will ever be namespaced — which, in a multi-robot world, is *every* node — never write a leading slash on a data topic. Write `scan`, not `/scan`. Let the namespace do its job. The single most common multi-robot bug is one stray `/cmd_vel` in a node you wrote in week 6 when you were alone.

### 2.1 Namespacing in code

In `rclpy`, the namespace is set when the node is constructed, usually from the launch system, but you can hard-set it:

```python
import rclpy
from rclpy.node import Node


class ScanPublisher(Node):
    def __init__(self) -> None:
        # No namespace here — it comes from launch. Topic is RELATIVE.
        super().__init__("scan_publisher")
        # 'scan' is relative: becomes /robotA/scan when this node runs under
        # the robotA namespace. Writing '/scan' here would defeat namespacing.
        self.pub = self.create_publisher(LaserScan, "scan", qos_profile_sensor_data)
```

You do *not* hard-code the namespace in the node. You set it in the launch file, so the same node code spawns under any namespace. That is the whole point: write the stack once, launch it twice.

### 2.2 Namespacing in launch — `PushRosNamespace`

The clean way to namespace a *whole sub-stack* (robot_state_publisher + the SLAM node + the sensor bridge, all at once) is a `GroupAction` with `PushRosNamespace`:

```python
from launch import LaunchDescription
from launch.actions import GroupAction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description() -> LaunchDescription:
    ns = LaunchConfiguration("namespace")

    robot_group = GroupAction(
        actions=[
            PushRosNamespace(ns),          # everything below runs under <ns>/
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                # frame_prefix makes this robot's TF frames <ns>/base_link etc.
                parameters=[{"frame_prefix": [ns, "/"]}],
            ),
            Node(
                package="slam_toolbox",
                executable="async_slam_toolbox_node",
                # remap so slam_toolbox's /map becomes /<ns>/map
                remappings=[("/map", "map"), ("/scan", "scan")],
            ),
        ]
    )

    return LaunchDescription([
        DeclareLaunchArgument("namespace", default_value="robotA"),
        robot_group,
    ])
```

Now `ros2 launch crunchbot_multi one_robot.launch.py namespace:=robotA` brings up the whole stack under `robotA`, and a second invocation with `namespace:=robotB` brings up an independent copy. One launch file, two robots.

Note the `remappings=[("/map", "map")]` on `slam_toolbox`. Many upstream nodes — `slam_toolbox` is one — publish to an **absolute** `/map` internally. `PushRosNamespace` cannot rewrite an absolute name on its own; you must *remap* the absolute `/map` to the relative `map` so the namespace can then prefix it. This is the single most common reason "I namespaced it but `/map` is still global." Remap the absolutes, then namespace the relatives.

---

## 3. The TF frame-prefix fix (different from namespacing)

Here is the distinction that trips up everyone: **namespacing a node does not rename its TF frames.** A namespace prefixes *topic* names. TF frame names are *data inside* the messages on `/tf` — strings like `base_link` and `odom` in the `frame_id` field — and the namespace machinery never touches message *contents*. So even after you namespace both robots perfectly, both still broadcast a transform whose `child_frame_id` is the literal string `base_link`, and tf2 still sees two `base_link`s fighting.

The fix is a **frame prefix**, applied where the transform is *created*:

- `robot_state_publisher` takes a `frame_prefix` parameter. Set it to `robotA/` and every frame it publishes becomes `robotA/base_link`, `robotA/laser_link`, etc.
- Your odometry node (week 6) must prefix the frames it stamps: publish `header.frame_id = "robotA/odom"` and `child_frame_id = "robotA/base_link"`, not the bare names.
- `slam_toolbox` takes `map_frame`, `odom_frame`, and `base_frame` parameters. Set them to `robotA/map`, `robotA/odom`, `robotA/base_link`.

After this, robot A's tf tree is `robotA/map -> robotA/odom -> robotA/base_link -> robotA/laser_link`, and robot B's is the parallel `robotB/...`. Two clean, non-overlapping trees in one buffer.

> **Why ROS2 doesn't have a global `tf_prefix` like ROS1.** ROS1 had a `tf_prefix` parameter that the TF library read globally. It was removed in ROS2 deliberately, because a global frame rewrite is too blunt — it can't express "prefix these frames but leave `world` shared." In ROS2 you prefix frames *at the broadcaster*, which is more typing but lets you keep `world` un-prefixed (shared by both robots) while prefixing everything below each robot's `map`. That shared, un-prefixed `world` is exactly what §6 needs.

### 3.1 A worked frame prefix in an odometry broadcaster

```python
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster


class OdomBroadcaster(Node):
    def __init__(self, frame_prefix: str) -> None:
        super().__init__("odom_broadcaster")
        self.prefix = frame_prefix          # e.g. "robotA/"
        self.tf = TransformBroadcaster(self)

    def publish_odom_tf(self, x: float, y: float, yaw_quat) -> None:
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        # Prefix BOTH frames so this robot's tree doesn't collide with the other's.
        t.header.frame_id = f"{self.prefix}odom"
        t.child_frame_id = f"{self.prefix}base_link"
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.rotation = yaw_quat
        self.tf.sendTransform(t)
```

The `frame_prefix` is passed in (from a launch parameter), never hard-coded, for the same reason the namespace is: write once, run per-robot.

---

## 4. Discovery: should the two robots even see each other?

Topics and frames sorted, the third axis is **discovery**: do robot A's nodes and robot B's nodes discover each other at the DDS layer at all? This is a *deliberate* decision, not a default to accept.

Recall week 5: every DDS participant lives in a **domain** (`ROS_DOMAIN_ID`, default 0), and participants only discover participants in the same domain. That gives you the coarse knob:

- **Same domain** — robot A's nodes and robot B's nodes discover each other. Robot A *can* subscribe to `/robotB/scan`. This is what you want this week, because the merger node must see both robots' maps.
- **Different domains** — total isolation. Two robots on one LAN that should never interact get `ROS_DOMAIN_ID=1` and `ROS_DOMAIN_ID=2`; discovery never introduces them. This is how you run two *independent* fleets, or your dev robot next to the production robot, on one network without cross-talk.

For shared mapping, the two robots and the merger **must share a domain.** They have to discover each other for the merger to consume both maps. So this week everything runs on one `ROS_DOMAIN_ID`.

### 4.1 The localhost knob and the multi-machine reality

`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` (the Jazzy replacement for `ROS_LOCALHOST_ONLY`) restricts discovery to the local machine. For this week's sim, both robots run on your one laptop, so localhost-only is fine and keeps your experiments off the lab network:

```bash
export ROS_DOMAIN_ID=7
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST   # both robots on this laptop
```

In the *real* multi-robot world — two physical robots, each its own computer — they're on different machines on a shared Wi-Fi, and discovery must cross the network. That's where week 5's multicast-filtering pain returns at fleet scale: a Wi-Fi AP that drops multicast means SPDP never completes and the robots never discover each other. The fix is the same as week 5 — a discovery server or unicast peer lists — and it's the standard pattern for any real fleet. We stay on one laptop this week so discovery "just works," but know that the moment you go to hardware, discovery becomes the first thing that breaks.

### 4.2 Partitions: sharing a domain but not all topics

Sometimes you want robots in the *same* domain (so a fleet manager can see all of them) but you don't want robot A flooding robot B with its 30 Hz LiDAR. The DDS-level answer is **partitions** — a sub-domain isolation inside a domain. In practice, ROS2 robotics achieves the same effect more simply with **namespaces plus selective subscription**: every robot publishes everything under its namespace, and each consumer subscribes only to the specific namespaced topics it needs. The merger subscribes to `/robotA/map` and `/robotB/map` and nothing else; it never touches the LiDAR streams. Namespacing isn't just collision-avoidance — it's also your selective-attention mechanism. You'll lean on this hard in week 36 when a fleet manager watches a dozen robots' heartbeats but none of their raw sensors.

---

## 5. Why two robots have two `map` frames

Here is the conceptual heart of the week. Run `slam_toolbox` on robot A and it defines a frame called `map` whose origin is *where robot A was when it took its first scan*. Run a second `slam_toolbox` on robot B and it defines *its* `map` frame whose origin is *where robot B was when it took its first scan*. These are two different physical points in the world, and SLAM has no idea the other robot exists. **Robot A's `map` and robot B's `map` are two unrelated coordinate frames that happen to share a name.**

This is why §3's frame prefix matters so much: after prefixing, you have `robotA/map` and `robotB/map`, two distinct frames, honestly named. If you had *not* prefixed, both would be `map`, and tf2 would think they were the same frame — silently gluing robot B's coordinate system onto robot A's origin, so robot B's walls would appear shifted by the (unknown) offset between where the two robots started. The merged map would be nonsense and you wouldn't know why.

So: two robots, two prefixed `map` frames, no relationship between them yet. The entire problem of shared mapping reduces to one question:

> **What is the transform from `robotA/map` to `robotB/map`?**

Answer that, and you can express both robots' maps in one common frame and merge them. Get it wrong, and you double-wall the world (Lecture 2, §3). The rest of the week is about producing that transform — by assuming it (robots start at known offsets, our simplification), or by estimating it (a shared landmark, an inter-robot loop closure, what real distributed SLAM does).

---

## 6. The shared `world` frame

You don't merge `robotB/map` *into* `robotA/map` directly — that would privilege robot A's origin arbitrarily. Instead you introduce a third, neutral frame, conventionally `world`, and tie both robots' maps into it:

```
            world                         (the shared, un-prefixed root)
           /     \
  world->robotA/map    world->robotB/map  (the inter-robot transforms)
         |                   |
  robotA/map           robotB/map         (each robot's SLAM origin)
         |                   |
  robotA/odom          robotB/odom        (each robot's odometry)
         |                   |
  robotA/base_link     robotB/base_link   (each robot's body)
```

The two transforms `world -> robotA/map` and `world -> robotB/map` are what you publish (Lecture 2, §2). With them in the tf tree, *any* node can ask tf2 for `world -> robotB/base_link` and get robot B's pose in the shared frame — which is exactly the "both maps, one frame" promise from the README. The merged occupancy grid lives in `world`. rviz2's Fixed Frame is set to `world`. Both robots' footprints appear inside one grid, in one frame, because you tied them together with two transforms.

If you set up the robots at known starting offsets — say robot A at the origin and robot B two meters to its left, facing the same way — then `world -> robotA/map` is identity and `world -> robotB/map` is a pure 2 m translation. That's the simplification we use this week: *known* relative poses, so the transform is a static broadcast you write by hand. Estimating it is the stretch goal and the subject of real distributed SLAM.

---

## 7. A complete two-robot launch sketch

Putting §2–§6 together, the two-robot bring-up is one launch file that instantiates the per-robot group twice and adds the two `world -> robot/map` static transforms:

```python
from launch import LaunchDescription
from launch.actions import GroupAction
from launch_ros.actions import Node, PushRosNamespace


def robot(ns: str, x: float, y: float):
    """One namespaced, frame-prefixed robot stack."""
    return GroupAction([
        PushRosNamespace(ns),
        Node(
            package="robot_state_publisher", executable="robot_state_publisher",
            parameters=[{"frame_prefix": f"{ns}/"}],
        ),
        Node(
            package="slam_toolbox", executable="async_slam_toolbox_node",
            parameters=[{
                "map_frame": f"{ns}/map",
                "odom_frame": f"{ns}/odom",
                "base_frame": f"{ns}/base_link",
                "scan_topic": f"/{ns}/scan",
            }],
            remappings=[("/map", "map")],
        ),
    ])


def world_to_map(ns: str, x: float, y: float):
    """Static transform tying this robot's map into the shared world frame.
    Known starting offset (our week-35 simplification): a pure translation."""
    return Node(
        package="tf2_ros", executable="static_transform_publisher",
        arguments=[str(x), str(y), "0", "0", "0", "0", "world", f"{ns}/map"],
    )


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        robot("robotA", 0.0, 0.0),
        robot("robotB", 0.0, 2.0),
        world_to_map("robotA", 0.0, 0.0),   # A's map origin == world origin
        world_to_map("robotB", 0.0, 2.0),   # B started 2 m along world +y
    ])
```

This is the spine of Exercise 1 and the mini-project. Two robots, two clean prefixed trees, both tied into `world`, one launch file.

---

## 7.5 Namespacing services, actions, and parameters too

Topics are the loud part, but a robot stack also exposes **services**, **actions**, and **parameters**, and all three are namespaced by the same rules — which matters the moment you want to command one specific robot.

- **Services and actions** are relative names just like topics. Robot A's `Spin90Degrees` action (week 4) becomes `/robotA/spin90`; a fleet manager that wants to spin robot A calls the action server at `/robotA/spin90`, and robot B at `/robotB/spin90`. The namespace is your *addressing scheme*: it's how week 36's task allocator says "robot A, go here" without robot B reacting. If you'd hard-coded `/spin90` (absolute), both robots would spin on one command — a genuinely dangerous bug in a shared space.
- **Parameters** are per-node, and the node is namespaced, so `/robotA/slam_toolbox` and `/robotB/slam_toolbox` hold *independent* parameter sets. You can retune robot A's SLAM resolution without touching robot B. A parameter YAML for a namespaced launch must therefore key parameters under the namespaced node name (`/robotA/slam_toolbox: { resolution: 0.05 }`), not the bare node name, or the param simply doesn't bind and you spend an hour wondering why your setting was ignored.

The throughline: **namespacing is not just collision-avoidance, it's the addressing layer of the whole fleet.** Every per-robot command, query, and config flows through the namespace. Get it clean now and week 36's fleet manager is a joy; get it sloppy and every "command the wrong robot" bug traces back to a missing prefix.

```bash
# Address one specific robot's action / service / params by namespace:
ros2 action send_goal /robotA/spin90 crunch_interfaces/action/Spin90 "{}"
ros2 param get /robotB/slam_toolbox resolution
ros2 service call /robotA/clear_map std_srvs/srv/Empty "{}"
```

---

## 7.6 One `/tf`, two robots: the shared tree and shared time

Notice what we did *not* namespace: `/tf` and `/tf_static`. Both robots broadcast into the *same* global `/tf` topic, and that is correct and deliberate. tf2 is a *single distributed buffer*: every transform any node broadcasts goes onto the one `/tf` topic, and every listener assembles them into one tree. That single shared tree is precisely what lets a node ask for `world -> robotB/base_link` and have tf2 chain `world -> robotB/map -> robotB/odom -> robotB/base_link` even though those transforms were broadcast by three different nodes across two robots. If you *had* namespaced `/tf` to `/robotA/tf` and `/robotB/tf`, you'd have two disconnected buffers and no node could ever resolve a cross-robot transform — the shared `world` frame would be impossible. **The frame names are prefixed; the `/tf` topic is not.** That asymmetry is the whole trick.

This shared buffer carries a consequence that bites in the real multi-machine world: **time.** tf2 transforms are stamped, and a lookup at time *t* interpolates the tree at *t*. If robot A's clock and robot B's clock disagree by 200 ms — trivially possible on two computers whose NTP drifts — then a transform robot B stamped "now" looks 200 ms stale (or 200 ms in the future) to robot A, and tf2 either extrapolates (and lies) or throws `ExtrapolationException`. In sim on one laptop everyone shares one clock (`use_sim_time`), so this is invisible; on hardware, **fleet-wide time synchronization (PTP or chrony/NTP) is a prerequisite, not a nicety.** A fleet whose clocks drift produces transforms that are individually correct and collectively inconsistent — the subtlest multi-robot bug there is, and one more thing the laptop never makes you confront. Put it on the hardware list next to multicast, latency, and bandwidth.

---

## 7.7 The remapping vs. namespacing decision, made explicit

Engineers conflate **remapping** and **namespacing** constantly, so here is the clean distinction with a rule for each.

- **Namespacing** prefixes *all* of a node's relative names at once. It's a blunt, total instrument: "everything this node touches lives under `robotA/`." You apply it with `PushRosNamespace` or `Node(namespace=...)`.
- **Remapping** rewrites *one specific* name to another. It's a scalpel: "this node calls it `/map`, but route that to `map`." You apply it with `remappings=[("/map", "map")]`.

The rule that resolves 90% of multi-robot launch confusion:

> **Use namespacing to separate the two robots. Use remapping to fix individual nodes that hard-coded an absolute name you can't change** (because they're upstream packages — `slam_toolbox`, a sensor driver — and you won't fork them to fix one string).

So a typical per-robot group does *both*: `PushRosNamespace("robotA")` to put everything under `robotA/`, plus `remappings=[("/map", "map")]` on `slam_toolbox` specifically, because that one node insists on absolute `/map` and remapping is the only way to drag it back under the namespace. If you find yourself remapping *every* topic of a node, you wanted a namespace; if you find yourself namespacing to fix *one* topic, you wanted a remap. Reaching for the wrong tool is how a launch file becomes forty lines of remappings that a namespace would have done in one.

There's a third, finer tool you'll meet in week 36 — the **launch substitution** (`LaunchConfiguration`, `TextSubstitution`) that lets the *value* `robotA` flow into both the namespace and the frame prefix from a single argument, so you declare the robot's identity once and it propagates everywhere. The `robot(ns, x, y)` function in §7 is exactly that pattern: one `ns` argument drives the namespace, the frame prefix, the SLAM frame params, and the static transform, so there is one place to change a robot's name and zero chance of the namespace and the frame prefix drifting out of sync. Single source of truth, multi-robot edition.

---

## 8. Recap

You should now be able to:

- Name the three collisions — topics, TF frames, node names — and the distinct fix for each (namespace, frame prefix, namespace again for the node name).
- Explain why a leading-slash topic name defeats namespacing, and why upstream nodes that publish absolute `/map` must be *remapped* before they can be namespaced.
- State why namespacing a node does *not* rename its TF frames, and apply a `frame_prefix` at the broadcaster instead.
- Decide deliberately whether two robots share a `ROS_DOMAIN_ID` (coordinate) or not (isolate), and know that real multi-machine fleets re-hit week 5's multicast pain.
- Explain why two `slam_toolbox` robots have two unrelated `map` frames, and reduce shared mapping to "what is the transform between them?"
- Introduce a shared `world` frame, tie both robots' maps into it with two transforms, and verify with `tf2_echo world robotB/base_link`.
- Distinguish namespacing from remapping, and use a single launch argument to drive a robot's namespace, frame prefix, and SLAM frames in lockstep.
- Name the four things that are free in single-laptop sim and expensive on real hardware — multicast discovery, latency, bandwidth, and clock synchronization — so none of them surprises you on integration day.

The mental model to carry into Lecture 2: you now have two robots that are *cleanly separated* (namespaces, frame prefixes) yet *addressable as a fleet* (one `world`, one `/tf`, namespaced services). That is exactly the substrate a shared map and, next week, a task allocator need. Separation without addressability is two robots that can't cooperate; addressability without separation is two robots that collide. You built both.

Next: how to actually merge the two grids, publish the inter-robot transform, keep coordination off the critical path, and where real distributed SLAM goes from here. Continue to [Lecture 2 — Shared Mapping, Merging, and Coordination](./02-shared-mapping-merging-and-coordination.md).

---

## References

- *Using ROS2 launch for large projects* (namespaces, groups) — ROS2 docs: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-ROS2-Launch-For-Large-Projects.html>
- *About discovery* (`ROS_DOMAIN_ID`, discovery range) — ROS2 docs: <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Discovery.html>
- *`slam_toolbox`* (per-robot frames and params): <https://github.com/SteveMacenski/slam_toolbox>
- *`tf2_ros` static transform broadcaster* — ROS2 docs: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html>
- *`nav_msgs/OccupancyGrid`* (the frame the merged map lives in): <https://docs.ros.org/en/jazzy/p/nav_msgs/interfaces/msg/OccupancyGrid.html>
- *Kimera-Multi* (why estimating the inter-robot transform is the hard part): <https://arxiv.org/abs/2106.14386>

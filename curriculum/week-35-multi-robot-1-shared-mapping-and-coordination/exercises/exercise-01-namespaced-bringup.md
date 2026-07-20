# Exercise 1 — Namespaced Two-Robot Bring-Up

**Goal:** Bring up two copies of your week-8 robot from one launch file under `robotA` and `robotB` namespaces, and *prove* — not assume — that the two stacks share no topic names, no TF frames, and no node names, and that both robots resolve into a single shared `world` frame. You will train the core multi-robot diagnostic habit: reading `ros2 topic list`, `view_frames`, and `tf2_echo` to confirm two robots are genuinely independent yet tied to a common frame.

**Estimated time:** 50 minutes. Guided.

---

## Setup

You need your **week-8 `crunchbot_bringup`** robot launchable in Gz Sim, plus `slam_toolbox` installed. Verify a single robot still works:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch crunchbot_bringup robot.launch.py
ros2 topic list | grep -E "scan|map"
# /map
# /scan
```

If the single robot doesn't spawn, fix that first — every step below launches two of it.

**Fallback if your sim is heavy.** You don't need full SLAM running to learn the namespacing. You can substitute the `robot_state_publisher` + a fake scan publisher per robot. The namespacing and frame-prefix lessons are identical; only the map is missing, which you supply in Exercise 2.

---

## Step 1 — Write the per-robot group

Create `launch/two_robots.launch.py` in a `crunchbot_multi` package (you'll grow this into the mini-project). The spine is from Lecture 1 §7 — a function that builds one namespaced, frame-prefixed robot, called twice:

```python
from launch import LaunchDescription
from launch.actions import GroupAction
from launch_ros.actions import Node, PushRosNamespace


def robot(ns: str, x: float, y: float):
    return GroupAction([
        PushRosNamespace(ns),
        Node(
            package="robot_state_publisher", executable="robot_state_publisher",
            parameters=[{"frame_prefix": f"{ns}/"}],
            # ... your URDF on robot_description as usual ...
        ),
        # TODO 1: add your sensor bringup / Gz spawn for this robot here,
        #         making sure every topic name is RELATIVE (no leading slash).
        Node(
            package="slam_toolbox", executable="async_slam_toolbox_node",
            parameters=[{
                "map_frame": f"{ns}/map",
                "odom_frame": f"{ns}/odom",
                "base_frame": f"{ns}/base_link",
                "scan_topic": f"/{ns}/scan",
            }],
            remappings=[("/map", "map")],   # absolute /map -> relative, so ns prefixes it
        ),
    ])


def world_to_map(ns: str, x: float, y: float):
    return Node(
        package="tf2_ros", executable="static_transform_publisher",
        arguments=[str(x), str(y), "0", "0", "0", "0", "world", f"{ns}/map"],
    )


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        robot("robotA", 0.0, 0.0),
        robot("robotB", 0.0, 2.0),
        world_to_map("robotA", 0.0, 0.0),
        world_to_map("robotB", 0.0, 2.0),
    ])
```

Fill in `TODO 1` with however your week-8 bring-up spawns the robot and its sensors in Gz Sim — the key constraint is that **every topic name must be relative**.

---

## Step 2 — Launch both robots

```bash
ros2 launch crunchbot_multi two_robots.launch.py
```

Two robots come up. Now prove they're independent.

---

## Step 3 — Prove the topics are namespaced (no collision)

```bash
ros2 topic list
```

You should see paired, prefixed topics — and crucially, **no bare `/scan` or `/map`**:

```
/robotA/scan
/robotA/map
/robotA/odom
/robotB/scan
/robotB/map
/robotB/odom
/tf
/tf_static
```

`/tf` and `/tf_static` are *shared* by design — that's the one global tree both robots broadcast into. Everything robot-specific is prefixed.

> **If you see a bare `/scan` or `/map`:** you have a leading-slash topic name somewhere (Lecture 1 §2), or an upstream node publishing absolute `/map` that you forgot to remap. Find it: `ros2 node info /robotA/<node>` lists each node's topics with their resolved names.

---

## Step 4 — Prove the TF frames are prefixed (no collision)

Dump the whole tree:

```bash
ros2 run tf2_tools view_frames
# produces frames.pdf in the current directory
```

Open `frames.pdf`. You want **two parallel sub-trees** hanging off a single `world`:

```
world
├── robotA/map → robotA/odom → robotA/base_link → robotA/laser_link
└── robotB/map → robotB/odom → robotB/base_link → robotB/laser_link
```

If instead you see **one** `base_link` with two parents, or a frame named just `map`, your frame prefix didn't take (Lecture 1 §3) — check `frame_prefix` on `robot_state_publisher` and the `*_frame` params on `slam_toolbox`.

---

## Step 5 — Prove both robots resolve into the shared `world` frame

This is the **"both maps, one frame" promise** from the README. Ask tf2 for each robot's body in the shared frame:

```bash
ros2 run tf2_ros tf2_echo world robotA/base_link
ros2 run tf2_ros tf2_echo world robotB/base_link
```

Both must resolve (no `LookupException`). Robot A sits near the world origin; robot B sits ~2 m along `+y`, matching the static transform you set:

```
$ ros2 run tf2_ros tf2_echo world robotB/base_link
At time ...
- Translation: [0.00, 2.00, 0.00]
- Rotation: in Quaternion [0.00, 0.00, 0.00, 1.00]
```

If `tf2_echo world robotB/base_link` throws `LookupException`, your `world -> robotB/map` static transform isn't reaching the listener. Remember `/tf_static` is `TRANSIENT_LOCAL` — confirm with `ros2 topic info /tf_static -v` that the publisher offers `TRANSIENT_LOCAL`, or a late `tf2_echo` will never see it.

---

## Step 6 — Confirm no node-name collision

```bash
ros2 node list
```

Every node must be uniquely named under its namespace — `/robotA/robot_state_publisher` and `/robotB/robot_state_publisher`, never two bare `/robot_state_publisher`. If you see a duplicate-name warning at launch, `PushRosNamespace` didn't wrap that node (it's outside the `GroupAction`).

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `ros2 topic list` shows `/robotA/*` and `/robotB/*` topics with **no bare** `/scan`, `/map`, or `/odom`.
- [ ] `view_frames` shows two parallel sub-trees under a single `world` frame, with prefixed frame names.
- [ ] `ros2 run tf2_ros tf2_echo world robotA/base_link` and `... world robotB/base_link` both resolve, with robot B offset ~2 m from robot A.
- [ ] `ros2 node list` shows uniquely-namespaced node names, no duplicates.
- [ ] You can state, in one sentence, the difference between what `PushRosNamespace` fixed (topic/node names) and what `frame_prefix` fixed (TF frame names).

---

## Stretch

- Launch the *same* file twice with `ROS_DOMAIN_ID=1` and `ROS_DOMAIN_ID=2` (four robots, two fleets). Confirm `ros2 topic list` in a domain-1 terminal shows only the domain-1 robots — the discovery isolation knob from Lecture 1 §4.
- Add `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` and confirm with `ros2 doctor --report` that announcements stay local.
- Bring up a *third* robot (`robotC`) by adding two lines. Note how cheap adding a robot is once the namespacing is clean — that's the payoff of writing the stack once.

---

When this feels comfortable, move to [Exercise 2 — Merge two grids](exercise-02-merge-two-grids.py).

# Exercise 1 — Wire the Foxglove Telemetry Dashboard

**Goal:** Stand up the `foxglove_bridge`, build a dashboard layout, and stream the four required telemetry channels — live **pose**, the Nav2 **costmap**, the policy's chosen **action**, and the latched **safety-filter** banner. By the end, an operator who is not you can watch your capstone robot and see the safety filter override the policy in real time.

**Estimated time:** 60 minutes.

---

## Setup

You need ROS2 Jazzy sourced, your capstone workspace building, and Foxglove (desktop or web) installed. Install the bridge:

```bash
sudo apt install ros-jazzy-foxglove-bridge
```

Confirm your capstone publishes the prerequisites. With the robot (or sim) running:

```bash
ros2 topic list | grep -E "amcl_pose|costmap|policy"
```

You should see at least `/amcl_pose` (or `/localization/pose`), `/global_costmap/costmap`, and `/policy/action`. If any are missing, fix that before continuing — there is nothing to visualize otherwise. (Pose comes from your Week 7/Week 32 localization; the costmap from your Week 18 Nav2 stack; the policy action from Week 32.)

---

## Step 1 — Launch the bridge and connect

```bash
ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=8765
```

In Foxglove: **Open connection → Foxglove WebSocket → `ws://localhost:8765`** (or `ws://robot.local:8765` if Foxglove runs on a different machine). The left sidebar should now list every topic the robot publishes. If the connection refuses, check the port is open and the bridge logged `Server listening on port 8765`.

---

## Step 2 — The 3D panel: pose + costmap

Add a **3D panel**. In its settings:

- Set **Fixed frame** to `map`.
- Add the topic `/global_costmap/costmap` — it renders as a colored occupancy layer.
- Add `/amcl_pose` — it renders as a coordinate frame showing where the robot thinks it is.
- Add your TF tree (`/tf`, `/tf_static`) so the robot model and frames place correctly.

The costmap is published with **transient-local** durability, so even though you connected after it was first published, the last map appears immediately. If it does *not* appear, that is your first debugging lesson: confirm the QoS with `ros2 topic info /global_costmap/costmap --verbose` and look for `Durability: TRANSIENT_LOCAL`.

---

## Step 3 — Render the policy's chosen action

The policy decides an action each cycle but does not yet *show* it. Write the adapter node below at `capstone_ops/capstone_ops/action_marker_node.py`. This is the **starter**, with the marker construction left for you:

```python
#!/usr/bin/env python3
"""STARTER — render the policy's chosen action as a Marker."""
import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node
from visualization_msgs.msg import Marker

from capstone_msgs.msg import PolicyAction


class ActionMarkerNode(Node):
    def __init__(self) -> None:
        super().__init__("action_marker")
        self._pub = self.create_publisher(Marker, "/policy/action_marker", 10)
        self._safety_override = False
        self.create_subscription(PolicyAction, "/policy/action", self._on_action, 10)
        # TODO: subscribe to /safety/trigger (latched) to know when to recolor.

    def _on_action(self, action: PolicyAction) -> None:
        m = Marker()
        # TODO: fill in header (frame_id="base_link", stamp=now),
        # type=ARROW, two points (origin -> commanded direction),
        # scale, and color (green normally, red when overriding).
        self._pub.publish(m)


def main() -> None:
    rclpy.init()
    rclpy.spin(ActionMarkerNode())
    rclpy.shutdown()
```

The **solution**:

```python
#!/usr/bin/env python3
"""SOLUTION — render the policy's chosen action as a Marker, recolored on override."""
import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from visualization_msgs.msg import Marker

from capstone_msgs.msg import PolicyAction, SafetyTrigger


class ActionMarkerNode(Node):
    def __init__(self) -> None:
        super().__init__("action_marker")
        self._pub = self.create_publisher(Marker, "/policy/action_marker", 10)
        self._safety_override = False

        self.create_subscription(PolicyAction, "/policy/action", self._on_action, 10)

        latched = QoSProfile(depth=1)
        latched.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(
            SafetyTrigger, "/safety/trigger", self._on_safety, latched
        )

    def _on_safety(self, msg: SafetyTrigger) -> None:
        self._safety_override = msg.active

    def _on_action(self, action: PolicyAction) -> None:
        m = Marker()
        m.header.frame_id = "base_link"
        m.header.stamp = self.get_clock().now().to_msg()
        m.ns = "policy"
        m.id = 0
        m.type = Marker.ARROW
        m.action = Marker.ADD
        m.points = [
            Point(x=0.0, y=0.0, z=0.1),
            Point(x=float(action.linear_x), y=float(action.linear_y), z=0.1),
        ]
        m.scale.x = 0.05
        m.scale.y = 0.10
        m.scale.z = 0.0
        if self._safety_override:
            m.color.r, m.color.g, m.color.b, m.color.a = 0.9, 0.1, 0.1, 0.9
        else:
            m.color.r, m.color.g, m.color.b, m.color.a = 0.1, 0.9, 0.2, 0.9
        self._pub.publish(m)


def main() -> None:
    rclpy.init()
    rclpy.spin(ActionMarkerNode())
    rclpy.shutdown()
```

Run it, then add `/policy/action_marker` to the 3D panel. You should see a green arrow on the robot swinging as the policy reasons.

---

## Step 4 — The latched safety banner

The safety filter must publish `/safety/trigger` (latched), per Lecture 1 §4.3. If your filter does not yet, add this where it makes its override decision:

```python
from rclpy.qos import DurabilityPolicy, QoSProfile
from capstone_msgs.msg import SafetyTrigger

latched = QoSProfile(depth=1)
latched.durability = DurabilityPolicy.TRANSIENT_LOCAL
self._safety_pub = self.create_publisher(SafetyTrigger, "/safety/trigger", latched)

def fire_safety(self, reason: str, severity: float) -> None:
    msg = SafetyTrigger()
    msg.active = True
    msg.reason = reason
    msg.severity = float(severity)
    msg.stamp = self.get_clock().now().to_msg()
    self._safety_pub.publish(msg)

def clear_safety(self) -> None:
    msg = SafetyTrigger()
    msg.active = False
    msg.stamp = self.get_clock().now().to_msg()
    self._safety_pub.publish(msg)
```

In Foxglove, add an **Indicator panel** bound to `/safety/trigger`. Configure the rule: when `active == true`, show **red** with the label from `reason`; when `false`, show **green / NOMINAL**. Place it across the top of the layout where the operator's eye lands first.

---

## Step 5 — See the override happen

Drive the robot (or place a sim obstacle) so the safety filter fires. Watch two things change *together*:

1. The safety banner flips red and reads `obstacle_proximity` (or whatever your reason is).
2. The policy-action arrow turns red — the recolor from Step 3 — showing the operator that the *policy's* command is being overridden, not just that something is wrong somewhere.

Clear the obstacle. Both return to green. That coupled behavior — the banner and the arrow agreeing — is what makes the dashboard *legible* to someone who is not you.

---

## Step 6 — Export the layout

`⋯ → Export layout` and save the JSON to your capstone repo at `dashboard/capstone_layout.json`. Commit it. Anyone who clones the repo and connects to the bridge gets your exact operator view.

---

## Expected output

With everything running, your 3D panel shows the costmap, the robot pose, and a live policy-action arrow; your Indicator shows the safety state. Triggering the filter produces:

```
# terminal: the safety filter logs the trigger
[safety_filter]: override engaged: obstacle_proximity (severity 0.82)
# Foxglove: banner -> RED "obstacle_proximity", action arrow -> RED
```

And clearing it:

```
[safety_filter]: override cleared
# Foxglove: banner -> GREEN "NOMINAL", action arrow -> GREEN
```

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `foxglove_bridge` is running and Foxglove is connected over WebSocket.
- [ ] The 3D panel streams live **pose** and the Nav2 **costmap** in the `map` frame.
- [ ] The **policy action** renders as an arrow that swings with the policy's decisions.
- [ ] The **safety banner** (Indicator panel) is latched, flips red on override with the reason, and green on clear.
- [ ] The policy-action arrow **recolors red** when the safety filter overrides, in lockstep with the banner.
- [ ] You exported `dashboard/capstone_layout.json` and committed it.

---

## Stretch

- Add a **Plot panel** of `/perf/cycle_latency` so the operator sees the latency trend, not just the current value.
- Add a **Raw Messages** panel on `/safety/trigger` so the operator can read the full struct, including `severity`, during an incident.
- Record a 30-second **MCAP** of an override happening and confirm it replays — every panel rewinds together when you scrub.

---

## Hints

<details>
<summary>The costmap does not appear in the 3D panel</summary>

It is almost always QoS. `nav_msgs/OccupancyGrid` from Nav2 is published transient-local. Foxglove must subscribe with compatible durability — recent `foxglove_bridge` does this automatically, but confirm with `ros2 topic info /global_costmap/costmap --verbose`. If you still see nothing, set the 3D panel's fixed frame to `map` (not `odom` or `base_link`); a wrong fixed frame silently hides the map.

</details>

<details>
<summary>The action arrow points the wrong way</summary>

`PolicyAction.linear_x` / `linear_y` are in the `base_link` frame, so the marker's `frame_id` must be `base_link` and Foxglove must have the TF tree to place it on the map. If the arrow is on the map but rotated, your policy publishes body-frame velocities and Foxglove is applying the base→map transform — that is correct; the arrow *should* rotate with the robot.

</details>

<details>
<summary>The banner does not update when a late subscriber connects</summary>

The publisher must be transient-local *and* depth 1. If you used the default QoS, only subscribers present at publish time see the event; a Foxglove instance that connects afterward sees nothing until the next trigger. Re-create the publisher with the latched profile shown in Step 4.

</details>

---

When the override is visible end-to-end, move to [Exercise 2 — Add the CPU/GPU load panel](./exercise-02-cpu-gpu-load-panel.py).

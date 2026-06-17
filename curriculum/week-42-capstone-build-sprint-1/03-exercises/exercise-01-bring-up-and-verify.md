# Exercise 1 — Bring Up and Verify (Path A)

**Goal:** Bring a real robot up from cold metal to a fully verified state — every sensor publishing at its rated rate with sane values, every actuator responding with the correct sign, and the TF tree fully connected — and capture the whole thing as a single scripted gate you can re-run after every power cycle.

**Estimated time:** 75 minutes.

**Path:** A (hardware). If you are on Path B, read this for context and do Exercise 3.

---

## Why this exercise exists

The temptation on integration day is to launch the whole stack, open RViz, and "see if it works." That tells you almost nothing when it does not. This exercise builds the discipline from Lecture 2 §A: bring the robot up one layer at a time, and confirm each layer reports correctly before trusting the layer above it. The deliverable is a script that exits `0` only when the robot is genuinely ready — a gate you will lean on for the rest of the course.

---

## Setup

You need:

- A powered, E-stop-verified robot on a solid surface with room to make a small motion.
- ROS2 Jazzy sourced, your robot's bringup package built.
- A workspace where you can `colcon build` a small package.

Confirm the basics by hand first:

```bash
source /opt/ros/jazzy/setup.bash
source ~/capstone_ws/install/setup.bash
ros2 topic list
```

You should see your sensor and command topics. If you do not, your drivers are not up — fix that before continuing.

---

## Step 1 — Verify safety before anything moves

With your hand near the E-stop:

```bash
# Confirm the motor bus is enabled, then press the physical E-stop.
# Confirm the bus de-energizes. Release. Confirm it does NOT auto-re-enable.
ros2 topic echo --once /diagnostics 2>/dev/null || echo "no diagnostics yet (fine)"
```

Do not proceed until the physical E-stop demonstrably cuts motor power and requires an explicit re-enable. This is non-negotiable and your draft safety case requires it.

---

## Step 2 — Confirm `use_sim_time` is false everywhere

A single node left on sim time will read a `/clock` that nobody publishes and silently corrupt your fusion.

```bash
for node in $(ros2 node list); do
  echo -n "$node use_sim_time="
  ros2 param get "$node" use_sim_time 2>/dev/null || echo "(no param)"
done
```

Every node that has the parameter must report `false`. If any reports `true`, fix its launch file before continuing.

---

## Step 3 — Write the bring-up gate

Create a package and drop in the gate. The starter below is missing three checks marked `TODO`; fill them in.

```bash
cd ~/capstone_ws/src
ros2 pkg create --build-type ament_python capstone_bringup_check \
  --dependencies rclpy sensor_msgs nav_msgs geometry_msgs tf2_ros
```

Put this in `capstone_bringup_check/capstone_bringup_check/gate.py`:

```python
#!/usr/bin/env python3
"""gate.py - bring-up gate. Exits 0 only if all sensors + TF + actuator pass.

Usage:
    ros2 run capstone_bringup_check gate
"""
import sys
import math
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from sensor_msgs.msg import Imu, LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from tf2_ros import Buffer, TransformListener, LookupException

# (topic, msg type, min Hz over the window)
REQUIRED = [
    ("/imu/data", Imu, 100.0),
    ("/scan", LaserScan, 8.0),
    ("/odom", Odometry, 20.0),
]
WINDOW_S = 3.0


class Gate(Node):
    def __init__(self):
        super().__init__("bringup_gate")
        self.counts = {t: 0 for t, _, _ in REQUIRED}
        self.last = {t: None for t, _, _ in REQUIRED}
        for topic, msg_type, _ in REQUIRED:
            self.create_subscription(
                msg_type, topic, lambda m, t=topic: self._on(t, m), 50)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

    def _on(self, topic, msg):
        self.counts[topic] += 1
        self.last[topic] = msg

    def check_rates(self) -> bool:
        ok = True
        for topic, _, min_hz in REQUIRED:
            hz = self.counts[topic] / WINDOW_S
            status = "OK " if hz >= min_hz else "LOW"
            if hz < min_hz:
                ok = False
            self.get_logger().info(
                f"[{status}] {topic:12s} {hz:6.1f} Hz (need >= {min_hz})")
        return ok

    def check_imu_sane(self) -> bool:
        imu = self.last["/imu/data"]
        if imu is None:
            self.get_logger().error("no IMU message received")
            return False
        # TODO 1: assert the gravity axis (linear_acceleration.z) is between
        # 8.5 and 11.0 in magnitude when the robot is level and still. Log the
        # value and return False if out of band.
        raise NotImplementedError("fill in TODO 1")

    def check_tf_connected(self) -> bool:
        # TODO 2: use self.tf_buffer.can_transform("odom", "base_link",
        # rclpy.time.Time(), timeout=Duration(seconds=1.0)). Return True if the
        # transform is available, log and return False (catching LookupException)
        # otherwise. This proves the TF tree is connected.
        raise NotImplementedError("fill in TODO 2")

    def check_actuator_sign(self) -> bool:
        """Nudge forward at 0.05 m/s for 1.5 s; confirm odom x increases."""
        odom0 = self.last["/odom"]
        if odom0 is None:
            self.get_logger().error("no odom before actuator test")
            return False
        x0 = odom0.pose.pose.position.x
        cmd = Twist()
        cmd.linear.x = 0.05
        end = self.get_clock().now() + Duration(seconds=1.5)
        while rclpy.ok() and self.get_clock().now() < end:
            self.cmd_pub.publish(cmd)
            rclpy.spin_once(self, timeout_sec=0.05)
        # Stop.
        self.cmd_pub.publish(Twist())
        x1 = self.last["/odom"].pose.pose.position.x
        dx = x1 - x0
        # TODO 3: a forward nudge must increase odom x by at least 0.01 m. If dx
        # is negative the encoder sign is inverted; if ~0 the robot did not move
        # (check enable/E-stop). Log dx and return True only if dx >= 0.01.
        raise NotImplementedError("fill in TODO 3")


def collect_window(node: Gate):
    end = node.get_clock().now() + Duration(seconds=WINDOW_S)
    while rclpy.ok() and node.get_clock().now() < end:
        rclpy.spin_once(node, timeout_sec=0.1)


def main():
    rclpy.init()
    node = Gate()
    node.get_logger().info(f"collecting {WINDOW_S}s of sensor data...")
    collect_window(node)

    results = {
        "rates": node.check_rates(),
        "imu_sane": node.check_imu_sane(),
        "tf_connected": node.check_tf_connected(),
        "actuator_sign": node.check_actuator_sign(),
    }
    ok = all(results.values())
    node.get_logger().info("---- bring-up gate ----")
    for name, passed in results.items():
        node.get_logger().info(f"  {name:16s} {'PASS' if passed else 'FAIL'}")
    node.get_logger().info(
        f"[capstone] bringup_gate={'PASS' if ok else 'FAIL'}")
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

Register the entry point in `setup.py`:

```python
    entry_points={
        "console_scripts": [
            "gate = capstone_bringup_check.gate:main",
        ],
    },
```

---

## Step 2.5 — The solution to the three TODOs

If you get stuck for more than ten minutes, here are the three fills.

**TODO 1 — IMU sanity:**

```python
        g = abs(imu.linear_acceleration.z)
        if not (8.5 < g < 11.0):
            self.get_logger().error(
                f"IMU gravity axis = {g:.2f}; expected ~9.81 when level")
            return False
        self.get_logger().info(f"[OK ] IMU gravity axis = {g:.2f}")
        return True
```

**TODO 2 — TF connectivity:**

```python
        try:
            if self.tf_buffer.can_transform(
                    "odom", "base_link", rclpy.time.Time(),
                    timeout=Duration(seconds=1.0)):
                self.get_logger().info("[OK ] TF odom -> base_link connected")
                return True
            self.get_logger().error("TF odom -> base_link not available")
            return False
        except LookupException as exc:
            self.get_logger().error(f"TF lookup failed: {exc}")
            return False
```

**TODO 3 — actuator sign:**

```python
        self.get_logger().info(f"actuator nudge: dx = {dx:+.3f} m")
        if dx >= 0.01:
            self.get_logger().info("[OK ] forward command increases odom x")
            return True
        if dx <= -0.01:
            self.get_logger().error("encoder/odometry SIGN INVERTED (dx < 0)")
        else:
            self.get_logger().error("robot did not move (check enable/E-stop)")
        return False
```

---

## Step 3 — Build and run

```bash
cd ~/capstone_ws
colcon build --packages-select capstone_bringup_check
source install/setup.bash
ros2 run capstone_bringup_check gate
```

Keep a hand near the E-stop — the gate commands a small forward nudge.

---

## Expected output

```
[bringup_gate]: collecting 3.0s of sensor data...
[bringup_gate]: [OK ] /imu/data    201.3 Hz (need >= 100.0)
[bringup_gate]: [OK ] /scan          9.8 Hz (need >= 8.0)
[bringup_gate]: [OK ] /odom         49.7 Hz (need >= 20.0)
[bringup_gate]: [OK ] IMU gravity axis = 9.79
[bringup_gate]: [OK ] TF odom -> base_link connected
[bringup_gate]: actuator nudge: dx = +0.071 m
[bringup_gate]: [OK ] forward command increases odom x
[bringup_gate]: ---- bring-up gate ----
[bringup_gate]:   rates            PASS
[bringup_gate]:   imu_sane         PASS
[bringup_gate]:   tf_connected     PASS
[bringup_gate]:   actuator_sign    PASS
[bringup_gate]: [capstone] bringup_gate=PASS
```

---

## Acceptance criteria

- [ ] The package builds with `colcon build` cleanly.
- [ ] The gate exits `0` when the robot is healthy and non-zero when any check fails.
- [ ] All three TODOs are implemented; the gate never raises `NotImplementedError`.
- [ ] You ran it, power-cycled the robot, and ran it again — same result.
- [ ] You captured at least one *failing* run too (unplug the LiDAR, watch `/scan` go LOW). A gate that only ever passes is a gate you have not tested.
- [ ] Terminal prints `[capstone] bringup_gate=PASS` with sane numbers.

---

## What you just built

This gate is the precondition for everything else this week. Exercise 2 (the 20-meter drive) assumes it exits 0. You will run it after every power cycle for the rest of the course, and it is the first thing you show in the Week 48 defense when the panel asks "how did you know the robot was actually ready?"

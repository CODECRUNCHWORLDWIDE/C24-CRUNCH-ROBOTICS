#!/usr/bin/env python3
"""Exercise 3 — The telemetry spine.

The Week 40 milestone is not "the robot did a pick-and-place." It is "every
layer of the robot was OBSERVABLE in telemetry while it did a pick-and-place."
This node is the spine that makes that true: it subscribes to one signal per
layer of the stack and republishes a compact, dashboard-friendly view onto
`/telemetry/*`, plus the `/fleet/heartbeat` the capstone spec requires at 1 Hz.

The layers, and the signal each contributes:
  - localization/control : /odometry/filtered  -> /telemetry/pose
  - perception           : /perception/objects -> /telemetry/detections (count + nearest)
  - planning             : /plan                -> /telemetry/path_summary (length, waypoints)
  - policy               : /policy/action       -> /telemetry/policy (last grasp pose, source)
  - safety               : /safety/status       -> /telemetry/safety (estop, clamps, fallbacks)
  - fleet readiness      : (aggregate)          -> /fleet/heartbeat (id, capabilities, health)

A reviewer watching a Foxglove dashboard wired to these topics should be able to
narrate the run without reading a single log line. If a layer is not on this
spine, it is invisible, and an invisible layer cannot be graded or debugged.

--------------------------------------------------------------------------------
RUN
--------------------------------------------------------------------------------
Against the live composed stack:
    source install/setup.bash
    python3 exercise-03-telemetry-spine.py
    # then in Foxglove (via foxglove_bridge) subscribe to /telemetry/* and
    # /fleet/heartbeat, or:
    ros2 topic echo /fleet/heartbeat
    ros2 topic echo /telemetry/safety

Standalone in demo mode (drives synthetic inputs through one happy-path run):
    python3 exercise-03-telemetry-spine.py --demo
    # Watch the heartbeat tick at 1 Hz and the telemetry topics populate as the
    # synthetic run progresses (perception -> plan -> policy -> safety).

--------------------------------------------------------------------------------
EXPECTED OUTPUT (demo)
--------------------------------------------------------------------------------
[telemetry_spine] telemetry spine up; heartbeat at 1.0 Hz
[telemetry_spine] /fleet/heartbeat: id=crunchbot-01 health=OK caps=[navigate,manipulate,vla] uptime=1.0s
[telemetry_spine] /telemetry/detections: 1 object(s); nearest=red_cup @ map(1.82,-0.41,0.74) conf=0.91
[telemetry_spine] /telemetry/policy: source=vla grasp @ base_link(0.41,0.02,0.31) accepted=True
[telemetry_spine] /telemetry/safety: estop=clear clamps=0 fallbacks=0
"""

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                       ReliabilityPolicy)

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path
from std_msgs.msg import Bool, String
from vision_msgs.msg import (BoundingBox3D, Detection3D, Detection3DArray,
                             ObjectHypothesisWithPose)


@dataclass
class SafetyState:
    estop: bool = False
    clamps: int = 0
    fallbacks: int = 0


@dataclass
class SpineState:
    """The latest-known state of each layer, for the heartbeat aggregate."""
    detections: int = 0
    nearest_label: str = ""
    last_plan_len_m: float = 0.0
    last_policy_source: str = ""
    policy_accepted: bool = False
    safety: SafetyState = field(default_factory=SafetyState)
    boot_time: float = field(default_factory=time.monotonic)


# A latched QoS for the heartbeat so a late-joining fleet manager gets the
# last sample immediately.
HEARTBEAT_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class TelemetrySpine(Node):
    def __init__(self) -> None:
        super().__init__("telemetry_spine")
        self._state = SpineState()

        # Inputs: one per layer of the stack.
        self.create_subscription(Odometry, "/odometry/filtered",
                                 self._on_odom, 10)
        self.create_subscription(Detection3DArray, "/perception/objects",
                                 self._on_detections, 10)
        self.create_subscription(Path, "/plan", self._on_plan, 10)
        self.create_subscription(PoseStamped, "/policy/action",
                                 self._on_policy, 10)
        self.create_subscription(Bool, "/policy/accepted",
                                 self._on_policy_accepted, 10)
        self.create_subscription(String, "/safety/status",
                                 self._on_safety, 10)

        # Outputs: the dashboard-friendly spine.
        self._pose_pub = self.create_publisher(PoseStamped, "/telemetry/pose", 10)
        self._det_pub = self.create_publisher(String, "/telemetry/detections", 10)
        self._path_pub = self.create_publisher(String, "/telemetry/path_summary", 10)
        self._policy_pub = self.create_publisher(String, "/telemetry/policy", 10)
        self._safety_pub = self.create_publisher(String, "/telemetry/safety", 10)
        self._heartbeat_pub = self.create_publisher(
            String, "/fleet/heartbeat", HEARTBEAT_QOS)

        self.create_timer(1.0, self._publish_heartbeat)  # 1 Hz, per spec
        self.get_logger().info("telemetry spine up; heartbeat at 1.0 Hz")

    # --- input callbacks: fold each layer into spine state + republish ---

    def _on_odom(self, msg: Odometry) -> None:
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose = msg.pose.pose
        self._pose_pub.publish(pose)

    def _on_detections(self, msg: Detection3DArray) -> None:
        self._state.detections = len(msg.detections)
        nearest_label, nearest_pos, nearest_conf = "", None, 0.0
        best_d = math.inf
        for det in msg.detections:
            p = det.bbox.center.position
            d = math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z)
            label = det.results[0].hypothesis.class_id if det.results else "?"
            conf = det.results[0].hypothesis.score if det.results else 0.0
            if d < best_d:
                best_d, nearest_label, nearest_pos, nearest_conf = (
                    d, label, p, conf)
        self._state.nearest_label = nearest_label
        out = String()
        if nearest_pos is not None:
            out.data = (
                f"{len(msg.detections)} object(s); nearest={nearest_label} "
                f"@ {msg.header.frame_id}({nearest_pos.x:.2f},"
                f"{nearest_pos.y:.2f},{nearest_pos.z:.2f}) "
                f"conf={nearest_conf:.2f}")
        else:
            out.data = "0 object(s)"
        self._det_pub.publish(out)
        self.get_logger().info(f"/telemetry/detections: {out.data}")

    def _on_plan(self, msg: Path) -> None:
        length = 0.0
        for a, b in zip(msg.poses, msg.poses[1:]):
            dx = b.pose.position.x - a.pose.position.x
            dy = b.pose.position.y - a.pose.position.y
            length += math.sqrt(dx * dx + dy * dy)
        self._state.last_plan_len_m = length
        out = String()
        out.data = f"{len(msg.poses)} waypoints, {length:.2f} m"
        self._path_pub.publish(out)

    def _on_policy(self, msg: PoseStamped) -> None:
        self._state.last_policy_source = "vla"
        p = msg.pose.position
        out = String()
        out.data = (
            f"source=vla grasp @ {msg.header.frame_id}"
            f"({p.x:.2f},{p.y:.2f},{p.z:.2f}) "
            f"accepted={self._state.policy_accepted}")
        self._policy_pub.publish(out)
        self.get_logger().info(f"/telemetry/policy: {out.data}")

    def _on_policy_accepted(self, msg: Bool) -> None:
        self._state.policy_accepted = msg.data

    def _on_safety(self, msg: String) -> None:
        # Convention: /safety/status carries a small JSON blob.
        try:
            blob = json.loads(msg.data)
            self._state.safety = SafetyState(
                estop=bool(blob.get("estop", False)),
                clamps=int(blob.get("clamps", 0)),
                fallbacks=int(blob.get("fallbacks", 0)))
        except (json.JSONDecodeError, ValueError, TypeError):
            self.get_logger().warn(f"unparseable /safety/status: {msg.data!r}")
            return
        s = self._state.safety
        out = String()
        out.data = (f"estop={'LATCHED' if s.estop else 'clear'} "
                    f"clamps={s.clamps} fallbacks={s.fallbacks}")
        self._safety_pub.publish(out)
        self.get_logger().info(f"/telemetry/safety: {out.data}")

    # --- the heartbeat: the fleet-readiness aggregate --------------------

    def _publish_heartbeat(self) -> None:
        s = self._state
        uptime = time.monotonic() - s.boot_time
        # Health is OK unless a safety condition is active or a layer is silent.
        health = "OK"
        if s.safety.estop:
            health = "ESTOP"
        elif s.safety.fallbacks > 0:
            health = "DEGRADED"
        beat = {
            "id": "crunchbot-01",
            "capabilities": ["navigate", "manipulate", "vla"],
            "health": health,
            "uptime_s": round(uptime, 1),
            "detections": s.detections,
            "last_policy_source": s.last_policy_source,
            "estop": s.safety.estop,
        }
        msg = String()
        msg.data = json.dumps(beat)
        self._heartbeat_pub.publish(msg)
        self.get_logger().info(
            f"/fleet/heartbeat: id={beat['id']} health={beat['health']} "
            f"caps=[{','.join(beat['capabilities'])}] "
            f"uptime={beat['uptime_s']}s")


# ----------------------------------------------------------------------------
# Demo harness: drive synthetic inputs through one happy-path run so the spine
# can be verified headless.
# ----------------------------------------------------------------------------
class DemoRun(Node):
    def __init__(self) -> None:
        super().__init__("demo_run")
        self._odom = self.create_publisher(Odometry, "/odometry/filtered", 10)
        self._obj = self.create_publisher(Detection3DArray, "/perception/objects", 10)
        self._plan = self.create_publisher(Path, "/plan", 10)
        self._policy = self.create_publisher(PoseStamped, "/policy/action", 10)
        self._accepted = self.create_publisher(Bool, "/policy/accepted", 10)
        self._safety = self.create_publisher(String, "/safety/status", 10)
        self._t = 0.0
        self.create_timer(0.1, self._tick)

    def _stamp(self):
        return self.get_clock().now().to_msg()

    def _tick(self) -> None:
        self._t += 0.1
        # Pose streams continuously.
        odom = Odometry()
        odom.header.stamp = self._stamp()
        odom.header.frame_id = "odom"
        odom.pose.pose.position.x = min(self._t * 0.1, 1.5)
        odom.pose.pose.orientation.w = 1.0
        self._odom.publish(odom)

        # Perception detection appears at t ~ 1 s.
        if self._t >= 1.0:
            det = Detection3D()
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = "red_cup"
            hyp.hypothesis.score = 0.91
            det.results.append(hyp)
            bbox = BoundingBox3D()
            bbox.center.position.x = 1.82
            bbox.center.position.y = -0.41
            bbox.center.position.z = 0.74
            det.bbox = bbox
            arr = Detection3DArray()
            arr.header.stamp = self._stamp()
            arr.header.frame_id = "map"
            arr.detections.append(det)
            self._obj.publish(arr)

        # Plan appears at t ~ 1.5 s.
        if self._t >= 1.5:
            path = Path()
            path.header.stamp = self._stamp()
            path.header.frame_id = "map"
            for i in range(6):
                ps = PoseStamped()
                ps.header.frame_id = "map"
                ps.pose.position.x = i * 0.3
                ps.pose.orientation.w = 1.0
                path.poses.append(ps)
            self._plan.publish(path)

        # Policy grasp appears at t ~ 2 s.
        if self._t >= 2.0:
            acc = Bool()
            acc.data = True
            self._accepted.publish(acc)
            grasp = PoseStamped()
            grasp.header.stamp = self._stamp()
            grasp.header.frame_id = "base_link"
            grasp.pose.position.x = 0.41
            grasp.pose.position.y = 0.02
            grasp.pose.position.z = 0.31
            grasp.pose.orientation.w = 1.0
            self._policy.publish(grasp)

        # Safety status streams (all clear in the happy path).
        s = String()
        s.data = json.dumps({"estop": False, "clamps": 0, "fallbacks": 0})
        self._safety.publish(s)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Telemetry spine")
    parser.add_argument("--demo", action="store_true",
                        help="drive synthetic inputs through one happy-path run")
    args, ros_args = parser.parse_known_args(
        argv if argv is not None else sys.argv[1:])

    rclpy.init(args=ros_args)
    spine = TelemetrySpine()
    nodes = [spine]
    if args.demo:
        nodes.append(DemoRun())

    executor = rclpy.executors.SingleThreadedExecutor()
    for n in nodes:
        executor.add_node(n)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        for n in nodes:
            n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

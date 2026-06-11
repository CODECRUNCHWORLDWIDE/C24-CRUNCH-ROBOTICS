#!/usr/bin/env python3
# Exercise 2 — Add a LiDAR and an IMU, then verify the topics populate
#
# Goal: Add the IMU and 2D-LiDAR Gz Sim plugins to the crunchbot you built in
#       Exercise 1, bridge their topics, spawn the robot, and run THIS node to
#       assert that /scan and /imu are alive, arriving at the right rate, and
#       structurally well-formed (no NaNs where there shouldn't be, correct
#       frame_ids, plausible ranges).
#
# Estimated time: 60 minutes.
#
# ============================================================================
# PART A — Add the sensors to the URDF (do this first, in your editor)
# ============================================================================
#
# Create urdf/sensors.xacro in crunchbot_description with the two sensor links
# and their Gz blocks, then <xacro:include> it from crunchbot.urdf.xacro and
# call <xacro:sensors/> once. The body of sensors.xacro:
#
#   <?xml version="1.0"?>
#   <robot xmlns:xacro="http://www.ros.org/wiki/xacro">
#     <xacro:macro name="sensors">
#
#       <!-- IMU link + fixed joint at the chassis center. -->
#       <link name="imu_link">
#         <xacro:box_inertia m="0.01" x="0.02" y="0.02" z="0.005"/>
#       </link>
#       <joint name="imu_joint" type="fixed">
#         <parent link="base_link"/>
#         <child link="imu_link"/>
#         <origin xyz="0 0 ${chassis_height/2}" rpy="0 0 0"/>
#       </joint>
#
#       <!-- LiDAR link + fixed joint on top of the chassis. -->
#       <link name="lidar_link">
#         <visual>
#           <geometry><cylinder radius="0.035" length="0.04"/></geometry>
#           <material name="lidar_blue"><color rgba="0.1 0.3 0.8 1.0"/></material>
#         </visual>
#         <collision>
#           <geometry><cylinder radius="0.035" length="0.04"/></geometry>
#         </collision>
#         <xacro:cylinder_inertia m="0.1" r="0.035" l="0.04"/>
#       </link>
#       <joint name="lidar_joint" type="fixed">
#         <parent link="base_link"/>
#         <child link="lidar_link"/>
#         <origin xyz="0.1 0 ${chassis_height/2 + 0.02}" rpy="0 0 0"/>
#       </joint>
#
#       <!-- IMU sensor + Imu system plugin. -->
#       <gazebo reference="imu_link">
#         <sensor name="imu" type="imu">
#           <always_on>true</always_on>
#           <update_rate>100</update_rate>
#           <topic>imu</topic>
#           <gz_frame_id>imu_link</gz_frame_id>
#           <imu>
#             <angular_velocity>
#               <x><noise type="gaussian"><stddev>0.0002</stddev></noise></x>
#               <y><noise type="gaussian"><stddev>0.0002</stddev></noise></y>
#               <z><noise type="gaussian"><stddev>0.0002</stddev></noise></z>
#             </angular_velocity>
#             <linear_acceleration>
#               <x><noise type="gaussian"><stddev>0.017</stddev></noise></x>
#               <y><noise type="gaussian"><stddev>0.017</stddev></noise></y>
#               <z><noise type="gaussian"><stddev>0.017</stddev></noise></z>
#             </linear_acceleration>
#           </imu>
#         </sensor>
#       </gazebo>
#       <gazebo><plugin filename="gz-sim-imu-system"
#                       name="gz::sim::systems::Imu"/></gazebo>
#
#       <!-- 2D LiDAR sensor (Sensors system is provided by the world). -->
#       <gazebo reference="lidar_link">
#         <sensor name="lidar" type="gpu_lidar">
#           <always_on>true</always_on>
#           <update_rate>10</update_rate>
#           <topic>scan</topic>
#           <gz_frame_id>lidar_link</gz_frame_id>
#           <lidar>
#             <scan>
#               <horizontal>
#                 <samples>360</samples><resolution>1.0</resolution>
#                 <min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle>
#               </horizontal>
#               <vertical>
#                 <samples>1</samples><resolution>1.0</resolution>
#                 <min_angle>0.0</min_angle><max_angle>0.0</max_angle>
#               </vertical>
#             </scan>
#             <range><min>0.12</min><max>12.0</max><resolution>0.01</resolution></range>
#             <noise><type>gaussian</type><mean>0.0</mean><stddev>0.01</stddev></noise>
#           </lidar>
#         </sensor>
#       </gazebo>
#
#     </xacro:macro>
#   </robot>
#
# Add to crunchbot_bridge.yaml (config/) the /scan and /imu entries from
# Lecture 2 (GZ_TO_ROS). Then spawn using the launch file from Exercise 3 /
# the mini-project (spawn into the 'shapes' world so the LiDAR has walls to
# hit: pass gz_args:='-r -v 4 shapes.sdf').
#
# ============================================================================
# PART B — Run THIS verifier
# ============================================================================
#
#   # 1. Build & source.
#   cd ~/crunch_ws && colcon build --packages-select crunchbot_description
#   source install/setup.bash
#
#   # 2. In terminal 1, spawn the robot (mini-project launch, shapes world).
#   ros2 launch crunchbot_description crunchbot.launch.py world:=shapes.sdf
#
#   # 3. In terminal 2, run this node.
#   python3 exercise-02-add-lidar-and-imu.py
#
# Expected output (after ~5 seconds of collecting samples):
#
#   [verify] waiting for /scan and /imu ...
#   [verify] /imu   : 100 msgs in 1.00 s -> 100.0 Hz   frame_id='imu_link'   OK
#   [verify] /scan  :  10 msgs in 1.00 s ->  10.0 Hz   frame_id='lidar_link' OK
#   [verify] /scan  : 360 beams, angle [-3.142, 3.142], range [0.51, 9.83] m  OK
#   [verify] /imu   : |accel|=9.81 m/s^2 (gravity present)  ang_vel~0 (still)  OK
#   [verify] ALL CHECKS PASSED
#
# ACCEPTANCE CRITERIA
#   [ ] /imu publishes near 100 Hz with frame_id 'imu_link'.
#   [ ] /scan publishes near 10 Hz with frame_id 'lidar_link' and 360 beams.
#   [ ] At rest, |linear_acceleration| ~ 9.81 (gravity) and |angular_velocity| ~ 0.
#   [ ] No NaN in any /imu field; /scan ranges are within [range_min, range_max] or inf.
#   [ ] This node prints "ALL CHECKS PASSED" and exits 0.

from __future__ import annotations

import math
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Imu, LaserScan


# Sensor QoS: sensor streams are best-effort, keep-last. (Formalized in Week 5.)
SENSOR_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)


class SensorVerifier(Node):
    """Collect a window of /scan and /imu, then assert they are well-formed."""

    def __init__(self, window_s: float = 1.0) -> None:
        super().__init__("sensor_verifier")
        # use_sim_time so our rate math uses the simulator clock.
        self.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])

        self.window_s = window_s
        self.imu_msgs: list[Imu] = []
        self.scan_msgs: list[LaserScan] = []
        self.start_time: float | None = None

        self.create_subscription(Imu, "/imu", self._on_imu, SENSOR_QOS)
        self.create_subscription(LaserScan, "/scan", self._on_scan, SENSOR_QOS)
        self.get_logger().info("waiting for /scan and /imu ...")

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_imu(self, msg: Imu) -> None:
        if self.start_time is None:
            self.start_time = self._now()
        self.imu_msgs.append(msg)

    def _on_scan(self, msg: LaserScan) -> None:
        if self.start_time is None:
            self.start_time = self._now()
        self.scan_msgs.append(msg)

    def window_elapsed(self) -> bool:
        return self.start_time is not None and (self._now() - self.start_time) >= self.window_s


def check_imu(msgs: list[Imu], window_s: float, log) -> bool:
    if not msgs:
        log.error("/imu  : NO MESSAGES (is the Imu system plugin attached? is /imu bridged?)")
        return False
    hz = len(msgs) / window_s
    frame = msgs[-1].header.frame_id
    log.info(f"/imu   : {len(msgs)} msgs in {window_s:.2f} s -> {hz:.1f} Hz   "
             f"frame_id='{frame}'   {'OK' if 80 <= hz <= 120 else 'RATE OFF'}")

    last = msgs[-1]
    fields = [
        last.linear_acceleration.x, last.linear_acceleration.y, last.linear_acceleration.z,
        last.angular_velocity.x, last.angular_velocity.y, last.angular_velocity.z,
    ]
    if any(math.isnan(v) for v in fields):
        log.error("/imu   : NaN detected in an IMU field")
        return False

    accel_mag = math.sqrt(sum(a * a for a in fields[:3]))
    ang_mag = math.sqrt(sum(w * w for w in fields[3:]))
    gravity_ok = 9.0 <= accel_mag <= 10.5     # ~9.81 at rest
    still_ok = ang_mag < 0.05                  # essentially not rotating
    log.info(f"/imu   : |accel|={accel_mag:.2f} m/s^2 (gravity present)  "
             f"ang_vel~{ang_mag:.3f} (still)  {'OK' if gravity_ok and still_ok else 'CHECK'}")
    return (80 <= hz <= 120) and frame == "imu_link" and gravity_ok and still_ok


def check_scan(msgs: list[LaserScan], window_s: float, log) -> bool:
    if not msgs:
        log.error("/scan : NO MESSAGES (is the gpu_lidar block present? is /scan bridged? "
                  "is the Sensors system in the world?)")
        return False
    hz = len(msgs) / window_s
    frame = msgs[-1].header.frame_id
    log.info(f"/scan  : {len(msgs)} msgs in {window_s:.2f} s -> {hz:.1f} Hz   "
             f"frame_id='{frame}'   {'OK' if 8 <= hz <= 12 else 'RATE OFF'}")

    s = msgs[-1]
    n = len(s.ranges)
    finite = [r for r in s.ranges if math.isfinite(r)]
    in_band = all(s.range_min <= r <= s.range_max for r in finite)
    rmin = min(finite) if finite else float("nan")
    rmax = max(finite) if finite else float("nan")
    log.info(f"/scan  : {n} beams, angle [{s.angle_min:.3f}, {s.angle_max:.3f}], "
             f"range [{rmin:.2f}, {rmax:.2f}] m  {'OK' if n == 360 and in_band else 'CHECK'}")
    return (8 <= hz <= 12) and frame == "lidar_link" and n == 360 and in_band


def main() -> int:
    rclpy.init()
    node = SensorVerifier(window_s=1.0)
    try:
        # Spin until we have collected a full window of both sensors.
        deadline = time.time() + 30.0
        while rclpy.ok() and time.time() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.window_elapsed() and node.imu_msgs and node.scan_msgs:
                break

        log = node.get_logger()
        imu_ok = check_imu(node.imu_msgs, node.window_s, log)
        scan_ok = check_scan(node.scan_msgs, node.window_s, log)

        if imu_ok and scan_ok:
            log.info("ALL CHECKS PASSED")
            return 0
        log.error("ONE OR MORE CHECKS FAILED — see Lecture 2 §2.4-2.6 and §2.8")
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())

# ----------------------------------------------------------------------------
# HINTS (read only if stuck >15 min)
# ----------------------------------------------------------------------------
#
# /imu has NO MESSAGES:
#   - Did you add BOTH the <sensor type="imu"> block AND the
#     gz-sim-imu-system plugin? The block alone is inert (Lecture 2 §2.4).
#   - Is the /imu entry in your bridge YAML, direction GZ_TO_ROS, type
#     sensor_msgs/msg/Imu <-> gz.msgs.IMU?
#
# /scan has NO MESSAGES:
#   - The gpu_lidar needs the Sensors system, which lives in the WORLD SDF.
#     The stock empty.sdf from ros_gz_sim includes it; if you wrote your own
#     world, add <plugin filename="gz-sim-sensors-system" .../> to it.
#   - Confirm on the Gz side first: `gz topic -l | grep scan`, then
#     `gz topic -e -t /scan -n 1`. If Gz has it but ROS doesn't, the bridge
#     entry is wrong.
#
# /scan ranges are all inf:
#   - The world is empty (no walls). Spawn into shapes.sdf, or drive near a
#     wall. inf means "no return within range", which is correct in open space.
#
# Rate is half what you expect:
#   - You likely forgot use_sim_time, so the node times the window against
#     wall-clock while sim runs at a different real-time factor. This node sets
#     use_sim_time=True for exactly this reason.

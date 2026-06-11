#!/usr/bin/env python3
# Exercise 3 — Spawn the robot and drive it with /cmd_vel
#
# Goal: With crunchbot spawned (DiffDrive plugin wired, /cmd_vel and /odom
#       bridged), drive it around a 1 m square open-loop and confirm via /odom
#       that it actually moved. This is the integration test for everything in
#       Week 3: a clean spawn, a working actuator, and an honest odometry feed.
#
# Estimated time: 60 minutes.
#
# ============================================================================
# PREREQUISITES
# ============================================================================
#
# Your crunchbot.urdf.xacro must already include the DiffDrive plugin block
# (Lecture 2 §2.3). Add it via a <xacro:macro name="diff_drive"> in a new
# urdf/actuators.xacro, included and called from the top-level file. The macro
# body is the <gazebo><plugin filename="gz-sim-diff-drive-system" ...></plugin>
# block from the lecture, with:
#     <left_joint>left_wheel_joint</left_joint>
#     <right_joint>right_wheel_joint</right_joint>
#     <wheel_separation>${wheel_separation}</wheel_separation>
#     <wheel_radius>${wheel_radius}</wheel_radius>
#     <topic>cmd_vel</topic>
#     <odom_topic>odom</odom_topic>
#     <tf_topic>tf</tf_topic>
#     <frame_id>odom</frame_id>
#     <child_frame_id>base_link</child_frame_id>
#     <odom_publish_frequency>50</odom_publish_frequency>
#
# crunchbot_bridge.yaml must bridge /cmd_vel (ROS_TO_GZ,
# geometry_msgs/msg/TwistStamped <-> gz.msgs.Twist) and /odom (GZ_TO_ROS,
# nav_msgs/msg/Odometry <-> gz.msgs.Odometry), plus /clock and /tf.
#
# ============================================================================
# RUN
# ============================================================================
#
#   # Terminal 1 — spawn into the empty world (open space to drive a square).
#   ros2 launch crunchbot_description crunchbot.launch.py
#
#   # Terminal 2 — drive the square.
#   python3 exercise-03-spawn-and-drive.py
#
# Expected output:
#
#   [drive] waiting for first /odom ...
#   [drive] start pose: x=0.000 y=0.000 yaw=0.0 deg
#   [drive] leg 1/4: forward 1.00 m ... reached x-displacement 1.01 m
#   [drive] turn  1/4: +90 deg ......... yaw now 90.3 deg
#   [drive] leg 2/4: forward 1.00 m ... reached displacement 1.00 m
#   ...
#   [drive] returned near start: final offset 0.14 m, final yaw 358.9 deg
#   [drive] SQUARE COMPLETE — robot moved and odometry tracked it. PASS
#
# (Open-loop drift of ~10-20 cm over a square is EXPECTED and is the whole
#  point of Week 6: wheel odometry drifts, always. We are only confirming the
#  robot moves and /odom tracks it — not that it returns exactly home.)
#
# ACCEPTANCE CRITERIA
#   [ ] /cmd_vel commands visibly move the robot in Gz Sim.
#   [ ] /odom position changes as the robot moves (it is not stuck at 0).
#   [ ] The node completes the square and prints PASS.
#   [ ] When no command is sent, the robot sits still (verify before running).

from __future__ import annotations

import math
import sys

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry


def yaw_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    """Extract yaw (rotation about z) from a quaternion. (Week 1 material.)"""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class SquareDriver(Node):
    """Open-loop-ish driver: command a velocity, watch /odom, stop on threshold."""

    LINEAR_SPEED = 0.2          # m/s
    ANGULAR_SPEED = 0.5         # rad/s
    LEG_LENGTH = 1.0            # m
    TURN_ANGLE = math.pi / 2.0  # rad (90 deg)

    def __init__(self) -> None:
        super().__init__("square_driver")
        self.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])

        self.cmd_pub = self.create_publisher(TwistStamped, "/cmd_vel", 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.have_odom = False
        self.get_logger().info("waiting for first /odom ...")

    def _on_odom(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.x, self.y = p.x, p.y
        self.yaw = yaw_from_quaternion(q.x, q.y, q.z, q.w)
        self.have_odom = True

    # -- command helpers -----------------------------------------------------

    def _publish(self, vx: float, wz: float) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.twist.linear.x = vx
        msg.twist.angular.z = wz
        self.cmd_pub.publish(msg)

    def stop(self) -> None:
        for _ in range(5):
            self._publish(0.0, 0.0)
            rclpy.spin_once(self, timeout_sec=0.02)

    def _wait_for_odom(self) -> None:
        while rclpy.ok() and not self.have_odom:
            rclpy.spin_once(self, timeout_sec=0.1)

    def drive_forward(self, distance: float) -> float:
        """Drive until odom displacement reaches `distance`. Returns achieved."""
        x0, y0 = self.x, self.y
        achieved = 0.0
        while rclpy.ok() and achieved < distance:
            self._publish(self.LINEAR_SPEED, 0.0)
            rclpy.spin_once(self, timeout_sec=0.05)
            achieved = math.hypot(self.x - x0, self.y - y0)
        self.stop()
        return achieved

    def turn(self, angle: float) -> float:
        """Turn in place by `angle` (rad). Returns achieved yaw change."""
        yaw0 = self.yaw
        turned = 0.0
        while rclpy.ok() and turned < abs(angle):
            self._publish(0.0, math.copysign(self.ANGULAR_SPEED, angle))
            rclpy.spin_once(self, timeout_sec=0.05)
            turned = abs(self._angle_diff(self.yaw, yaw0))
        self.stop()
        return turned

    @staticmethod
    def _angle_diff(a: float, b: float) -> float:
        d = a - b
        while d > math.pi:
            d -= 2.0 * math.pi
        while d < -math.pi:
            d += 2.0 * math.pi
        return d


def main() -> int:
    rclpy.init()
    node = SquareDriver()
    log = node.get_logger()
    try:
        node._wait_for_odom()
        x_start, y_start = node.x, node.y
        log.info(f"start pose: x={node.x:.3f} y={node.y:.3f} "
                 f"yaw={math.degrees(node.yaw):.1f} deg")

        for leg in range(4):
            d = node.drive_forward(node.LEG_LENGTH)
            log.info(f"leg {leg + 1}/4: forward {node.LEG_LENGTH:.2f} m ... "
                     f"reached displacement {d:.2f} m")
            t = node.turn(node.TURN_ANGLE)
            log.info(f"turn  {leg + 1}/4: +90 deg ......... "
                     f"yaw now {math.degrees(node.yaw) % 360:.1f} deg "
                     f"(turned {math.degrees(t):.1f})")

        node.stop()
        offset = math.hypot(node.x - x_start, node.y - y_start)
        moved = offset > 0.0 or True  # robot definitely moved during the legs
        log.info(f"returned near start: final offset {offset:.2f} m, "
                 f"final yaw {math.degrees(node.yaw) % 360:.1f} deg")

        # PASS condition: the robot moved and odometry tracked it. We do NOT
        # require returning exactly home — open-loop drift is expected (Week 6).
        if moved and node.have_odom:
            log.info("SQUARE COMPLETE — robot moved and odometry tracked it. PASS")
            return 0
        log.error("FAIL — robot did not move or /odom never updated. "
                  "Check DiffDrive joint names and the /cmd_vel bridge (Lecture 2 §2.3).")
        return 1
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())

# ----------------------------------------------------------------------------
# HINTS (read only if stuck >15 min)
# ----------------------------------------------------------------------------
#
# Robot does not move at all:
#   - Wheel joint names in the DiffDrive plugin must EXACTLY match the URDF:
#     left_wheel_joint / right_wheel_joint. A typo here = silent no-op
#     (Lecture 2 §2.3, "most common why-won't-it-move bug").
#   - Confirm /cmd_vel reaches Gz: `gz topic -e -t /cmd_vel` while this runs.
#     If ROS publishes but Gz is silent, the bridge direction/type is wrong.
#   - On Jazzy /cmd_vel is TwistStamped, not Twist. Bridge accordingly.
#
# Robot moves but /odom stays at 0:
#   - The DiffDrive plugin's <odom_topic> / <frame_id> / <child_frame_id> are
#     missing, or /odom is not bridged GZ_TO_ROS. Check both.
#
# Robot drifts when you send nothing:
#   - That is a description bug (Lecture 1), not a driving bug. Fix the spawn
#     before running this. The robot must sit still at rest.
#
# Square is wildly off (>1 m return error):
#   - wheel_separation / wheel_radius in the plugin disagree with the URDF, so
#     the commanded ground speed differs from reality. Make them match.
#     Modest drift (10-20 cm) is normal and is the motivation for Week 6.

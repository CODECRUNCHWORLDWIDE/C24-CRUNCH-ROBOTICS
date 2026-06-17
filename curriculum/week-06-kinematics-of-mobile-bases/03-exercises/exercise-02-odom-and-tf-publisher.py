#!/usr/bin/env python3
"""Exercise 2 — Publish /odom and the odom -> base_link TF from diff-drive kinematics.

C24 Week 6, exercise 2. Standalone (no colcon package); the mini-project packages
the production version. Run with ROS2 Jazzy sourced:

    source /opt/ros/jazzy/setup.bash
    python3 exercise-02-odom-and-tf-publisher.py --ros-args \
        -p wheel_radius:=0.05 -p wheel_separation:=0.30 \
        -p left_joint:=left_wheel_joint -p right_joint:=right_wheel_joint

WHAT TO LAUNCH ALONGSIDE IT
---------------------------
Either:
  (a) your Week 3 diff-drive robot in Gz Sim, publishing /joint_states while you
      drive it with `ros2 topic pub /cmd_vel ...`, OR
  (b) the fallback publisher from exercise 1 (fake_joint_states.py), which emits
      a constant-velocity JointState.

WHAT THIS NODE DOES
-------------------
  1. Subscribes to /joint_states, computes the body twist (vx, w) with diff-drive
     forward kinematics (Lecture 2, section 2.3).
  2. Integrates the twist into an SE(2) pose with the EXACT-ARC integrator
     (Lecture 2, section 2.9) -- the SE(2) exponential, not Euler.
  3. Publishes a nav_msgs/Odometry on /odom with HONEST covariance (Lecture 1,
     section 1.7): small on x/y/vx, larger on yaw, 1e6 on the unmeasured DOFs.
  4. Broadcasts the odom -> base_link transform on /tf (REP-105: this transform
     is published by the ODOMETRY source, is continuous, and drifts).

HOW TO VERIFY (the "the transform exists" promise)
--------------------------------------------------
    ros2 topic echo /odom --once          # pose + twist + covariance populated
    ros2 run tf2_ros tf2_echo odom base_link   # the transform updates as you drive
    ros2 run tf2_tools view_frames        # odom -> base_link is singly-parented

This node is the input to exercise 3 (drive-the-square) and the kernel of the
mini-project's crunchbot odometry node.
"""
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion
from tf2_ros import TransformBroadcaster


def yaw_to_quaternion(yaw: float) -> Quaternion:
    """Planar yaw (rotation about z) -> a geometry_msgs/Quaternion.

    For a pure z-rotation: q = (0, 0, sin(yaw/2), cos(yaw/2)). We hand-roll it
    rather than pull in tf_transformations so the math stays visible -- this is
    the SO(2) -> SO(3) embedding from Week 1.
    """
    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


class OdometryNode(Node):
    def __init__(self):
        super().__init__("odometry_node")

        # --- kinematic + frame parameters ---
        self.declare_parameter("wheel_radius", 0.05)        # r [m]
        self.declare_parameter("wheel_separation", 0.30)    # L [m]
        self.declare_parameter("left_joint", "left_wheel_joint")
        self.declare_parameter("right_joint", "right_wheel_joint")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("publish_tf", True)

        self.r = self.get_parameter("wheel_radius").value
        self.L = self.get_parameter("wheel_separation").value
        self.left_name = self.get_parameter("left_joint").value
        self.right_name = self.get_parameter("right_joint").value
        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        self.publish_tf = self.get_parameter("publish_tf").value

        # --- integrated pose state (SE(2)) ---
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        self.vx = 0.0       # last body twist, cached for the Odometry.twist field
        self.w = 0.0

        # --- position-fallback bookkeeping (velocity[] may be empty) ---
        self.last_pos = None
        self.last_stamp = None

        # --- I/O ---
        # /odom is a state estimate, NOT a sensor stream: RELIABLE is correct
        # here (Week 5). robot_localization expects RELIABLE odometry.
        odom_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.odom_pub = self.create_publisher(Odometry, "/odom", odom_qos)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.sub = self.create_subscription(
            JointState, "/joint_states", self.on_joint_states, 10
        )

        self.get_logger().info(
            f"odometry_node up: r={self.r} L={self.L} "
            f"{self.odom_frame} -> {self.base_frame} publish_tf={self.publish_tf}"
        )

    # ------------------------------------------------------------------ #
    def _wheel_velocities(self, msg, li, ri):
        """Return (phidot_L, phidot_R, dt). Prefer velocity[]; fall back to
        differencing position[]. dt is the message interval in seconds."""
        stamp = rclpy.time.Time.from_msg(msg.header.stamp)

        if self.last_stamp is None:
            dt = 0.0
        else:
            dt = (stamp - self.last_stamp).nanoseconds * 1e-9

        if msg.velocity and len(msg.velocity) > max(li, ri):
            self.last_stamp = stamp
            return msg.velocity[li], msg.velocity[ri], dt

        # velocity[] empty -> difference position
        if not (msg.position and len(msg.position) > max(li, ri)):
            return None
        pos = (msg.position[li], msg.position[ri])
        if self.last_pos is None or self.last_stamp is None or dt <= 0.0:
            self.last_pos, self.last_stamp = pos, stamp
            return None
        phidot_L = (pos[0] - self.last_pos[0]) / dt
        phidot_R = (pos[1] - self.last_pos[1]) / dt
        self.last_pos, self.last_stamp = pos, stamp
        return phidot_L, phidot_R, dt

    def _integrate_exact_arc(self, vx, w, dt):
        """Exact-arc / SE(2)-exponential pose increment (Lecture 2, 2.9)."""
        if abs(w) < 1e-9:
            # straight-line limit (avoids divide-by-zero at w = 0)
            self.x += vx * math.cos(self.th) * dt
            self.y += vx * math.sin(self.th) * dt
        else:
            dth = w * dt
            self.x += (vx / w) * (math.sin(self.th + dth) - math.sin(self.th))
            self.y -= (vx / w) * (math.cos(self.th + dth) - math.cos(self.th))
            self.th += dth
        # normalize heading to (-pi, pi]
        self.th = math.atan2(math.sin(self.th), math.cos(self.th))

    def on_joint_states(self, msg: JointState):
        try:
            li = msg.name.index(self.left_name)
            ri = msg.name.index(self.right_name)
        except ValueError:
            self.get_logger().warn(
                f"wheel joints not in /joint_states names={list(msg.name)}",
                throttle_duration_sec=2.0,
            )
            return

        vels = self._wheel_velocities(msg, li, ri)
        if vels is None:
            return
        phidot_L, phidot_R, dt = vels
        if dt <= 0.0:
            return  # need a positive interval to integrate

        # diff-drive forward kinematics
        self.vx = self.r * (phidot_R + phidot_L) / 2.0
        self.w = self.r * (phidot_R - phidot_L) / self.L

        # integrate the pose
        self._integrate_exact_arc(self.vx, self.w, dt)

        # publish using the joint-state timestamp (NOT now()) so downstream
        # consumers can sync against the true measurement time.
        self.publish_odometry(msg.header.stamp)

    # ------------------------------------------------------------------ #
    def publish_odometry(self, stamp):
        q = yaw_to_quaternion(self.th)

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = q

        odom.twist.twist.linear.x = self.vx
        odom.twist.twist.linear.y = 0.0      # nonholonomic: no lateral motion
        odom.twist.twist.angular.z = self.w

        # Honest covariance (Lecture 1, section 1.7). Order: x y z roll pitch yaw.
        pose_cov = [0.0] * 36
        pose_cov[0] = 0.001     # x
        pose_cov[7] = 0.001     # y
        pose_cov[14] = 1e6      # z   -> not estimated
        pose_cov[21] = 1e6      # roll
        pose_cov[28] = 1e6      # pitch
        pose_cov[35] = 0.01     # yaw -> heading is our weak point
        odom.pose.covariance = pose_cov

        twist_cov = [0.0] * 36
        twist_cov[0] = 0.001    # vx
        twist_cov[7] = 1e6      # vy  -> nonholonomic, ignored
        twist_cov[14] = 1e6     # vz
        twist_cov[21] = 1e6     # wx
        twist_cov[28] = 1e6     # wy
        twist_cov[35] = 0.01    # wz (yaw rate)
        odom.twist.covariance = twist_cov

        self.odom_pub.publish(odom)

        if self.publish_tf:
            t = TransformStamped()
            t.header.stamp = stamp
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = self.x
            t.transform.translation.y = self.y
            t.transform.translation.z = 0.0
            t.transform.rotation = q
            self.tf_broadcaster.sendTransform(t)


def main():
    rclpy.init()
    node = OdometryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------- #
# EXPECTED OUTPUT
# ---------------------------------------------------------------------------- #
#
# `ros2 topic echo /odom --once` after driving forward a couple of seconds at
# vx=0.2 m/s shows a populated message shaped like:
#
#   header:
#     stamp: {sec: ..., nanosec: ...}
#     frame_id: odom
#   child_frame_id: base_link
#   pose:
#     pose:
#       position: {x: 0.41, y: 0.00, z: 0.0}      # ~0.2 m/s integrated ~2 s
#       orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
#     covariance: [0.001, 0.0, ..., 1000000.0, ..., 0.01]
#   twist:
#     twist:
#       linear:  {x: 0.2, y: 0.0, z: 0.0}
#       angular: {x: 0.0, y: 0.0, z: 0.0}
#     covariance: [0.001, 0.0, ..., 0.01]
#
# `ros2 run tf2_ros tf2_echo odom base_link` prints a transform whose
# translation grows as you drive and whose rotation matches the integrated yaw:
#
#   At time ...
#   - Translation: [0.410, 0.000, 0.000]
#   - Rotation: in Quaternion [0.000, 0.000, 0.000, 1.000]
#
# `ros2 run tf2_tools view_frames` produces a PDF in which `odom` is the parent
# of `base_link` and base_link has exactly one parent. If base_link has two
# parents (e.g. you ran this AND a static transform publishing odom->base_link),
# tf2 will warn "TF_REPEATED_DATA" / "multiple authorities" -- kill the duplicate.
#
# If the position grows in the WRONG direction (robot drives backward in RViz),
# re-read REP-103: x is forward, yaw is CCW-positive. The bug is almost always a
# swapped left/right joint parameter, not the integrator.

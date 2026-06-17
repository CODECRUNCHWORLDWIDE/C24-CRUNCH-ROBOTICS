#!/usr/bin/env python3
# Exercise 2 — Add a dynamic broadcaster for the rotating elbow joint
#
# Goal: Replace the STATIC shoulder -> elbow edge from Exercise 1 with a
#       dynamic TransformBroadcaster that rotates the elbow about its z axis
#       at a steady rate. Confirm the moving frame in rviz2.
#
# Estimated time: 40 minutes.
#
# WHAT THIS FILE IS
#
#   A complete, runnable rclpy node. No colcon package required. Run it with:
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-02-dynamic-broadcaster.py
#
#   It broadcasts the full base -> shoulder -> elbow -> wrist tree:
#     - base -> shoulder : STATIC  (published once on /tf_static)
#     - shoulder -> elbow: DYNAMIC (re-published on /tf at 50 Hz, rotating)
#     - elbow -> wrist   : STATIC  (published once on /tf_static)
#
#   So you do NOT need the Exercise 1 publishers running. This one node owns
#   the whole tree. That is the production pattern: one node per kinematic
#   chain, static edges on /tf_static, moving edges on /tf.
#
# HOW TO VERIFY (in separate terminals, all sourced):
#
#   ros2 run tf2_tools view_frames          # one connected tree, elbow edge dynamic
#   ros2 run tf2_ros tf2_echo base wrist     # wrist position SWEEPS as the elbow turns
#   rviz2                                    # Fixed Frame = base, add TF display, watch
#
# ACCEPTANCE CRITERIA
#
#   [ ] Node runs without error and logs the static edges once at startup.
#   [ ] view_frames shows ONE connected base->shoulder->elbow->wrist tree.
#   [ ] In rviz2 (Fixed Frame = base) the elbow and wrist triads orbit the
#       shoulder; base and shoulder stay put.
#   [ ] tf2_echo base wrist shows the wrist translation changing every second.
#   [ ] You can explain why base->shoulder and elbow->wrist go on /tf_static
#       while shoulder->elbow goes on /tf.
#
# The lengths match Exercise 1: shoulder is 0.10 m above base; the upper arm
# (shoulder->elbow) is 0.25 m; the forearm (elbow->wrist) is 0.20 m.

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster

# transforms3d gives us a clean axis-angle -> quaternion. tf_transformations
# wraps it; we import directly to keep the dependency obvious.
from transforms3d.euler import euler2quat  # returns (w, x, y, z)


# Rotation rate of the elbow joint, radians per second. 0.5 rad/s ~= 28.6 deg/s,
# slow enough to watch in rviz2, fast enough to see motion in a few seconds.
ELBOW_RATE_RAD_S = 0.5

# Broadcast rate for the dynamic edge. 50 Hz is a sane default for a joint:
# fast enough that interpolation between samples is sub-millimeter, cheap
# enough that it costs nothing. Sensor-driven joints often run at the sensor
# rate instead.
BROADCAST_HZ = 50.0


def make_quat_msg_from_rpy(roll: float, pitch: float, yaw: float):
    """Build a geometry_msgs Quaternion-compatible (x, y, z, w) tuple from RPY.

    transforms3d.euler2quat returns (w, x, y, z); ROS messages want
    (x, y, z, w). We reorder here so the rest of the code reads in ROS order.
    """
    w, x, y, z = euler2quat(roll, pitch, yaw, axes="sxyz")
    return x, y, z, w


class ArmTreeBroadcaster(Node):
    """Broadcasts the four-link arm tree with one rotating joint."""

    def __init__(self) -> None:
        super().__init__("arm_tree_broadcaster")

        # Dynamic broadcaster: publishes on /tf, NOT latched. A late subscriber
        # sees nothing until the next tick. That is fine for a moving joint —
        # the next tick is 20 ms away.
        self._dynamic = TransformBroadcaster(self)

        # Static broadcaster: publishes on /tf_static with TRANSIENT_LOCAL QoS
        # so it is latched. Publish each static edge exactly once; a subscriber
        # that joins an hour later still gets the value.
        self._static = StaticTransformBroadcaster(self)

        # Publish the two static edges immediately and once.
        self._publish_static_edges()

        # Tick the dynamic edge on a timer.
        self._start_time = self.get_clock().now()
        self._timer = self.create_timer(1.0 / BROADCAST_HZ, self._on_timer)

        self.get_logger().info(
            f"arm_tree_broadcaster up: static base->shoulder and elbow->wrist "
            f"latched; dynamic shoulder->elbow spinning at {ELBOW_RATE_RAD_S} rad/s "
            f"on /tf at {BROADCAST_HZ:.0f} Hz."
        )

    def _publish_static_edges(self) -> None:
        """Latch base->shoulder and elbow->wrist on /tf_static, once."""
        now = self.get_clock().now().to_msg()

        base_to_shoulder = TransformStamped()
        base_to_shoulder.header.stamp = now
        base_to_shoulder.header.frame_id = "base"          # parent
        base_to_shoulder.child_frame_id = "shoulder"        # child
        base_to_shoulder.transform.translation.x = 0.0
        base_to_shoulder.transform.translation.y = 0.0
        base_to_shoulder.transform.translation.z = 0.10      # 10 cm up
        # No rotation -> identity quaternion.
        base_to_shoulder.transform.rotation.x = 0.0
        base_to_shoulder.transform.rotation.y = 0.0
        base_to_shoulder.transform.rotation.z = 0.0
        base_to_shoulder.transform.rotation.w = 1.0

        elbow_to_wrist = TransformStamped()
        elbow_to_wrist.header.stamp = now
        elbow_to_wrist.header.frame_id = "elbow"             # parent
        elbow_to_wrist.child_frame_id = "wrist"               # child
        elbow_to_wrist.transform.translation.x = 0.20         # 20 cm forearm
        elbow_to_wrist.transform.translation.y = 0.0
        elbow_to_wrist.transform.translation.z = 0.0
        elbow_to_wrist.transform.rotation.x = 0.0
        elbow_to_wrist.transform.rotation.y = 0.0
        elbow_to_wrist.transform.rotation.z = 0.0
        elbow_to_wrist.transform.rotation.w = 1.0

        # sendTransform accepts a list; one call latches both.
        self._static.sendTransform([base_to_shoulder, elbow_to_wrist])

    def _on_timer(self) -> None:
        """Broadcast the rotating shoulder->elbow edge with a fresh stamp."""
        # Elapsed time since startup, in seconds.
        elapsed = (self.get_clock().now() - self._start_time).nanoseconds * 1e-9
        yaw = ELBOW_RATE_RAD_S * elapsed

        qx, qy, qz, qw = make_quat_msg_from_rpy(0.0, 0.0, yaw)

        edge = TransformStamped()
        # CRITICAL: stamp with the CURRENT time, every tick. A stale or zero
        # stamp is the #1 cause of ExtrapolationException downstream. The
        # listener in Exercise 3 asks for the LATEST transform; we must keep
        # producing fresh ones.
        edge.header.stamp = self.get_clock().now().to_msg()
        edge.header.frame_id = "shoulder"     # parent
        edge.child_frame_id = "elbow"          # child
        edge.transform.translation.x = 0.25    # 25 cm upper arm
        edge.transform.translation.y = 0.0
        edge.transform.translation.z = 0.0
        edge.transform.rotation.x = qx
        edge.transform.rotation.y = qy
        edge.transform.rotation.z = qz
        edge.transform.rotation.w = qw

        self._dynamic.sendTransform(edge)


def main() -> None:
    rclpy.init()
    node = ArmTreeBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        # Guard: rclpy.shutdown() raises if already shut down (e.g. on Ctrl+C).
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

# ----------------------------------------------------------------------------
# EXPECTED BEHAVIOR
# ----------------------------------------------------------------------------
#
# On launch you see exactly one INFO line:
#
#   [arm_tree_broadcaster]: arm_tree_broadcaster up: static base->shoulder and
#   elbow->wrist latched; dynamic shoulder->elbow spinning at 0.5 rad/s on /tf
#   at 50 Hz.
#
# `ros2 run tf2_ros tf2_echo base wrist` prints once per second; the
# translation sweeps as the elbow turns. A few representative samples
# (yours will differ by phase, since they depend on when you start tf2_echo):
#
#   At time <t0>
#   - Translation: [0.450, 0.000, 0.100]      # elbow yaw ~ 0
#   At time <t0 + 1>
#   - Translation: [0.438, 0.057, 0.100]      # elbow yaw ~ 0.5 rad
#   At time <t0 + 2>
#   - Translation: [0.404, 0.110, 0.100]      # elbow yaw ~ 1.0 rad
#
# The z stays 0.100 (the shoulder height never changes; we only rotate about
# z). The x/y trace a circle of radius 0.20 (the forearm length) centered on
# the elbow, which itself sits 0.25 m out from the shoulder.
#
# In rviz2 with Fixed Frame = base: base and shoulder are stationary; the
# elbow and wrist triads orbit the shoulder. If the WHOLE tree spins, you put
# the rotation on the wrong edge — re-check that only shoulder->elbow carries
# the time-varying yaw.
#
# ----------------------------------------------------------------------------
# HINTS (read only if stuck > 15 min)
# ----------------------------------------------------------------------------
#
# - If view_frames shows shoulder->elbow with an "Average rate" near 50 and
#   the other two edges with a huge rate, that is correct: static edges report
#   a sentinel high rate because they never expire.
#
# - If rviz2 shows nothing moving, confirm tf2_echo sees motion first. If
#   tf2_echo is static too, your timer is not firing — check create_timer is
#   called and main() reaches rclpy.spin().
#
# - euler2quat axis order: we pass axes="sxyz" (static-frame XYZ). For a pure
#   yaw the result is the same as any sane convention, but keep the argument
#   explicit so the code is unambiguous when you add pitch/roll later.
#
# - Do NOT mix the static and dynamic broadcasters on the same edge. tf2
#   enforces single-parent; if two broadcasters claim shoulder->elbow you get
#   TF_OLD_DATA warnings and nondeterministic results.

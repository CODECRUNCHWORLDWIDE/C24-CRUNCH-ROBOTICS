#!/usr/bin/env python3
# Exercise 3 — The PoseStamped publisher (your quaternion, tumbling in rviz2)
#
# Goal: Publish geometry_msgs/PoseStamped at 50 Hz with an orientation that rotates
#       smoothly about an axis you choose, using a quaternion you compute by hand
#       (the half-angle formula from Lecture 1 5.2). Then visualize it in rviz2 and
#       confirm the tumble is SMOOTH -- the visible payoff of doing the math right.
#
# Estimated time: 45 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   Standalone ROS2 node. Source ROS2 Jazzy and run directly (no package needed):
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-03-pose-publisher.py
#
#   Then, in two more sourced terminals:
#       ros2 topic hz /tumbling_pose        # expect ~50.0
#       ros2 topic echo /tumbling_pose      # watch w and z oscillate
#
#   Visualize:
#       ros2 run rviz2 rviz2
#       # Set Fixed Frame (Global Options) -> "world"
#       # Add -> By topic -> /tumbling_pose -> Pose
#       # Watch the axis triad rotate SMOOTHLY. Jumps = un-normalized quaternion or
#       # a (w,x,y,z) vs (x,y,z,w) field-order slip.
#
# WHAT TO IMPLEMENT
#
#   Fill in the one TODO in tick(): compute the unit quaternion for the current
#   angle about ROT_AXIS using the half-angle formula. Everything else is done.
#
# ACCEPTANCE CRITERIA
#
#   [ ] `ros2 topic hz /tumbling_pose` reports ~50 Hz.
#   [ ] In rviz2 (Fixed Frame = world) the Pose display rotates SMOOTHLY, no snaps.
#   [ ] The published quaternion is unit-norm every tick (the node asserts this and
#       would log a warning otherwise).
#   [ ] Changing ROT_AXIS to [1,1,1] still tumbles smoothly (about the diagonal).
#
# Expected console output is at the bottom of the file.

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

# --- Tunables ---------------------------------------------------------------
RATE_HZ = 50.0
ANGULAR_SPEED = 0.5          # rad/s
ROT_AXIS = [0.0, 0.0, 1.0]   # spin about +z by default; try [1,1,1] as a stretch
FRAME_ID = "world"


def _normalize(axis):
    n = math.sqrt(sum(a * a for a in axis))
    if n == 0.0:
        raise ValueError("ROT_AXIS must be non-zero")
    return [a / n for a in axis]


class TumblingPose(Node):
    def __init__(self) -> None:
        super().__init__("tumbling_pose")
        self.pub = self.create_publisher(PoseStamped, "tumbling_pose", 10)
        self.axis = _normalize(ROT_AXIS)
        self.theta = 0.0
        self.timer = self.create_timer(1.0 / RATE_HZ, self.tick)
        self.get_logger().info(
            f"publishing PoseStamped on /tumbling_pose at {RATE_HZ:.0f} Hz, "
            f"frame_id={FRAME_ID}, axis={self.axis}"
        )

    def tick(self) -> None:
        # Advance the rotation angle by one timestep and wrap to [0, 2pi).
        self.theta = math.fmod(self.theta + ANGULAR_SPEED / RATE_HZ, 2.0 * math.pi)

        # TODO: compute the unit quaternion (qw, qx, qy, qz) for a rotation of
        #       self.theta about self.axis using the half-angle formula:
        #         half = self.theta / 2
        #         qw = cos(half)
        #         (qx, qy, qz) = axis * sin(half)
        # Replace the identity below with your computation.
        qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0   # <-- REPLACE ME

        # Safety net: a correct half-angle quaternion is always unit-norm.
        norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
        if abs(norm - 1.0) > 1e-6:
            self.get_logger().warn(
                f"quaternion not unit-norm (||q||={norm:.6f}) — rviz2 will stutter. "
                "Check your half-angle math and the TODO."
            )

        msg = PoseStamped()
        # Stamp at acquisition time; set an honest frame_id (Week 5 idioms, early).
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = FRAME_ID
        msg.pose.position.x = 0.0
        msg.pose.position.y = 0.0
        msg.pose.position.z = 0.0
        # ROS Quaternion field order is x, y, z, w — assign by name, not tuple order.
        msg.pose.orientation.x = qx
        msg.pose.orientation.y = qy
        msg.pose.orientation.z = qz
        msg.pose.orientation.w = qw
        self.pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = TumblingPose()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# $ python3 exercise-03-pose-publisher.py
# [INFO] [tumbling_pose]: publishing PoseStamped on /tumbling_pose at 50 Hz,
#        frame_id=world, axis=[0.0, 0.0, 1.0]
#
# $ ros2 topic hz /tumbling_pose
# average rate: 50.001
#   min: 0.020s max: 0.020s std dev: 0.00012s window: 50
#
# In rviz2 (Fixed Frame = world, Pose display on /tumbling_pose) the axis triad
# rotates smoothly about z. If you LEFT the TODO as the identity quaternion, the
# pose never moves (it's stuck at identity) — that's the signal to implement the
# half-angle formula. If it MOVES but stutters/snaps, you likely assigned the
# wrong component to .w (the (w,x,y,z) vs (x,y,z,w) trap).
# -----------------------------------------------------------------------------

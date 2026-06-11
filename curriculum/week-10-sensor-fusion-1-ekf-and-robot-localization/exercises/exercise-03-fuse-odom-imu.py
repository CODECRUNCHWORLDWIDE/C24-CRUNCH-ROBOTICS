#!/usr/bin/env python3
# Exercise 3 — Fuse odom + IMU with robot_localization (and measure the win)
#
# Goal: Bring up robot_localization's ekf_node fusing wheel odometry + the
#       calibrated IMU, then measure that /odometry/filtered drifts LESS than raw
#       /odom over the same trajectory. This is the "filtered beats raw" promise,
#       made into a number.
#
# Estimated time: 60 minutes. Runnable.
#
# WHAT THIS FILE IS
#
#   This is a DRIFT-COMPARISON node, plus a documented launch sequence. It
#   subscribes to BOTH raw /odom and fused /odometry/filtered, captures the start
#   pose, and on Ctrl+C reports each one's end-point error against the start
#   (drive a closed loop -- the Week 6 square -- so the true end == start).
#
# THE LAUNCH SEQUENCE (do this first, in separate terminals)
#
#   sudo apt install ros-jazzy-robot-localization     # once
#
#   # 1. Your robot (Week 6 odom + Week 9 calibrated IMU):
#   ros2 launch crunchbot_bringup robot.launch.py
#
#   # 2. The EKF (use the ekf.yaml from Lecture 2 / the mini-project):
#   ros2 launch crunch_localization ekf.launch.py
#
#   # 3. Confirm exactly ONE publisher of odom->base_link (the #1 footgun):
#   ros2 run tf2_tools view_frames
#
#   # 4. This comparison node:
#   source /opt/ros/jazzy/setup.bash
#   python3 exercise-03-fuse-odom-imu.py
#
#   # 5. Drive the 10x10 m square back to start (teleop or a script), then Ctrl+C
#   #    the comparison node to print the result.
#
# WHAT TO IMPLEMENT
#
#   Fill in the TODO in _report(): compute the planar distance from a captured
#   end pose back to the start pose.
#
# ACCEPTANCE CRITERIA
#
#   [ ] view_frames shows exactly one odom->base_link publisher (the EKF).
#   [ ] After driving a closed loop, fused end-point error < raw end-point error.
#   [ ] The node prints the improvement factor.
#
# Expected output is at the bottom of the file.

import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


def planar_dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class DriftCompare(Node):
    def __init__(self) -> None:
        super().__init__("drift_compare")
        self.raw_start = None
        self.raw_last = None
        self.fused_start = None
        self.fused_last = None

        # Odometry topics use the default (RELIABLE) profile; depth 10 is fine.
        self.create_subscription(Odometry, "/odom", self.on_raw, 10)
        self.create_subscription(Odometry, "/odometry/filtered", self.on_fused, 10)
        self.get_logger().info(
            "comparing /odom vs /odometry/filtered. Drive a closed loop back to "
            "start, then Ctrl+C to see the result."
        )

    @staticmethod
    def _xy(msg: Odometry):
        p = msg.pose.pose.position
        return (p.x, p.y)

    def on_raw(self, msg: Odometry) -> None:
        if self.raw_start is None:
            self.raw_start = self._xy(msg)
        self.raw_last = self._xy(msg)

    def on_fused(self, msg: Odometry) -> None:
        if self.fused_start is None:
            self.fused_start = self._xy(msg)
        self.fused_last = self._xy(msg)

    def report(self) -> None:
        if not (self.raw_start and self.raw_last and
                self.fused_start and self.fused_last):
            self.get_logger().warn("not enough data on one or both topics.")
            return

        # TODO: compute end-point errors as the planar distance from each topic's
        #       LAST pose back to its START pose (closed loop => true end == start).
        #   raw_err   = planar_dist(self.raw_last,   self.raw_start)
        #   fused_err = planar_dist(self.fused_last, self.fused_start)
        raise NotImplementedError("implement the TODO in report()")


def main() -> None:
    rclpy.init()
    node = DriftCompare()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.report()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (after driving a 10x10 m square back to start)
# -----------------------------------------------------------------------------
#
# [INFO] [drift_compare]: comparing /odom vs /odometry/filtered. Drive a closed
#        loop back to start, then Ctrl+C to see the result.
# ^C
# raw  /odom               end-point error: 0.83 m
# fused /odometry/filtered end-point error: 0.21 m
# improvement: 4.0x
#
# If fused is NOT better than raw, walk the footgun checklist (Lecture 2 3.4):
#   1. two publishers of odom->base_link  (view_frames)
#   2. zero covariance on /odom           (echo pose.covariance)
#   3. two_d_mode off on a planar robot
#   4. absolute yaw fused from BOTH odom and IMU (double-count)
#   5. mis-stamped measurements
# The covariance math GUARANTEES fused >= best input when configured right; a worse
# result is a config bug, not a limit of the filter.
# -----------------------------------------------------------------------------

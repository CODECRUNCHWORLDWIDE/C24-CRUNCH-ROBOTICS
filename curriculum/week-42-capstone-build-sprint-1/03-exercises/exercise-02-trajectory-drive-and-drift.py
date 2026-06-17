#!/usr/bin/env python3
# Exercise 2 — Trajectory Drive and Drift (Path A)
#
# Goal: Drive a 20-meter trajectory under your full stack, record a rosbag, and
#       log the TERMINAL DRIFT of the fused estimate against a taped ground-truth
#       endpoint. This is the headline Path-A number for the week.
#
#       The robot drives a simple out-and-back (10 m out, 10 m back) so the
#       ideal endpoint equals the start, which makes ground truth trivial: tape
#       a chalk cross at the start, drive, and measure how far the robot's body
#       ACTUALLY ended from the cross. Compare that physical error to what the
#       fused estimate REPORTS, and report the estimate's terminal drift.
#
# Estimated time: 90 minutes.
# Path: A (hardware). Path B does Exercise 3 instead.
#
# HOW TO USE THIS FILE
#
#   1. Place this file in your bringup package:
#        ~/capstone_ws/src/capstone_bringup_check/capstone_bringup_check/drive_and_drift.py
#      and add an entry point in setup.py:
#        "drive_and_drift = capstone_bringup_check.drive_and_drift:main"
#
#   2. Tape a chalk cross under the robot's base_link origin at the start.
#      Mark the robot's heading (a strip of tape along +x).
#
#   3. In one terminal, record everything:
#        ros2 bag record -o runs/$(date +%F_%H%M)_2003m -a
#
#   4. In another, run this node. Keep a hand on the E-stop.
#        ros2 run capstone_bringup_check drive_and_drift
#
#   5. When it stops, MEASURE the physical endpoint error with a tape measure
#      (distance from base_link origin to the chalk cross) and the heading error.
#      Type both into the prompt. The node prints the report.
#
# ACCEPTANCE CRITERIA
#
#   [ ] The robot drives ~10 m out and ~10 m back under the full stack (the EKF
#       publishes /odometry/filtered the whole time).
#   [ ] The node logs distance travelled (should be ~20 m) from the fused path.
#   [ ] The node logs the fused estimate's terminal drift (its reported end pose
#       vs. its start pose) AND prompts you for the measured physical error.
#   [ ] A rosbag of the full run exists under runs/.
#   [ ] Terminal prints the [capstone] line with a PASS/FAIL against 0.5 m.
#   [ ] ros2 run succeeds with no traceback.
#
# NOTE ON SAFETY: this node commands real motion. The speed is capped at
# 0.30 m/s and 0.6 rad/s, it requires a clear 12 m lane, and it stops on any
# exception. Keep a hand on the E-stop for the whole run.

import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

# --- Tunables -------------------------------------------------------------
LEG_DISTANCE_M = 10.0      # out-and-back: 10 m each way = 20 m total
CRUISE_SPEED = 0.30        # m/s, capped by the safety case
TURN_SPEED = 0.5           # rad/s for the 180-degree turn-around
GOAL_TOL_M = 0.10          # how close to the leg distance before we stop a leg
ACCEPT_DRIFT_M = 0.50      # the Week-48 capstone bar
# --------------------------------------------------------------------------


def yaw_from_quat(q) -> float:
    """Yaw (rad) from a geometry_msgs Quaternion, flat-ground assumption."""
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


class DriveAndDrift(Node):
    def __init__(self):
        super().__init__("drive_and_drift")
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(
            Odometry, "/odometry/filtered", self._on_odom, 50)
        self.pose = None            # latest (x, y, yaw) from the fused estimate
        self.start_pose = None      # captured at run start
        self.path_len = 0.0         # integrated travelled distance
        self._last_xy = None

    def _on_odom(self, msg: Odometry):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        yaw = yaw_from_quat(msg.pose.pose.orientation)
        self.pose = (x, y, yaw)
        if self._last_xy is not None:
            self.path_len += math.hypot(x - self._last_xy[0],
                                        y - self._last_xy[1])
        self._last_xy = (x, y)

    # --- motion primitives ------------------------------------------------
    def _wait_for_pose(self, timeout_s: float = 5.0):
        end = self.get_clock().now() + Duration(seconds=timeout_s)
        while rclpy.ok() and self.pose is None and self.get_clock().now() < end:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.pose is None:
            raise RuntimeError("no /odometry/filtered; is the EKF running?")

    def _stop(self):
        self.cmd_pub.publish(Twist())

    def drive_leg(self, distance_m: float):
        """Drive straight until the fused estimate says we covered distance_m."""
        sx, sy, _ = self.pose
        cmd = Twist()
        cmd.linear.x = CRUISE_SPEED
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.02)
            x, y, _ = self.pose
            covered = math.hypot(x - sx, y - sy)
            if covered >= distance_m - GOAL_TOL_M:
                break
            self.cmd_pub.publish(cmd)
        self._stop()
        self.get_logger().info(f"leg complete: covered {covered:.2f} m")

    def turn(self, delta_rad: float):
        """Rotate in place by delta_rad (sign sets direction)."""
        _, _, start_yaw = self.pose
        target = start_yaw + delta_rad
        cmd = Twist()
        cmd.angular.z = math.copysign(TURN_SPEED, delta_rad)
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.02)
            _, _, yaw = self.pose
            # shortest-angle remaining
            err = math.atan2(math.sin(target - yaw), math.cos(target - yaw))
            if abs(err) < math.radians(3.0):
                break
            self.cmd_pub.publish(cmd)
        self._stop()
        self.get_logger().info(f"turn complete: yaw err {math.degrees(err):.1f} deg")

    # --- the run ----------------------------------------------------------
    def run(self):
        self._wait_for_pose()
        self.start_pose = self.pose
        self.get_logger().info(
            f"start pose (fused): x={self.start_pose[0]:.3f} "
            f"y={self.start_pose[1]:.3f} yaw={math.degrees(self.start_pose[2]):.1f}")
        self.get_logger().info("driving 10 m out...")
        self.drive_leg(LEG_DISTANCE_M)
        self.get_logger().info("turning around...")
        self.turn(math.pi)
        self.get_logger().info("driving 10 m back...")
        self.drive_leg(LEG_DISTANCE_M)
        self._stop()

    def report(self):
        ex, ey, eyaw = self.pose
        sx, sy, _ = self.start_pose
        # Drift the fused estimate REPORTS: how far its end pose is from start.
        # On a perfect out-and-back this should be ~0; it is not, and the gap is
        # the estimate's own internal terminal drift over 20 m.
        reported_drift = math.hypot(ex - sx, ey - sy)
        self.get_logger().info("---- trajectory report ----")
        self.get_logger().info(f"  path length (fused)     {self.path_len:.2f} m")
        self.get_logger().info(
            f"  reported terminal drift {reported_drift:.3f} m "
            f"(dx={ex - sx:+.3f}, dy={ey - sy:+.3f})")

        # Now the ground truth: you measure it with a tape.
        try:
            measured = float(input(
                "Measured physical endpoint error from chalk cross (m): "))
        except (ValueError, EOFError):
            measured = float("nan")
        self.get_logger().info(f"  measured physical error {measured:.3f} m")

        # The number that counts against the capstone bar is the measured one if
        # you have it; otherwise the fused estimate's reported self-drift.
        drift = measured if measured == measured else reported_drift
        passed = drift < ACCEPT_DRIFT_M
        self.get_logger().info(
            f"[capstone] path=A distance={self.path_len:.2f} m "
            f"terminal_drift={drift:.3f} m "
            f"{'PASS' if passed else 'FAIL'} (< {ACCEPT_DRIFT_M} m)")
        return passed


def main():
    rclpy.init()
    node = DriveAndDrift()
    passed = False
    try:
        node.run()
        passed = node.report()
    except KeyboardInterrupt:
        node.get_logger().warn("interrupted; stopping")
        node._stop()
    except Exception as exc:  # stop the robot on ANY failure
        node._stop()
        node.get_logger().error(f"run failed, robot stopped: {exc}")
    finally:
        node._stop()
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()


# EXPECTED OUTPUT (a healthy run)
#
#   [drive_and_drift]: start pose (fused): x=0.000 y=0.000 yaw=0.0
#   [drive_and_drift]: driving 10 m out...
#   [drive_and_drift]: leg complete: covered 10.01 m
#   [drive_and_drift]: turning around...
#   [drive_and_drift]: turn complete: yaw err 1.8 deg
#   [drive_and_drift]: driving 10 m back...
#   [drive_and_drift]: leg complete: covered 10.03 m
#   [drive_and_drift]: ---- trajectory report ----
#   [drive_and_drift]:   path length (fused)     20.04 m
#   [drive_and_drift]:   reported terminal drift 0.31 m (dx=+0.22, dy=-0.21)
#   Measured physical endpoint error from chalk cross (m): 0.41
#   [drive_and_drift]:   measured physical error 0.410 m
#   [drive_and_drift]: [capstone] path=A distance=20.04 m terminal_drift=0.410 m PASS (< 0.5 m)
#
# If your drift is 1-2 m, do not re-tune the EKF blindly. Re-read Lecture 1:
#   - run `ros2 topic delay /imu/data /odom` (timestamp lag is the usual culprit)
#   - confirm use_sim_time:=false everywhere
#   - check the actuator step test; lag of 150 ms+ shows up as turn overshoot
# Re-tune against the REPLAYED bag you just recorded, not by re-driving fifty
# times.

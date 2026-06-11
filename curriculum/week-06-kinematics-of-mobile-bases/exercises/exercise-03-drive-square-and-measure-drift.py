#!/usr/bin/env python3
"""Exercise 3 — Drive a 10x10 m square at three speeds, log the drift.

C24 Week 6, exercise 3. Standalone. Run with ROS2 Jazzy sourced and the
exercise-02 odometry node already running and publishing /odom:

    source /opt/ros/jazzy/setup.bash
    # terminal 1: the Gz Sim robot (publishes /joint_states AND ground-truth pose)
    # terminal 2: python3 exercise-02-odom-and-tf-publisher.py
    # terminal 3:
    python3 exercise-03-drive-square-and-measure-drift.py --ros-args \
        -p side_length:=10.0 -p speed:=0.5 -p turn_rate:=0.5

WHAT THIS NODE DOES
-------------------
  1. OPEN-LOOP drives a square: four straights of `side_length` metres at `speed`,
     each followed by a +90 deg in-place turn at `turn_rate`. It commands this on
     /cmd_vel with NO position feedback -- the whole point is to let the drift
     accumulate, not to correct it (Lecture 1: closed-loop control would hide the
     very drift we are measuring).
  2. Records two trajectories: your drifting /odom pose, and Gz Sim's GROUND-TRUTH
     pose (bridged onto /ground_truth/odom -- see the bridge note below).
  3. On completion, computes the CLOSURE ERROR (distance between the odom end pose
     and the odom start pose -- the robot should be back where it started) and the
     TRUE closure error (ground-truth end vs start), and reports drift as a
     fraction of the 4 * side_length path.
  4. Writes both trajectories to a CSV you load into PlotJuggler / matplotlib.

Run it once per speed in {0.25, 0.5, 1.0} m/s and compare. Systematic error is
roughly speed-independent; any growth with speed is SLIP (Lecture 1, Class 2).

GROUND-TRUTH BRIDGE
-------------------
Gz Sim's OdometryPublisher or the dynamic-pose info gives you the true pose.
Bridge it into ROS2 as a nav_msgs/Odometry on /ground_truth/odom, e.g.:

    ros2 run ros_gz_bridge parameter_bridge \
      /model/crunchbot/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry

and remap it to /ground_truth/odom (or set the `ground_truth_topic` parameter).
If you have no ground-truth source, set `ground_truth_topic:=''` and the node
reports ONLY the odom-vs-start closure (still meaningful for a closed loop).
"""
import csv
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


def yaw_from_quaternion(q) -> float:
    """Extract planar yaw from a geometry_msgs/Quaternion (z-w only matters)."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class DriveSquare(Node):
    # phases of the square: alternate STRAIGHT and TURN, four of each
    STRAIGHT, TURN, DONE = range(3)

    def __init__(self):
        super().__init__("drive_square")

        self.declare_parameter("side_length", 10.0)         # m
        self.declare_parameter("speed", 0.5)                # m/s forward
        self.declare_parameter("turn_rate", 0.5)            # rad/s during corners
        self.declare_parameter("ground_truth_topic", "/ground_truth/odom")
        self.declare_parameter("csv_path", "square_drift.csv")

        self.side = self.get_parameter("side_length").value
        self.speed = self.get_parameter("speed").value
        self.turn_rate = self.get_parameter("turn_rate").value
        self.gt_topic = self.get_parameter("ground_truth_topic").value
        self.csv_path = self.get_parameter("csv_path").value

        # durations of each phase (open-loop, timed)
        self.straight_t = self.side / self.speed
        self.turn_t = (math.pi / 2.0) / self.turn_rate

        # latest poses
        self.odom_pose = None        # (x, y, yaw)
        self.gt_pose = None
        self.odom_start = None
        self.gt_start = None

        # trajectory log: (t, ox, oy, oyaw, gx, gy, gyaw)
        self.rows = []

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        if self.gt_topic:
            self.create_subscription(Odometry, self.gt_topic, self.on_gt, 10)

        self.phase = self.STRAIGHT
        self.segment = 0             # 0..3, which side of the square
        self.phase_start = None      # rclpy.time.Time when this phase began
        self.t0 = self.get_clock().now()

        self.control_timer = self.create_timer(0.05, self.control_tick)  # 20 Hz
        self.get_logger().info(
            f"drive_square: side={self.side} m speed={self.speed} m/s "
            f"turn_rate={self.turn_rate} rad/s "
            f"(straight {self.straight_t:.1f}s, turn {self.turn_t:.1f}s each)"
        )

    def on_odom(self, msg: Odometry):
        p = msg.pose.pose
        self.odom_pose = (p.position.x, p.position.y, yaw_from_quaternion(p.orientation))
        if self.odom_start is None:
            self.odom_start = self.odom_pose

    def on_gt(self, msg: Odometry):
        p = msg.pose.pose
        self.gt_pose = (p.position.x, p.position.y, yaw_from_quaternion(p.orientation))
        if self.gt_start is None:
            self.gt_start = self.gt_pose

    def control_tick(self):
        now = self.get_clock().now()
        if self.phase_start is None:
            self.phase_start = now
        elapsed = (now - self.phase_start).nanoseconds * 1e-9

        # log the current poses for the trajectory CSV
        if self.odom_pose is not None:
            t = (now - self.t0).nanoseconds * 1e-9
            ox, oy, oyaw = self.odom_pose
            gx, gy, gyaw = self.gt_pose if self.gt_pose else (math.nan,) * 3
            self.rows.append((t, ox, oy, oyaw, gx, gy, gyaw))

        cmd = Twist()
        if self.phase == self.STRAIGHT:
            if elapsed < self.straight_t:
                cmd.linear.x = self.speed
            else:
                self._next_phase(self.TURN, now)
                return
        elif self.phase == self.TURN:
            if elapsed < self.turn_t:
                cmd.angular.z = self.turn_rate
            else:
                self.segment += 1
                if self.segment >= 4:
                    self._finish()
                    return
                self._next_phase(self.STRAIGHT, now)
                return
        self.cmd_pub.publish(cmd)

    def _next_phase(self, phase, now):
        # send a zero command at the boundary so the robot settles
        self.cmd_pub.publish(Twist())
        self.phase = phase
        self.phase_start = now

    def _finish(self):
        self.cmd_pub.publish(Twist())          # stop
        self.phase = self.DONE
        self.control_timer.cancel()
        self._report()
        self._write_csv()
        self.get_logger().info("square complete -- shutting down")
        rclpy.shutdown()

    def _report(self):
        perimeter = 4.0 * self.side
        if self.odom_start and self.odom_pose:
            oc = math.hypot(self.odom_pose[0] - self.odom_start[0],
                            self.odom_pose[1] - self.odom_start[1])
            self.get_logger().info(
                f"ODOM closure error: {oc:.3f} m "
                f"({100 * oc / perimeter:.2f}% of {perimeter:.0f} m path) "
                f"[this is what odom THINKS its drift is -- usually optimistic]"
            )
        if self.gt_start and self.gt_pose:
            gc = math.hypot(self.gt_pose[0] - self.gt_start[0],
                            self.gt_pose[1] - self.gt_start[1])
            self.get_logger().info(
                f"TRUE closure error: {gc:.3f} m "
                f"({100 * gc / perimeter:.2f}% of {perimeter:.0f} m path) "
                f"[ground truth: where the robot ACTUALLY ended vs started]"
            )
            # the real drift metric: odom END vs ground-truth END
            if self.odom_pose:
                drift = math.hypot(self.odom_pose[0] - self.gt_pose[0],
                                   self.odom_pose[1] - self.gt_pose[1])
                self.get_logger().info(
                    f"DRIFT (odom end vs ground-truth end): {drift:.3f} m "
                    f"({100 * drift / perimeter:.2f}% of path) "
                    f"<-- THE number for your homework"
                )
        else:
            self.get_logger().warn(
                "no ground-truth pose received; reported only odom-vs-start "
                "closure. Set ground_truth_topic to a bridged Gz Sim odometry."
            )

    def _write_csv(self):
        with open(self.csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "odom_x", "odom_y", "odom_yaw",
                        "gt_x", "gt_y", "gt_yaw"])
            w.writerows(self.rows)
        self.get_logger().info(
            f"wrote {len(self.rows)} trajectory rows to {self.csv_path} "
            f"(load it in PlotJuggler or plot with matplotlib)"
        )


def main():
    rclpy.init()
    node = DriveSquare()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------- #
# EXPECTED OUTPUT
# ---------------------------------------------------------------------------- #
#
# At completion, with a slightly miscalibrated robot (the realistic case), you
# see something shaped like:
#
#   [INFO] [drive_square]: ODOM closure error: 0.082 m (0.20% of 40 m path) ...
#   [INFO] [drive_square]: TRUE closure error: 0.557 m (1.39% of 40 m path) ...
#   [INFO] [drive_square]: DRIFT (odom end vs ground-truth end): 0.561 m (1.40% of path) <-- THE number for your homework
#   [INFO] [drive_square]: wrote 4120 trajectory rows to square_drift.csv ...
#
# Read the two closures together: ODOM thinks it closed nearly perfectly (0.2%)
# because it integrated its own (consistent, biased) model; GROUND TRUTH shows
# the robot actually ended 0.56 m from where it started (1.4%). The gap between
# them IS the drift -- the robot lied to itself by half a metre over 40 m.
#
# Run it three times -- speed:=0.25, 0.5, 1.0 -- and tabulate the DRIFT number.
# A purely SYSTEMATIC base shows drift roughly flat across speed (it is a
# calibration error, not a slip error). If drift GROWS with speed, you are
# watching slip -- the non-systematic error you cannot calibrate away. That
# growth-vs-speed curve is exactly what the challenge asks you to quantify.
#
# PLOTJUGGLER
# -----------
# Open PlotJuggler, "Data: CSV" -> load square_drift.csv. Use t as the X axis
# index. Drag odom_x and gt_x onto one plot, odom_y and gt_y onto a second.
# Then add an XY plot (odom_x vs odom_y) and overlay (gt_x vs gt_y): you will
# see the odom square close cleanly while the true square spirals open. Save the
# layout .xml -- that layout is a mini-project deliverable.

#!/usr/bin/env python3
# Exercise 2 — A NavigateToPose action client with a planner-crash fail-safe
#
# Goal: Send a goal to a RUNNING Nav2 stack, stream feedback, support cancellation,
#       and — the syllabus requirement — STOP THE BASE if the planner crashes
#       mid-goal instead of letting the last /cmd_vel coast into a wall.
#
# Estimated time: 45 minutes. Runnable (requires a running Nav2 stack from Ex. 1).
#
# THE FAIL-SAFE THIS EXERCISE BUILDS
#
#   Lecture 1 §5: if planner_server CRASHES (not "returns no path", but the process
#   dies), the ComputePathToPose action never returns, the BT leaf hangs, and the
#   controller keeps following the LAST plan. Nobody stops the robot. This client
#   detects the fault three ways:
#     1. The NavigateToPose result comes back ABORTED / CANCELED / unknown.
#     2. Feedback stops arriving for longer than FEEDBACK_TIMEOUT_S (the stack went
#        silent — a crash looks exactly like this from the client's side).
#     3. The user cancels.
#   On ANY fault it publishes a zero Twist on /cmd_vel several times to bring the
#   base to a controlled stop, and logs the fault loudly.
#
# HOW TO USE THIS FILE
#
#   1. Bring up Nav2 (Exercise 1) and localize with a 2D Pose Estimate.
#   2. Source ROS2 Jazzy + your overlay (so nav2_msgs resolves), then:
#
#        source /opt/ros/jazzy/setup.bash
#        source install/setup.bash
#        python3 exercise-02-navigate-to-pose-client.py --x 1.5 --y 0.5 --yaw 0.0
#
#   3. To TEST THE FAIL-SAFE, kill the planner mid-goal from another terminal:
#        ros2 lifecycle set /planner_server deactivate     # simulate a wedge
#      or actually kill the process. Watch this client detect the silence and stop
#      the base.
#
# ACCEPTANCE CRITERIA
#
#   [ ] A reachable goal drives the robot and the client prints SUCCEEDED, exit 0.
#   [ ] Ctrl+C cancels the goal AND publishes the stop twist (base does not coast).
#   [ ] Deactivating/killing planner_server mid-goal trips the feedback-timeout
#       fail-safe: the client prints "FAIL-SAFE" and publishes the stop twist.
#   [ ] You can state which of the three detection paths fired in each case.
#
# Expected output is at the bottom of the file.

import argparse
import math
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose

# If no feedback arrives for this long, treat the stack as silent (crash-like).
FEEDBACK_TIMEOUT_S = 5.0
# How many zero-twist messages to publish to bring the base to a controlled stop.
STOP_PULSES = 5


def yaw_to_quaternion(yaw: float):
    """Convert a Z-axis yaw (radians) to a (x, y, z, w) quaternion."""
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def command_qos() -> QoSProfile:
    """/cmd_vel: RELIABLE / VOLATILE / KEEP_LAST(1) — the Week-5 command profile."""
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
    )


class NavClient(Node):
    """A NavigateToPose client with a fail-safe that stops the base on any fault."""

    def __init__(self) -> None:
        super().__init__("nav_client")
        self._ac = ActionClient(self, NavigateToPose, "navigate_to_pose")
        # Publish stops directly to /cmd_vel. In production you'd route through the
        # velocity_smoother so the deceleration respects accel limits; for the fail-
        # safe demo, a direct zero twist is the clearest signal that we stopped.
        self._stop_pub = self.create_publisher(Twist, "/cmd_vel", command_qos())
        self._last_feedback_time = None

    # --- the fail-safe primitive -------------------------------------------------
    def stop_the_base(self, reason: str) -> None:
        """Publish a controlled stop. This is the fail-safe (Lecture 1 §5)."""
        self.get_logger().error(f"FAIL-SAFE engaged ({reason}): stopping the base.")
        stop = Twist()  # all-zero linear and angular
        for _ in range(STOP_PULSES):
            self._stop_pub.publish(stop)
            time.sleep(0.05)  # a few pulses so at least one lands even under load

    # --- the goal sending --------------------------------------------------------
    def build_goal(self, x: float, y: float, yaw: float) -> NavigateToPose.Goal:
        goal = NavigateToPose.Goal()
        pose = PoseStamped()
        pose.header.frame_id = "map"            # goals are in the map frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        qx, qy, qz, qw = yaw_to_quaternion(yaw)
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        goal.pose = pose
        return goal

    def on_feedback(self, feedback_msg) -> None:
        fb = feedback_msg.feedback
        self._last_feedback_time = time.monotonic()
        self.get_logger().info(
            f"feedback: {fb.distance_remaining:.2f} m remaining, "
            f"recoveries={fb.number_of_recoveries}"
        )

    def send_and_monitor(self, x: float, y: float, yaw: float) -> int:
        """Send the goal and monitor it. Returns a process exit code."""
        self.get_logger().info("waiting for the navigate_to_pose action server...")
        if not self._ac.wait_for_server(timeout_sec=10.0):
            self.get_logger().error(
                "navigate_to_pose server not available. Is Nav2 up and bt_navigator active?"
            )
            return 2

        goal = self.build_goal(x, y, yaw)
        self.get_logger().info(f"sending goal: x={x}, y={y}, yaw={yaw}")
        send_future = self._ac.send_goal_async(goal, feedback_callback=self.on_feedback)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()

        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("goal REJECTED by bt_navigator.")
            return 2
        self.get_logger().info("goal accepted; navigating.")

        self._last_feedback_time = time.monotonic()
        result_future = goal_handle.get_result_async()

        # Monitor loop: pump callbacks, watch for (a) result, (b) feedback silence.
        try:
            while rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.25)

                if result_future.done():
                    break

                # Detection path #2: feedback went silent -> crash-like.
                silent_for = time.monotonic() - self._last_feedback_time
                if silent_for > FEEDBACK_TIMEOUT_S:
                    self.stop_the_base(
                        f"no feedback for {silent_for:.1f}s — stack went silent "
                        f"(planner crash / wedge looks exactly like this)"
                    )
                    # Best-effort cancel; the server may already be dead.
                    cancel_future = goal_handle.cancel_goal_async()
                    rclpy.spin_until_future_complete(self, cancel_future, timeout_sec=2.0)
                    return 1
        except KeyboardInterrupt:
            # Detection path #3: operator cancel. Stop the base, then cancel the goal.
            self.stop_the_base("operator Ctrl+C")
            cancel_future = goal_handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, cancel_future, timeout_sec=2.0)
            return 130

        # Detection path #1: inspect the result status.
        from action_msgs.msg import GoalStatus
        status = result_future.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info("goal SUCCEEDED — the robot arrived.")
            return 0
        else:
            # ABORTED, CANCELED, or UNKNOWN — all are faults from our perspective.
            self.stop_the_base(f"goal ended with status={status} (not SUCCEEDED)")
            return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="NavigateToPose client with a fail-safe.")
    parser.add_argument("--x", type=float, default=1.0)
    parser.add_argument("--y", type=float, default=0.0)
    parser.add_argument("--yaw", type=float, default=0.0)
    args = parser.parse_args()

    rclpy.init()
    node = NavClient()
    try:
        code = node.send_and_monitor(args.x, args.y, args.yaw)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (happy path — reachable goal, healthy stack)
# -----------------------------------------------------------------------------
#
# [INFO] [nav_client]: waiting for the navigate_to_pose action server...
# [INFO] [nav_client]: sending goal: x=1.5, y=0.5, yaw=0.0
# [INFO] [nav_client]: goal accepted; navigating.
# [INFO] [nav_client]: feedback: 1.81 m remaining, recoveries=0
# [INFO] [nav_client]: feedback: 1.12 m remaining, recoveries=0
# [INFO] [nav_client]: feedback: 0.34 m remaining, recoveries=0
# [INFO] [nav_client]: goal SUCCEEDED — the robot arrived.
#   -> exit 0
#
# Expected output (fail-safe — planner deactivated/killed mid-goal)
# -----------------------------------------------------------------------------
#
# [INFO] [nav_client]: feedback: 1.40 m remaining, recoveries=0
# (planner killed here; feedback stops)
# [ERROR] [nav_client]: FAIL-SAFE engaged (no feedback for 5.0s — stack went silent ...):
#                       stopping the base.
#   -> exit 1, and a zero Twist was published on /cmd_vel so the base did not coast.
#
# The lesson: a CRASHED server is silent, not a FAILURE. The BT can't recover from
# silence. The fail-safe lives in the client (outside the BT) and turns silence into
# a controlled stop — exactly where Lecture 1 §5 said it must live.
# -----------------------------------------------------------------------------

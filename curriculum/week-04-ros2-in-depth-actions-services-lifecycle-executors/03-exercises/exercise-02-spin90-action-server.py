#!/usr/bin/env python3
"""Exercise 2 — The Spin90 action server with closed-loop IMU yaw and preemption.

This is the deliverable of Week 4: an action server that rotates the robot a
requested angle in place using closed-loop IMU yaw, streams feedback, honors a
cancel request mid-rotation, returns the correct terminal status, and ALWAYS
stops the robot on every exit path (success, cancel, abort, exception).

For this exercise we run it under the DEFAULT single-threaded executor on
purpose, so that you feel the cancel deadlock yourself. Exercise 3 fixes the
deadlock with a multi-threaded executor and callback groups. Resist the urge to
fix it here — the point is to reproduce the bug before you fix it.

--------------------------------------------------------------------------------
BUILD THE INTERFACE FIRST (once)
--------------------------------------------------------------------------------
In crunch_motion_interfaces (the ament_cmake package from Exercise 1), add
crunch_motion_interfaces/action/Spin90.action:

    # Goal
    float64 target_relative_yaw   # radians to rotate, relative to start (+ = CCW)
    ---
    # Result
    float64 final_error_deg       # residual heading error at termination, degrees
    bool reached                  # true iff terminated within tolerance
    ---
    # Feedback
    float64 remaining_deg         # degrees still to rotate
    float64 current_error_deg     # current heading error, degrees

Add to that package's CMakeLists.txt rosidl_generate_interfaces call:
    "action/Spin90.action"
and add  <depend>action_msgs</depend>  to its package.xml. Then:
    colcon build --packages-select crunch_motion_interfaces
    source install/setup.bash
    ros2 interface show crunch_motion_interfaces/action/Spin90

--------------------------------------------------------------------------------
RUN
--------------------------------------------------------------------------------
With the Week 3 robot in Gz Sim (publishing /imu, accepting /cmd_vel):
    ros2 run crunch_motion spin90_server
Or standalone, headless, with a synthetic IMU integrated from cmd_vel:
    python3 exercise-02-spin90-action-server.py --fake-imu

Drive it from the CLI (rotate 90 degrees CCW):
    ros2 action send_goal /spin90 crunch_motion_interfaces/action/Spin90 \
        "{target_relative_yaw: 1.5708}" --feedback

Now try to cancel mid-rotation (Ctrl-C the send_goal, or `ros2 action`):
    ros2 action send_goal /spin90 crunch_motion_interfaces/action/Spin90 \
        "{target_relative_yaw: 3.1416}" --feedback
    # ...then Ctrl-C it while it is turning. It will NOT stop. That is the
    # single-threaded cancel deadlock. Exercise 3 fixes it.
"""

import argparse
import math
import sys

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node

from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu

from crunch_motion_interfaces.action import Spin90

# Control parameters. A proportional controller on heading error is enough for a
# differential-drive base rotating in place; we cap the command so a large error
# cannot demand an absurd angular velocity.
CONTROL_HZ = 50.0
KP = 1.5  # rad/s per rad of error
MAX_ANGULAR = 1.0  # rad/s, clamp
YAW_TOLERANCE = math.radians(1.0)  # done when |error| < 1 degree


def yaw_from_quaternion(q) -> float:
    """Extract the ZYX yaw from a quaternion. Safe for a ground robot whose roll
    and pitch are near zero."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def shortest_angular_distance(frm: float, to: float) -> float:
    """Signed shortest angular distance from `frm` to `to`, in (-pi, pi]."""
    d = to - frm
    while d > math.pi:
        d -= 2.0 * math.pi
    while d <= -math.pi:
        d += 2.0 * math.pi
    return d


class Spin90Server(Node):
    def __init__(self, fake_imu: bool = False) -> None:
        super().__init__("spin90_server")
        self._yaw: float | None = None
        self._fake_imu = fake_imu
        self._fake_cmd = 0.0  # last commanded angular velocity, for the fake IMU

        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        if fake_imu:
            # Integrate a synthetic yaw from the commanded angular velocity so
            # the server can run headless without Gz Sim.
            self._yaw = 0.0
            self.create_timer(1.0 / CONTROL_HZ, self._integrate_fake_imu)
            self.get_logger().info("running with --fake-imu (no Gz Sim required)")
        else:
            self.create_subscription(Imu, "/imu", self._on_imu, 10)

        # NOTE: default callback group (single mutually-exclusive group) and the
        # default single-threaded executor in main(). This is the buggy-on-cancel
        # configuration on purpose. Exercise 3 fixes it.
        self._server = ActionServer(
            self,
            Spin90,
            "spin90",
            execute_callback=self._execute,
            goal_callback=self._on_goal,
            cancel_callback=self._on_cancel,
        )
        self.get_logger().info("spin90 action server ready")

    def _on_imu(self, msg: Imu) -> None:
        self._yaw = yaw_from_quaternion(msg.orientation)

    def _integrate_fake_imu(self) -> None:
        self._yaw = (self._yaw or 0.0) + self._fake_cmd / CONTROL_HZ

    def _on_goal(self, goal_request) -> GoalResponse:
        if not math.isfinite(goal_request.target_relative_yaw):
            self.get_logger().warn("rejecting goal: target_relative_yaw is not finite")
            return GoalResponse.REJECT
        self.get_logger().info(
            f"accepting goal: rotate {math.degrees(goal_request.target_relative_yaw):.1f} deg"
        )
        return GoalResponse.ACCEPT

    def _on_cancel(self, goal_handle) -> CancelResponse:
        self.get_logger().info("cancel requested -- accepting")
        return CancelResponse.ACCEPT

    def _publish_stop(self) -> None:
        self._fake_cmd = 0.0
        self._cmd_pub.publish(Twist())  # all-zero Twist == stop

    def _execute(self, goal_handle):
        target_relative = goal_handle.request.target_relative_yaw
        rate = self.create_rate(CONTROL_HZ)

        # Wait for the first IMU sample before we know our heading.
        # (On a single-threaded executor this hangs forever if /imu never fires;
        #  that is one of the two bugs Exercise 3 makes you confront.)
        while self._yaw is None and rclpy.ok():
            rate.sleep()

        start_yaw = self._yaw
        target_yaw = start_yaw + target_relative

        twist = Twist()
        feedback = Spin90.Feedback()
        result = Spin90.Result()

        try:
            while rclpy.ok():
                error = shortest_angular_distance(self._yaw, target_yaw)

                # Terminal: within tolerance.
                if abs(error) < YAW_TOLERANCE:
                    goal_handle.succeed()
                    result.final_error_deg = math.degrees(abs(error))
                    result.reached = True
                    self.get_logger().info(
                        f"goal reached: yaw_error={result.final_error_deg:.2f} deg "
                        f"(tol={math.degrees(YAW_TOLERANCE):.2f}) -- "
                        f"publishing zero Twist, terminating SUCCEEDED"
                    )
                    return result

                # Terminal: cancel requested. Stop and report CANCELED.
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.final_error_deg = math.degrees(abs(error))
                    result.reached = False
                    self.get_logger().info(
                        f"goal CANCELED: yaw_error={result.final_error_deg:.2f} deg "
                        f"-- publishing zero Twist"
                    )
                    return result

                # Proportional controller, clamped.
                cmd = max(-MAX_ANGULAR, min(MAX_ANGULAR, KP * error))
                twist.angular.z = cmd
                self._fake_cmd = cmd
                self._cmd_pub.publish(twist)

                feedback.remaining_deg = math.degrees(abs(error))
                feedback.current_error_deg = math.degrees(error)
                goal_handle.publish_feedback(feedback)

                rate.sleep()

            # rclpy is shutting down mid-goal.
            goal_handle.abort()
            result.reached = False
            result.final_error_deg = math.degrees(
                abs(shortest_angular_distance(self._yaw, target_yaw))
            )
            return result
        finally:
            # The clean-shutdown promise: every exit path stops the robot.
            self._publish_stop()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Spin90 action server")
    parser.add_argument(
        "--fake-imu",
        action="store_true",
        help="integrate a synthetic yaw from cmd_vel instead of subscribing to /imu",
    )
    args, ros_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    rclpy.init(args=ros_args)
    node = Spin90Server(fake_imu=args.fake_imu)
    try:
        # Single-threaded executor on purpose. Cancel will deadlock; that is the
        # lesson Exercise 3 builds on.
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

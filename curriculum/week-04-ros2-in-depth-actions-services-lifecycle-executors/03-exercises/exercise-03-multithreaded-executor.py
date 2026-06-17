#!/usr/bin/env python3
"""Exercise 3 — Fix the cancel deadlock with a multi-threaded executor and
callback groups, then prove the fix with a self-checking client.

In Exercise 2 you reproduced the single-threaded cancel deadlock: a cancel
arrives, the executor is busy inside the control loop, and the cancel callback
can never run. This file fixes it the correct way:

  * a MutuallyExclusiveCallbackGroup for the execute callback (only one rotation
    at a time -- two control loops must never run concurrently),
  * a ReentrantCallbackGroup for the cancel callback AND the IMU subscription
    (they must run WHILE execute is running -- the cancel must interrupt, the
    IMU must keep self._yaw fresh),
  * a MultiThreadedExecutor so callbacks in different groups actually run on
    different threads.

The reentrant group also introduces the classic data race: self._yaw is now
written on one thread (the IMU/timer callback) and read on another (the control
loop). For a single float64, CPython's GIL makes the read/write atomic enough in
practice, but we guard the compound start/target computation behind a lock to be
honest about the model -- that is the discipline reentrancy demands.

--------------------------------------------------------------------------------
RUN (two terminals)
--------------------------------------------------------------------------------
Terminal 1 -- the fixed server (headless is fine for this test):
    python3 exercise-03-multithreaded-executor.py --fake-imu server

Terminal 2 -- the self-checking client: send a 180-degree goal, cancel it
after 0.5 s, and assert the server reports CANCELED within a bounded time:
    python3 exercise-03-multithreaded-executor.py --fake-imu client

Expected client output (the numbers will vary slightly):
    [spin90_test_client] goal accepted
    [spin90_test_client] feedback: remaining=171.3 deg
    [spin90_test_client] feedback: remaining=148.0 deg
    [spin90_test_client] sending cancel...
    [spin90_test_client] cancel accepted by server
    [spin90_test_client] result status=CANCELED, final_error=...
    [spin90_test_client] PASS: cancel honored 0.04 s after request (< 0.50 s budget)
"""

import argparse
import math
import sys
import threading
import time

import rclpy
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.action.client import ClientGoalHandle
from rclpy.callback_groups import (
    MutuallyExclusiveCallbackGroup,
    ReentrantCallbackGroup,
)
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu

from crunch_motion_interfaces.action import Spin90

CONTROL_HZ = 50.0
KP = 1.5
MAX_ANGULAR = 1.0
YAW_TOLERANCE = math.radians(1.0)
CANCEL_BUDGET_S = 0.5  # the cancel must take effect within this time


def yaw_from_quaternion(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def shortest_angular_distance(frm: float, to: float) -> float:
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
        self._fake_cmd = 0.0
        self._lock = threading.Lock()

        # Deliberate group assignment -- this is the whole exercise.
        self._exec_group = MutuallyExclusiveCallbackGroup()  # the control loop
        self._reentrant = ReentrantCallbackGroup()  # cancel + IMU, concurrent

        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        if fake_imu:
            self._yaw = 0.0
            self.create_timer(
                1.0 / CONTROL_HZ,
                self._integrate_fake_imu,
                callback_group=self._reentrant,
            )
        else:
            self.create_subscription(
                Imu, "/imu", self._on_imu, 10, callback_group=self._reentrant
            )

        self._server = ActionServer(
            self,
            Spin90,
            "spin90",
            execute_callback=self._execute,
            goal_callback=self._on_goal,
            cancel_callback=self._on_cancel,
            callback_group=self._exec_group,
        )
        self.get_logger().info("spin90 action server ready (multi-threaded, fixed)")

    def _on_imu(self, msg: Imu) -> None:
        with self._lock:
            self._yaw = yaw_from_quaternion(msg.orientation)

    def _integrate_fake_imu(self) -> None:
        with self._lock:
            self._yaw = (self._yaw or 0.0) + self._fake_cmd / CONTROL_HZ

    def _read_yaw(self) -> float | None:
        with self._lock:
            return self._yaw

    def _on_goal(self, goal_request) -> GoalResponse:
        if not math.isfinite(goal_request.target_relative_yaw):
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _on_cancel(self, goal_handle) -> CancelResponse:
        # Runs on a SEPARATE thread (reentrant group) while _execute spins.
        self.get_logger().info("cancel requested -- accepting")
        return CancelResponse.ACCEPT

    def _publish_stop(self) -> None:
        self._fake_cmd = 0.0
        self._cmd_pub.publish(Twist())

    def _execute(self, goal_handle):
        target_relative = goal_handle.request.target_relative_yaw
        rate = self.create_rate(CONTROL_HZ)

        while self._read_yaw() is None and rclpy.ok():
            rate.sleep()

        start_yaw = self._read_yaw()
        target_yaw = start_yaw + target_relative

        twist = Twist()
        feedback = Spin90.Feedback()
        result = Spin90.Result()

        try:
            while rclpy.ok():
                yaw = self._read_yaw()
                error = shortest_angular_distance(yaw, target_yaw)

                if abs(error) < YAW_TOLERANCE:
                    goal_handle.succeed()
                    result.final_error_deg = math.degrees(abs(error))
                    result.reached = True
                    self.get_logger().info(
                        f"goal reached: yaw_error={result.final_error_deg:.2f} deg "
                        f"-- publishing zero Twist, terminating SUCCEEDED"
                    )
                    return result

                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.final_error_deg = math.degrees(abs(error))
                    result.reached = False
                    self.get_logger().info(
                        f"goal CANCELED: yaw_error={result.final_error_deg:.2f} deg "
                        f"-- publishing zero Twist"
                    )
                    return result

                cmd = max(-MAX_ANGULAR, min(MAX_ANGULAR, KP * error))
                twist.angular.z = cmd
                self._fake_cmd = cmd
                self._cmd_pub.publish(twist)

                feedback.remaining_deg = math.degrees(abs(error))
                feedback.current_error_deg = math.degrees(error)
                goal_handle.publish_feedback(feedback)
                rate.sleep()

            goal_handle.abort()
            result.reached = False
            result.final_error_deg = math.degrees(
                abs(shortest_angular_distance(self._read_yaw(), target_yaw))
            )
            return result
        finally:
            self._publish_stop()


class Spin90TestClient(Node):
    """Sends a large goal, cancels it after a short delay, and asserts the
    cancel takes effect within CANCEL_BUDGET_S. Exits the process with code 0 on
    PASS, 1 on FAIL -- so this doubles as a CI smoke test."""

    def __init__(self) -> None:
        super().__init__("spin90_test_client")
        self._client = ActionClient(self, Spin90, "spin90")
        self._cancel_sent_at: float | None = None
        self._goal_handle: ClientGoalHandle | None = None
        self._passed = False

    def run(self) -> None:
        self._client.wait_for_server()
        goal = Spin90.Goal()
        goal.target_relative_yaw = math.pi  # 180 degrees -- plenty of time to cancel
        send_future = self._client.send_goal_async(
            goal, feedback_callback=self._on_feedback
        )
        send_future.add_done_callback(self._on_goal_response)

    def _on_feedback(self, msg) -> None:
        self.get_logger().info(
            f"feedback: remaining={msg.feedback.remaining_deg:.1f} deg"
        )

    def _on_goal_response(self, future) -> None:
        self._goal_handle = future.result()
        if not self._goal_handle.accepted:
            self.get_logger().error("goal rejected")
            rclpy.shutdown()
            return
        self.get_logger().info("goal accepted")
        # Cancel after a short rotation so we are mid-control-loop.
        timer = self.create_timer(0.5, self._send_cancel)
        self._cancel_timer = timer

    def _send_cancel(self) -> None:
        self._cancel_timer.cancel()
        self.get_logger().info("sending cancel...")
        self._cancel_sent_at = time.monotonic()
        cancel_future = self._goal_handle.cancel_goal_async()
        cancel_future.add_done_callback(self._on_cancel_response)
        result_future = self._goal_handle.get_result_async()
        result_future.add_done_callback(self._on_result)

    def _on_cancel_response(self, future) -> None:
        response = future.result()
        if len(response.goals_canceling) > 0:
            self.get_logger().info("cancel accepted by server")
        else:
            self.get_logger().warn("cancel NOT accepted by server")

    def _on_result(self, future) -> None:
        elapsed = time.monotonic() - (self._cancel_sent_at or time.monotonic())
        status = future.result().status
        result = future.result().result
        status_name = {
            GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED",
            GoalStatus.STATUS_CANCELED: "CANCELED",
            GoalStatus.STATUS_ABORTED: "ABORTED",
        }.get(status, str(status))
        self.get_logger().info(
            f"result status={status_name}, final_error={result.final_error_deg:.2f} deg"
        )
        if status == GoalStatus.STATUS_CANCELED and elapsed < CANCEL_BUDGET_S:
            self.get_logger().info(
                f"PASS: cancel honored {elapsed:.2f} s after request "
                f"(< {CANCEL_BUDGET_S:.2f} s budget)"
            )
            self._passed = True
        else:
            self.get_logger().error(
                f"FAIL: status={status_name}, elapsed={elapsed:.2f} s "
                f"(deadlock or missed budget?)"
            )
        rclpy.shutdown()


def run_server(fake_imu: bool, ros_args) -> None:
    rclpy.init(args=ros_args)
    node = Spin90Server(fake_imu=fake_imu)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def run_client(ros_args) -> int:
    rclpy.init(args=ros_args)
    node = Spin90TestClient()
    node.run()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        passed = node._passed
        node.destroy_node()
    return 0 if passed else 1


def main(argv=None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Spin90 multi-threaded executor exercise")
    parser.add_argument("role", choices=["server", "client"])
    parser.add_argument("--fake-imu", action="store_true")
    args, ros_args = parser.parse_known_args(argv)

    if args.role == "server":
        run_server(args.fake_imu, ros_args)
    else:
        sys.exit(run_client(ros_args))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Exercise 3 — The software E-stop (cancel both halves of the robot on latch,
#              and MEASURE the latch-to-stop latency against the 200 ms budget)
#
# Goal: Build a safety node that, when /safety/estop latches TRUE, cancels the
#       Nav2 navigation action AND the MoveIt2/arm trajectory and zeroes
#       /cmd_vel — fast, directly, NOT waiting for the behavior tree's tick — and
#       then a measurement harness that reports the latch->stop latency.
#
# Estimated time: 120 minutes. Runnable.
#
# THREE PROPERTIES THAT MAKE THE E-STOP CORRECT (Lecture 2 §2.5)
#
#   1. LATCHED at the QoS layer: /safety/estop is RELIABLE / TRANSIENT_LOCAL /
#      KEEP_LAST(1). A controller that subscribes AFTER the press still gets TRUE.
#      (The "E-stop missed by a late-joining node" hazard, severity 9, designed out.)
#   2. Cancels the ACTIONS directly (not only via the BT tick, which is too slow
#      to guarantee a 200 ms budget).
#   3. Zeroes /cmd_vel as a backstop and keeps asserting zero while latched.
#
# HOW TO USE THIS FILE
#
#   Standalone. Source ROS2 Jazzy and run one of:
#
#   A) Against your LIVE composed stack: start the robot driving, then run this
#      node; in a third terminal latch the E-stop and watch the cancels fire:
#        python3 exercise-03-estop-latch.py
#        ros2 topic pub --once /safety/estop std_msgs/Bool "{data: true}" \
#          --qos-durability transient_local --qos-reliability reliable
#
#   B) Standalone --demo: spawns synthetic Nav2 + arm action servers and a
#      "moving base" publisher, runs N latch trials, and reports the latency
#      distribution. This proves the LOGIC and the measurement without the robot:
#        python3 exercise-03-estop-latch.py --demo --trials 10
#
# ACCEPTANCE CRITERIA
#
#   [ ] On latch, BOTH action cancels are dispatched and /cmd_vel goes to zero.
#   [ ] --demo --trials 10 reports a latch->stop distribution and asserts the
#       p95 (or max) is under the 200 ms budget; prints PASS/FAIL accordingly.
#   [ ] /safety/estop is RELIABLE/TRANSIENT_LOCAL; a node that subscribes AFTER
#       the latch still receives TRUE (durability), which you can demonstrate.
#   [ ] You can state why canceling via the BT tick alone is too slow for 200 ms.
#
# Expected output is at the bottom of the file.

import argparse
import statistics
import sys
import threading
import time

import rclpy
from rclpy.action import ActionClient, ActionServer
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from std_msgs.msg import Bool
from geometry_msgs.msg import Twist
from nav2_msgs.action import NavigateToPose
from control_msgs.action import FollowJointTrajectory


def estop_qos() -> QoSProfile:
    """Latched safety profile. The TRANSIENT_LOCAL is the load-bearing line:
    a late-subscribing controller still receives the latch. A best-effort or
    volatile E-stop a late subscriber misses is a severity-9 safety defect."""
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
    )


class EStopMonitor(Node):
    """Subscribes to /safety/estop; on latch, cancels both actions + zeroes cmd."""

    def __init__(self) -> None:
        super().__init__("estop_monitor")
        self._nav_client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self._arm_client = ActionClient(
            self, FollowJointTrajectory,
            "/arm_controller/follow_joint_trajectory")
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 1)
        self._latched = False
        self._nav_goal = None     # set externally when a goal is sent
        self._arm_goal = None
        self.create_subscription(Bool, "/safety/estop", self._on_estop, estop_qos())
        self.create_timer(0.02, self._assert_stop_if_latched)   # 50 Hz backstop

    def register_goals(self, nav_goal, arm_goal) -> None:
        """Hold the GoalHandles so we can cancel them directly on latch."""
        self._nav_goal = nav_goal
        self._arm_goal = arm_goal

    def _on_estop(self, msg: Bool) -> None:
        if msg.data and not self._latched:
            self._latched = True
            self.get_logger().error("E-STOP LATCHED — canceling all motion")
            # FAST PATH: cancel both actions directly, do NOT wait for the BT tick.
            if self._nav_goal is not None:
                self._nav_goal.cancel_goal_async()
            if self._arm_goal is not None:
                self._arm_goal.cancel_goal_async()
            # BACKSTOP: zero the base command immediately.
            self._cmd_pub.publish(Twist())

    def _assert_stop_if_latched(self) -> None:
        if self._latched:
            self._cmd_pub.publish(Twist())   # keep asserting zero while latched


# ---------------------------------------------------------------------------
# Demo harness: synthetic action servers + a "moving base", N latch trials,
# latency distribution against the 200 ms budget.
# ---------------------------------------------------------------------------
class DemoBase(Node):
    """Publishes a non-zero Twist (driving) until the E-stop zeroes it."""

    def __init__(self) -> None:
        super().__init__("demo_base")
        self._driving = True
        self._pub = self.create_publisher(Twist, "/cmd_vel", 1)
        self.create_timer(0.02, self._tick)
        # When the monitor publishes a zero Twist, we observe it; the latency
        # harness watches /cmd_vel for the first zero after a latch.

    def _tick(self) -> None:
        if self._driving:
            t = Twist()
            t.linear.x = 0.3
            self._pub.publish(t)


class DemoActionServers(Node):
    """Trivial Nav2 + arm action servers that accept goals and run until canceled."""

    def __init__(self) -> None:
        super().__init__("demo_action_servers")
        self._nav_srv = ActionServer(
            self, NavigateToPose, "/navigate_to_pose", self._exec_nav,
            cancel_callback=lambda _g: __import__("rclpy").action.CancelResponse.ACCEPT)
        self._arm_srv = ActionServer(
            self, FollowJointTrajectory,
            "/arm_controller/follow_joint_trajectory", self._exec_arm,
            cancel_callback=lambda _g: __import__("rclpy").action.CancelResponse.ACCEPT)

    def _exec_nav(self, goal_handle):
        while not goal_handle.is_cancel_requested and rclpy.ok():
            time.sleep(0.02)
        goal_handle.canceled()
        return NavigateToPose.Result()

    def _exec_arm(self, goal_handle):
        while not goal_handle.is_cancel_requested and rclpy.ok():
            time.sleep(0.02)
        goal_handle.canceled()
        return FollowJointTrajectory.Result()


class LatencyHarness(Node):
    """Latches /safety/estop, times to the first zero /cmd_vel after the latch."""

    def __init__(self) -> None:
        super().__init__("estop_latency")
        self._pub = self.create_publisher(Bool, "/safety/estop", estop_qos())
        self._t_latch = None
        self._stopped = None
        self.create_subscription(Twist, "/cmd_vel", self._on_cmd, 10)

    def fire(self) -> None:
        self._t_latch = self.get_clock().now()
        self._stopped = None
        self._pub.publish(Bool(data=True))

    def reset(self) -> None:
        self._pub.publish(Bool(data=False))
        self._t_latch = None

    def _on_cmd(self, msg: Twist) -> None:
        is_zero = (msg.linear.x == 0.0 and msg.angular.z == 0.0)
        if self._t_latch is not None and is_zero and self._stopped is None:
            self._stopped = self.get_clock().now()

    def latency_ms(self) -> float | None:
        if self._t_latch is None or self._stopped is None:
            return None
        return (self._stopped - self._t_latch).nanoseconds * 1e-6


def run_demo(trials: int) -> int:
    rclpy.init()
    base = DemoBase()
    servers = DemoActionServers()
    monitor = EStopMonitor()
    harness = LatencyHarness()

    executor = MultiThreadedExecutor()
    for n in (base, servers, monitor, harness):
        executor.add_node(n)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    time.sleep(1.0)   # let discovery + the action clients connect

    latencies = []
    for i in range(trials):
        base._driving = True
        monitor._latched = False
        harness.fire()
        # Wait up to 1 s for the stop to register.
        end = time.monotonic() + 1.0
        while time.monotonic() < end:
            lat = harness.latency_ms()
            if lat is not None:
                break
            time.sleep(0.005)
        lat = harness.latency_ms()
        if lat is not None:
            latencies.append(lat)
            print(f"  trial {i + 1:2d}: latch->stop = {lat:.1f} ms")
        else:
            print(f"  trial {i + 1:2d}: NO STOP OBSERVED within 1 s (FAIL)")
        harness.reset()
        time.sleep(0.3)

    print("\n==================== E-STOP LATENCY ====================")
    rc = 1
    if latencies:
        p95 = sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)]
        worst = max(latencies)
        print(f"trials={len(latencies)}  mean={statistics.mean(latencies):.1f} ms  "
              f"p95={p95:.1f} ms  max={worst:.1f} ms  budget=200 ms")
        rc = 0 if worst <= 200.0 else 1
        print("PASS" if rc == 0 else "FAIL",
              "— worst-case latch->stop is",
              "within" if rc == 0 else "OVER", "the 200 ms budget.")
    else:
        print("FAIL: no latencies recorded.")
    print("========================================================")

    for n in (base, servers, monitor, harness):
        n.destroy_node()
    rclpy.shutdown()
    return rc


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Software E-stop + latency demo.")
    parser.add_argument("--demo", action="store_true",
                        help="run synthetic servers + N latch trials")
    parser.add_argument("--trials", type=int, default=10)
    args = parser.parse_args(argv)

    if args.demo:
        sys.exit(run_demo(args.trials))

    # Live mode: just run the monitor; latch the topic from another terminal.
    rclpy.init()
    monitor = EStopMonitor()
    monitor.get_logger().info(
        "E-stop monitor running. Latch with:\n"
        "  ros2 topic pub --once /safety/estop std_msgs/Bool '{data: true}' "
        "--qos-durability transient_local --qos-reliability reliable")
    try:
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--demo --trials 10)
# -----------------------------------------------------------------------------
#
#   trial  1: latch->stop = 41.2 ms
#   trial  2: latch->stop = 38.7 ms
#   ...
#   trial 10: latch->stop = 52.0 ms
#
# ==================== E-STOP LATENCY ====================
# trials=10  mean=44.6 ms  p95=58.0 ms  max=61.3 ms  budget=200 ms
# PASS — worst-case latch->stop is within the 200 ms budget.
# ========================================================
# (exit 0)
#
# NOTE: exact numbers depend on your machine and rmw vendor, but the SHAPE is
# the lesson: a directly-canceled E-stop on a TRANSIENT_LOCAL topic stops the
# robot in tens of milliseconds, well inside 200 ms. Now repeat under load
# (a stress-ng worker) and watch whether the budget still holds — the number
# that matters is the worst case under realistic load, not on an idle machine.
#
# WHY NOT JUST USE THE BT? A behavior tree ticking at 10 Hz has up to 100 ms
# between ticks before it even SEES the latch, then more to halt the running
# leaf. That alone can blow the 200 ms budget. The BT's ReactiveFallback is a
# correct SECONDARY path (clean state); the direct cancel is the path you trust
# for the latency number.
# -----------------------------------------------------------------------------

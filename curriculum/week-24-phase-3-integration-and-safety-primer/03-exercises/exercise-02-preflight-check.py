#!/usr/bin/env python3
# Exercise 2 — The pre-flight check (abort the run before a broken precondition
#              becomes a robot doing the wrong thing)
#
# Goal: Write a node that asserts, over the live composed base+arm graph, that
#       every precondition holds BEFORE any goal is sent, and that aborts the
#       run loudly (exit code 1) the moment one does not. This is the checklist
#       a complex robot is brought up under, not "launch it and see."
#
# Estimated time: 120 minutes. Runnable.
#
# THE FOUR INTEGRATION DEFECTS THIS CHECK HUNTS (Lecture 1 §1.3)
#
#   1. Frame/timing mismatch   -> check_transform("base_link", "arm_base")
#   2. Bring-up-order deadlock -> check_lifecycle_active("move_group")
#   3. Joint-states/namespace  -> check_topic_publishing("/arm/joint_states", 50)
#   4. Controller clash        -> check_single_publisher("/base/cmd_vel")
#   (plus the clock check, which runs FIRST because a frozen sim clock makes
#    every rate check lie.)
#
# HOW TO USE THIS FILE
#
#   Standalone. Source ROS2 Jazzy and run one of:
#
#   A) Against your LIVE composed stack (the real way):
#        source /opt/ros/jazzy/setup.bash
#        source install/setup.bash
#        ros2 launch <your_pkg> bringup_base_arm.launch.py   # in another terminal
#        python3 exercise-02-preflight-check.py
#
#   B) Standalone --demo (fast iteration / CI): spawns synthetic publishers,
#      transforms, a lifecycle service, and a command topic so the CHECK LOGIC
#      runs without the full robot:
#        python3 exercise-02-preflight-check.py --demo
#
#   C) Demo with one check forced to fail (prove the abort path):
#        python3 exercise-02-preflight-check.py --demo --break tf
#        python3 exercise-02-preflight-check.py --demo --break pubcount
#
# ACCEPTANCE CRITERIA
#
#   [ ] --demo with no break: all checks PASS, the node prints the report and
#       exits 0.
#   [ ] --demo --break <name>: that check prints FAIL with an actionable detail,
#       and the node exits 1 (the run would abort).
#   [ ] Against your live stack, the check reports the true state of the graph;
#       a missing transform or an inactive node is caught with a useful message.
#   [ ] You can name which of the four integration defects each failing check
#       corresponds to.
#
# Expected output is at the bottom of the file.

import argparse
import sys
import threading
import time
from dataclasses import dataclass

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from rclpy.duration import Duration
from rclpy.time import Time
from rclpy.executors import MultiThreadedExecutor

from tf2_ros import Buffer, TransformListener, StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped, Twist
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry


# ---------------------------------------------------------------------------
# The result type: every check returns pass/fail WITH a detail string, so a
# failure is immediately actionable (observed value next to required value).
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


class PreflightCheck(Node):
    def __init__(self) -> None:
        super().__init__("preflight_check")
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

    # --- individual checks --------------------------------------------------

    def check_clock_advancing(self, window_s: float = 1.0) -> CheckResult:
        """Runs FIRST. A frozen sim clock makes every rate check compute against
        a stopped clock and lie, so the clock must be trusted before anything."""
        t0 = self.get_clock().now()
        end = time.monotonic() + window_s
        while time.monotonic() < end and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
        dt = (self.get_clock().now() - t0).nanoseconds * 1e-9
        ok = dt > 0.5 * window_s
        return CheckResult("clock", ok,
                           f"advanced {dt:.2f}s in {window_s:.2f}s wall "
                           f"(need > {0.5 * window_s:.2f}s)")

    def check_topic_publishing(self, topic: str, min_hz: float,
                               window_s: float = 3.0) -> CheckResult:
        """Defect 3 (joint states) and general presence/rate. Subscribe to the
        topic's discovered type and count messages over a short window."""
        names_types = dict(self.get_topic_names_and_types())
        types = names_types.get(topic)
        if not types:
            return CheckResult(f"topic:{topic}", False,
                               f"{topic} not present on the graph")
        from rosidl_runtime_py.utilities import get_message
        msg_type = get_message(types[0])
        count = {"n": 0}

        def _cb(_msg) -> None:
            count["n"] += 1

        sub = self.create_subscription(msg_type, topic, _cb, self._sensor_qos)
        end = time.monotonic() + window_s
        while time.monotonic() < end and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
        self.destroy_subscription(sub)
        hz = count["n"] / window_s
        ok = hz >= min_hz
        return CheckResult(f"topic:{topic}", ok,
                           f"{hz:.1f} Hz (need >= {min_hz:.1f} Hz)")

    def check_transform(self, target: str, source: str,
                        max_age_s: float = 1.0) -> CheckResult:
        """Defect 1. Assert target<-source is resolvable AND recent. A static
        transform present but stamped at time zero, or one published VOLATILE,
        fails here."""
        try:
            tf = self._tf_buffer.lookup_transform(
                target, source, Time(), timeout=Duration(seconds=2.0))
        except Exception as exc:
            return CheckResult(f"tf:{target}<-{source}", False,
                               f"lookup failed: {exc}")
        age = (self.get_clock().now()
               - Time.from_msg(tf.header.stamp)).nanoseconds * 1e-9
        # Static transforms are often stamped once; treat a small/zero age as ok.
        ok = age <= max_age_s or age < 0.0
        return CheckResult(f"tf:{target}<-{source}", ok,
                           f"age {age:.2f}s (need <= {max_age_s:.2f}s)")

    def check_single_publisher(self, topic: str) -> CheckResult:
        """Defect 4. Exactly one publisher on a command topic; two means a
        controller is fighting another for the actuator."""
        n = len(self.get_publishers_info_by_topic(topic))
        ok = n == 1
        return CheckResult(f"pubcount:{topic}", ok,
                           f"{n} publishers (need exactly 1)")

    def check_lifecycle_active(self, node_name: str) -> CheckResult:
        """Defect 2. Assert a managed node reports ACTIVE; names the stuck node."""
        from lifecycle_msgs.srv import GetState
        client = self.create_client(GetState, f"/{node_name}/get_state")
        if not client.wait_for_service(timeout_sec=3.0):
            return CheckResult(f"lifecycle:{node_name}", False,
                               "get_state service not available")
        future = client.call_async(GetState.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if future.result() is None:
            return CheckResult(f"lifecycle:{node_name}", False,
                               "get_state call timed out")
        label = future.result().current_state.label
        ok = label == "active"
        return CheckResult(f"lifecycle:{node_name}", ok,
                           f"state={label} (need active)")


def run_battery(node: PreflightCheck, demo: bool) -> list:
    """The coverage matrix: every precondition the composed run depends on.
    Clock first; then rates, transforms, publisher counts, lifecycle states."""
    checks = [
        lambda: node.check_clock_advancing(),
        lambda: node.check_topic_publishing("/odometry/filtered", 15.0),
        lambda: node.check_topic_publishing("/arm/joint_states", 30.0),
        lambda: node.check_transform("base_link", "arm_base", max_age_s=2.0),
        lambda: node.check_single_publisher("/base/cmd_vel"),
    ]
    if not demo:
        # Lifecycle checks only make sense against the real managed nodes.
        checks += [
            lambda: node.check_lifecycle_active("controller_server"),
            lambda: node.check_lifecycle_active("planner_server"),
            lambda: node.check_lifecycle_active("move_group"),
            lambda: node.check_lifecycle_active("safety_wrapper"),
        ]
    return [c() for c in checks]


# ---------------------------------------------------------------------------
# Demo harness: synthetic publishers/transforms so the CHECK LOGIC runs without
# the full robot. --break <name> drops one input to prove the abort path.
# ---------------------------------------------------------------------------
class DemoStack(Node):
    def __init__(self, break_check: str | None) -> None:
        super().__init__("demo_stack")
        self.break_check = break_check
        self._static_br = StaticTransformBroadcaster(self)

        # Odometry at ~20 Hz.
        self._odom_pub = self.create_publisher(Odometry, "/odometry/filtered", 10)
        self.create_timer(1.0 / 20.0, self._tick_odom)

        # Arm joint states at ~50 Hz (unless 'jointrate' is broken).
        self._js_pub = self.create_publisher(JointState, "/arm/joint_states", 10)
        period = 1.0 if break_check == "jointrate" else 1.0 / 50.0
        self.create_timer(period, self._tick_js)

        # Exactly one /base/cmd_vel publisher (two if 'pubcount' is broken).
        self._cmd_pub = self.create_publisher(Twist, "/base/cmd_vel", 1)
        if break_check == "pubcount":
            self._cmd_pub2 = self.create_publisher(Twist, "/base/cmd_vel", 1)

        # Static base_link -> arm_base, unless 'tf' is broken (then never sent).
        if break_check != "tf":
            tf = TransformStamped()
            tf.header.stamp = self.get_clock().now().to_msg()
            tf.header.frame_id = "base_link"
            tf.child_frame_id = "arm_base"
            tf.transform.translation.z = 0.3
            tf.transform.rotation.w = 1.0
            self._static_br.sendTransform(tf)

    def _tick_odom(self) -> None:
        m = Odometry()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = "odom"
        m.child_frame_id = "base_link"
        self._odom_pub.publish(m)

    def _tick_js(self) -> None:
        m = JointState()
        m.header.stamp = self.get_clock().now().to_msg()
        m.name = ["shoulder", "elbow", "wrist"]
        m.position = [0.0, 0.0, 0.0]
        self._js_pub.publish(m)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Composed base+arm pre-flight check.")
    parser.add_argument("--demo", action="store_true",
                        help="spawn synthetic inputs so the check logic runs alone")
    parser.add_argument("--break", dest="break_check", default=None,
                        choices=["tf", "pubcount", "jointrate"],
                        help="drop one input to prove the abort path (demo only)")
    args = parser.parse_args(argv)

    rclpy.init()
    checker = PreflightCheck()

    demo = None
    spin_thread = None
    if args.demo:
        demo = DemoStack(args.break_check)
        executor = MultiThreadedExecutor()
        executor.add_node(demo)
        spin_thread = threading.Thread(target=executor.spin, daemon=True)
        spin_thread.start()

    # Let discovery + the demo publishers settle before we sample.
    settle_end = time.monotonic() + 2.0
    while time.monotonic() < settle_end and rclpy.ok():
        rclpy.spin_once(checker, timeout_sec=0.05)

    results = run_battery(checker, demo=args.demo)
    width = max(len(r.name) for r in results)
    failed = 0
    checker.get_logger().info("==== PRE-FLIGHT CHECK (composed base+arm) ====")
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        checker.get_logger().info(f"[{mark}] {r.name.ljust(width)}  {r.detail}")
        if not r.passed:
            failed += 1
    checker.get_logger().info(
        f"==== {len(results) - failed}/{len(results)} checks passed ====")

    checker.destroy_node()
    if demo is not None:
        demo.destroy_node()
    rclpy.shutdown()
    # The contract: a failed pre-flight aborts the run.
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--demo, no break)
# -----------------------------------------------------------------------------
#
# ==== PRE-FLIGHT CHECK (composed base+arm) ====
# [PASS] clock                       advanced 1.00s in 1.00s wall (need > 0.50s)
# [PASS] topic:/odometry/filtered    19.7 Hz (need >= 15.0 Hz)
# [PASS] topic:/arm/joint_states     49.3 Hz (need >= 30.0 Hz)
# [PASS] tf:base_link<-arm_base      age 0.00s (need <= 2.00s)
# [PASS] pubcount:/base/cmd_vel      1 publishers (need exactly 1)
# ==== 5/5 checks passed ====
# (exit 0)
#
# Expected output (--demo --break tf)
# -----------------------------------------------------------------------------
#
# [FAIL] tf:base_link<-arm_base      lookup failed: "arm_base" passed to lookupTransform...
# ==== 4/5 checks passed ====
# (exit 1)   <-- the run would abort. This is integration defect #1.
#
# Expected output (--demo --break pubcount)
# -----------------------------------------------------------------------------
#
# [FAIL] pubcount:/base/cmd_vel      2 publishers (need exactly 1)
# ==== 4/5 checks passed ====
# (exit 1)   <-- the run would abort. This is integration defect #4 (controller clash).
#
# NOTE: against your LIVE stack, run_battery also includes the lifecycle checks
# (controller_server, planner_server, move_group, safety_wrapper). A move_group
# stuck 'inactive' is integration defect #2 (bring-up-order deadlock), named for
# you in the detail string so you fix the ORDER, not the node.
# -----------------------------------------------------------------------------

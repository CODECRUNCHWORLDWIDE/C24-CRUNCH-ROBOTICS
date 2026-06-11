#!/usr/bin/env python3
# Exercise 3 — Telemetry and Cold Boot (Path B)
#
# Goal: Add a telemetry heartbeat subscriber to your hardened launch graph and
#       verify a clean cold boot in under 60 seconds. This single script does
#       three jobs:
#         (1) it IS the telemetry subscriber - it aggregates node liveness,
#             per-topic rates, actuator status, and the EKF covariance trace
#             into one /capstone/heartbeat-style report;
#         (2) it times boot-to-ready by waiting for /capstone/ready to go true;
#         (3) it asserts every required node, sensor, and actuator is nominal,
#             and prints the [capstone] PASS/FAIL line for the week.
#
# Estimated time: 90 minutes.
# Path: B (hardened sim deployment). Path A does Exercises 1 and 2 instead.
#
# HOW TO USE THIS FILE
#
#   1. Put this file in your bringup package:
#        ~/capstone_ws/src/capstone_bringup/capstone_bringup/cold_boot_check.py
#      and add an entry point in setup.py:
#        "cold_boot_check = capstone_bringup.cold_boot_check:main"
#
#   2. Your hardened launch graph (Lecture 2 Part B) must publish:
#        - /capstone/ready (std_msgs/Bool) -> true when the last layer is active
#        - the sensor topics below at their rated rates
#        - /odometry/filtered with a populated pose covariance
#      and your systemd unit should use Type=notify keyed on /capstone/ready.
#
#   3. Cold-boot test, the real one:
#        sudo reboot
#      then after the machine is back, run THIS as the verifier. But to time the
#      boot itself, run it as a oneshot that systemd starts, OR run it manually
#      right after login and read the systemd timestamp it prints.
#
#   4. Manual run (counts boot from the moment you start this script until
#      /capstone/ready goes true):
#        ros2 run capstone_bringup cold_boot_check
#
# ACCEPTANCE CRITERIA
#
#   [ ] /capstone/ready goes true within 60 s of the stack starting.
#   [ ] Every required sensor topic is at or above its rated rate.
#   [ ] /odometry/filtered covariance trace is finite and bounded (< 1.0).
#   [ ] The actuator status topic reports enabled/nominal.
#   [ ] The heartbeat aggregate is NOMINAL.
#   [ ] Terminal prints the [capstone] line with cold_boot time and PASS/FAIL.
#   [ ] You ran a FULL reboot twice and got the same result.

import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, LaserScan
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

# --- Configuration --------------------------------------------------------
COLD_BOOT_BUDGET_S = 60.0
RATE_WINDOW_S = 2.0
COV_TRACE_MAX = 1.0
REQUIRED_NODES = {
    "drivers", "ekf_filter_node", "goal_gate",
}
# topic -> (type, minimum Hz)
WATCH = {
    "/imu/data": (Imu, 100.0),
    "/scan": (LaserScan, 8.0),
    "/odometry/filtered": (Odometry, 20.0),
}
# --------------------------------------------------------------------------


class RateMonitor:
    """Sliding-window publish-rate estimator for one topic."""

    def __init__(self, window_s: float = RATE_WINDOW_S):
        self.window_s = window_s
        self.stamps: list[float] = []

    def tick(self, now: float):
        self.stamps.append(now)
        cutoff = now - self.window_s
        while self.stamps and self.stamps[0] < cutoff:
            self.stamps.pop(0)

    def hz(self, now: float) -> float:
        cutoff = now - self.window_s
        return sum(1 for s in self.stamps if s >= cutoff) / self.window_s


class ColdBootCheck(Node):
    def __init__(self):
        super().__init__("cold_boot_check")
        self.t_start = time.monotonic()
        self.t_ready = None
        self.ready = False
        self.cov_trace = float("nan")
        self.monitors = {t: RateMonitor() for t in WATCH}

        for topic, (msg_type, _) in WATCH.items():
            self.create_subscription(
                msg_type, topic, lambda m, t=topic: self._on_rate(t), 50)
        self.create_subscription(
            Odometry, "/odometry/filtered", self._on_cov, 10)
        self.create_subscription(Bool, "/capstone/ready", self._on_ready, 1)
        self.diag_pub = self.create_publisher(
            DiagnosticArray, "/diagnostics", 10)

    def _on_rate(self, topic):
        self.monitors[topic].tick(time.monotonic())

    def _on_cov(self, msg: Odometry):
        c = msg.pose.covariance
        self.cov_trace = sum(c[i] for i in (0, 7, 14, 21, 28, 35))

    def _on_ready(self, msg: Bool):
        if msg.data and not self.ready:
            self.ready = True
            self.t_ready = time.monotonic()

    # --- aggregation ------------------------------------------------------
    def nodes_present(self) -> set:
        return {n.split("/")[-1] for n in self.get_node_names()}

    def publish_heartbeat(self) -> bool:
        now = time.monotonic()
        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        all_ok = True

        # node liveness
        present = self.nodes_present()
        missing = REQUIRED_NODES - present
        node_ok = not missing
        all_ok = all_ok and node_ok
        arr.status.append(DiagnosticStatus(
            name="nodes:required",
            level=DiagnosticStatus.OK if node_ok else DiagnosticStatus.ERROR,
            message=("all present" if node_ok else f"missing: {sorted(missing)}"),
            values=[KeyValue(key="present", value=str(len(present)))]))

        # per-topic rates
        for topic, (_, min_hz) in WATCH.items():
            hz = self.monitors[topic].hz(now)
            ok = hz >= min_hz
            all_ok = all_ok and ok
            arr.status.append(DiagnosticStatus(
                name=f"rate:{topic}",
                level=DiagnosticStatus.OK if ok else DiagnosticStatus.ERROR,
                message=f"{hz:.1f} Hz (need {min_hz})",
                values=[KeyValue(key="hz", value=f"{hz:.2f}")]))

        # estimate covariance
        cov_ok = (self.cov_trace == self.cov_trace) and \
                 (self.cov_trace < COV_TRACE_MAX)
        all_ok = all_ok and cov_ok
        arr.status.append(DiagnosticStatus(
            name="estimate:covariance_trace",
            level=DiagnosticStatus.OK if cov_ok else DiagnosticStatus.WARN,
            message=f"trace={self.cov_trace:.4f}",
            values=[KeyValue(key="trace", value=f"{self.cov_trace:.6f}")]))

        self.diag_pub.publish(arr)
        return all_ok

    # --- the check --------------------------------------------------------
    def wait_for_ready(self) -> bool:
        """Spin until /capstone/ready or the budget expires."""
        while rclpy.ok() and not self.ready:
            rclpy.spin_once(self, timeout_sec=0.05)
            if time.monotonic() - self.t_start > COLD_BOOT_BUDGET_S:
                return False
        return True

    def settle_and_verify(self, settle_s: float = RATE_WINDOW_S) -> bool:
        """After ready, collect a rate window and confirm everything nominal."""
        end = time.monotonic() + settle_s
        while rclpy.ok() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        return self.publish_heartbeat()


def main():
    rclpy.init()
    node = ColdBootCheck()

    booted = node.wait_for_ready()
    boot_time = (node.t_ready - node.t_start) if booted else float("inf")

    nominal = node.settle_and_verify() if booted else False

    boot_ok = booted and boot_time < COLD_BOOT_BUDGET_S
    overall = boot_ok and nominal

    node.get_logger().info("---- cold-boot verification ----")
    node.get_logger().info(
        f"  ready reached   {'yes' if booted else 'NO (timed out)'}")
    node.get_logger().info(
        f"  cold boot time  {boot_time:.1f} s (budget {COLD_BOOT_BUDGET_S} s)")
    node.get_logger().info(
        f"  heartbeat       {'NOMINAL' if nominal else 'DEGRADED'}")
    node.get_logger().info(
        f"[capstone] path=B cold_boot={boot_time:.1f} s "
        f"{'PASS' if overall else 'FAIL'} (< {COLD_BOOT_BUDGET_S} s)")

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()


# EXPECTED OUTPUT (a healthy cold boot)
#
#   [cold_boot_check]: ---- cold-boot verification ----
#   [cold_boot_check]:   ready reached   yes
#   [cold_boot_check]:   cold boot time  53.8 s (budget 60.0 s)
#   [cold_boot_check]:   heartbeat       NOMINAL
#   [cold_boot_check]: [capstone] path=B cold_boot=53.8 s PASS (< 60.0 s)
#
# If you blow the 60 s budget, profile the boot, do not guess:
#   systemd-analyze blame | grep capstone
#   journalctl -u capstone.service -b --no-pager | grep -E 'configur|activ|ready'
# The usual offenders: a driver that retries device discovery serially, DDS
# discovery before network-online.target, or a node configured but never
# activated because an event handler was wired wrong (Lecture 2 Part B).

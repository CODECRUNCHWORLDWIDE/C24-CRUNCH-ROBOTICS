#!/usr/bin/env python3
# Exercise 2 — Measure a simulator from ROS2 (the sim-agnostic metrics tool)
#
# Goal: Build the measurement tool the whole week leans on. It subscribes to /clock
#       and a sensor topic and computes, from the OUTSIDE, the three throughput/fidelity
#       numbers you compare across simulators:
#         * real-time factor (RTF)  = sim-time elapsed / wall-time elapsed
#         * mean step-time (ms)     = wall-time per published /clock tick
#         * sensor rate (Hz)        = measured publish rate of the sensor topic
#       Because it reads only ROS2 topics, it works against Gz Sim, Isaac Sim, or any
#       sim that bridges /clock + a sensor — which is exactly what makes the Gz-vs-Isaac
#       comparison FAIR (Lecture 2 Part 3.1): the measurement tool doesn't change.
#
# Estimated time: 50 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   AGAINST A LIVE SIM (the real use):
#       source /opt/ros/jazzy/setup.bash
#       # start your sim with use_sim_time / a /clock publisher and the sensor bridge
#       python3 exercise-02-sim-metrics.py --duration 30 --sensor /scan
#     It collects for --duration seconds, then prints the metrics table. Run it once
#     per simulator/engine, holding robot + behavior fixed, and diff the tables.
#
#   SELF-TEST (no ROS2 needed — verifies the math):
#       python3 exercise-02-sim-metrics.py --self-test
#     Feeds synthetic (sim_time, wall_time, sensor_stamp) samples representing a sim
#     running at RTF≈1.2 with a 10 Hz scan, and asserts the computed metrics match.
#
# ACCEPTANCE CRITERIA
#
#   [ ] --self-test prints "SELF-TEST PASS" and exits 0 (the metric math is correct).
#   [ ] Against a live sim, it prints RTF, mean step-time (ms), and sensor Hz.
#   [ ] You ran it against your week-3 robot in (at least) two engines/sims and the
#       tables differ in at least one metric.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import argparse
import sys


class SimMetrics:
    """Pure metric math, decoupled from ROS2 so it's unit-testable.

    Feed it (sim_time_sec, wall_time_sec) pairs as /clock arrives, and sensor message
    wall-times as the sensor publishes. It computes RTF, step-time, and sensor rate.
    """

    def __init__(self) -> None:
        self._first_sim = None
        self._first_wall = None
        self._last_sim = None
        self._last_wall = None
        self._clock_ticks = 0
        self._sensor_walls: list[float] = []

    def on_clock(self, sim_time_sec: float, wall_time_sec: float) -> None:
        if self._first_sim is None:
            self._first_sim = sim_time_sec
            self._first_wall = wall_time_sec
        self._last_sim = sim_time_sec
        self._last_wall = wall_time_sec
        self._clock_ticks += 1

    def on_sensor(self, wall_time_sec: float) -> None:
        self._sensor_walls.append(wall_time_sec)

    def real_time_factor(self) -> float:
        """sim-time elapsed / wall-time elapsed. 1.0 = real time; >1 faster than real."""
        if self._first_sim is None or self._clock_ticks < 2:
            return float("nan")
        sim_elapsed = self._last_sim - self._first_sim
        wall_elapsed = self._last_wall - self._first_wall
        if wall_elapsed <= 0:
            return float("nan")
        return sim_elapsed / wall_elapsed

    def mean_step_time_ms(self) -> float:
        """Mean wall-clock time between /clock ticks, in ms (the throughput primitive)."""
        if self._clock_ticks < 2:
            return float("nan")
        wall_elapsed = self._last_wall - self._first_wall
        return 1000.0 * wall_elapsed / (self._clock_ticks - 1)

    def sensor_hz(self) -> float:
        """Measured sensor publish rate (Hz) over the collection window."""
        if len(self._sensor_walls) < 2:
            return float("nan")
        span = self._sensor_walls[-1] - self._sensor_walls[0]
        if span <= 0:
            return float("nan")
        return (len(self._sensor_walls) - 1) / span

    def report(self, sensor_topic: str) -> str:
        return (
            "=== SIM METRICS ===\n"
            f"  clock ticks         : {self._clock_ticks}\n"
            f"  real-time factor    : {self.real_time_factor():.3f}\n"
            f"  mean step-time (ms) : {self.mean_step_time_ms():.3f}\n"
            f"  {sensor_topic} rate (Hz)   : {self.sensor_hz():.2f}\n"
        )


def run_live(duration: float, sensor_topic: str) -> int:
    """Subscribe to /clock and the sensor topic; collect for `duration`; report."""
    import time

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from rosgraph_msgs.msg import Clock
    # Type of the sensor topic is resolved generically via the topic's type at runtime
    # would be ideal; for simplicity we accept LaserScan or Imu, the two common cases.
    from sensor_msgs.msg import Imu, LaserScan

    metrics = SimMetrics()

    class MetricsNode(Node):
        def __init__(self) -> None:
            super().__init__("sim_metrics")
            # /clock is RELIABLE/VOLATILE by convention; the sensor is BEST_EFFORT
            # (Week 5!). Using qos_profile_sensor_data on the sensor avoids the silent
            # mismatch that would make this tool read 0 Hz against a BEST_EFFORT bridge.
            self.create_subscription(Clock, "/clock", self._on_clock, 10)
            msg_type = Imu if "imu" in sensor_topic.lower() else LaserScan
            self.create_subscription(
                msg_type, sensor_topic, self._on_sensor, qos_profile_sensor_data
            )

        def _on_clock(self, msg: Clock) -> None:
            sim_t = msg.clock.sec + msg.clock.nanosec * 1e-9
            metrics.on_clock(sim_t, time.monotonic())

        def _on_sensor(self, _msg) -> None:
            metrics.on_sensor(time.monotonic())

    rclpy.init()
    node = MetricsNode()
    node.get_logger().info(
        f"collecting for {duration}s — drive your robot now (sensor={sensor_topic})"
    )
    end = time.monotonic() + duration
    while rclpy.ok() and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    print(metrics.report(sensor_topic))
    node.destroy_node()
    rclpy.shutdown()

    # A trustworthy reading needs clock + sensor data.
    ok = metrics._clock_ticks >= 2 and len(metrics._sensor_walls) >= 2
    if not ok:
        print("WARN: not enough /clock or sensor samples. Is the sim publishing /clock?")
        print("      Is use_sim_time set and the sensor bridged? (Check QoS — Week 5.)")
    return 0 if ok else 1


def run_self_test() -> int:
    """Synthetic samples: a sim at RTF≈1.2 publishing /clock at 100 Hz and /scan at 10 Hz."""
    metrics = SimMetrics()
    # 100 clock ticks: each wall-step is 1/120 s but sim advances 1/100 s -> RTF=1.2.
    wall = 0.0
    sim = 0.0
    for i in range(101):
        metrics.on_clock(sim, wall)
        sim += 1.0 / 100.0          # sim advances 10 ms per tick
        wall += 1.0 / 120.0         # but only 1/120 s of wall passed -> faster than real
    # 10 Hz scan over ~0.83 s of wall (the wall span of the 100 ticks).
    wall_span = 100.0 / 120.0
    n_scans = 9
    for k in range(n_scans):
        metrics.on_sensor(k * (wall_span / (n_scans - 1)))

    rtf = metrics.real_time_factor()
    step = metrics.mean_step_time_ms()
    hz = metrics.sensor_hz()
    print(metrics.report("/scan"))

    ok = (
        abs(rtf - 1.2) < 0.02
        and abs(step - (1000.0 / 120.0)) < 0.1   # ~8.333 ms wall per tick
        and 9.0 < hz < 13.0
    )
    print(f"expected RTF≈1.20, step≈{1000.0/120.0:.3f} ms, scan≈10–11 Hz")
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    p = argparse.ArgumentParser(description="Measure a simulator from ROS2 topics.")
    p.add_argument("--duration", type=float, default=30.0)
    p.add_argument("--sensor", default="/scan", help="sensor topic to measure rate of")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        sys.exit(run_self_test())
    sys.exit(run_live(args.duration, args.sensor))


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--self-test)
# -----------------------------------------------------------------------------
#
# === SIM METRICS ===
#   clock ticks         : 101
#   real-time factor    : 1.200
#   mean step-time (ms) : 8.333
#   /scan rate (Hz)     : 10.xx
#
# expected RTF≈1.20, step≈8.333 ms, scan≈10–11 Hz
# SELF-TEST PASS
#
# Against a LIVE sim, the same node prints the real RTF/step-time/Hz for THAT sim.
# Run it once per simulator (Gz/DART, Gz/Bullet, Isaac/PhysX), holding robot + behavior
# fixed, and the three tables ARE your throughput/fidelity comparison.
# -----------------------------------------------------------------------------

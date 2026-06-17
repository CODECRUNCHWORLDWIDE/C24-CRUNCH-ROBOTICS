#!/usr/bin/env python3
# Exercise 2 — Software watchdog + perception confidence gate (rclpy, ROS2 Jazzy)
#
# Goal: Build two of the four mitigation layers from Lecture 2 as a single,
#       runnable rclpy node:
#         * a SOFTWARE WATCHDOG that latches a software E-stop when a critical
#           sensor stops publishing within its deadline, and
#         * a PERCEPTION CONFIDENCE GATE that vetoes acting on low-confidence
#           perception.
#
#       The node owns the last word on motion: while the E-stop is latched it
#       publishes a zero Twist on /cmd_vel_safe at a fixed rate, so a latched
#       stop always beats a stale autonomy command at a downstream mux.
#
# Estimated time: 60 minutes.
#
# HOW TO USE THIS FILE
#   1. Fill in the bodies marked `# TODO`. Do not change public signatures.
#   2. Run the offline self-test (no ROS graph, no hardware needed):
#
#         python3 exercise-02-watchdog-and-confidence-gate.py --selftest
#
#      When all TODOs are correct it prints:  SELFTEST PASSED
#   3. To run it as a real node in your workspace (optional, needs a graph):
#
#         python3 exercise-02-watchdog-and-confidence-gate.py
#
#      Then in another terminal, stop publishing /scan and watch the watchdog
#      latch the software E-stop; echo /cmd_vel_safe to see the zero Twist.
#
# ACCEPTANCE CRITERIA
#   [ ] All TODOs implemented.
#   [ ] `--selftest` prints SELFTEST PASSED.
#   [ ] The watchdog deadline logic is pure (no wall-clock surprises): it trips
#       when (now - last_seen) > deadline for ANY monitored topic.
#   [ ] The confidence gate is CONSERVATIVE: any sub-threshold signal vetoes.
#   [ ] The E-stop is LATCHING: once tripped it stays tripped until re-arm.
#
# Hints are at the bottom. Don't peek for 15 minutes.

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Pure logic (no ROS dependency) — this is what the self-test exercises.
# Keeping the safety logic ROS-free makes it unit-testable, which is exactly
# what a safety case's validation plan needs.
# ---------------------------------------------------------------------------


@dataclass
class Watchdog:
    """Deadline monitor over a set of critical topics.

    For each topic name we record the last time (seconds, monotonic) a message
    was seen. `check(now)` returns the list of topics whose deadline has been
    missed. The owning E-stop trips if that list is non-empty.
    """

    deadlines: dict[str, float]                      # topic -> max gap (seconds)
    _last_seen: dict[str, float] = field(default_factory=dict)

    def heartbeat(self, topic: str, now: float) -> None:
        """Record that `topic` produced a message at time `now`."""
        # TODO: store `now` as the last-seen time for `topic`.
        raise NotImplementedError

    def stale_topics(self, now: float) -> list[str]:
        """Return topics whose (now - last_seen) exceeds their deadline.

        A topic that has NEVER been seen counts as stale once `now` exceeds its
        own deadline (i.e. treat last_seen as 0.0 / start-of-time until proven
        otherwise) — a sensor that never came up is a failed sensor.
        """
        # TODO: return [topic for each monitored topic that is past deadline].
        #       Use self._last_seen.get(topic, 0.0) as the default last-seen.
        raise NotImplementedError


@dataclass
class SoftwareEStop:
    """A LATCHING software E-stop.

    Once `trip()` is called the state is latched True until `rearm()` is called.
    `engaged` is the single boolean every motion path must consult.
    """

    _latched: bool = False

    @property
    def engaged(self) -> bool:
        return self._latched

    def trip(self, reason: str) -> None:
        """Latch the stop. Idempotent: tripping an already-latched stop is a no-op."""
        # TODO: set the latch True. (Logging the reason is done by the caller.)
        raise NotImplementedError

    def rearm(self) -> None:
        """Deliberately clear the latch. The ONLY way out of a tripped state."""
        # TODO: set the latch False.
        raise NotImplementedError


def gate_action(detection_confidence: float,
                depth_valid_fraction: float,
                min_conf: float = 0.6,
                min_depth_valid: float = 0.7) -> bool:
    """Return True ONLY if it is safe to act on this perception.

    Conservative by construction: ANY signal below its threshold vetoes the
    action. A vetoed action should slow/stop and request operator assist —
    never guess. Returning True means "confident enough to act."
    """
    # TODO: return False if detection_confidence < min_conf;
    #       return False if depth_valid_fraction < min_depth_valid;
    #       otherwise return True.
    raise NotImplementedError


# ---------------------------------------------------------------------------
# The rclpy node — thin wiring around the pure logic above.
# Imported lazily so the self-test runs without ROS installed.
# ---------------------------------------------------------------------------


def _run_node() -> None:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Bool
    from geometry_msgs.msg import Twist
    from sensor_msgs.msg import LaserScan, Imu

    class SafetyNode(Node):
        def __init__(self) -> None:
            super().__init__("safety_watchdog_gate")

            # Deadlines in seconds. Justify each in your safety case:
            # at 0.5 m/s, a 0.2 s LiDAR deadline = up to 10 cm of travel on
            # stale data before the latch — state that in HZ-03's mitigation.
            self.wd = Watchdog(deadlines={"/scan": 0.2, "/imu/data": 0.1})
            self.estop = SoftwareEStop()

            self.create_subscription(LaserScan, "/scan", self._on_scan, 10)
            self.create_subscription(Imu, "/imu/data", self._on_imu, 10)
            self.create_subscription(Bool, "/safety/rearm", self._on_rearm, 10)

            self._zero_pub = self.create_publisher(Twist, "/cmd_vel_safe", 10)
            self._estop_pub = self.create_publisher(Bool, "/safety/estop_state", 10)

            # 50 Hz tick: faster than any controller, so a latched zero wins.
            self.create_timer(0.02, self._tick)
            self.get_logger().info("safety_watchdog_gate up; monitoring /scan, /imu/data")

        def _now(self) -> float:
            return self.get_clock().now().nanoseconds * 1e-9

        def _on_scan(self, _msg: "LaserScan") -> None:
            self.wd.heartbeat("/scan", self._now())

        def _on_imu(self, _msg: "Imu") -> None:
            self.wd.heartbeat("/imu/data", self._now())

        def _on_rearm(self, msg: "Bool") -> None:
            if msg.data and self.estop.engaged:
                self.estop.rearm()
                self.get_logger().warn("Software E-stop RE-ARMED by operator")

        def _tick(self) -> None:
            stale = self.wd.stale_topics(self._now())
            if stale and not self.estop.engaged:
                self.estop.trip(reason=f"stale topics: {stale}")
                self.get_logger().error(f"SOFTWARE E-STOP LATCHED — stale: {stale}")

            # Publish the latch state for the dashboard / mux.
            self._estop_pub.publish(Bool(data=self.estop.engaged))

            # While latched, hold zero velocity. This is the "last word".
            if self.estop.engaged:
                self._zero_pub.publish(Twist())

    rclpy.init()
    node = SafetyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


# ---------------------------------------------------------------------------
# Offline self-test — no ROS, no hardware. Validates the pure safety logic.
# ---------------------------------------------------------------------------


def _selftest() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    # --- Watchdog ---
    wd = Watchdog(deadlines={"/scan": 0.2, "/imu/data": 0.1})

    # Fresh heartbeats: nothing stale.
    wd.heartbeat("/scan", now=10.0)
    wd.heartbeat("/imu/data", now=10.0)
    check(wd.stale_topics(now=10.05) == [], "fresh heartbeats should not be stale")

    # /imu deadline is 0.1: at now=10.15 it is 0.05 past deadline -> stale.
    # /scan deadline is 0.2: at now=10.15 it is still fresh.
    check(wd.stale_topics(now=10.15) == ["/imu/data"],
          "imu should be stale at 0.15s gap, scan should not")

    # Both stale after a long gap.
    check(sorted(wd.stale_topics(now=11.0)) == ["/imu/data", "/scan"],
          "both topics stale after 1s gap")

    # A never-seen topic is stale once now exceeds its deadline.
    wd2 = Watchdog(deadlines={"/never": 0.2})
    check(wd2.stale_topics(now=0.3) == ["/never"],
          "a topic that never published should be stale")

    # --- SoftwareEStop latching behavior ---
    es = SoftwareEStop()
    check(es.engaged is False, "estop should start un-latched")
    es.trip("test")
    check(es.engaged is True, "trip should latch the estop")
    es.trip("again")  # idempotent
    check(es.engaged is True, "re-tripping stays latched")
    es.rearm()
    check(es.engaged is False, "rearm should clear the latch")

    # --- Confidence gate ---
    check(gate_action(0.9, 0.9) is True, "high confidence + valid depth -> act")
    check(gate_action(0.5, 0.9) is False, "low detection confidence -> veto")
    check(gate_action(0.9, 0.5) is False, "too many NaN depths -> veto")
    check(gate_action(0.6, 0.7) is True, "exactly at thresholds -> act (>=)")
    check(gate_action(0.59, 0.99) is False, "just below conf threshold -> veto")

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SELFTEST PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true",
                        help="run offline logic tests (no ROS needed)")
    args = parser.parse_args()
    if args.selftest:
        return _selftest()
    _run_node()
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# HINTS (read only if stuck > 15 min)
# ---------------------------------------------------------------------------
#
# Watchdog.heartbeat:
#     self._last_seen[topic] = now
#
# Watchdog.stale_topics:
#     return [t for t, d in self.deadlines.items()
#             if now - self._last_seen.get(t, 0.0) > d]
#
# SoftwareEStop.trip:
#     self._latched = True
#
# SoftwareEStop.rearm:
#     self._latched = False
#
# gate_action:
#     if detection_confidence < min_conf:
#         return False
#     if depth_valid_fraction < min_depth_valid:
#         return False
#     return True
#
# Why >= passes "exactly at threshold": confidence of exactly min_conf is
# "confident enough" — we veto strictly BELOW threshold, not at it. Be
# deliberate about boundary semantics; a reviewer will ask.

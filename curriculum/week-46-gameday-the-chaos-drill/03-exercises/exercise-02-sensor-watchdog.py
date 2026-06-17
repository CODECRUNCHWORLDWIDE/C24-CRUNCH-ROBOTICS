#!/usr/bin/env python3
# Exercise 2 -- The sensor watchdog + health aggregator.
#
# Goal: build the detection-and-degradation half of gameday (Lecture 1 sections 3-5).
#       A watchdog detects a /scan dropout via a staleness check (and, in the real
#       ROS2 version, a QoS deadline event), per-sensor statuses are fused into ONE
#       robot-health signal, and the aggregator decides DEGRADED vs FAULT based on
#       which sensor losses are survivable. The lesson: a robot must NOTICE a fault,
#       and "noticing" is concrete engineering, not a vibe.
#
# Estimated time: 50 minutes. Runnable. Pure-Python simulator -- no ROS2 needed to
# exercise the logic. The real version is a ROS2 node with QoS deadline callbacks.
#
# HOW TO USE THIS FILE
#   python3 exercise-02-sensor-watchdog.py
#   Fill in the two TODOs (the staleness rule and the DEGRADED/FAULT decision).
#
# ACCEPTANCE CRITERIA
#   [ ] A stale sensor (no fresh message within the deadline) is detected as DEAD.
#   [ ] can_degrade() encodes which losses are survivable: losing LiDAR alone with
#       camera+imu alive -> survivable (DEGRADED); losing LiDAR AND camera -> not
#       survivable (FAULT -> controlled stop).
#   [ ] The aggregator emits OK / DEGRADED / FAULT correctly across the scenarios.
#   [ ] `python3 exercise-02-sensor-watchdog.py` prints ALL CHECKS PASSED.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import sys
from dataclasses import dataclass, field

# A sensor is DEAD if no fresh message arrived within this many seconds
# (the staleness backstop from Lecture 1 section 3.2; the real node ALSO uses a
#  QoS deadline event for sub-200ms detection -- section 3.1).
STALENESS_TIMEOUT_S = 0.5


@dataclass
class SensorWatchdog:
    name: str
    last_msg_time: float = -1e9   # sim clock seconds of the last fresh message
    status: str = "UNKNOWN"

    def on_message(self, now: float) -> None:
        """Call when a fresh message arrives."""
        self.last_msg_time = now
        self.status = "OK"

    def tick(self, now: float) -> None:
        """Call on a timer to age out the sensor."""
        # TODO 1: set self.status to 'DEAD' if the time since last_msg_time exceeds
        #         STALENESS_TIMEOUT_S, else 'OK'. (The robot must NOTICE the dropout.)
        if now - self.last_msg_time > STALENESS_TIMEOUT_S:
            self.status = "DEAD"
        else:
            self.status = "OK"


@dataclass
class HealthAggregator:
    """Fuses per-sensor status into ONE robot-health signal and decides whether a
    given loss is survivable (Lecture 1 section 4)."""
    watchdogs: dict[str, SensorWatchdog] = field(default_factory=dict)

    def statuses(self) -> dict[str, str]:
        return {n: w.status for n, w in self.watchdogs.items()}

    def can_degrade(self, statuses: dict[str, str]) -> bool:
        """Encode which sensor losses are survivable. This encoding IS part of your
        safety case. Rule for the capstone:
          - Navigation needs at least ONE of {lidar, camera} alive AND the imu alive.
          - Losing lidar alone (camera+imu alive) -> survivable (camera-only nav).
          - Losing lidar AND camera -> NOT survivable (no exteroceptive sensing).
          - Losing imu -> NOT survivable (no reliable state estimate)."""
        dead = {n for n, s in statuses.items() if s == "DEAD"}
        if "imu" in dead:
            return False
        exteroceptive_alive = (statuses.get("lidar") == "OK") or (statuses.get("camera") == "OK")
        return exteroceptive_alive

    def overall(self) -> str:
        statuses = self.statuses()
        any_dead = any(s == "DEAD" for s in statuses.values())
        all_ok = all(s == "OK" for s in statuses.values())
        # TODO 2: return 'OK' if all OK; if any DEAD, return 'DEGRADED' when
        #         can_degrade(statuses) else 'FAULT'. (FAULT -> controlled stop.)
        if all_ok:
            return "OK"
        if any_dead:
            return "DEGRADED" if self.can_degrade(statuses) else "FAULT"
        return "DEGRADED"  # e.g. a STALE-but-not-dead sensor


def build() -> HealthAggregator:
    agg = HealthAggregator()
    for name in ("lidar", "camera", "imu"):
        agg.watchdogs[name] = SensorWatchdog(name)
    return agg


def feed_all(agg: HealthAggregator, now: float, alive: set[str]) -> None:
    """Deliver a fresh message to each alive sensor at time `now`, then tick all."""
    for name, wd in agg.watchdogs.items():
        if name in alive:
            wd.on_message(now)
    for wd in agg.watchdogs.values():
        wd.tick(now)


def run_scenarios() -> bool:
    ok = True

    # Scenario A: all healthy -> OK
    agg = build()
    feed_all(agg, now=10.0, alive={"lidar", "camera", "imu"})
    a = agg.overall()
    print(f"A  all healthy                      -> {a}")
    ok &= (a == "OK")

    # Scenario B: lidar killed at T=10, now T=11 (1 s later, > 0.5 s timeout).
    # camera+imu still publishing -> survivable -> DEGRADED.
    agg = build()
    feed_all(agg, now=10.0, alive={"lidar", "camera", "imu"})  # last lidar msg @ 10
    feed_all(agg, now=11.0, alive={"camera", "imu"})            # lidar now stale
    b = agg.overall()
    print(f"B  lidar dead, camera+imu alive      -> {b}  (detected: {agg.statuses()['lidar']})")
    ok &= (b == "DEGRADED")
    ok &= (agg.statuses()["lidar"] == "DEAD")  # the robot NOTICED

    # Scenario C: lidar AND camera dead -> no exteroceptive sensing -> FAULT (stop).
    agg = build()
    feed_all(agg, now=10.0, alive={"lidar", "camera", "imu"})
    feed_all(agg, now=11.0, alive={"imu"})
    c = agg.overall()
    print(f"C  lidar+camera dead, imu alive       -> {c}  (controlled stop)")
    ok &= (c == "FAULT")

    # Scenario D: imu dead -> no reliable state estimate -> FAULT regardless.
    agg = build()
    feed_all(agg, now=10.0, alive={"lidar", "camera", "imu"})
    feed_all(agg, now=11.0, alive={"lidar", "camera"})
    d = agg.overall()
    print(f"D  imu dead -> no state estimate      -> {d}  (controlled stop)")
    ok &= (d == "FAULT")

    return ok


def main() -> int:
    print("=" * 60)
    print("Sensor watchdog + health aggregator (Lecture 1 sections 3-5)")
    print("=" * 60)
    if run_scenarios():
        print("-" * 60)
        print("ALL CHECKS PASSED")
        return 0
    print("-" * 60)
    print("CHECKS FAILED -- see scenarios above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ---------------------------------------------------------------------------
# EXPECTED OUTPUT:
#
#   ============================================================
#   Sensor watchdog + health aggregator (Lecture 1 sections 3-5)
#   ============================================================
#   A  all healthy                      -> OK
#   B  lidar dead, camera+imu alive      -> DEGRADED  (detected: DEAD)
#   C  lidar+camera dead, imu alive       -> FAULT  (controlled stop)
#   D  imu dead -> no state estimate      -> FAULT  (controlled stop)
#   ------------------------------------------------------------
#   ALL CHECKS PASSED
#
# The takeaway: the robot NOTICES the dropout (B: lidar -> DEAD), and the aggregator
# decides DEGRADED (survivable, camera-only nav) vs FAULT (no safe perception ->
# controlled stop) by encoding which losses are survivable. That encoding is part of
# your Week 41 safety case.
# ---------------------------------------------------------------------------

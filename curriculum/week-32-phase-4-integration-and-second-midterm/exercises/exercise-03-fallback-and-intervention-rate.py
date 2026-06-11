#!/usr/bin/env python3
"""Exercise 3 — The three-rejection fallback switch and the intervention meter

Goal: Build the two things that turn the safety filter (Exercise 2) into a
      shippable leash: (1) the THREE-CONSECUTIVE-REJECTION switch that hands the
      task from the learned policy to the classical fallback, with the counter
      resetting on any safe action; and (2) the INTERVENTION METER that produces
      the deployment numbers you defend at the second-midterm review --
      rejections by constraint, fallback-episode rate, and filter latency.

Estimated time: 120 minutes. Runnable.

THE SWITCH LOGIC (Lecture 1 section 6)
  - A REJECT increments the consecutive-rejection counter.
  - A PASS or CLAMP (a safe action was found) RESETS the counter to 0.
  - On the 3rd consecutive REJECT, the SafetyGuardedPolicy fails -> the BT's
    ReactiveFallback ticks the classical branch -> the fallback "fires" for
    this episode -> the counter resets.
  This is why one bad action is noise and three-in-a-row is a stuck policy.

HOW TO USE THIS FILE
  Standalone, demo mode (no robot needed):
      source /opt/ros/jazzy/setup.bash
      python3 exercise-03-fallback-and-intervention-rate.py --demo

    The demo runs synthetic episodes. Some episodes the policy is "good"
    (PASS/CLAMP, no fallback); some it gets "stuck" (3 rejects in a row ->
    fallback fires). It prints the per-episode verdict stream and the final
    intervention-rate breakdown, then asserts the switch fired exactly when it
    should and exits 0.

  Against your live stack:
      python3 exercise-03-fallback-and-intervention-rate.py
      # Subscribes to /safety/status (the filter's verdict stream from
      # Exercise 2), tracks the consecutive-rejection counter, publishes
      # /policy/fallback (Bool) when the switch fires, and publishes the running
      # intervention meter on /safety/intervention_rate (JSON) for telemetry.

ACCEPTANCE CRITERIA
  [ ] --demo: the fallback fires ONLY on episodes with 3 consecutive rejections;
      the counter resets on a safe action; the breakdown prints; exit 0.
  [ ] A "good" episode (no 3-in-a-row) does NOT fire the fallback even if it has
      isolated rejections separated by safe actions.
  [ ] The intervention rate (fallback episodes / total) is reported as a
      fraction, alongside the rejection-by-constraint and clamp counts.
  [ ] Against the live stack, /policy/fallback latches True for an episode where
      the policy is stuck, and the meter on /safety/intervention_rate updates.

Expected output is at the bottom of the file.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field

import rclpy
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                       ReliabilityPolicy)
from std_msgs.msg import Bool, String


# --- the leash switch --------------------------------------------------------
class ThreeStrikeSwitch:
    """Counts CONSECUTIVE rejections. Resets on a safe action. Fires the
    fallback on the 3rd consecutive rejection."""

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.consecutive = 0

    def on_verdict(self, verdict: str) -> bool:
        """Feed one filter verdict. Returns True iff the fallback should fire NOW."""
        if verdict.startswith("REJECT"):
            self.consecutive += 1
            if self.consecutive >= self.threshold:
                self.consecutive = 0      # reset after firing
                return True
        else:
            # PASS or CLAMP: a safe action was found -> the run of rejections ends.
            self.consecutive = 0
        return False


# --- the intervention meter --------------------------------------------------
@dataclass
class InterventionMeter:
    """The deployment numbers. Aggregated across episodes."""
    episodes: int = 0
    successes: int = 0
    actions: int = 0
    clamp_velocity: int = 0
    clamp_workspace: int = 0
    rejections: int = 0
    fallback_episodes: int = 0
    policy_latencies_ms: list = field(default_factory=list)
    filter_latencies_ms: list = field(default_factory=list)

    def record_verdict(self, verdict: str) -> None:
        self.actions += 1
        if verdict.startswith("CLAMP(velocity"):
            self.clamp_velocity += 1
        elif verdict.startswith("CLAMP"):
            self.clamp_workspace += 1
        elif verdict.startswith("REJECT"):
            self.rejections += 1

    def intervention_rate(self) -> float:
        """The STRONG signal: fraction of episodes the FALLBACK carried."""
        return self.fallback_episodes / max(self.episodes, 1)

    def report(self) -> str:
        sr = self.successes / max(self.episodes, 1)
        lines = [
            f"episodes={self.episodes}",
            f"  success:        {self.successes}/{self.episodes} ({sr*100:.1f}%)",
            f"  clamps:         velocity={self.clamp_velocity} "
            f"workspace={self.clamp_workspace}  (of {self.actions} actions)",
            f"  rejections:     {self.rejections} actions",
            f"  fallback fired: {self.fallback_episodes} episodes "
            f"({self.intervention_rate()*100:.1f}%)",
            f"  intervention rate (episodes carried by the leash): "
            f"{self.intervention_rate()*100:.1f}%",
        ]
        return "\n".join(lines)


# --- the ROS2 node (live mode) ----------------------------------------------
class FallbackMeterNode(Node):
    def __init__(self) -> None:
        super().__init__("fallback_meter")
        self.switch = ThreeStrikeSwitch(threshold=3)
        self.meter = InterventionMeter()
        self.create_subscription(String, "/safety/status", self._on_status, 10)
        latched = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             history=HistoryPolicy.KEEP_LAST, depth=1)
        self._fallback_pub = self.create_publisher(Bool, "/policy/fallback", latched)
        self._meter_pub = self.create_publisher(
            String, "/safety/intervention_rate", latched)
        self.get_logger().info("fallback meter up; watching /safety/status")

    def _on_status(self, msg: String) -> None:
        try:
            verdict = json.loads(msg.data).get("verdict", "PASS")
        except (json.JSONDecodeError, AttributeError):
            return
        self.meter.record_verdict(verdict)
        if self.switch.on_verdict(verdict):
            self.get_logger().warn(
                "THREE consecutive rejections -> firing classical fallback")
            self._fallback_pub.publish(Bool(data=True))
            self.meter.fallback_episodes += 1
        self._meter_pub.publish(String(data=json.dumps({
            "actions": self.meter.actions,
            "rejections": self.meter.rejections,
            "clamps": self.meter.clamp_velocity + self.meter.clamp_workspace,
            "fallback_episodes": self.meter.fallback_episodes,
        })))


# --- demo harness ------------------------------------------------------------
def run_demo() -> int:
    """Run synthetic episodes through the switch + meter and assert correctness."""
    meter = InterventionMeter()

    # Each episode is a verdict stream. The leash should fire only when there
    # are 3 REJECTs in a ROW (not merely 3 rejects total).
    episodes = {
        "ep1 clean":            ["PASS", "PASS", "CLAMP(velocity)", "PASS"],
        "ep2 isolated rejects": ["REJECT(workspace)", "PASS", "REJECT(workspace)",
                                 "PASS", "REJECT(velocity)", "PASS"],   # 3 total, not in a row
        "ep3 stuck policy":     ["PASS", "REJECT(workspace:below_table)",
                                 "REJECT(workspace:below_table)",
                                 "REJECT(workspace:below_table)"],      # 3 in a row -> fallback
        "ep4 clean":            ["CLAMP(velocity)", "PASS", "PASS"],
    }
    expect_fallback = {"ep1 clean": False, "ep2 isolated rejects": False,
                       "ep3 stuck policy": True, "ep4 clean": False}

    for name, stream in episodes.items():
        switch = ThreeStrikeSwitch(threshold=3)   # fresh per episode
        meter.episodes += 1
        fired = False
        for verdict in stream:
            meter.record_verdict(verdict)
            if switch.on_verdict(verdict):
                fired = True
        if fired:
            meter.fallback_episodes += 1
            meter.successes += 1     # fallback completed the task
            tag = "FALLBACK FIRED (classical planner completed it)"
        else:
            meter.successes += 1     # learned policy completed it
            tag = "learned policy completed it"
        ok = fired == expect_fallback[name]
        print(f"  {name:22s} verdicts={len(stream):2d}  "
              f"fallback={'YES' if fired else 'no ':3s}  "
              f"-> {'ok' if ok else 'MISMATCH'}  ({tag})")
        assert ok, f"{name}: expected fallback={expect_fallback[name]}, got {fired}"

    print("\n=== intervention-rate breakdown ===")
    print(meter.report())

    # The switch must fire exactly once (ep3) and never on isolated rejects (ep2).
    assert meter.fallback_episodes == 1, "fallback should fire exactly once (ep3)"
    print("\nSWITCH CORRECT: the fallback fired only on the episode with THREE "
          "consecutive rejections; isolated rejects (ep2) did NOT fire it, "
          "because the counter resets on every safe action.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Fallback switch + intervention meter")
    parser.add_argument("--demo", action="store_true",
                        help="run synthetic episodes through the switch + meter")
    args, ros_args = parser.parse_known_args(sys.argv[1:])

    if args.demo:
        sys.exit(run_demo())

    rclpy.init(args=ros_args)
    node = FallbackMeterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# EXPECTED OUTPUT (--demo)
# -----------------------------------------------------------------------------
#
#   ep1 clean              verdicts= 4  fallback=no   -> ok  (learned policy completed it)
#   ep2 isolated rejects   verdicts= 6  fallback=no   -> ok  (learned policy completed it)
#   ep3 stuck policy       verdicts= 4  fallback=YES  -> ok  (FALLBACK FIRED ...)
#   ep4 clean              verdicts= 3  fallback=no   -> ok  (learned policy completed it)
#
# === intervention-rate breakdown ===
# episodes=4
#   success:        4/4 (100.0%)
#   clamps:         velocity=2 workspace=0  (of 17 actions)
#   rejections:     6 actions
#   fallback fired: 1 episodes (25.0%)
#   intervention rate (episodes carried by the leash): 25.0%
#
# SWITCH CORRECT: the fallback fired only on the episode with THREE consecutive
# rejections; isolated rejects (ep2) did NOT fire it, because the counter resets
# on every safe action.
#
# READ ep2 CAREFULLY: it has THREE rejections total, but they are separated by
# safe actions, so the consecutive counter never reaches 3 -- the fallback does
# NOT fire. That is the whole point of "three consecutive": one bad action is
# noise; a RUN of three is a stuck policy. A 25% fallback rate on this toy set is
# high; on a real eval you want it in the low single digits, and the breakdown
# tells you which subtask to collect more demos for.
# -----------------------------------------------------------------------------

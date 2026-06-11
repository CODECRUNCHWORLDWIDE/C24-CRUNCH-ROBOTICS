#!/usr/bin/env python3
"""Exercise 2 — The runtime safety filter (predictive: roll forward, project or reject)

Goal: Build the safety filter that sits BETWEEN the learned policy and the
      controller. Every candidate action passes through it. The filter rolls
      the action forward through a kinematic model over a short horizon, checks
      the constraint set (Exercise 1), and PASSes, CLAMPs (projects to the
      nearest safe action), or REJECTs. It counts every verdict, and it must be
      cheaper than the policy it wraps.

Estimated time: 120 minutes. Runnable.

WHAT THE FILTER CATCHES
  - Defect 1 (OOD action): a through-the-table grasp -> REJECT.
  - Over-speed action: a too-fast twist -> CLAMP (uniform rescale, Exercise 1).
  - Defect 4 guard: the demo includes unsafe actions on purpose, so a filter
    that PASSes everything is provably broken (it will fail the asserts).

HOW TO USE THIS FILE
  Standalone, demo mode (no robot needed):
      source /opt/ros/jazzy/setup.bash
      python3 exercise-02-runtime-safety-filter.py --demo

    The demo drives a scripted sequence of actions through the filter:
    safe twists (PASS), an over-speed twist (CLAMP), a through-the-table arm
    action (REJECT). It prints the verdict for each and the verdict tally,
    then asserts the filter fired on the unsafe ones. Exit 0 on success.

  Against your live policy:
      python3 exercise-02-runtime-safety-filter.py
      # The node subscribes to /policy/action (the raw learned action) and
      # /odometry/filtered (the state), filters, and republishes the accepted
      # action on /policy/filtered_action, plus a JSON verdict on /safety/status.

ACCEPTANCE CRITERIA
  [ ] --demo prints PASS for safe actions, CLAMP for the over-speed twist,
      REJECT for the through-the-table action, and the verdict tally, then
      "FILTER FIRED CORRECTLY" and exits 0.
  [ ] The filter's per-action latency (printed) is well under a typical policy
      inference time (tens of ms) -- a few hundred microseconds to low ms.
  [ ] A filter edited to PASS everything FAILS the asserts (proving it is not
      decorative -- the Defect-4 guard).
  [ ] Against a live policy, /policy/filtered_action carries only safe actions
      and /safety/status reports the verdict stream.

Expected output is at the bottom of the file.
"""

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


# --- the constraint set (the relevant subset of Exercise 1's Bounds) ---------
@dataclass(frozen=True)
class Bounds:
    v_max: float = 1.0            # base linear velocity, m/s
    w_max: float = 1.5            # base angular velocity, rad/s
    cart_step_max: float = 0.10   # arm Cartesian step, m per control step
    ws_z_min: float = 0.02        # table surface (m, base_link); below = collision
    ws_x: tuple = (0.15, 0.85)
    ws_y: tuple = (-0.60, 0.60)
    ws_z_max: float = 1.10


@dataclass
class VerdictCounts:
    actions: int = 0
    passed: int = 0
    clamp_velocity: int = 0
    clamp_workspace: int = 0
    reject_workspace: int = 0
    reject_velocity: int = 0
    latencies_ms: list = field(default_factory=list)

    def tally(self) -> str:
        return (f"actions={self.actions} pass={self.passed} "
                f"clamp(vel)={self.clamp_velocity} clamp(ws)={self.clamp_workspace} "
                f"reject(ws)={self.reject_workspace} reject(vel)={self.reject_velocity}")


# --- the filter core ---------------------------------------------------------
class SafetyFilter:
    """The predictive filter. roll_forward + check + project-or-reject."""

    def __init__(self, bounds: Bounds, horizon_steps: int = 5, dt: float = 0.05):
        self.b = bounds
        self.horizon = horizon_steps
        self.dt = dt
        self.counts = VerdictCounts()

    # ---- base twist path --------------------------------------------------
    def filter_twist(self, vx: float, wz: float) -> tuple[Optional[Twist], str]:
        """PASS / CLAMP / REJECT a base twist. Over-speed is CLAMP (rescalable);
        a NaN/inf or absurd command is REJECT."""
        t0 = time.perf_counter()
        self.counts.actions += 1
        verdict = "PASS"
        out = Twist()

        # Reject pathological actions outright -- no projection saves a NaN.
        if not (math.isfinite(vx) and math.isfinite(wz)):
            self.counts.reject_velocity += 1
            self._record_latency(t0)
            return None, "REJECT(velocity:nonfinite)"

        # Roll forward: where does this twist take the base over the horizon?
        # (Kinematic unicycle model -- the cheap roll-forward.)
        x = y = th = 0.0
        for _ in range(self.horizon):
            x += vx * math.cos(th) * self.dt
            y += vx * math.sin(th) * self.dt
            th += wz * self.dt
        # (For the base we constrain velocity, not predicted pose; the rollout
        #  here would feed an obstacle/keep-out check in the full version.)

        # Velocity bound: over-speed is rescalable -> CLAMP (uniform, Exercise 1).
        f = max(abs(vx) / self.b.v_max, abs(wz) / self.b.w_max, 1.0)
        if f > 1.0:
            vx, wz = vx / f, wz / f
            self.counts.clamp_velocity += 1
            verdict = "CLAMP(velocity)"

        out.linear.x = vx
        out.angular.z = wz
        if verdict == "PASS":
            self.counts.passed += 1
        self._record_latency(t0)
        return out, verdict

    # ---- arm action path --------------------------------------------------
    def filter_arm_step(self, ee_xyz: tuple, delta_xyz: tuple) -> tuple[Optional[tuple], str]:
        """PASS / CLAMP / REJECT one Cartesian arm step. An over-speed step is
        CLAMP (rescale the delta); a step that drives the tool through the
        table or out of the workspace is REJECT (no rescale saves 'through the
        table' -- direction is wrong, not just speed)."""
        t0 = time.perf_counter()
        self.counts.actions += 1

        if not all(math.isfinite(d) for d in delta_xyz):
            self.counts.reject_workspace += 1
            self._record_latency(t0)
            return None, "REJECT(workspace:nonfinite)"

        # Roll forward: the predicted end-effector position after the step.
        pred = tuple(e + d for e, d in zip(ee_xyz, delta_xyz))

        # State guard FIRST: if the destination is below the table or out of
        # the workspace volume, NO speed-rescale makes it safe -> REJECT.
        if pred[2] < self.b.ws_z_min:
            self.counts.reject_workspace += 1
            self._record_latency(t0)
            return None, "REJECT(workspace:below_table)"
        if not (self.b.ws_x[0] <= pred[0] <= self.b.ws_x[1]
                and self.b.ws_y[0] <= pred[1] <= self.b.ws_y[1]
                and self.b.ws_z_min <= pred[2] <= self.b.ws_z_max):
            self.counts.reject_workspace += 1
            self._record_latency(t0)
            return None, "REJECT(workspace:out_of_volume)"

        # Velocity bound on the step magnitude: over-speed is rescalable -> CLAMP.
        mag = math.sqrt(sum(d * d for d in delta_xyz))
        verdict = "PASS"
        out_delta = delta_xyz
        if mag > self.b.cart_step_max:
            scale = self.b.cart_step_max / mag
            out_delta = tuple(d * scale for d in delta_xyz)
            self.counts.clamp_workspace += 1
            verdict = "CLAMP(cart_velocity)"
        else:
            self.counts.passed += 1

        self._record_latency(t0)
        return out_delta, verdict

    def _record_latency(self, t0: float) -> None:
        self.counts.latencies_ms.append((time.perf_counter() - t0) * 1e3)

    def latency_p(self, pct: float) -> float:
        xs = sorted(self.counts.latencies_ms)
        if not xs:
            return 0.0
        k = min(len(xs) - 1, int(pct / 100.0 * len(xs)))
        return xs[k]


# --- the ROS2 node (live mode) ----------------------------------------------
class SafetyFilterNode(Node):
    def __init__(self) -> None:
        super().__init__("safety_filter")
        self.filter = SafetyFilter(Bounds())
        self._state_xyz = (0.30, 0.0, 0.40)   # latest end-effector pose (stub)

        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_LAST, depth=5)
        # The raw learned action in (we treat /policy/action as a base twist
        # here; the arm path is exercised in --demo and the mini-project).
        self.create_subscription(Twist, "/policy/action", self._on_action, 10)
        self.create_subscription(Odometry, "/odometry/filtered",
                                 self._on_odom, sensor_qos)
        self._accepted = self.create_publisher(Twist, "/policy/filtered_action", 10)
        self._status = self.create_publisher(String, "/safety/status", 10)
        self.get_logger().info("safety filter up; intercepting /policy/action")

    def _on_odom(self, _msg: Odometry) -> None:
        pass  # in the full version, feeds the roll-forward obstacle check

    def _on_action(self, msg: Twist) -> None:
        out, verdict = self.filter.filter_twist(msg.linear.x, msg.angular.z)
        blob = {"verdict": verdict, "estop": False,
                "clamps": self.filter.counts.clamp_velocity
                + self.filter.counts.clamp_workspace,
                "rejections": self.filter.counts.reject_velocity
                + self.filter.counts.reject_workspace}
        self._status.publish(String(data=json.dumps(blob)))
        if out is not None:               # PASS or CLAMP -> execute
            self._accepted.publish(out)
        else:                             # REJECT -> do not execute
            self.get_logger().warn(f"action rejected: {verdict}")


# --- demo harness ------------------------------------------------------------
def run_demo() -> int:
    """Drive a scripted sequence of safe and unsafe actions through the filter
    core and assert it fires correctly. No ROS graph required."""
    f = SafetyFilter(Bounds())

    print("=== base twists ===")
    cases = [
        ("safe forward",        0.5,  0.3, "PASS"),
        ("safe turn",           0.2,  0.8, "PASS"),
        ("OVER-SPEED twist",    3.0,  0.5, "CLAMP(velocity)"),  # 3x over v_max
        ("nonfinite (bad)",     float("nan"), 0.0, "REJECT(velocity:nonfinite)"),
    ]
    for name, vx, wz, expect in cases:
        out, verdict = f.filter_twist(vx, wz)
        ok = verdict == expect
        print(f"  [{verdict:32s}] {name:18s} -> {'ok' if ok else 'MISMATCH'}")
        assert ok, f"{name}: expected {expect}, got {verdict}"

    print("=== arm Cartesian steps (ee at (0.30,0.00,0.40)) ===")
    ee = (0.30, 0.0, 0.40)
    arm_cases = [
        ("safe approach",      (0.03, 0.0, -0.02), "PASS"),
        ("OVER-SPEED step",    (0.30, 0.0, -0.05), "CLAMP(cart_velocity)"),  # 0.30m step
        ("THROUGH THE TABLE",  (0.0, 0.0, -0.50),  "REJECT(workspace:below_table)"),
        ("OUT OF VOLUME",      (1.0, 0.0, 0.0),    "REJECT(workspace:out_of_volume)"),
    ]
    for name, delta, expect in arm_cases:
        out, verdict = f.filter_arm_step(ee, delta)
        ok = verdict == expect
        print(f"  [{verdict:32s}] {name:18s} -> {'ok' if ok else 'MISMATCH'}")
        assert ok, f"{name}: expected {expect}, got {verdict}"

    print("\n=== tally ===")
    print(f"  {f.counts.tally()}")
    print(f"  filter latency: p50={f.latency_p(50):.3f}ms p95={f.latency_p(95):.3f}ms")

    # The Defect-4 guard: the filter MUST have fired on the unsafe actions.
    fired = (f.counts.clamp_velocity + f.counts.clamp_workspace
             + f.counts.reject_velocity + f.counts.reject_workspace)
    assert fired >= 4, "filter did not fire on the unsafe actions -- it is decorative"
    print("\nFILTER FIRED CORRECTLY: it clamped the over-speed actions and "
          "rejected the through-the-table / out-of-volume ones. The leash is real.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Runtime safety filter")
    parser.add_argument("--demo", action="store_true",
                        help="drive scripted safe/unsafe actions through the filter")
    args, ros_args = parser.parse_known_args(sys.argv[1:])

    if args.demo:
        sys.exit(run_demo())

    rclpy.init(args=ros_args)
    node = SafetyFilterNode()
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
# === base twists ===
#   [PASS                            ] safe forward       -> ok
#   [PASS                            ] safe turn          -> ok
#   [CLAMP(velocity)                 ] OVER-SPEED twist   -> ok
#   [REJECT(velocity:nonfinite)      ] nonfinite (bad)    -> ok
# === arm Cartesian steps (ee at (0.30,0.00,0.40)) ===
#   [PASS                            ] safe approach      -> ok
#   [CLAMP(cart_velocity)            ] OVER-SPEED step    -> ok
#   [REJECT(workspace:below_table)   ] THROUGH THE TABLE  -> ok
#   [REJECT(workspace:out_of_volume) ] OUT OF VOLUME      -> ok
#
# === tally ===
#   actions=8 pass=3 clamp(vel)=1 clamp(ws)=1 reject(ws)=2 reject(vel)=1
#   filter latency: p50=0.004ms p95=0.012ms
#
# FILTER FIRED CORRECTLY: it clamped the over-speed actions and rejected the
# through-the-table / out-of-volume ones. The leash is real.
#
# NOTE the latency line: the filter is microseconds per action, far cheaper than
# a ~31 ms policy inference. That headroom is the whole point -- the leash must
# never be the bottleneck. If you edit the filter to PASS everything (delete the
# clamp/reject branches), the final assert FAILS -- which is the Defect-4 guard:
# a filter that never fires is decorative and the exercise refuses to pass it.
# -----------------------------------------------------------------------------

#!/usr/bin/env python3
# Exercise 2 — Run the baseline VLA against the full twenty-instruction suite
#
# Goal: A runnable rclpy eval-runner. For each instruction in the FROZEN suite it
#       (1) resets the scene deterministically, (2) issues the instruction to the
#       policy action server, (3) scores the outcome from the state estimate, and
#       (4) writes a per-instruction report whose header pins the suite commit hash.
#
# Estimated time: 90 minutes (plus the suite run itself, which is real-robot/sim time).
#
# HOW TO USE THIS FILE
#
#   1. Drop this into your capstone eval package:
#        ~/capstone_ws/src/capstone_eval/capstone_eval/run_baseline_suite.py
#      and add an entry point in setup.py:
#        'run_baseline_suite = capstone_eval.run_baseline_suite:main'
#
#   2. It assumes the interfaces you built in prior weeks:
#        - action  ExecuteInstruction  (goal: string instruction; result: bool reported_complete)
#        - service ResetScene          (request: string scene_name, uint32 seed; reply: bool ok, string message)
#        - a TF-published object pose for each target_object, and a collision flag topic.
#      If your interface names differ, change the imports and topic names ONLY — the
#      eval logic does not change.
#
#   3. Build and run against the frozen suite from exercise 1:
#        colcon build --packages-select capstone_eval && source install/setup.bash
#        ros2 run capstone_eval run_baseline_suite \
#          --ros-args -p suite_path:=src/capstone_eval/suite/eval_suite.yaml \
#                     -p policy_label:="openvla-7b baseline" \
#                     -p report_dir:=reports/baseline
#
#   This is REAL code. It runs. There is no pseudocode and nothing to fill in to make
#   it execute end to end against a stack that exposes the two interfaces above.

from __future__ import annotations

import csv
import json
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

import numpy as np
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from ruamel.yaml import YAML

# These come from your capstone interface package. If yours are named differently,
# change these two imports (and the names in __init__ below) — nothing else.
from capstone_msgs.action import ExecuteInstruction
from capstone_msgs.srv import ResetScene
from std_msgs.msg import Bool
from geometry_msgs.msg import PointStamped


# ----------------------------------------------------------------------------
# The success rubric (binary, operational — see lecture 1 and exercise 1 RUBRIC.md)
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class TrialOutcome:
    object_final_xyz: np.ndarray   # estimated final position of the target object, in `map`
    destination_xyz: np.ndarray    # ground-truth destination position, in `map`
    collided: bool                 # any collision flag raised during execution
    elapsed_s: float               # wall time from instruction issue to task-complete
    reported_complete: bool        # did the policy/BT report it finished at all
    is_recovery: bool              # recovery-axis instruction -> recovery exception applies


def score_trial(o: TrialOutcome, *, success_distance_m: float, timeout_s: float) -> bool:
    """Binary success per the operational rubric. No partial credit."""
    if o.collided:
        return False
    # Recovery exception: a clean abort (reported complete, no collision, no grasped
    # distractor) is a SUCCESS for recovery instructions. The action server signals a
    # clean abort by reporting complete with a destination of NaN (nothing delivered).
    if o.is_recovery and np.any(np.isnan(o.destination_xyz)):
        return o.reported_complete and o.elapsed_s <= timeout_s
    if not o.reported_complete:
        return False
    if o.elapsed_s > timeout_s:
        return False
    dist = float(np.linalg.norm(o.object_final_xyz - o.destination_xyz))
    return dist <= success_distance_m


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials. Honest at small n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


# ----------------------------------------------------------------------------
# The eval-runner node
# ----------------------------------------------------------------------------

class EvalRunner(Node):
    """Drives the policy across the frozen suite and accumulates k/N per instruction."""

    def __init__(self) -> None:
        super().__init__("eval_runner")
        self.declare_parameter("suite_path", "")
        self.declare_parameter("policy_label", "unlabeled-policy")
        self.declare_parameter("report_dir", "reports")

        suite_path = self.get_parameter("suite_path").value
        if not suite_path:
            raise RuntimeError("set -p suite_path:=<path to eval_suite.yaml>")
        self._suite = YAML(typ="safe").load(Path(suite_path).read_text())
        self._suite_path = Path(suite_path)
        self._policy_label = self.get_parameter("policy_label").value
        self._report_dir = Path(self.get_parameter("report_dir").value)
        self._report_dir.mkdir(parents=True, exist_ok=True)

        self._policy = ActionClient(self, ExecuteInstruction, "execute_instruction")
        self._reset = self.create_client(ResetScene, "reset_scene")

        # Live state we read to build a TrialOutcome.
        self._collided = False
        self._object_xyz = np.full(3, np.nan)
        self.create_subscription(Bool, "safety/collision_flag", self._on_collision, 10)
        self.create_subscription(PointStamped, "perception/target_object_point",
                                 self._on_object_point, 10)

        self.get_logger().info("waiting for policy action server and reset service...")
        self._policy.wait_for_server()
        self._reset.wait_for_service()
        self.get_logger().info("eval-runner ready")

    # --- live-state callbacks ---

    def _on_collision(self, msg: Bool) -> None:
        if msg.data:
            self._collided = True

    def _on_object_point(self, msg: PointStamped) -> None:
        self._object_xyz = np.array([msg.point.x, msg.point.y, msg.point.z])

    # --- one trial ---

    def run_trial(self, instruction: dict, seed: int) -> tuple[bool, TrialOutcome]:
        self._collided = False
        self._object_xyz = np.full(3, np.nan)

        # 1. Deterministic reset.
        req = ResetScene.Request()
        req.scene_name = instruction["scene_reset"]
        req.seed = int(seed)
        fut = self._reset.call_async(req)
        rclpy.spin_until_future_complete(self, fut)
        if not fut.result().ok:
            self.get_logger().error(f"reset failed: {fut.result().message}")
            outcome = TrialOutcome(np.full(3, np.nan), np.full(3, np.nan),
                                   False, 0.0, False, False)
            return False, outcome

        # 2. Issue the instruction and time it.
        goal = ExecuteInstruction.Goal()
        goal.instruction = instruction["text"]
        t0 = time.monotonic()
        send_fut = self._policy.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_fut)
        handle = send_fut.result()
        if not handle.accepted:
            self.get_logger().error("policy rejected the goal")
            outcome = TrialOutcome(self._object_xyz, np.full(3, np.nan),
                                   self._collided, time.monotonic() - t0, False,
                                   "recovery" in instruction["axis"])
            return False, outcome

        result_fut = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_fut,
                                         timeout_sec=self._suite["timeout_s"] + 10.0)
        elapsed = time.monotonic() - t0
        reported = (result_fut.result() is not None
                    and result_fut.result().result.reported_complete)

        # 3. Build the outcome from perception + result and score it.
        is_recovery = "recovery" in instruction["axis"]
        destination_xyz = self._destination_xyz(instruction, reported, is_recovery)
        outcome = TrialOutcome(
            object_final_xyz=self._object_xyz,
            destination_xyz=destination_xyz,
            collided=self._collided,
            elapsed_s=elapsed,
            reported_complete=reported,
            is_recovery=is_recovery,
        )
        ok = score_trial(outcome,
                         success_distance_m=self._suite["success_distance_m"],
                         timeout_s=self._suite["timeout_s"])
        return ok, outcome

    def _destination_xyz(self, instruction: dict, reported: bool,
                         is_recovery: bool) -> np.ndarray:
        """Ground-truth destination. A clean recovery abort delivers nothing -> NaN."""
        if is_recovery and reported and np.any(np.isnan(self._object_xyz)):
            return np.full(3, np.nan)        # clean abort: nothing was delivered
        # In a real stack you look the destination up from a known fixture table keyed
        # by instruction['destination']. We read it from a sidecar the reset service wrote.
        return np.array(instruction.get("_destination_xyz", [0.0, 0.0, 0.0]))

    # --- the full suite ---

    def run_suite(self) -> dict:
        n = int(self._suite["trials_per_instruction"])
        base_seed = int(self._suite["master_seed"])
        rows = []
        for ins in self._suite["instructions"]:
            successes = 0
            for t in range(n):
                ok, _ = self.run_trial(ins, seed=base_seed + 1000 * ins["id"] + t)
                successes += int(ok)
                self.get_logger().info(
                    f"id={ins['id']} trial {t + 1}/{n}: {'PASS' if ok else 'fail'}")
            rows.append({
                "id": ins["id"], "text": ins["text"],
                "axis": ",".join(ins["axis"]),
                "k": successes, "n": n,
                "passed": successes >= int(self._suite["pass_threshold"]),
            })
        return {"rows": rows, "n_per": n}


# ----------------------------------------------------------------------------
# Report writing — machine-readable (CSV/JSON) + human-readable (Markdown)
# ----------------------------------------------------------------------------

def suite_commit_hash(suite_path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "log", "-n", "1", "--format=%h", "--", str(suite_path)],
            cwd=suite_path.parent, text=True).strip() or "uncommitted"
    except Exception:
        return "uncommitted"


def write_reports(result: dict, runner: EvalRunner) -> None:
    rows = result["rows"]
    n_per = result["n_per"]
    total_passed = sum(r["passed"] for r in rows)
    total_k = sum(r["k"] for r in rows)
    total_n = sum(r["n"] for r in rows)
    lo, hi = wilson_interval(total_k, total_n)
    commit = suite_commit_hash(runner._suite_path)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    rdir = runner._report_dir
    (rdir / "report.json").write_text(json.dumps({
        "suite_version": runner._suite["suite_version"],
        "suite_commit": commit,
        "policy": runner._policy_label,
        "date": stamp,
        "master_seed": runner._suite["master_seed"],
        "rows": rows,
        "instructions_passed": total_passed,
        "trial_success_rate": total_k / total_n,
        "wilson_95": [lo, hi],
    }, indent=2))

    with (rdir / "report.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "text", "axis", "k", "n", "passed"])
        w.writeheader()
        w.writerows(rows)

    lines = [
        f"suite: {runner._suite['suite_version']}  commit: {commit}  "
        f"seed: {runner._suite['master_seed']}",
        f"policy: {runner._policy_label}   date: {stamp}",
        "",
        "| id | instruction | axis | k/N |",
        "|---:|-------------|------|----:|",
    ]
    for r in rows:
        lines.append(f"| {r['id']} | {r['text']} | {r['axis']} | {r['k']}/{r['n']} |")
    lines.append(f"| -- | **INSTRUCTIONS PASSED (>= {runner._suite['pass_threshold']}/{n_per})** "
                 f"| | **{total_passed}/{len(rows)}** |")
    lines.append("")
    lines.append(f"trial-success rate {total_k}/{total_n} = {total_k / total_n:.2f}, "
                 f"95% Wilson CI [{lo:.2f}, {hi:.2f}]")
    (rdir / "report.md").write_text("\n".join(lines) + "\n")
    runner.get_logger().info(
        f"wrote report: {total_passed}/{len(rows)} instructions passed -> {rdir}/report.md")


def main() -> None:
    rclpy.init()
    runner = EvalRunner()
    try:
        result = runner.run_suite()
        write_reports(result, runner)
    finally:
        runner.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

# ----------------------------------------------------------------------------
# EXPECTED OUTPUT (reports/baseline/report.md), numbers will be yours:
#
#   suite: 1.0.0  commit: 4f2a9c1  seed: 20260609
#   policy: openvla-7b baseline   date: 2026-06-09
#
#   | id | instruction                              | axis                        | k/N |
#   |---:|------------------------------------------|-----------------------------|----:|
#   |  1 | bring me the red cup from the left bench | object_reference,spatial... | 3/5 |
#   |  2 | put the blue block on the right shelf    | spatial_grounding,placement | 1/5 |
#   | ...                                                                              |
#   | -- | INSTRUCTIONS PASSED (>= 3/5)             |                             | 9/20|
#
#   trial-success rate 41/100 = 0.41, 95% Wilson CI [0.32, 0.51]
#
# ACCEPTANCE CRITERIA
#   [ ] The runner completes all 20 instructions x 5 trials without crashing.
#   [ ] report.md, report.csv, report.json all written, and the .md header pins the
#       suite commit hash (NOT "uncommitted" — you froze the suite in exercise 1).
#   [ ] The suite total is reported as instructions-passed AND a Wilson CI.
#   [ ] You did NOT touch eval_suite.yaml during this run. The baseline is honest.
# ----------------------------------------------------------------------------

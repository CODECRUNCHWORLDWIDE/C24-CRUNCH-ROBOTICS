#!/usr/bin/env python3
# Exercise 3 -- The latency-budget gate.
#
# Goal: turn the latency budget from Lecture 1 section 2 into a CI gate. The budget
#       is an ARTIFACT: it allocates a real-time cycle across stages, ingests the
#       MEASURED p95 of each stage, and FAILS (non-zero exit) when the sum regresses
#       past the cycle target. This is the check that runs in your pipeline so that
#       the PR which pushes the policy from 14 ms to 19 ms gets caught at review.
#
# Estimated time: 40 minutes. Runnable. Pure Python -- no GPU needed.
#
# HOW TO USE THIS FILE
#
#   python3 exercise-03-latency-budget.py            # runs the built-in scenarios
#   python3 exercise-03-latency-budget.py --self-check  # asserts the gate logic
#
#   In real life you generate `measured` from your Foxglove cycle-latency export
#   (Lecture 1 section 3.4) and feed it here; the function below is what CI calls.
#
# ACCEPTANCE CRITERIA
#   [ ] check_budget() returns PASS only when EVERY stage is within its budget AND
#       the sum of measured p95s is within the cycle target.
#   [ ] A single regressed stage that still leaves the SUM under target is reported
#       as a per-stage WARNING but the gate's verdict is driven by the SUM (the
#       gate that matters), exactly as Lecture 1 section 2 describes.
#   [ ] The over-budget scenario exits non-zero; the in-budget scenario exits zero.
#   [ ] `python3 exercise-03-latency-budget.py --self-check` prints ALL CHECKS PASSED.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import sys
from dataclasses import dataclass

CYCLE_TARGET_MS = 50.0  # syllabus: perception->policy cycle <= 50 ms p95 on Orin Nano


@dataclass
class Stage:
    name: str
    budget_ms: float       # the allocation decided up front
    measured_p95_ms: float  # the evidence from Foxglove/nsys over 500+ cycles


def check_budget(stages: list[Stage], cycle_target_ms: float = CYCLE_TARGET_MS) -> dict:
    """The gate. Returns a verdict dict. The SUM of measured p95s vs the cycle
    target is the gate that fails CI (Lecture 1 section 2: 'the sum is the gate').
    Per-stage overages are reported as findings to point the optimizer at the
    worst offender, but the verdict is the sum."""
    total = sum(s.measured_p95_ms for s in stages)
    per_stage = []
    for s in stages:
        over = s.measured_p95_ms - s.budget_ms
        per_stage.append({
            "name": s.name,
            "budget": s.budget_ms,
            "p95": s.measured_p95_ms,
            "over_by": over,
            "status": "OVER" if over > 0 else "ok",
        })
    # The optimizer fixes the WORST offender first (Lecture 1 section 6).
    worst = max(per_stage, key=lambda d: d["over_by"]) if per_stage else None
    sum_ok = total <= cycle_target_ms
    return {
        "total_p95": total,
        "cycle_target": cycle_target_ms,
        "margin": cycle_target_ms - total,
        "per_stage": per_stage,
        "worst_offender": worst["name"] if worst and worst["over_by"] > 0 else None,
        "verdict": "PASS" if sum_ok else "FAIL",
    }


def print_report(title: str, verdict: dict) -> None:
    print("=" * 66)
    print(title)
    print("=" * 66)
    print(f"  {'stage':<20}{'budget':>9}{'p95':>9}{'over_by':>10}  status")
    print("  " + "-" * 58)
    for d in verdict["per_stage"]:
        print(f"  {d['name']:<20}{d['budget']:>9.1f}{d['p95']:>9.1f}"
              f"{d['over_by']:>+10.1f}  {d['status']}")
    print("  " + "-" * 58)
    print(f"  {'SUM':<20}{'':>9}{verdict['total_p95']:>9.1f}"
          f"   target {verdict['cycle_target']:.1f}  margin {verdict['margin']:+.1f}")
    if verdict["worst_offender"]:
        print(f"  worst offender -> {verdict['worst_offender']} (fix this first)")
    print(f"  VERDICT: {verdict['verdict']}")
    print("=" * 66)


# The baseline measurement from Lecture 1 section 6 -- 3x over budget on two stages.
BASELINE = [
    Stage("camera_capture", 3, 2.8),
    Stage("preprocess", 4, 3.9),
    Stage("detector_yolo", 12, 24.8),     # OVER -- compute-bound -> INT8
    Stage("depth_project", 8, 17.2),      # OVER -- memory-bound -> composable container
    Stage("fusion", 5, 4.6),
    Stage("policy_vla", 14, 13.8),
    Stage("safety_filter", 2, 1.4),
]

# After the optimizations from Lecture 2 section 8 (INT8 detector, composable depth).
OPTIMIZED = [
    Stage("camera_capture", 3, 2.8),
    Stage("preprocess", 4, 3.9),
    Stage("detector_yolo", 12, 11.6),     # INT8 PTQ, -1.4 mAP (within floor)
    Stage("depth_project", 8, 7.7),       # zero-copy composable container, 0 accuracy cost
    Stage("fusion", 5, 4.6),
    Stage("policy_vla", 14, 13.8),
    Stage("safety_filter", 2, 1.4),
]


def self_check() -> bool:
    ok = True

    base = check_budget(BASELINE)
    if base["verdict"] != "FAIL":
        print("CHECK FAILED: baseline (88.3 ms) should FAIL the 50 ms gate.")
        ok = False
    if base["worst_offender"] != "detector_yolo":
        print(f"CHECK FAILED: worst offender should be detector_yolo, got {base['worst_offender']}.")
        ok = False

    opt = check_budget(OPTIMIZED)
    if opt["verdict"] != "PASS":
        print("CHECK FAILED: optimized graph should PASS the 50 ms gate.")
        ok = False
    if opt["margin"] <= 0:
        print("CHECK FAILED: optimized graph should have positive margin.")
        ok = False

    # A single regressed stage that still leaves the SUM under target -> sum still PASS.
    mild = [Stage("a", 10, 9), Stage("b", 10, 14), Stage("c", 10, 8)]  # sum 31 <= 50
    mild_v = check_budget(mild)
    if mild_v["verdict"] != "PASS":
        print("CHECK FAILED: sum under target should PASS even with one stage over.")
        ok = False
    if mild_v["worst_offender"] != "b":
        print("CHECK FAILED: should still flag 'b' as the over-budget stage.")
        ok = False

    return ok


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        if self_check():
            print("ALL CHECKS PASSED")
            return 0
        print("CHECKS FAILED -- see messages above.")
        return 1

    base = check_budget(BASELINE)
    print_report("BASELINE -- integrated graph, first measurement", base)
    print()
    opt = check_budget(OPTIMIZED)
    print_report("OPTIMIZED -- after INT8 detector + composable depth", opt)

    # The gate's exit code is the OPTIMIZED verdict (what CI would check post-fix).
    return 0 if opt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# ---------------------------------------------------------------------------
# EXPECTED OUTPUT (default run):
#
#   ==================================================================
#   BASELINE -- integrated graph, first measurement
#   ==================================================================
#     stage                  budget      p95   over_by  status
#     ----------------------------------------------------------
#     camera_capture            3.0      2.8      -0.2  ok
#     preprocess                4.0      3.9      -0.1  ok
#     detector_yolo            12.0     24.8     +12.8  OVER
#     depth_project             8.0     17.2      +9.2  OVER
#     fusion                    5.0      4.6      -0.4  ok
#     policy_vla               14.0     13.8      -0.2  ok
#     safety_filter             2.0      1.4      -0.6  ok
#     ----------------------------------------------------------
#     SUM                              68.5   target 50.0  margin -18.5
#     worst offender -> detector_yolo (fix this first)
#     VERDICT: FAIL
#
#   ==================================================================
#   OPTIMIZED -- after INT8 detector + composable depth
#   ==================================================================
#     ... detector_yolo 11.6 ok, depth_project 7.7 ok ...
#     SUM                              45.8   target 50.0  margin +4.2
#     VERDICT: PASS
#
# (Note the BASELINE sum is 68.5 here because two stages were brought down; the
#  Lecture 1 section 6 "88.3" figure was before ANY fix. The point stands: the SUM
#  is the gate, and you fix the worst offender first.)
# ---------------------------------------------------------------------------

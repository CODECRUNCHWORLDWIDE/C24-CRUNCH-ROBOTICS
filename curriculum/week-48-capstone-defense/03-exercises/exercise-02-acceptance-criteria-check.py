#!/usr/bin/env python3
# Exercise 2 -- The acceptance-criteria check.
#
# Goal: score your robot against the capstone spec's acceptance criteria (Lecture 1
#       section 4) BEFORE the panel does, so you know exactly where you stand --
#       including where you fall short. The lesson: an honest gap with a plan beats a
#       hidden one, and a safety-relevant defect is the ONE unforgivable fail.
#
# Estimated time: 40 minutes. Runnable. Pure Python.
#
# HOW TO USE THIS FILE
#   Edit MY_RESULTS with your real, MEASURED numbers (from your eval bag, drift
#   comparison, timed cold-boot, chaos postmortems, and safety case), then:
#       python3 exercise-02-acceptance-criteria-check.py
#   The checker prints PASS/FAIL per criterion and an overall verdict. A safety
#   defect forces an overall FAIL regardless of the rest (per the spec).
#
# ACCEPTANCE CRITERIA
#   [ ] Each spec criterion is checked against its bar with the correct comparison
#       (>= for instructions, < for drift and boot time).
#   [ ] An unaddressed safety-relevant defect forces an overall FAIL even if every
#       other criterion passes (the spec's one unforgivable failure).
#   [ ] The overall verdict is PASS only if ALL criteria pass and no safety defect.
#   [ ] `python3 exercise-02-acceptance-criteria-check.py --self-check` prints
#       ALL CHECKS PASSED.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass
class Criterion:
    name: str
    bar_text: str
    passed: bool
    measured_text: str


def evaluate(results: dict) -> tuple[list[Criterion], str]:
    """Evaluate the capstone acceptance criteria. Returns (criteria, overall)."""
    crit: list[Criterion] = []

    # >= 15 of 20 language-conditioned instructions.
    instr = results["instructions_passed"]
    crit.append(Criterion(
        "instructions", ">= 15/20", instr >= 15, f"{instr}/20"))

    # Fused-estimate drift < 0.5 m over 20 m.
    drift = results["drift_m"]
    crit.append(Criterion(
        "drift", "< 0.5 m / 20 m", drift < 0.5, f"{drift:.2f} m"))

    # Cold-boot < 60 s.
    boot = results["cold_boot_s"]
    crit.append(Criterion(
        "cold_boot", "< 60 s", boot < 60, f"{boot:.0f} s"))

    # Both chaos drills recovered, operator-detectable, within 60 s.
    drills = results["chaos_drills_recovered"]
    crit.append(Criterion(
        "chaos_drills", "2/2 recovered, operator-detectable, < 60 s",
        drills == 2, f"{drills}/2"))

    # Safety case signed by peer reviewer (panel signs live).
    signed = results["safety_case_peer_signed"]
    crit.append(Criterion(
        "safety_case_signed", "peer-signed", bool(signed),
        "signed" if signed else "UNSIGNED"))

    # Overall: PASS iff all criteria pass AND no unaddressed safety-relevant defect.
    all_pass = all(c.passed for c in crit)
    safety_defect = results["unaddressed_safety_defect"]
    if safety_defect:
        overall = "FAIL (unaddressed safety-relevant defect -- the one unforgivable fail)"
    elif all_pass:
        overall = "PASS"
    else:
        failing = [c.name for c in crit if not c.passed]
        overall = f"FAIL (criteria short: {', '.join(failing)})"
    return crit, overall


def report(results: dict) -> str:
    crit, overall = evaluate(results)
    print("=" * 64)
    print("Capstone acceptance criteria (Lecture 1 section 4)")
    print("=" * 64)
    print(f"  {'criterion':<20}{'bar':<40}{'result':>10}  status")
    print("  " + "-" * 78)
    for c in crit:
        print(f"  {c.name:<20}{c.bar_text:<40}{c.measured_text:>10}  "
              f"{'PASS' if c.passed else 'FAIL'}")
    if results["unaddressed_safety_defect"]:
        print("  " + "-" * 78)
        print("  !! UNADDRESSED SAFETY-RELEVANT DEFECT -- forces overall FAIL (spec) !!")
    print("  " + "-" * 78)
    print(f"  OVERALL: {overall}")
    print("=" * 64)
    return overall


# EDIT THESE with your real measured numbers.
MY_RESULTS = {
    "instructions_passed": 17,        # of 20
    "drift_m": 0.38,                  # over 20 m
    "cold_boot_s": 52,
    "chaos_drills_recovered": 2,      # of 2
    "safety_case_peer_signed": True,
    "unaddressed_safety_defect": False,  # MUST be False to pass -- the unforgivable one
}


def self_check() -> bool:
    ok = True

    # The sample MY_RESULTS should PASS.
    _, overall = evaluate(MY_RESULTS)
    if overall != "PASS":
        print(f"CHECK FAILED: sample results should PASS, got {overall}.")
        ok = False

    # 14/20 instructions should FAIL (one short).
    short = dict(MY_RESULTS, instructions_passed=14)
    _, ov = evaluate(short)
    if not ov.startswith("FAIL"):
        print("CHECK FAILED: 14/20 instructions should FAIL.")
        ok = False

    # A safety defect forces FAIL even with everything else passing.
    with_defect = dict(MY_RESULTS, unaddressed_safety_defect=True)
    _, ov = evaluate(with_defect)
    if "safety" not in ov.lower() or not ov.startswith("FAIL"):
        print("CHECK FAILED: a safety defect must force overall FAIL.")
        ok = False

    # Drift exactly 0.5 m should FAIL (strict <).
    at_bar = dict(MY_RESULTS, drift_m=0.5)
    _, ov = evaluate(at_bar)
    if not ov.startswith("FAIL"):
        print("CHECK FAILED: drift == 0.5 m should FAIL (bar is strictly < 0.5).")
        ok = False

    return ok


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        if self_check():
            print("ALL CHECKS PASSED")
            return 0
        print("CHECKS FAILED -- see above.")
        return 1
    overall = report(MY_RESULTS)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# ---------------------------------------------------------------------------
# EXPECTED OUTPUT (default run, with the sample MY_RESULTS):
#
#   ================================================================
#   Capstone acceptance criteria (Lecture 1 section 4)
#   ================================================================
#     criterion           bar                                         result  status
#     ------------------------------------------------------------------------------
#     instructions        >= 15/20                                     17/20  PASS
#     drift               < 0.5 m / 20 m                               0.38 m  PASS
#     cold_boot           < 60 s                                        52 s  PASS
#     chaos_drills        2/2 recovered, operator-detectable, < 60 s    2/2  PASS
#     safety_case_signed  peer-signed                                 signed  PASS
#     ------------------------------------------------------------------------------
#     OVERALL: PASS
#   ================================================================
#
# The takeaway: you know EXACTLY where you stand before the panel does. If you're at
# 14/20, the checker says FAIL and you walk in with the honest number and a plan for
# the two failing instruction classes -- a far stronger position than a fudged 15
# the panel reruns and catches. And an unaddressed safety defect fails the capstone
# regardless of every other PASS, so finding one this week is your top priority.
# ---------------------------------------------------------------------------

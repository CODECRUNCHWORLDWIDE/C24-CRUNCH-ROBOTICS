#!/usr/bin/env python3
# Exercise 3 -- The full-loop scorecard.
#
# Goal: score your five-round mock loop (Lecture 1 section 1) with the rubric's
#       weighting, compute a weighted total, and rank your two weakest rounds so you
#       can turn them into a focused fix before Week 48. The lesson: grade yourself
#       honestly -- an inflated mock is a lie the Week 48 panel uncovers for free.
#
# Estimated time: 30 minutes. Runnable. Pure Python.
#
# HOW TO USE THIS FILE
#   Edit MY_SCORES with your real per-round scores (and your interviewer's), then:
#       python3 exercise-03-loop-scorecard.py
#   The tool prints the weighted total, the self-vs-interviewer gap, and your two
#   weakest rounds with a suggested fix anchor.
#
# ACCEPTANCE CRITERIA
#   [ ] The five rounds are weighted per the rubric (technical + system-design carry
#       the most, matching where the loop is won/lost -- Lecture 1 section 7).
#   [ ] The tool ranks the two weakest rounds (by normalized score).
#   [ ] The self-vs-interviewer gap is reported per round (overrating yourself is a
#       finding, not a pass).
#   [ ] `python3 exercise-03-loop-scorecard.py --self-check` prints ALL CHECKS PASSED.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import sys
from dataclasses import dataclass

# Round -> (max points, rubric weight). Technical + system-design carry the most
# because that's where the loop is won and lost (Lecture 1 section 7).
RUBRIC = {
    "intro":         (10, 0.10),
    "technical":     (30, 0.30),
    "system_design": (30, 0.30),
    "behavioral":    (20, 0.20),
    "culture":       (10, 0.10),
}

FIX_ANCHOR = {
    "intro":         "rehearse the 5-minute pitch (Lecture 1 section 5) until it's < 5:00 cold",
    "technical":     "re-do the EKF-on-the-board drill (Week 45 exercise 2) + your INT8 trade-off",
    "system_design": "run the 7-phase method twice on a NEW robot prompt; watch the clock (Lecture 1 section 3)",
    "behavioral":    "tighten the two chaos-drill postmortems into STAR stories (Week 46)",
    "culture":       "write three honest sentences on why robotics and why this company",
}


@dataclass
class RoundScore:
    name: str
    self_score: float       # what you gave yourself
    interviewer_score: float  # what your interviewer gave you


def weighted_total(rounds: list[RoundScore]) -> float:
    """Weighted percentage out of 100 using the interviewer's scores (the honest
    ones). Each round contributes (interviewer/max) * weight * 100."""
    total = 0.0
    for r in rounds:
        max_pts, weight = RUBRIC[r.name]
        total += (r.interviewer_score / max_pts) * weight * 100.0
    return total


def weakest_two(rounds: list[RoundScore]) -> list[str]:
    """The two rounds with the lowest normalized (fraction-of-max) interviewer score."""
    ranked = sorted(rounds, key=lambda r: r.interviewer_score / RUBRIC[r.name][0])
    return [r.name for r in ranked[:2]]


def report(rounds: list[RoundScore]) -> None:
    print("=" * 64)
    print("Full-loop scorecard (Lecture 1)")
    print("=" * 64)
    print(f"  {'round':<16}{'self':>8}{'interviewer':>14}{'gap':>8}")
    print("  " + "-" * 46)
    for r in rounds:
        max_pts = RUBRIC[r.name][0]
        gap = r.self_score - r.interviewer_score
        flag = "  <-- overrated yourself" if gap >= 4 else ""
        print(f"  {r.name:<16}{r.self_score:>6.0f}/{max_pts}{r.interviewer_score:>10.0f}/{max_pts}"
              f"{gap:>+8.0f}{flag}")
    print("  " + "-" * 46)
    total = weighted_total(rounds)
    print(f"  WEIGHTED TOTAL (interviewer): {total:.0f}/100")
    weak = weakest_two(rounds)
    print(f"  Two weakest rounds: {weak[0]}, {weak[1]}")
    print("  Fix before Week 48:")
    for w in weak:
        print(f"    - {w}: {FIX_ANCHOR[w]}")
    print("=" * 64)


# EDIT THESE with your real numbers.
MY_SCORES = [
    RoundScore("intro", self_score=8, interviewer_score=8),
    RoundScore("technical", self_score=27, interviewer_score=26),
    RoundScore("system_design", self_score=27, interviewer_score=22),  # overrated by 5
    RoundScore("behavioral", self_score=17, interviewer_score=17),
    RoundScore("culture", self_score=9, interviewer_score=9),
]


def self_check() -> bool:
    ok = True
    # Weighting sums to 1.0.
    if abs(sum(w for _, w in RUBRIC.values()) - 1.0) > 1e-9:
        print("CHECK FAILED: rubric weights must sum to 1.0.")
        ok = False
    # technical and system_design must be the highest-weighted.
    weights = {k: w for k, (_, w) in RUBRIC.items()}
    top_two = sorted(weights, key=weights.get, reverse=True)[:2]
    if set(top_two) != {"technical", "system_design"}:
        print("CHECK FAILED: technical + system_design should carry the most weight.")
        ok = False
    # With MY_SCORES, system_design (22/30 = 0.733) is the weakest; intro (8/10=0.8)
    # and behavioral (17/20=0.85) compete for second-weakest -> intro.
    weak = weakest_two(MY_SCORES)
    if weak[0] != "system_design":
        print(f"CHECK FAILED: weakest should be system_design, got {weak[0]}.")
        ok = False
    # The overrated round (gap >= 4) should be flagged: system_design (gap 5).
    overrated = [r.name for r in MY_SCORES if (r.self_score - r.interviewer_score) >= 4]
    if "system_design" not in overrated:
        print("CHECK FAILED: system_design overrating (gap 5) should be flagged.")
        ok = False
    return ok


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        if self_check():
            print("ALL CHECKS PASSED")
            return 0
        print("CHECKS FAILED -- see above.")
        return 1
    report(MY_SCORES)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# ---------------------------------------------------------------------------
# EXPECTED OUTPUT (default run, with the sample MY_SCORES):
#
#   ================================================================
#   Full-loop scorecard (Lecture 1)
#   ================================================================
#     round              self   interviewer     gap
#     ----------------------------------------------
#     intro              8/10        8/10      +0
#     technical         27/30       26/30      +1
#     system_design     27/30       22/30      +5  <-- overrated yourself
#     behavioral        17/20       17/20      +0
#     culture            9/10        9/10      +0
#     ----------------------------------------------
#     WEIGHTED TOTAL (interviewer): 84/100
#     Two weakest rounds: system_design, intro
#     Fix before Week 48:
#       - system_design: run the 7-phase method twice on a NEW robot prompt; watch the clock ...
#       - intro: rehearse the 5-minute pitch until it's < 5:00 cold
#   ================================================================
#
# The takeaway: the tool uses the INTERVIEWER's scores (the honest ones) for the
# total, flags where you overrated yourself (a finding to fix, not hide), and names
# the two weakest rounds with a concrete anchor for the pre-Week-48 fix.
# ---------------------------------------------------------------------------

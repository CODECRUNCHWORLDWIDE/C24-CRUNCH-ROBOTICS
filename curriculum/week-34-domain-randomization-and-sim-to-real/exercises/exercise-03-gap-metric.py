#!/usr/bin/env python3
# Exercise 3 — The sim-to-real gap-closure metric
#
# Goal: Compute, correctly and honestly, the number that proves domain randomization
#       worked: the gap-closure metric. Two policies (nominal-trained vs randomized-
#       trained), one HELD-OUT "real-style" world, fixed n. gap = randomized_success -
#       nominal_success. This file also implements the SANITY CHECK that catches a
#       contaminated held-out set — the way most fake gap numbers get caught.
#
# Estimated time: 50 minutes. Runnable. Pure NumPy — operates on eval results, so you
#                 can build and test it BEFORE you have a trained policy, then feed it
#                 your real eval counts in the challenge.
#
# THE METRIC (Lecture 2 Part 4.2)
#
#   gap_closed = success_rate(randomized, held_out) - success_rate(nominal, held_out)
#
#   Plus the sanity line: BOTH policies evaluated on the TRAINING/nominal world. A
#   correctly-randomized policy is usually SLIGHTLY WORSE on the easy nominal world
#   (it spent capacity on robustness) and MUCH better on the held-out world. If the
#   randomized policy is better on BOTH, the held-out world probably isn't held out.
#
# HOW TO USE THIS FILE
#
#       python3 exercise-03-gap-metric.py            # runs a self-test with synthetic counts
#
#   In the challenge, replace the synthetic EvalResult numbers with YOUR real eval
#   counts (successes / trials on each world for each policy) and re-run.
#
# ACCEPTANCE CRITERIA
#
#   [ ] gap_closed computed correctly from success counts (self-test PASS).
#   [ ] The sanity check FLAGS a contaminated case (randomized better on BOTH worlds)
#       and PASSES a healthy case (randomized worse-on-nominal, better-on-held-out).
#   [ ] A Wilson confidence interval is reported so the gap comes with a spread, not
#       a bare point estimate (a reviewer's first question is "what's the CI?").
#   [ ] You can explain why the sanity line matters.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class EvalResult:
    """successes out of trials on a named world, for a named policy."""
    policy: str
    world: str
    successes: int
    trials: int

    @property
    def rate(self) -> float:
        return self.successes / self.trials if self.trials else float("nan")


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a success rate — robust at small/large n."""
    if trials == 0:
        return (float("nan"), float("nan"))
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    margin = (z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def gap_closed(nominal_heldout: EvalResult, randomized_heldout: EvalResult) -> float:
    """The headline metric: randomized minus nominal success on the held-out world."""
    return randomized_heldout.rate - nominal_heldout.rate


def sanity_check(
    nominal_nominal: EvalResult, nominal_heldout: EvalResult,
    randomized_nominal: EvalResult, randomized_heldout: EvalResult,
) -> tuple[bool, str]:
    """Return (healthy, message).

    Healthy pattern: randomized policy is better on HELD-OUT (the point) and NOT better
    on the easy NOMINAL world (it traded nominal peak for robustness). If randomized is
    better on BOTH by a margin, the held-out world is probably contaminated (it reused a
    trained-on parameter), inflating the gap.
    """
    better_heldout = randomized_heldout.rate > nominal_heldout.rate
    better_nominal_by_margin = randomized_nominal.rate > nominal_nominal.rate + 0.03

    if not better_heldout:
        return (False, "SUSPECT: randomization did NOT improve held-out — recipe too "
                       "narrow, wrong family, or training under-converged.")
    if better_nominal_by_margin:
        return (False, "SUSPECT: randomized beats nominal on BOTH worlds. The held-out "
                       "world is likely contaminated (reuses a trained parameter), or "
                       "the nominal policy under-fit. Re-check the held-out parameters.")
    return (True, "HEALTHY: randomized worse-or-equal on the easy nominal world (the "
                  "robustness trade) and better on held-out (the transfer win).")


def report(results: dict[str, EvalResult]) -> None:
    nn = results["nominal_nominal"]
    nh = results["nominal_heldout"]
    rn = results["randomized_nominal"]
    rh = results["randomized_heldout"]

    gc = gap_closed(nh, rh)
    nh_ci = wilson_ci(nh.successes, nh.trials)
    rh_ci = wilson_ci(rh.successes, rh.trials)
    healthy, msg = sanity_check(nn, nh, rn, rh)

    print("=== SIM-TO-REAL GAP: held-out 'real-style' world ===")
    print(f"  nominal-trained     held-out: {nh.successes:3d}/{nh.trials} "
          f"({nh.rate*100:5.1f}%)  CI[{nh_ci[0]*100:.0f},{nh_ci[1]*100:.0f}]")
    print(f"  randomized-trained  held-out: {rh.successes:3d}/{rh.trials} "
          f"({rh.rate*100:5.1f}%)  CI[{rh_ci[0]*100:.0f},{rh_ci[1]*100:.0f}]")
    print(f"  GAP CLOSED: {gc*100:+.1f} pts")
    print(f"  (sanity) on the nominal/training world: "
          f"nominal {nn.rate*100:.0f}% | randomized {rn.rate*100:.0f}%")
    print(f"  sanity verdict: {'OK' if healthy else 'SUSPECT'} — {msg}")


def self_test() -> int:
    print("---- CASE 1: healthy gap closure ----")
    healthy = {
        "nominal_nominal":    EvalResult("nominal", "nominal", 92, 100),
        "nominal_heldout":    EvalResult("nominal", "heldout", 31, 100),
        "randomized_nominal": EvalResult("randomized", "nominal", 88, 100),
        "randomized_heldout": EvalResult("randomized", "heldout", 84, 100),
    }
    report(healthy)
    gc = gap_closed(healthy["nominal_heldout"], healthy["randomized_heldout"])
    ok1, _ = sanity_check(healthy["nominal_nominal"], healthy["nominal_heldout"],
                          healthy["randomized_nominal"], healthy["randomized_heldout"])
    case1 = abs(gc - 0.53) < 1e-6 and ok1

    print("\n---- CASE 2: contaminated held-out (should be flagged SUSPECT) ----")
    contaminated = {
        "nominal_nominal":    EvalResult("nominal", "nominal", 80, 100),
        "nominal_heldout":    EvalResult("nominal", "heldout", 60, 100),
        "randomized_nominal": EvalResult("randomized", "nominal", 95, 100),  # better on BOTH
        "randomized_heldout": EvalResult("randomized", "heldout", 90, 100),
    }
    report(contaminated)
    ok2, _ = sanity_check(contaminated["nominal_nominal"], contaminated["nominal_heldout"],
                          contaminated["randomized_nominal"], contaminated["randomized_heldout"])
    case2 = not ok2   # we WANT this flagged as suspect

    print()
    print("=" * 60)
    print(f"CASE 1 (healthy, gap=+53pts, sanity OK): {'PASS' if case1 else 'FAIL'}")
    print(f"CASE 2 (contaminated, flagged SUSPECT)  : {'PASS' if case2 else 'FAIL'}")
    print("=" * 60)
    return 0 if (case1 and case2) else 1


if __name__ == "__main__":
    raise SystemExit(self_test())


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# ---- CASE 1: healthy gap closure ----
# === SIM-TO-REAL GAP: held-out 'real-style' world ===
#   nominal-trained     held-out:  31/100 ( 31.0%)  CI[23,41]
#   randomized-trained  held-out:  84/100 ( 84.0%)  CI[75,90]
#   GAP CLOSED: +53.0 pts
#   (sanity) on the nominal/training world: nominal 92% | randomized 88%
#   sanity verdict: OK — HEALTHY: randomized worse-or-equal on the easy nominal world ...
#
# ---- CASE 2: contaminated held-out (should be flagged SUSPECT) ----
# === SIM-TO-REAL GAP: held-out 'real-style' world ===
#   ...
#   sanity verdict: SUSPECT — randomized beats nominal on BOTH worlds ...
#
# ============================================================
# CASE 1 (healthy, gap=+53pts, sanity OK): PASS
# CASE 2 (contaminated, flagged SUSPECT)  : PASS
# ============================================================
#
# The gap number alone can be faked by a leaky held-out world. The sanity line — and
# the requirement that the randomized policy NOT beat nominal on the easy world — is
# what makes the result trustworthy. Report the gap AND the sanity line, always.
# -----------------------------------------------------------------------------

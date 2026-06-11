#!/usr/bin/env python3
# Exercise 3 — Your first GTSAM factor graph (build it, solve it, check it by hand)
#
# Goal: Build the smallest meaningful factor graph — a prior + two poses + one
#       between factor — solve it with Levenberg-Marquardt, and CONFIRM the
#       optimum matches a hand calculation. Then grow it to three poses + a loop
#       closure and watch the loop closure pull the trajectory into consistency
#       and SHRINK the marginal covariance. This is the back-end of SLAM, in
#       miniature, by hand.
#
# THE GRAPH (Part A)
#
#   prior(x0 @ origin)      between(x0->x1 = +2m in x)
#         │                        │
#       (X0) ──────────────────── (X1)
#
#   Hand calc: the prior pins x0 at (0,0,0). The between factor says x1 is 2 m
#   ahead of x0. With no conflicting information, the MAP estimate is exactly
#   x0=(0,0,0), x1=(2,0,0), and the graph error at the optimum is ~0. If GTSAM
#   does not land there, either the graph is mis-specified or your hand calc is.
#
# HOW TO USE THIS FILE
#
#       pip install numpy gtsam
#       python3 exercise-03-two-pose-factor-graph.py
#
#   It runs Part A (two-pose, checked against the hand calc) and Part B (three
#   poses with a conflicting odometry chain + a loop closure), printing initial
#   and final errors, the optimized poses, and the marginal covariance of x2
#   BEFORE and AFTER the loop closure is added.
#
# ACCEPTANCE CRITERIA
#
#   [ ] Part A: final graph error is ~0 (< 1e-6) and x1 optimizes to (2,0,0) to
#       4 decimals — matching the hand calculation.
#   [ ] Part B: adding the loop-closure between factor REDUCES the final error's
#       inconsistency and SHRINKS marginalCovariance(X2) vs the open chain.
#   [ ] You can state, in one sentence, why a graph with NO prior is unsolvable
#       (it floats — any rigid transform of the solution fits equally well).
#   [ ] (Stretch in comments) you tried a robust Huber model on a bad loop closure.
#
# Expected output is at the bottom of the file.

import numpy as np
import gtsam
from gtsam import Pose2, NonlinearFactorGraph, Values
from gtsam.symbol_shorthand import X     # X(0), X(1), ... are pose-variable keys


def trace_cov(cov):
    """A scalar 'how uncertain is this pose' summary: the trace of the covariance."""
    return float(np.trace(cov))


# ---------------------------------------------------------------------------
# Part A — two poses, checked against a hand calculation
# ---------------------------------------------------------------------------
def part_a():
    print("==================== PART A: two-pose graph ====================")
    graph = NonlinearFactorGraph()

    prior_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.1, 0.1, 0.05]))
    odom_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.2, 0.2, 0.1]))

    # Prior anchors x0 at the origin. Without it the graph FLOATS (unsolvable).
    graph.add(gtsam.PriorFactorPose2(X(0), Pose2(0.0, 0.0, 0.0), prior_noise))
    # Between factor: odometry says +2 m in x, no rotation.
    graph.add(gtsam.BetweenFactorPose2(
        X(0), X(1), Pose2(2.0, 0.0, 0.0), odom_noise))

    # Deliberately WRONG initial guess so we can watch the optimizer fix it.
    initial = Values()
    initial.insert(X(0), Pose2(0.3, 0.2, 0.1))
    initial.insert(X(1), Pose2(2.3, 0.1, -0.2))

    print(f"  initial error: {graph.error(initial):.4e}")
    result = gtsam.LevenbergMarquardtOptimizer(
        graph, initial, gtsam.LevenbergMarquardtParams()).optimize()
    print(f"  final   error: {graph.error(result):.4e}")

    p0, p1 = result.atPose2(X(0)), result.atPose2(X(1))
    print(f"  optimized x0: ({p0.x():.4f}, {p0.y():.4f}, {p0.theta():.4f})  "
          "[hand calc: (0,0,0)]")
    print(f"  optimized x1: ({p1.x():.4f}, {p1.y():.4f}, {p1.theta():.4f})  "
          "[hand calc: (2,0,0)]")

    ok = (graph.error(result) < 1e-6
          and abs(p1.x() - 2.0) < 1e-3
          and abs(p1.y()) < 1e-3)
    print(f"  -> {'MATCHES hand calculation' if ok else 'DOES NOT MATCH — debug'}")
    print("===============================================================\n")
    return ok


# ---------------------------------------------------------------------------
# Part B — three poses, a conflicting odometry chain, and a loop closure
# ---------------------------------------------------------------------------
def build_open_chain():
    """x0 -> x1 -> x2, each +2m in x. Odometry only, no loop closure."""
    graph = NonlinearFactorGraph()
    prior_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.05, 0.05, 0.02]))
    odom_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.2, 0.2, 0.1]))

    graph.add(gtsam.PriorFactorPose2(X(0), Pose2(0, 0, 0), prior_noise))
    # Noisy odometry: each step claims +2.0 m but the SECOND step over-reports.
    graph.add(gtsam.BetweenFactorPose2(X(0), X(1), Pose2(2.0, 0.0, 0.0), odom_noise))
    graph.add(gtsam.BetweenFactorPose2(X(1), X(2), Pose2(2.3, 0.0, 0.0), odom_noise))

    initial = Values()
    initial.insert(X(0), Pose2(0.0, 0.0, 0.0))
    initial.insert(X(1), Pose2(2.0, 0.0, 0.0))
    initial.insert(X(2), Pose2(4.3, 0.0, 0.0))
    return graph, initial


def part_b():
    print("==================== PART B: loop closure ====================")

    # --- open chain (odometry only) ---
    graph, initial = build_open_chain()
    open_result = gtsam.LevenbergMarquardtOptimizer(
        graph, initial, gtsam.LevenbergMarquardtParams()).optimize()
    open_cov = gtsam.Marginals(graph, open_result).marginalCovariance(X(2))
    p2_open = open_result.atPose2(X(2))
    print(f"  OPEN chain:  x2 = ({p2_open.x():.4f}, {p2_open.y():.4f}) | "
          f"trace(cov_x2) = {trace_cov(open_cov):.5f}")

    # --- add a loop closure: a STRONG measurement that x2 is actually at 4.0 m,
    #     not 4.3 m. (e.g. the robot re-recognized a landmark with known geometry.)
    graph2, initial2 = build_open_chain()
    loop_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.05, 0.05, 0.02]))
    graph2.add(gtsam.BetweenFactorPose2(
        X(0), X(2), Pose2(4.0, 0.0, 0.0), loop_noise))
    loop_result = gtsam.LevenbergMarquardtOptimizer(
        graph2, initial2, gtsam.LevenbergMarquardtParams()).optimize()
    loop_cov = gtsam.Marginals(graph2, loop_result).marginalCovariance(X(2))
    p2_loop = loop_result.atPose2(X(2))
    print(f"  + LOOP CLOSURE: x2 = ({p2_loop.x():.4f}, {p2_loop.y():.4f}) | "
          f"trace(cov_x2) = {trace_cov(loop_cov):.5f}")

    tightened = trace_cov(loop_cov) < trace_cov(open_cov)
    pulled = abs(p2_loop.x() - 4.0) < abs(p2_open.x() - 4.0)
    print(f"  -> loop closure {'TIGHTENED' if tightened else 'did NOT tighten'} the "
          f"x2 marginal and {'pulled' if pulled else 'did not pull'} x2 toward the "
          "loop-consistent estimate.")
    print("=============================================================\n")
    return tightened and pulled


def main():
    a = part_a()
    b = part_b()
    print(f"SUMMARY: Part A {'PASS' if a else 'FAIL'} | Part B {'PASS' if b else 'FAIL'}")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (exact decimals depend on your gtsam build)
# -----------------------------------------------------------------------------
#
# ==================== PART A: two-pose graph ====================
#   initial error: 1.4124e+01
#   final   error: 1.00xxe-33
#   optimized x0: (0.0000, 0.0000, 0.0000)  [hand calc: (0,0,0)]
#   optimized x1: (2.0000, 0.0000, 0.0000)  [hand calc: (2,0,0)]
#   -> MATCHES hand calculation
# ===============================================================
#
# ==================== PART B: loop closure ====================
#   OPEN chain:  x2 = (4.3000, 0.0000) | trace(cov_x2) = 0.245xx
#   + LOOP CLOSURE: x2 = (4.00xx, 0.0000) | trace(cov_x2) = 0.017xx
#   -> loop closure TIGHTENED the x2 marginal and pulled x2 toward the
#      loop-consistent estimate.
# =============================================================
#
# SUMMARY: Part A PASS | Part B PASS
#
# WHAT TO TAKE AWAY:
#   * Part A: a consistent, noise-free graph optimizes to error ~0 and the answer
#     your hand calc predicted. That is the "the estimate converged" promise for a
#     factor graph. If you DELETE the prior factor, GTSAM's optimizer will fail or
#     return garbage — the graph floats, because nothing anchors it to the world.
#   * Part B: the open odometry chain trusts its last (over-reported) step and puts
#     x2 at 4.3 with a LARGE marginal. Adding ONE loop-closure factor pulls x2 back
#     toward 4.0 AND shrinks its covariance — the smoother distributed the
#     correction across the whole trajectory. That is exactly what slam_toolbox does
#     when "the map snaps straight" on loop closure (Lecture 2 §8).
#
# STRETCH (try it):
#   * Plant a BAD loop closure (say Pose2(7.0, 0, 0) — wildly wrong). With the plain
#     Gaussian loop_noise above, least squares believes it and drags x2 off to a
#     compromise. Now wrap loop_noise in a robust kernel:
#         huber = gtsam.noiseModel.mEstimator.Huber.Create(1.345)
#         robust = gtsam.noiseModel.Robust.Create(huber, loop_noise)
#     and use `robust` for the loop factor. The Huber kernel down-weights the
#     outlier and the good odometry wins. This is why real pose graphs use robust
#     noise models on automatic loop closures (Lecture 2 §4).
#   * Convert this batch solve to gtsam.ISAM2 (Lecture 2 §7): add the prior+x0,
#     update(); add each between factor + new variable, update(); confirm you get
#     the same x2 as the batch solve at a fraction of the per-step cost.
# -----------------------------------------------------------------------------

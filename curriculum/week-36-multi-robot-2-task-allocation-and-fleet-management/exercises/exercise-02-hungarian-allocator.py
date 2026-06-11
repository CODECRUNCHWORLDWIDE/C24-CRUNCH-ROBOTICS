#!/usr/bin/env python3
# Exercise 2 — The Hungarian allocator (optimal one-shot assignment)
#
# Goal: Build the optimal ST-SR-IA allocator. Given robot poses and task
#       locations, construct a cost matrix and solve it with the Hungarian
#       algorithm (scipy.optimize.linear_sum_assignment), handling the
#       rectangular N != M case correctly. Then PROVE it beats greedy on a
#       matrix designed to break greedy.
#
# Estimated time: 45 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   Standalone. Pure Python; no ROS2. Needs numpy + scipy (you have them).
#
#       python3 exercise-02-hungarian-allocator.py
#
#   It runs three scenarios and prints, for each, the greedy assignment, the
#   Hungarian assignment, and their totals — so you SEE where greedy loses.
#   The cost functions are factored so you can later import allocate_hungarian
#   into a ROS2 node that reads poses from /fleet_states.
#
# ACCEPTANCE CRITERIA
#
#   [ ] Scenario A (square, greedy-friendly): greedy and Hungarian agree.
#   [ ] Scenario B (the planted 2x2): greedy total = 101, Hungarian total = 4.
#   [ ] Scenario C (rectangular, 2 robots / 4 tasks): exactly 2 tasks assigned,
#       the other 2 reported as unassigned (back to the queue).
#   [ ] You can explain why scipy returns only min(N, M) pairs on a non-square
#       matrix, and what "unassigned" means for a live fleet.
#
# Expected output is at the bottom of the file.
#
# ---------------------------------------------------------------------------
# TODO MARKERS: this file is COMPLETE and runs as-is. The "# TODO" lines below
# mark the two spots a learner extends it (a real nav-graph cost, and an
# infeasibility sentinel). They are optional extensions, not missing code.
# ---------------------------------------------------------------------------

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

# A pose / location is just a 2D point here. In a node these come from
# /fleet_states (robot poses) and the task request (pickup locations).
Point = tuple[float, float]


def euclidean(a: Point, b: Point) -> float:
    """Straight-line distance. NOTE: lies through walls — see Lecture 1 §1.2."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def build_cost_matrix(
    robots: Sequence[Point],
    tasks: Sequence[Point],
    cost_fn=euclidean,
) -> np.ndarray:
    """C[i][j] = cost of robot i doing task j. Rows = robots, cols = tasks.

    cost_fn defaults to Euclidean. A real allocator passes a nav-graph path
    cost instead.
    """
    n, m = len(robots), len(tasks)
    cost = np.zeros((n, m), dtype=float)
    for i, r in enumerate(robots):
        for j, t in enumerate(tasks):
            cost[i, j] = cost_fn(r, t)
            # TODO 1: if robot i CANNOT do task j (wrong capability, barred
            #         zone), set cost[i, j] = INFEASIBLE so the solver avoids
            #         it. Define INFEASIBLE = 1e9 and wire a capability check.
    return cost


def allocate_greedy(cost: np.ndarray) -> tuple[list[tuple[int, int]], float]:
    """Repeatedly take the cheapest free (robot, task) cell. Fast, NOT optimal."""
    cost = cost.copy()
    n, m = cost.shape
    used_rows: set[int] = set()
    used_cols: set[int] = set()
    pairs: list[tuple[int, int]] = []
    total = 0.0
    for _ in range(min(n, m)):
        # Mask used rows/cols with +inf so they're never selected again.
        masked = cost.copy()
        for r in used_rows:
            masked[r, :] = math.inf
        for c in used_cols:
            masked[:, c] = math.inf
        i, j = np.unravel_index(np.argmin(masked), masked.shape)
        i, j = int(i), int(j)
        pairs.append((i, j))
        total += float(cost[i, j])
        used_rows.add(i)
        used_cols.add(j)
    return pairs, total


def allocate_hungarian(
    cost: np.ndarray,
) -> tuple[list[tuple[int, int]], float, list[int]]:
    """Optimal assignment via Kuhn-Munkres (scipy). Returns (pairs, total,
    unassigned_task_indices). On a non-square matrix scipy assigns min(N, M)
    pairs and leaves the surplus tasks unassigned — they go back in the queue.
    """
    row_ind, col_ind = linear_sum_assignment(cost)
    pairs = list(zip(row_ind.tolist(), col_ind.tolist()))
    total = float(cost[row_ind, col_ind].sum())
    assigned_tasks = set(col_ind.tolist())
    unassigned = [j for j in range(cost.shape[1]) if j not in assigned_tasks]
    return pairs, total, unassigned


def _print_scenario(name: str, robots, tasks) -> None:
    cost = build_cost_matrix(robots, tasks)
    print(f"\n===== {name} =====")
    print("cost matrix (rows=robots, cols=tasks):")
    with np.printoptions(precision=2, suppress=True):
        print(cost)

    g_pairs, g_total = allocate_greedy(cost)
    h_pairs, h_total, unassigned = allocate_hungarian(cost)

    print(f"greedy   : {g_pairs}  total={g_total:.2f}")
    print(f"hungarian: {h_pairs}  total={h_total:.2f}", end="")
    if unassigned:
        print(f"  UNASSIGNED tasks (back to queue): {unassigned}")
    else:
        print()

    if h_total < g_total - 1e-6:
        ratio = g_total / h_total if h_total > 0 else float("inf")
        print(f"  -> HUNGARIAN WINS: greedy is {ratio:.2f}x worse. "
              f"Greedy's local choice forced a globally bad assignment.")
    elif abs(h_total - g_total) <= 1e-6:
        print("  -> tie on this matrix (greedy got lucky; not guaranteed).")
    else:
        # Should never happen: Hungarian is optimal, so it can't be worse.
        print("  -> UNEXPECTED: Hungarian should never lose. Check the matrix.")


def main() -> None:
    # Scenario A: square, greedy happens to be optimal (Exercise 1 Step 1).
    _print_scenario(
        "Scenario A (3 robots, 3 tasks — greedy-friendly)",
        robots=[(0.0, 0.0), (10.0, 0.0), (5.0, 8.0)],
        tasks=[(1.0, 1.0), (9.0, 1.0), (4.0, 4.0)],
    )

    # Scenario B: the planted 2x2 where greedy is 25x worse. We pass a precomputed
    # matrix directly by faking poses whose Euclidean costs equal the matrix is
    # awkward, so build the matrix explicitly here.
    print("\n===== Scenario B (the planted 2x2 — greedy loses badly) =====")
    cost_b = np.array([[1.0, 2.0], [2.0, 100.0]])
    print("cost matrix:")
    print(cost_b)
    gb_pairs, gb_total = allocate_greedy(cost_b)
    hb_pairs, hb_total, _ = allocate_hungarian(cost_b)
    print(f"greedy   : {gb_pairs}  total={gb_total:.2f}")    # 101
    print(f"hungarian: {hb_pairs}  total={hb_total:.2f}")    # 4
    print(f"  -> greedy is {gb_total / hb_total:.2f}x worse — it stranded "
          f"robot 1 on the cost-100 cell.")

    # Scenario C: rectangular — 2 robots, 4 tasks. Only 2 tasks done this round.
    # TODO 2: re-run allocate_hungarian on the unassigned tasks in a SECOND round
    #         to simulate the robots becoming free again. (This is the bridge to
    #         time-extended assignment — see Exercise 3's auction.)
    _print_scenario(
        "Scenario C (2 robots, 4 tasks — rectangular)",
        robots=[(0.0, 0.0), (10.0, 0.0)],
        tasks=[(1.0, 1.0), (9.0, 1.0), (2.0, 0.5), (8.0, 0.5)],
    )


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (totals exact; pair tie-breaks may vary by scipy version)
# -----------------------------------------------------------------------------
#
# ===== Scenario A (3 robots, 3 tasks — greedy-friendly) =====
# cost matrix (rows=robots, cols=tasks):
# [[1.41 9.06 5.66]
#  [9.06 1.41 7.21]
#  [8.06 8.06 4.12]]
# greedy   : [(0, 0), (1, 1), (2, 2)]  total=6.95
# hungarian: [(0, 0), (1, 1), (2, 2)]  total=6.95
#   -> tie on this matrix (greedy got lucky; not guaranteed).
# (Exact total ~6.95; the by-hand value of 6.94 in Exercise 1 rounds each cell
#  separately, while this sums the full-precision distances — both are right.)
#
# ===== Scenario B (the planted 2x2 — greedy loses badly) =====
# cost matrix:
# [[  1.   2.]
#  [  2. 100.]]
# greedy   : [(0, 0), (1, 1)]  total=101.00
# hungarian: [(0, 1), (1, 0)]  total=4.00
#   -> greedy is 25.25x worse — it stranded robot 1 on the cost-100 cell.
#
# ===== Scenario C (2 robots, 4 tasks — rectangular) =====
# cost matrix (rows=robots, cols=tasks):
# [[1.41 9.06 2.06 8.02]
#  [9.06 1.41 8.02 2.06]]
# greedy   : [(0, 0), (1, 1)]  total=2.83
# hungarian: [(0, 0), (1, 1)]  total=2.83  UNASSIGNED tasks (back to queue): [2, 3]
#   -> tie on this matrix (greedy got lucky; not guaranteed).
#
# The lesson: with more tasks than robots, the Hungarian solver assigns each
# robot ONE task (min(N,M)=2 pairs) and leaves the surplus tasks unassigned.
# On a live fleet those go back in the queue for the next round — which is
# exactly why a streaming fleet wants an AUCTION (Exercise 3), not a fresh
# global re-solve on every task arrival.
# -----------------------------------------------------------------------------

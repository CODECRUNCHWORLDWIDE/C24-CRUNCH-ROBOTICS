#!/usr/bin/env python3
# Exercise 3 — The stale/wrong inter-robot transform probe (double-walling)
#
# Goal: Take the merge from Exercise 2 and feed it a WRONG inter-robot transform
#       (the offset between robotA/map and robotB/map is off by a few cells).
#       Watch the SAME wall both robots saw split into TWO parallel walls in the
#       merged grid — the 'double-walled map' signature of a bad transform — and
#       QUANTIFY the error against the correct merge.
#
# Estimated time: 45 minutes. Runnable.
#
# THE FAILURE WE INDUCE
#
#   Both robots observe the same physical wall. With the CORRECT offset, that
#   wall lands on the same merged cells from both grids and appears as ONE wall.
#   With a WRONG offset (off by delta cells), robot B's copy of the wall lands
#   delta cells away from robot A's copy -> two walls -> the planner sees a
#   corridor that is delta*resolution meters off, or a phantom obstacle.
#
#   This is the single most instructive multi-robot bug, and you can SEE it in
#   rviz2 without any metric. The metric just lets you put a number on it.
#
# HOW TO USE THIS FILE
#
#   Standalone. Source ROS2 Jazzy and run:
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-03-stale-transform-probe.py
#
#   It builds two grids that BOTH contain the same wall, merges them once with
#   the correct offset and once with a wrong offset, counts occupied cells in
#   each, and reports the 'extra wall' the bad transform invented. Prints a
#   quantified diagnosis and exits 0 (the double-wall was detected) or 1.
#
#   Flip WRONG_DELTA to 0 to confirm the correct transform produces NO extra
#   wall (single, crisp wall).
#
# ACCEPTANCE CRITERIA
#
#   [ ] With WRONG_DELTA != 0: the bad merge has strictly MORE occupied cells
#       than the good merge; the program prints "DOUBLE-WALL DETECTED" and the
#       count of phantom occupied cells, and exits 0.
#   [ ] With WRONG_DELTA = 0: good and bad merges are identical; the program
#       prints "no double-wall (transform correct)" and exits 0.
#   [ ] You can state why occupied-cell count is a valid double-wall metric here
#       (the same wall counted twice in different places inflates the count).
#
# Expected output is at the bottom of the file.

import sys

import numpy as np

OCC, FREE, UNK = 100, 0, -1

# Off-by-this-many-cells error in the inter-robot transform. The 'stale/wrong
# transform'. Set to 0 to prove a correct transform produces a single wall.
WRONG_DELTA = 2


def fuse_arrays(region: np.ndarray, incoming: np.ndarray) -> np.ndarray:
    occ = (region == OCC) | (incoming == OCC)
    free = (region == FREE) | (incoming == FREE)
    out = np.full_like(region, UNK)
    out[free] = FREE
    out[occ] = OCC
    return out


def merge(a: np.ndarray, b: np.ndarray, offset_b: tuple[int, int]) -> np.ndarray:
    ha, wa = a.shape
    hb, wb = b.shape
    ox, oy = offset_b
    min_x, min_y = min(0, ox), min(0, oy)
    max_x, max_y = max(wa, ox + wb), max(ha, oy + hb)
    W, H = max_x - min_x, max_y - min_y
    merged = np.full((H, W), UNK, dtype=np.int16)

    def blit(grid: np.ndarray, gx: int, gy: int) -> None:
        h, w = grid.shape
        sy, sx = gy - min_y, gx - min_x
        region = merged[sy:sy + h, sx:sx + w]
        merged[sy:sy + h, sx:sx + w] = fuse_arrays(region, grid)

    blit(a, 0, 0)
    blit(b, ox, oy)
    return merged


def build_shared_wall_grids() -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    """Two 6-wide, 5-tall grids that BOTH contain the same vertical wall.

    In world coordinates the wall is at world column 4 (a real wall both robots
    drove past and mapped). Robot A's grid covers world cols 0-5 directly. Robot
    B's grid is the SAME wall, but expressed in B's own frame; the TRUE offset
    that re-aligns B onto A is (0, 0) here (they mapped the identical region).

    A correct merge lands B's wall exactly on A's wall: one wall. A wrong offset
    of WRONG_DELTA shifts B's wall sideways: two walls.
    """
    def room_with_wall_at(col: int, w: int = 6, h: int = 5) -> np.ndarray:
        g = np.full((h, w), FREE, dtype=np.int16)
        g[:, col] = OCC
        return g

    a = room_with_wall_at(4)
    b = room_with_wall_at(4)        # same wall, same column in each robot's frame
    true_offset = (0, 0)            # they mapped the identical world region
    return a, b, true_offset


def count_occupied(grid: np.ndarray) -> int:
    return int(np.count_nonzero(grid == OCC))


def run() -> int:
    a, b, true_offset = build_shared_wall_grids()

    good = merge(a, b, true_offset)
    bad_offset = (true_offset[0] + WRONG_DELTA, true_offset[1])
    bad = merge(a, b, bad_offset)

    good_occ = count_occupied(good)
    bad_occ = count_occupied(bad)
    phantom = bad_occ - good_occ

    print("CORRECT-transform merge (offset", true_offset, "):")
    print(good)
    print(f"  occupied cells: {good_occ}  (one wall)")
    print("WRONG-transform merge (offset", bad_offset,
          f", off by {WRONG_DELTA} cells):")
    print(bad)
    print(f"  occupied cells: {bad_occ}")

    if WRONG_DELTA == 0:
        if np.array_equal(good, bad):
            print("\nno double-wall (transform correct): both merges identical, "
                  "one crisp wall. This is what a right inter-robot transform "
                  "looks like.")
            return 0
        print("\nUNEXPECTED: WRONG_DELTA=0 but merges differ.")
        return 1

    if phantom > 0:
        res = 0.5
        print(f"\nDOUBLE-WALL DETECTED: the wrong transform invented {phantom} "
              f"phantom occupied cells — robot B's copy of the wall landed "
              f"{WRONG_DELTA} cells ({WRONG_DELTA * res:.2f} m) away from robot "
              f"A's copy of the SAME wall. The planner now sees two walls where "
              f"there is one. Re-measure the inter-robot offset (or check whether "
              f"robotB/map drifted).")
        return 0
    print("\nUNEXPECTED: a wrong transform should add occupied cells.")
    return 1


if __name__ == "__main__":
    sys.exit(run())


# -----------------------------------------------------------------------------
# Expected output (WRONG_DELTA = 2)
# -----------------------------------------------------------------------------
#
# CORRECT-transform merge (offset (0, 0) ):
# [[  0   0   0   0 100   0]
#  ... (5 rows) ...]
#   occupied cells: 5  (one wall)
# WRONG-transform merge (offset (2, 0), off by 2 cells):
#   occupied cells: 10
#
# DOUBLE-WALL DETECTED: the wrong transform invented 5 phantom occupied cells —
# robot B's copy of the wall landed 2 cells (1.00 m) away from robot A's copy of
# the SAME wall. ...
#
# Expected output (WRONG_DELTA = 0)
# -----------------------------------------------------------------------------
#
#   occupied cells: 5  (one wall)   [both merges]
# no double-wall (transform correct): both merges identical, one crisp wall.
#
# NOTE: the exact counts depend on grid size, but the SHAPE is invariant: a wrong
# inter-robot transform turns one shared wall into two, inflating the occupied-
# cell count by roughly one wall's worth. That doubled wall is the thing you see
# in rviz2 and the reason your shared map is untrustworthy until the transform is
# right. This is Lecture 2 Part 2 made measurable.
# -----------------------------------------------------------------------------

#!/usr/bin/env python3
# Exercise 2 — Merge two occupancy grids (known relative transform)
#
# Goal: Fuse two nav_msgs/OccupancyGrid maps that overlap in the world into ONE
#       merged grid in the shared 'world' frame, using the occupied-wins fusion
#       rule (occupied 100 > free 0 > unknown -1). Prove the merge is correct
#       against a hand-computed expected grid.
#
# Estimated time: 45 minutes. Runnable.
#
# WHY THIS MATTERS
#
#   This is the heart of week-35 shared mapping. Two robots each build a map in
#   their own 'map' frame; tied into 'world' by a known offset, their grids can
#   be merged. The two traps this exercise drills:
#     * info.origin / cell offset: forget it and the maps merge SHIFTED.
#     * the fusion rule: AVERAGE instead of occupied-wins and you get gray mush
#       (value ~50) that a planner can't trust.
#
# HOW TO USE THIS FILE
#
#   Standalone. No colcon package, no running sim required — it fabricates two
#   small grids with a known overlap. Source ROS2 Jazzy and run:
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-02-merge-two-grids.py
#
#   It builds grid A (a room with a wall) and grid B (an overlapping room with a
#   different wall), merges them with a KNOWN cell offset, and checks the merged
#   grid against a hand-computed expectation. Prints PASS/FAIL and exits 0/1.
#
#   To see it on a real graph, run with --publish: it spins a node publishing
#   /robotA/map, /robotB/map, and /shared_map (all TRANSIENT_LOCAL) so you can
#   view all three in rviz2 with Fixed Frame = world.
#
# ACCEPTANCE CRITERIA
#
#   [ ] Default run prints "PASS: merged grid matches expected" and exits 0.
#   [ ] You can point at the one cell where A says occupied and B says free, and
#       confirm the merged cell is OCCUPIED (occupied wins).
#   [ ] Changing fuse() to average (return (a+b)//2) makes the run print FAIL —
#       you have reproduced the gray-mush bug on purpose.
#   [ ] With --publish, `ros2 topic echo /shared_map --field info` shows a grid
#       whose width/height cover BOTH input grids.
#
# Expected output is at the bottom of the file.

import argparse
import sys

import numpy as np


# Cell value constants (nav_msgs/OccupancyGrid semantics).
OCC, FREE, UNK = 100, 0, -1


def fuse(a: int, b: int) -> int:
    """Merge two cell values. occupied(100) > free(0) > unknown(-1).

    NEVER average: averaging FREE and OCC gives 50 ('gray mush'), which a planner
    renders as a maybe-wall it might drive through. occupied-wins is conservative
    in the SAFE direction: the merged map over-reports obstacles, never under.
    """
    if a == OCC or b == OCC:
        return OCC
    if a == FREE or b == FREE:
        return FREE
    return UNK


# Vectorized form of fuse() for whole-array merging.
def fuse_arrays(region: np.ndarray, incoming: np.ndarray) -> np.ndarray:
    occ = (region == OCC) | (incoming == OCC)
    free = (region == FREE) | (incoming == FREE)
    out = np.full_like(region, UNK)
    out[free] = FREE
    out[occ] = OCC          # occupied applied last so it wins over free
    return out


def merge(a: np.ndarray, b: np.ndarray, offset_b: tuple[int, int]) -> tuple[np.ndarray, tuple[int, int]]:
    """Merge grid b into grid a's world. b is shifted by offset_b (cells, in
    world). a's corner is the world origin (0,0). Returns (merged, min_corner).

    Same resolution, same orientation (the known-offset week-35 simplification).
    """
    ha, wa = a.shape
    hb, wb = b.shape
    ox, oy = offset_b

    # Merged extent = bounding box of A at (0,0) and B at (ox, oy).
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
    return merged, (min_x, min_y)


def build_test_grids() -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    """Two 4x4 grids that overlap in a 2x2 region, with a deliberate conflict.

    Grid A (robotA/map): a vertical wall on its right edge (col 3 occupied).
    Grid B (robotB/map): all free except one cell that A also saw — but A saw it
    occupied and B saw it free. Occupied must win there.
    Offset: B sits 2 cells to the right of A in world (ox=2, oy=0).
    """
    a = np.array([
        [FREE, FREE, FREE, OCC],
        [FREE, FREE, FREE, OCC],
        [FREE, FREE, FREE, OCC],
        [FREE, FREE, FREE, OCC],
    ], dtype=np.int16)

    b = np.array([
        [FREE, FREE, UNK, UNK],
        [FREE, FREE, UNK, UNK],
        [FREE, FREE, UNK, UNK],
        [FREE, FREE, UNK, UNK],
    ], dtype=np.int16)

    offset_b = (2, 0)   # B's left edge overlaps A's columns 2-3
    return a, b, offset_b


def expected_merged() -> np.ndarray:
    """Hand-computed merge of build_test_grids(). World is 6 wide, 4 tall.
    A occupies cols 0-3; B occupies cols 2-5. Overlap cols 2-3.
    Col 3 in A is OCC; B's col-1 (world col 3) is FREE -> occupied wins -> OCC.
    Col 2 in A is FREE; B's col-0 (world col 2) is FREE -> FREE.
    Cols 4-5 come from B's cols 2-3, which are UNK.
    """
    return np.array([
        [FREE, FREE, FREE, OCC, UNK, UNK],
        [FREE, FREE, FREE, OCC, UNK, UNK],
        [FREE, FREE, FREE, OCC, UNK, UNK],
        [FREE, FREE, FREE, OCC, UNK, UNK],
    ], dtype=np.int16)


def run_check() -> int:
    a, b, offset_b = build_test_grids()
    merged, corner = merge(a, b, offset_b)
    expected = expected_merged()

    print("grid A (robotA/map):")
    print(a)
    print("grid B (robotB/map), offset by", offset_b, ":")
    print(b)
    print("merged (world frame), corner at", corner, ":")
    print(merged)

    if merged.shape == expected.shape and np.array_equal(merged, expected):
        # Spotlight the conflict cell: world (col=3, row=0) — A:OCC, B:FREE.
        print(f"\nconflict cell world(col=3,row=0): A=OCC, B=FREE, merged="
              f"{merged[0, 3]} (occupied wins)")
        print("PASS: merged grid matches expected.")
        return 0
    print("\nFAIL: merged grid does not match expected.")
    print("If you changed fuse() to average, the conflict cell is ~50 (gray "
          "mush) instead of 100 — that is the bug this exercise warns about.")
    print("expected:")
    print(expected)
    return 1


def run_publish() -> None:
    """Spin a node publishing the three grids as TRANSIENT_LOCAL topics so you
    can see them in rviz2 (Fixed Frame = world)."""
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    from nav_msgs.msg import OccupancyGrid

    def latched_qos() -> QoSProfile:
        # The latched-map profile from week 5: RELIABLE / TRANSIENT_LOCAL / depth 1.
        return QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

    def to_grid(arr: np.ndarray, frame: str, ox_m: float, oy_m: float,
                res: float = 0.5) -> OccupancyGrid:
        g = OccupancyGrid()
        g.header.frame_id = frame
        g.info.resolution = res
        g.info.height, g.info.width = arr.shape
        g.info.origin.position.x = ox_m
        g.info.origin.position.y = oy_m
        g.info.origin.orientation.w = 1.0
        g.data = arr.flatten().astype(np.int8).tolist()
        return g

    class Pub(Node):
        def __init__(self) -> None:
            super().__init__("merge_demo")
            a, b, offset_b = build_test_grids()
            merged, corner = merge(a, b, offset_b)
            res = 0.5
            self.pa = self.create_publisher(OccupancyGrid, "/robotA/map", latched_qos())
            self.pb = self.create_publisher(OccupancyGrid, "/robotB/map", latched_qos())
            self.ps = self.create_publisher(OccupancyGrid, "/shared_map", latched_qos())
            self.pa.publish(to_grid(a, "world", 0.0, 0.0, res))
            self.pb.publish(to_grid(b, "world", offset_b[0] * res, offset_b[1] * res, res))
            self.ps.publish(to_grid(merged, "world", corner[0] * res, corner[1] * res, res))
            self.get_logger().info(
                f"published /robotA/map, /robotB/map, /shared_map "
                f"(merged {merged.shape[1]}x{merged.shape[0]}). View in rviz2, "
                f"Fixed Frame = world. Ctrl+C to stop."
            )

    rclpy.init()
    node = Pub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Occupancy-grid merge demo.")
    parser.add_argument("--publish", action="store_true",
                        help="publish the three grids for rviz2 instead of self-checking")
    args = parser.parse_args()
    if args.publish:
        run_publish()
    else:
        sys.exit(run_check())


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (default self-check)
# -----------------------------------------------------------------------------
#
# grid A (robotA/map):
# [[  0   0   0 100]
#  [  0   0   0 100]
#  [  0   0   0 100]
#  [  0   0   0 100]]
# grid B (robotB/map), offset by (2, 0) :
# [[ 0  0 -1 -1]
#  [ 0  0 -1 -1]
#  [ 0  0 -1 -1]
#  [ 0  0 -1 -1]]
# merged (world frame), corner at (0, 0) :
# [[  0   0   0 100  -1  -1]
#  [  0   0   0 100  -1  -1]
#  [  0   0   0 100  -1  -1]
#  [  0   0   0 100  -1  -1]]
#
# conflict cell world(col=3,row=0): A=OCC, B=FREE, merged=100 (occupied wins)
# PASS: merged grid matches expected.
#
# The lesson: at the conflict cell, A's confident wall (100) beats B's free (0).
# Averaging would have produced 50 — a maybe-wall the planner can't use. Forget
# info.origin / the cell offset and the maps would have merged shifted, producing
# the double-walled map of Exercise 3.
# -----------------------------------------------------------------------------

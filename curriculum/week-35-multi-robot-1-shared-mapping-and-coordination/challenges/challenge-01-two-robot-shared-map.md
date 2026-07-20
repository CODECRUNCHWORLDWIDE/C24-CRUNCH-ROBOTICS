# Challenge 1 — Two-Robot Shared Map With a Drifting Frame

**Time estimate:** ~90 minutes.

## Problem statement

You are the integrator on a two-robot mapping fleet. Both robots map a shared warehouse; a merger node fuses their maps into `/shared_map` that a planner consults. It works on the bench. Then in the field, one robot's SLAM closes a big loop and its `map` frame *jumps* — the origin shifts by 30 cm as the optimizer corrects accumulated drift. From that instant, the merger's static `world -> robotB/map` transform is wrong by 30 cm, and the shared map double-walls every wall both robots saw.

Your job: stand up the system, reproduce the drift-induced double-wall, **detect** it, and **recover** — re-establish a correct inter-robot transform so the shared map goes crisp again — all without restarting either robot's SLAM (in the real world you cannot; a restart loses the map).

This mirrors the real skill. Inter-robot transforms are not static in reality; they drift as each robot's SLAM corrects itself. A fleet that assumes a once-measured offset is forever-correct double-walls the first time anyone closes a loop. The senior move is to *expect* the drift and re-estimate.

## The harness

Save this as `drifting_merger.py`. It runs a self-contained two-robot world (no Gz Sim required): two grids of the same room with the same wall, a merger publishing `/shared_map`, and a `--drift` flag that jumps robot B's frame mid-run.

```python
#!/usr/bin/env python3
"""Two-robot shared-map harness with an injectable frame drift. Reproduce the
double-wall, detect it, recover the transform."""
import argparse
import threading
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from nav_msgs.msg import OccupancyGrid

OCC, FREE, UNK = 100, 0, -1


def latched_qos() -> QoSProfile:
    return QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                      durability=DurabilityPolicy.TRANSIENT_LOCAL,
                      history=HistoryPolicy.KEEP_LAST, depth=1)


def room_with_wall(col: int, w: int = 8, h: int = 6) -> np.ndarray:
    g = np.full((h, w), FREE, dtype=np.int16)
    g[:, col] = OCC
    return g


def fuse_arrays(region, incoming):
    occ = (region == OCC) | (incoming == OCC)
    free = (region == FREE) | (incoming == FREE)
    out = np.full_like(region, UNK)
    out[free] = FREE
    out[occ] = OCC
    return out


def merge(a, b, offset_b):
    ha, wa = a.shape; hb, wb = b.shape; ox, oy = offset_b
    min_x, min_y = min(0, ox), min(0, oy)
    max_x, max_y = max(wa, ox + wb), max(ha, oy + hb)
    merged = np.full((max_y - min_y, max_x - min_x), UNK, dtype=np.int16)
    for grid, gx, gy in ((a, 0, 0), (b, ox, oy)):
        h, w = grid.shape
        sy, sx = gy - min_y, gx - min_x
        merged[sy:sy + h, sx:sx + w] = fuse_arrays(merged[sy:sy + h, sx:sx + w], grid)
    return merged


class Harness(Node):
    def __init__(self, drift: int) -> None:
        super().__init__("drifting_merger")
        self.a = room_with_wall(4)
        self.b = room_with_wall(4)         # same wall, same column, in B's frame
        self.true_offset = (0, 0)          # correct alignment
        self.assumed_offset = (0, 0)       # what the merger believes
        self.drift = drift
        self.pub = self.create_publisher(OccupancyGrid, "/shared_map", latched_qos())
        self.create_timer(2.0, self.tick)  # merger runs every 2 s (periodic exchange)
        self.ticks = 0
        if drift:
            threading.Timer(6.0, self._inject_drift).start()

    def _inject_drift(self) -> None:
        # Robot B's SLAM closes a loop: its map frame jumps by `drift` cells.
        # The TRUE offset changes, but the merger's assumed_offset does NOT.
        self.true_offset = (self.true_offset[0] + self.drift, self.true_offset[1])
        self.get_logger().warn(
            f"robotB/map DRIFTED by {self.drift} cells (loop closure). "
            f"true offset now {self.true_offset}; merger still assumes "
            f"{self.assumed_offset}. Watch /shared_map double-wall.")

    def tick(self) -> None:
        self.ticks += 1
        # The merger fuses using its ASSUMED offset. If reality drifted, this is
        # now wrong and the map double-walls.
        b_in_world = self.true_offset   # where B's wall actually is, in world
        # The merger does NOT know true_offset; it blits B at assumed_offset.
        merged = merge(self.a, self.b, self.assumed_offset)
        occ = int(np.count_nonzero(merged == OCC))
        self.get_logger().info(f"tick {self.ticks}: /shared_map occupied cells = {occ} "
                               f"(one wall = {self.a.shape[0]})")
        g = OccupancyGrid()
        g.header.frame_id = "world"; g.info.resolution = 0.1
        g.info.height, g.info.width = merged.shape
        g.info.origin.orientation.w = 1.0
        g.data = merged.flatten().astype(np.int8).tolist()
        self.pub.publish(g)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drift", type=int, default=3,
                    help="cells robotB/map jumps at t=6s (0 = no drift)")
    args = ap.parse_args()
    rclpy.init()
    node = Harness(args.drift)
    print("harness running. Watch the occupied-cell count. Ctrl+C to stop.")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
```

```bash
source /opt/ros/jazzy/setup.bash
python3 drifting_merger.py --drift 3
```

Watch the logged occupied-cell count: it sits at one-wall's-worth for the first ~6 s, then the drift fires and... it *doesn't* change, because the harness merges at its `assumed_offset`, which is still the pre-drift value. The shared map is now wrong but the merger doesn't know. That gap — reality drifted, the assumed transform didn't — is the whole challenge.

## Your task

Deliver four things, in order:

1. **Reproduce and observe.** Run the harness with `--drift 3`. Confirm by inspecting `/shared_map` (echo `--field info`, or rviz2 with Fixed Frame `world`) that after the drift, robot B's contribution is misaligned. Note that the *logged* occupied count alone does **not** reveal the drift here — the merger is blind to it. That's the trap: the merger's own metric looks fine while the map is wrong.

2. **Build a double-wall detector.** Write a node `wall_auditor.py` that subscribes to `/shared_map` and detects double-walling *without* knowing the true offset. The robust signal: a single physical wall is one cell thick; a double-wall shows up as **two parallel occupied runs separated by free cells** in a row that should have one. Count "occupied runs per row" and flag when it exceeds the expected number. Report the gap (in cells, converted to meters) between the doubled walls.

3. **Recover the transform.** Make the merger re-estimate the inter-robot offset instead of trusting its static assumption. The honest approach for this harness: search small integer offsets and pick the one that **minimizes the merged occupied-cell count** (the correct alignment collapses the two walls into one, which is the *fewest* occupied cells). Implement `best_offset(a, b)` that sweeps a few-cell window and returns the offset that minimizes occupied cells; feed it back into the merger so `/shared_map` goes crisp again.

4. **Confirm recovery.** After recovery, `/shared_map` shows a single wall again and your `wall_auditor.py` reports zero double-walls. Capture before/after.

## Acceptance criteria

- [ ] A `challenge-01-writeup.md` documenting the four steps with the actual occupied-cell counts and auditor output before drift, after drift, and after recovery.
- [ ] `wall_auditor.py` detects the double-wall from `/shared_map` alone (no access to the true offset) and reports the gap in meters.
- [ ] `recovering_merger.py` — your modified harness whose `best_offset()` collapses the double-wall by minimizing occupied cells, so `/shared_map` is crisp again after the drift.
- [ ] You correctly explain *why* minimizing occupied cells recovers the alignment (two copies of one wall = more occupied cells than one aligned copy; correct alignment is the minimum).
- [ ] You state the limitation of the minimize-occupied-cells heuristic (it works because the room has structure; in a near-empty room there's nothing to align on, which is exactly why real systems use place recognition / loop closures, not occupied-cell counting).
- [ ] Committed to your Week 35 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The seductive wrong fix is to make `world -> robotB/map` a *static* transform you re-measure by hand each time it drifts. That works for one drift and fails forever after, because the frame drifts *continuously* as SLAM runs — every loop closure nudges it. The right mental model is that the inter-robot transform is a **continuously re-estimated** quantity, not a constant. Your `best_offset()` running on the merger's timer *is* a (crude) continuous re-estimator. Hand-re-measuring is the junior move; building the re-estimation into the loop is the senior one. State which you did.

## Stretch

- Replace the occupied-cell-minimizing search with a **2D cross-correlation** of the two occupancy grids (`scipy.signal.correlate2d` on the occupied masks). The peak of the correlation is the alignment offset — a real, if simple, map-registration technique, and exactly the kind of thing `multirobot_map_merge` does with features. Compare its recovered offset to your search.
- Make the drift *gradual* (1 cell every 4 s instead of a 3-cell jump) and show your continuous re-estimator tracks it, while a static transform would fall progressively further behind.
- Add a *third* robot and confirm your auditor and recovery still work — the occupied-cell-minimization generalizes, but you now search a transform per robot, and the cost grows.

## Why this matters

In week 40 the Phase 5 milestone requires "two simulated robots share a map without collision." A shared map that double-walls is a shared map that *causes* collisions — the planner routes through a corridor that's narrower than the doubled walls suggest, or stops dead at a phantom obstacle. Knowing that inter-robot transforms drift, detecting the double-wall it causes, and re-estimating the alignment live is the difference between a demo that works once and a fleet that works on Tuesday. Every multi-robot operator eventually watches a loop closure wreck a shared map; the one who can name it and recover it in five minutes is the one who keeps the fleet running.

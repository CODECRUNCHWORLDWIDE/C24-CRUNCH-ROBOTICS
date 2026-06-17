#!/usr/bin/env python3
"""Exercise 3 — Detection-to-cluster data association.

Fuse the two views of the world your perception stack produces:
  - 3D clusters (WHERE things are: position, size; no class)   [Week 15]
  - 2D detections (WHAT things are: class, confidence; no metric position) [Week 13]
into single fused objects (the red CUP at map(1.82, -0.41, 0.74)). This is the
data association at the heart of the fused perception node (Lecture 2 §2.1).

THE METHOD (Lecture 2 §2.1)

  1. Project each 3D cluster's box into the image plane (via the camera intrinsics
     and the transform AT THE DETECTION'S STAMP).
  2. Build the IoU matrix (clusters x detections).
  3. Solve the assignment with the Hungarian algorithm (NOT greedy — greedy double-
     matches and is order-dependent).
  4. Handle the no-match cases explicitly:
       - cluster with no detection  -> publish as a 3D object, class="unknown"
       - detection with no cluster  -> log (no metric position to publish)

--------------------------------------------------------------------------------
RUN
--------------------------------------------------------------------------------
Standalone. Source ROS2 Jazzy (+ pip install scipy numpy), then run.

  PART A — --demo (no stack): synthesize 3 clusters and 3 detections with a KNOWN
  correct pairing (plus one cluster with no detection = a LiDAR-only object), and
  assert the association recovers it.

      python3 exercise-03-detection-cluster-association.py        # runs --demo

  PART B — live: subscribe to /perception/clusters and /perception/detections_2d,
  synchronize them, associate, and publish /perception/objects.

      python3 exercise-03-detection-cluster-association.py --live

ACCEPTANCE CRITERIA
  [ ] --demo recovers the correct cluster<->detection pairing and prints PASS.
  [ ] --demo correctly handles the no-match cluster (publishes it as "unknown",
      does NOT drop it) and the no-match detection (logs it).
  [ ] You can state why the Hungarian solver beats greedy matching (no double-
      matches, order-independent, globally optimal assignment).

Expected output is at the bottom of the file.
"""

import argparse
import sys
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass
class Cluster:
    """A 3D cluster: a centroid and a projected 2D image box (already projected
    here for the demo; in --live you project via the camera model)."""
    cid: int
    centroid: tuple  # (x, y, z) in map frame
    image_box: tuple  # (u0, v0, u1, v1) — projection into the image


@dataclass
class Detection2D:
    did: int
    image_box: tuple  # (u0, v0, u1, v1)
    class_id: str
    score: float


@dataclass
class FusedObject:
    centroid: tuple
    class_id: str
    score: float
    source: str       # "2d+3d" or "lidar_only"


def iou(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / (area_a + area_b - inter + 1e-9)


def associate(clusters: list[Cluster], detections: list[Detection2D],
              iou_threshold: float = 0.3) -> list[FusedObject]:
    """Hungarian assignment of clusters to detections by IoU, with explicit
    no-match handling. Returns the fused objects."""
    fused: list[FusedObject] = []
    if not clusters:
        return fused

    if detections:
        # Cost matrix: negative IoU (linear_sum_assignment MINIMIZES cost).
        cost = np.zeros((len(clusters), len(detections)))
        for i, c in enumerate(clusters):
            for j, d in enumerate(detections):
                cost[i, j] = -iou(c.image_box, d.image_box)
        rows, cols = linear_sum_assignment(cost)
        matched_c, matched_d = set(), set()
        for i, j in zip(rows, cols):
            if -cost[i, j] >= iou_threshold:        # only keep good matches
                d = detections[j]
                fused.append(FusedObject(clusters[i].centroid, d.class_id,
                                         d.score, "2d+3d"))
                matched_c.add(i)
                matched_d.add(j)
        # No-match DETECTIONS: log them (no metric position to publish).
        for j, d in enumerate(detections):
            if j not in matched_d:
                print(f"  [assoc] detection '{d.class_id}' (#{d.did}) matched no "
                      f"cluster — logged, not published (no 3D position).")
    else:
        matched_c = set()

    # No-match CLUSTERS: publish as 3D objects with class "unknown" — an
    # unclassified obstacle is still an obstacle the planner must avoid.
    for i, c in enumerate(clusters):
        if i not in matched_c:
            fused.append(FusedObject(c.centroid, "unknown", 0.0, "lidar_only"))
    return fused


def run_demo() -> int:
    # 3 clusters; clusters 0,1 have matching detections; cluster 2 is LiDAR-only.
    clusters = [
        Cluster(0, (1.82, -0.41, 0.74), (300, 200, 360, 280)),   # the cup
        Cluster(1, (2.50, 0.30, 0.50), (120, 210, 200, 320)),    # the box
        Cluster(2, (0.90, 1.10, 0.40), (10, 220, 60, 300)),      # LiDAR-only
    ]
    detections = [
        Detection2D(0, (305, 205, 358, 278), "cup", 0.91),       # matches cluster 0
        Detection2D(1, (118, 212, 205, 322), "box", 0.84),       # matches cluster 1
        Detection2D(2, (500, 100, 540, 160), "person", 0.77),    # matches NOTHING
    ]

    print("[demo] associating 3 clusters with 3 detections "
          "(expect: 2 fused, 1 lidar-only, 1 detection unmatched)\n")
    fused = associate(clusters, detections)

    print("\n[demo] fused objects:")
    for f in fused:
        print(f"  {f.class_id:8s} conf={f.score:.2f} @ map{tuple(round(x,2) for x in f.centroid)}  [{f.source}]")

    by_class = {f.class_id: f for f in fused}
    ok = (
        len(fused) == 3
        and by_class.get("cup") and by_class["cup"].source == "2d+3d"
        and by_class.get("box") and by_class["box"].source == "2d+3d"
        and by_class.get("unknown") and by_class["unknown"].source == "lidar_only"
        and abs(by_class["cup"].centroid[0] - 1.82) < 1e-6
    )
    if ok:
        print("\nPASS: the cup and box fused (2D class + 3D position); the third "
              "cluster published as 'unknown' (lidar_only, NOT dropped); the "
              "unmatched 'person' detection was logged, not invented in 3D.")
        return 0
    print("\nFAIL: association did not recover the expected pairing. Check the IoU "
          "threshold and that no-match clusters become 'unknown' rather than "
          "being dropped.")
    return 1


def run_live() -> int:
    # The live path subscribes to /perception/clusters (Detection3DArray) and
    # /perception/detections_2d (Detection2DArray), synchronizes them with
    # message_filters (so cluster stamp ~ detection stamp), projects each cluster
    # into the image via image_geometry.PinholeCameraModel.project3dToPixel using
    # the transform AT THE DETECTION'S STAMP (Lecture 1 §1.5), runs associate(),
    # and publishes /perception/objects. The association logic above is reused
    # verbatim; only the I/O changes. See the mini-project for the full node.
    print("live mode: wire /perception/clusters + /perception/detections_2d via "
          "message_filters, project clusters into the image (transform at the "
          "DETECTION's stamp), call associate(), publish /perception/objects. "
          "The mini-project README has the full node spec.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Detection<->cluster association.")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    sys.exit(run_live() if args.live else run_demo())


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--demo)
# -----------------------------------------------------------------------------
#
# [demo] associating 3 clusters with 3 detections (expect: 2 fused, 1 lidar-only,
#        1 detection unmatched)
#
#   [assoc] detection 'person' (#2) matched no cluster — logged, not published
#           (no 3D position).
#
# [demo] fused objects:
#   cup      conf=0.91 @ map(1.82, -0.41, 0.74)  [2d+3d]
#   box      conf=0.84 @ map(2.5, 0.3, 0.5)      [2d+3d]
#   unknown  conf=0.00 @ map(0.9, 1.1, 0.4)      [lidar_only]
#
# PASS: the cup and box fused (2D class + 3D position); the third cluster
#       published as 'unknown' (lidar_only, NOT dropped); the unmatched 'person'
#       detection was logged, not invented in 3D.
#
# The lesson: data association is an ASSIGNMENT problem (Hungarian, not greedy),
# and the no-match cases are not edge cases — they are the common case. A LiDAR
# cluster with no class is still an obstacle (publish "unknown"); a detection with
# no cluster has no 3D position (log it). Dropping either is a perception bug.
# -----------------------------------------------------------------------------

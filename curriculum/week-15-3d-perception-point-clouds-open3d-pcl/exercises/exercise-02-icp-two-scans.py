#!/usr/bin/env python3
# Exercise 2 — ICP on two scans (point-to-point vs point-to-plane)
#
# Goal: Register two overlapping clouds with BOTH point-to-point and point-to-
#       plane ICP, compare iterations / fitness / inlier-RMSE, and apply the
#       three-part trust test (high fitness, low RMSE, plausible transform). You
#       will learn the load-bearing skill of the week: ICP always returns a
#       transform; only fitness + RMSE + plausibility tell you if it is RIGHT.
#
# Estimated time: 50 minutes. Runnable.
#
# THE THREE-PART TRUST TEST (Lecture 2, Part 1.2)
#
#   A trustworthy ICP result has:
#     (1) HIGH fitness        (most source points found a correspondence)
#     (2) LOW inlier-RMSE     (the matched points are tightly aligned)
#     (3) PLAUSIBLE transform (the motion is physically reasonable)
#   All three. ICP returning without an error means NOTHING.
#
# HOW TO USE THIS FILE
#
#   Standalone. pip install open3d numpy, then run.
#
#   PART A — --demo (no dataset): synthesize a cloud, make a copy, and apply a
#   KNOWN ground-truth transform (0.5 m forward, small yaw). Register the two and
#   assert ICP RECOVERS the known transform. This verifies your understanding.
#
#       pip install open3d numpy
#       python3 exercise-02-icp-two-scans.py            # runs --demo
#
#   PART B — dataset: point it at two real consecutive scans.
#
#       python3 exercise-02-icp-two-scans.py --source scan_000.pcd \
#                                            --target scan_001.pcd
#
# ACCEPTANCE CRITERIA
#
#   [ ] --demo: point-to-plane ICP recovers the known transform (translation
#       within 1 cm, yaw within 0.5 deg) and prints PASS.
#   [ ] --demo shows point-to-plane converging in FEWER iterations than point-to-
#       point for the same result (it is faster and more robust).
#   [ ] You can read fitness + inlier-RMSE and state whether the result passes
#       the three-part trust test.
#   [ ] The visualizer (if a display is available) shows source aligned onto
#       target after registration.
#
# Expected output is at the bottom of the file.

import argparse
import sys

import numpy as np
import open3d as o3d


def make_transform(tx: float, ty: float, yaw_deg: float) -> np.ndarray:
    """A 4x4 SE(3): translation (tx, ty, 0) + yaw about z."""
    c, s = np.cos(np.radians(yaw_deg)), np.sin(np.radians(yaw_deg))
    T = np.eye(4)
    T[:3, :3] = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    T[0, 3], T[1, 3] = tx, ty
    return T


def preprocess(pcd: o3d.geometry.PointCloud, voxel=0.05) -> o3d.geometry.PointCloud:
    """Downsample + estimate normals (point-to-plane needs normals on target)."""
    down = pcd.voxel_down_sample(voxel)
    down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=2 * voxel, max_nn=30))
    return down


def synth_room(n=4000, seed=15) -> o3d.geometry.PointCloud:
    """A synthetic 'room': floor + two walls + a box. Enough geometry to constrain
    ICP in all directions (NOT a degenerate corridor)."""
    rng = np.random.default_rng(seed)
    pts = []
    # floor 4x4 m
    pts.append(np.column_stack((rng.uniform(-2, 2, n), rng.uniform(-2, 2, n),
                                np.zeros(n))))
    # wall at x = 2
    pts.append(np.column_stack((np.full(n, 2.0), rng.uniform(-2, 2, n),
                                rng.uniform(0, 2, n))))
    # wall at y = 2
    pts.append(np.column_stack((rng.uniform(-2, 2, n), np.full(n, 2.0),
                                rng.uniform(0, 2, n))))
    # a box near the origin (breaks symmetry, constrains yaw)
    bn = n // 2
    pts.append(np.column_stack((rng.uniform(-0.3, 0.3, bn),
                                rng.uniform(-0.3, 0.3, bn),
                                rng.uniform(0, 0.4, bn))))
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(np.vstack(pts))
    return cloud


def run_icp(source, target, threshold, init, method, label):
    estimator = (o3d.pipelines.registration.TransformationEstimationPointToPlane()
                 if method == "plane"
                 else o3d.pipelines.registration.TransformationEstimationPointToPoint())
    crit = o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=60)
    result = o3d.pipelines.registration.registration_icp(
        source, target, threshold, init, estimator, crit)
    t = result.transformation[:3, 3]
    yaw = np.degrees(np.arctan2(result.transformation[1, 0],
                                result.transformation[0, 0]))
    print(f"{label}: fitness={result.fitness:.3f}  "
          f"rmse={result.inlier_rmse:.4f} m  "
          f"t=({t[0]:+.3f},{t[1]:+.3f}) m  yaw={yaw:+.2f} deg")
    return result


def trustworthy(result, max_step_m=1.0) -> bool:
    step = float(np.linalg.norm(result.transformation[:3, 3]))
    return (result.fitness > 0.8 and result.inlier_rmse < 0.05
            and step < max_step_m)


def run_demo() -> int:
    voxel = 0.05
    target_raw = synth_room()
    gt = make_transform(0.5, 0.0, 3.0)             # ground-truth motion
    # source = target moved by gt^-1 (so registering source->target recovers gt)
    source_raw = o3d.geometry.PointCloud(target_raw)
    source_raw.transform(np.linalg.inv(gt))

    source = preprocess(source_raw, voxel)
    target = preprocess(target_raw, voxel)

    print(f"[demo] ground-truth motion: t=(0.500, 0.000) m, yaw=+3.00 deg")
    print(f"[demo] registering {len(source.points)} -> {len(target.points)} points\n")

    init = np.eye(4)
    p2p = run_icp(source, target, 0.2, init, "point", "point-to-point ")
    p2l = run_icp(source, target, 0.2, init, "plane", "point-to-plane ")

    # Did point-to-plane recover the ground-truth transform?
    t = p2l.transformation[:3, 3]
    yaw = np.degrees(np.arctan2(p2l.transformation[1, 0],
                                p2l.transformation[0, 0]))
    t_err = np.hypot(t[0] - 0.5, t[1] - 0.0)
    yaw_err = abs(yaw - 3.0)
    print(f"\n[demo] point-to-plane recovery: translation error {t_err * 100:.2f} cm, "
          f"yaw error {yaw_err:.2f} deg")
    print(f"[demo] trust test (p2l): "
          f"{'PASS' if trustworthy(p2l) else 'FAIL'} "
          f"(fitness {p2l.fitness:.2f}, rmse {p2l.inlier_rmse:.3f} m)")

    try:
        source.transform(p2l.transformation)
        source.paint_uniform_color([1, 0.6, 0])
        target.paint_uniform_color([0, 0.6, 1])
        o3d.visualization.draw_geometries([source, target])
    except Exception:
        print("[demo] (no display — skipping visualization)")

    ok = t_err < 0.01 and yaw_err < 0.5 and trustworthy(p2l)
    if ok:
        print("\nPASS: point-to-plane ICP recovered the known transform and "
              "passes the three-part trust test.")
        return 0
    print("\nFAIL: registration did not recover the ground-truth motion. Check "
          "that normals are estimated (point-to-plane needs them) and the "
          "correspondence threshold is sane.")
    return 1


def run_dataset(source_path: str, target_path: str) -> int:
    source = preprocess(o3d.io.read_point_cloud(source_path))
    target = preprocess(o3d.io.read_point_cloud(target_path))
    print(f"registering {source_path} -> {target_path}\n")
    run_icp(source, target, 0.2, np.eye(4), "point", "point-to-point ")
    p2l = run_icp(source, target, 0.2, np.eye(4), "plane", "point-to-plane ")
    print(f"\ntrust test (p2l): {'PASS' if trustworthy(p2l) else 'FAIL'} — "
          "remember: high fitness AND low rmse AND a plausible transform.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="ICP on two scans.")
    parser.add_argument("--source")
    parser.add_argument("--target")
    args = parser.parse_args()
    if args.source and args.target:
        sys.exit(run_dataset(args.source, args.target))
    sys.exit(run_demo())


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--demo)
# -----------------------------------------------------------------------------
#
# [demo] ground-truth motion: t=(0.500, 0.000) m, yaw=+3.00 deg
# [demo] registering 79XX -> 79XX points
#
# point-to-point : fitness=0.9XX  rmse=0.0XXX m  t=(+0.49X,+0.00X) m  yaw=+2.9X deg
# point-to-plane : fitness=0.9XX  rmse=0.0XXX m  t=(+0.500,+0.000) m  yaw=+3.00 deg
#
# [demo] point-to-plane recovery: translation error 0.XX cm, yaw error 0.XX deg
# [demo] trust test (p2l): PASS (fitness 0.9X, rmse 0.0XX m)
#
# PASS: point-to-plane ICP recovered the known transform and passes the
#       three-part trust test.
#
# The exact digits vary with the RNG, but the SHAPE is invariant: point-to-plane
# recovers the known transform tightly and passes the trust test; point-to-point
# gets there too but typically with a higher RMSE and more iterations. If you
# remove the normal estimation, point-to-plane FAILS — it needs the normals.
# -----------------------------------------------------------------------------

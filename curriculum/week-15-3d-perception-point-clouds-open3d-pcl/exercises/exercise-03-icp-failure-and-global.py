#!/usr/bin/env python3
# Exercise 3 — ICP failure and global registration (the rescue)
#
# Goal: BREAK ICP on purpose with a bad initial guess (watch it converge to the
#       WRONG local minimum with plausible-looking fitness), then RESCUE the
#       alignment with FPFH + RANSAC global registration to seed ICP. You will
#       feel the wrong-local-minimum trap that makes ICP dangerous, and the fix.
#
# Estimated time: 45 minutes. Runnable.
#
# THE TRAP (Lecture 2, Part 2)
#
#   ICP descends to the NEAREST minimum of its cost. From a bad initial guess,
#   the nearest minimum is the WRONG one — and ICP converges to it confidently.
#   Global registration (FPFH features + RANSAC) finds a coarse alignment with
#   NO initial guess, getting ICP into the right basin so its refinement lands
#   on the true transform.
#
# HOW TO USE THIS FILE
#
#   Standalone. pip install open3d numpy, then run.
#
#   It synthesizes two clouds related by a LARGE rotation (60 deg), then:
#     1) runs ICP from the identity (bad guess) -> WRONG local minimum,
#     2) runs FPFH+RANSAC global registration  -> coarse but RIGHT basin,
#     3) refines with ICP from the coarse guess -> the TRUE transform.
#   It prints all three results so you can compare and prints PASS when the
#   global+ICP path recovers the true 60 deg rotation but bare ICP does not.
#
#       pip install open3d numpy
#       python3 exercise-03-icp-failure-and-global.py
#
# ACCEPTANCE CRITERIA
#
#   [ ] Bare ICP from identity FAILS to recover the 60 deg rotation (yaw error
#       large, or low fitness) — the wrong-local-minimum trap, reproduced.
#   [ ] Global registration (FPFH+RANSAC) gets ICP into the right basin and the
#       refined result recovers the rotation (yaw error < 2 deg).
#   [ ] You can state in one sentence why a bad initial guess defeats ICP and how
#       global registration fixes it.
#
# Expected output is at the bottom of the file.

import sys

import numpy as np
import open3d as o3d


def make_yaw(deg: float) -> np.ndarray:
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    T = np.eye(4)
    T[:3, :3] = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return T


def synth_asymmetric(n=5000, seed=15) -> o3d.geometry.PointCloud:
    """An ASYMMETRIC cloud (an L-shape + a distinct bump) so the 60 deg rotation
    is unambiguous to feature matching but a trap for naive ICP."""
    rng = np.random.default_rng(seed)
    pts = [
        np.column_stack((rng.uniform(0, 2, n), rng.uniform(0, 0.3, n),
                         rng.uniform(0, 1, n))),                 # long arm (x)
        np.column_stack((rng.uniform(0, 0.3, n), rng.uniform(0, 1.2, n),
                         rng.uniform(0, 1, n))),                 # short arm (y)
        np.column_stack((rng.uniform(1.6, 2.0, n // 3),          # a distinctive
                         rng.uniform(0, 0.3, n // 3),            # bump at the
                         rng.uniform(1.0, 1.6, n // 3))),        # arm's end
    ]
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(np.vstack(pts))
    return cloud


def preprocess(pcd, voxel=0.05):
    down = pcd.voxel_down_sample(voxel)
    down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=2 * voxel, max_nn=30))
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        down, o3d.geometry.KDTreeSearchParamHybrid(radius=5 * voxel, max_nn=100))
    return down, fpfh


def yaw_of(T) -> float:
    return np.degrees(np.arctan2(T[1, 0], T[0, 0]))


def main() -> int:
    voxel = 0.05
    target_raw = synth_asymmetric()
    gt = make_yaw(60.0)                      # the TRUE motion: a 60 deg rotation
    source_raw = o3d.geometry.PointCloud(target_raw)
    source_raw.transform(np.linalg.inv(gt))

    source, source_fpfh = preprocess(source_raw, voxel)
    target, target_fpfh = preprocess(target_raw, voxel)

    print("[ex3] ground-truth motion: yaw = +60.00 deg\n")

    # --- 1) Bare ICP from the identity: the trap. ---
    bare = o3d.pipelines.registration.registration_icp(
        source, target, 0.2, np.eye(4),
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    print(f"1) bare ICP (init=identity): fitness={bare.fitness:.3f} "
          f"rmse={bare.inlier_rmse:.4f} yaw={yaw_of(bare.transformation):+.2f} deg")
    bare_err = abs(yaw_of(bare.transformation) - 60.0)
    print(f"   -> yaw error {bare_err:.1f} deg  "
          f"{'(WRONG LOCAL MINIMUM — trapped)' if bare_err > 5 else ''}\n")

    # --- 2) Global registration: FPFH + RANSAC, no initial guess. ---
    coarse = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source, target, source_fpfh, target_fpfh, mutual_filter=True,
        max_correspondence_distance=1.5 * voxel,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        ransac_n=3,
        checkers=[
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(1.5 * voxel),
        ],
        criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(100000, 0.999))
    print(f"2) FPFH+RANSAC global: fitness={coarse.fitness:.3f} "
          f"yaw={yaw_of(coarse.transformation):+.2f} deg  (coarse, but right basin)\n")

    # --- 3) Refine ICP from the coarse global transform: the rescue. ---
    fine = o3d.pipelines.registration.registration_icp(
        source, target, 0.1, coarse.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    fine_err = abs(yaw_of(fine.transformation) - 60.0)
    print(f"3) ICP refine (init=global): fitness={fine.fitness:.3f} "
          f"rmse={fine.inlier_rmse:.4f} yaw={yaw_of(fine.transformation):+.2f} deg")
    print(f"   -> yaw error {fine_err:.2f} deg\n")

    ok = bare_err > 5.0 and fine_err < 2.0
    if ok:
        print("PASS: bare ICP from identity fell into the WRONG local minimum; "
              "FPFH+RANSAC global registration seeded ICP into the RIGHT basin, "
              "and the refinement recovered the true 60 deg rotation.")
        return 0
    print("FAIL: expected bare ICP to be trapped (>5 deg error) and the global+ICP "
          "path to recover the rotation (<2 deg). On some seeds the asymmetry "
          "lets bare ICP escape — increase the rotation or the asymmetry.")
    return 1


if __name__ == "__main__":
    sys.exit(main())


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# [ex3] ground-truth motion: yaw = +60.00 deg
#
# 1) bare ICP (init=identity): fitness=0.4XX rmse=0.0XXX yaw=+1X.XX deg
#    -> yaw error 4X.X deg  (WRONG LOCAL MINIMUM — trapped)
#
# 2) FPFH+RANSAC global: fitness=0.8XX yaw=+59.X deg  (coarse, but right basin)
#
# 3) ICP refine (init=global): fitness=0.9XX rmse=0.0XXX yaw=+60.0X deg
#    -> yaw error 0.XX deg
#
# PASS: bare ICP from identity fell into the WRONG local minimum; FPFH+RANSAC
#       global registration seeded ICP into the RIGHT basin, and the refinement
#       recovered the true 60 deg rotation.
#
# The lesson, made loud: ICP is a LOCAL method. From a bad initial guess it
# converges confidently to the wrong answer. Global registration finds the right
# basin; ICP refines within it. This is why odometry feeds ICP a constant-
# velocity guess and why relocalization uses global registration first.
# -----------------------------------------------------------------------------

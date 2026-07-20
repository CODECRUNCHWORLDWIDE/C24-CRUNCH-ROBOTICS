# Challenge 1 — Quantify Drift Over a 100-Scan Sequence

**Time estimate:** ~90 minutes.

## Problem statement

You are building the LiDAR-odometry front-end for a robot, and your lead asks the question every robotics lead eventually asks: **"What's our drift?"** You cannot answer that with a vibe. You run your scan-to-scan ICP over a real sequence, chain the transforms into a trajectory, compare the final pose to the dataset's ground truth, and report a number — *and* you explain where the error comes from, because "0.9% drift" without a root-cause story is half an answer.

You will take 100 consecutive scans from a public dataset (Newer College or KITTI), run pairwise point-to-plane ICP odometry, accumulate the trajectory, compute the drift against ground truth, and then locate and explain the sections where drift spikes — using the ICP failure modes from Lecture 2. This mirrors the real skill: drift is the headline number of any odometry system, and a senior engineer can both measure it and tell you which stretch of the route produced it.

## The harness

Save this as `drift_odometry.py`. It loads a sequence, runs chained point-to-plane ICP with a constant-velocity initial guess, and reports per-step and accumulated drift. Fill in the dataset-loading for your chosen dataset (the structure is the same; only `load_sequence` changes).

```python
#!/usr/bin/env python3
"""Scan-to-scan ICP odometry over a sequence, with drift accounting.
Fill in load_sequence() for your dataset (Newer College or KITTI)."""
import sys

import numpy as np
import open3d as o3d


def load_sequence(path: str, n: int = 100):
    """Return (clouds, gt_poses): n consecutive clouds and their ground-truth
    4x4 world poses. Implement for your dataset:
      - KITTI: read .bin velodyne scans + the poses.txt (12-number rows -> 4x4).
      - Newer College: read the .pcd/.ply scans + the ground-truth trajectory.
    """
    raise NotImplementedError("implement load_sequence for your dataset")


def preprocess(pcd, voxel=0.2):           # 0.2 m is sane for outdoor LiDAR
    down = pcd.voxel_down_sample(voxel)
    down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=2 * voxel, max_nn=30))
    return down


def run(path: str):
    clouds, gt = load_sequence(path, n=100)
    prev = preprocess(clouds[0])
    pose = gt[0].copy()                    # start at the true initial pose
    est_traj = [pose.copy()]
    guess = np.eye(4)
    per_step = []

    for i in range(1, len(clouds)):
        cur = preprocess(clouds[i])
        result = o3d.pipelines.registration.registration_icp(
            cur, prev, 1.0, guess,
            o3d.pipelines.registration.TransformationEstimationPointToPlane())
        T = result.transformation          # motion prev -> cur
        pose = pose @ T
        est_traj.append(pose.copy())
        guess = T                          # constant-velocity guess
        prev = cur
        # per-step error vs ground-truth incremental motion
        gt_step = np.linalg.inv(gt[i - 1]) @ gt[i]
        step_err = np.linalg.norm((np.linalg.inv(gt_step) @ T)[:3, 3])
        per_step.append((i, result.fitness, result.inlier_rmse, step_err))

    # --- accumulated drift ---
    est_final = est_traj[-1][:3, 3]
    gt_final = gt[-1][:3, 3]
    final_err = float(np.linalg.norm(est_final - gt_final))
    path_len = sum(np.linalg.norm(gt[i][:3, 3] - gt[i - 1][:3, 3])
                   for i in range(1, len(gt)))
    print(f"path length: {path_len:.1f} m")
    print(f"final position error: {final_err:.2f} m")
    print(f"drift: {100 * final_err / path_len:.2f}% of path length")

    # --- locate the worst steps ---
    per_step.sort(key=lambda r: r[3], reverse=True)
    print("\nworst 5 steps (where drift was injected):")
    for i, fit, rmse, err in per_step[:5]:
        print(f"  step {i:3d}: fitness={fit:.2f} rmse={rmse:.3f} "
              f"step_err={err * 100:.1f} cm")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "./sequence")
```

```bash
pip install open3d numpy
python3 drift_odometry.py /path/to/dataset/sequence
```

## Your task

1. **Implement `load_sequence`** for your chosen dataset (KITTI or Newer College). Load 100 consecutive scans and their ground-truth poses.
2. **Run the odometry** and report the headline numbers: path length, final position error, and drift as a percentage of path length.
3. **Locate the drift.** Identify the 5 steps that injected the most error (the harness sorts them for you). For each, look at the scan: what was the robot seeing? Match each high-error step to an ICP failure mode from Lecture 2.
4. **Plot it.** Produce a plot of the estimated trajectory vs. the ground-truth trajectory (top-down `x` vs `y`), and a plot of per-step error vs. step index, so the spikes are visible.
5. **Write the root-cause story.** A paragraph explaining where the drift came from and why — degenerate geometry (a long corridor / open road with no along-track features), insufficient overlap (a fast turn), or a bad correspondence (dynamic objects, a person walking through).

## Acceptance criteria

- [ ] `load_sequence` is implemented and loads 100 scans + ground-truth poses for your dataset.
- [ ] A `challenge-01-drift.md` reports: path length, final position error, and drift percentage.
- [ ] Two plots (committed as images): estimated-vs-ground-truth trajectory (top-down), and per-step error vs. step.
- [ ] The 5 worst steps are listed, each mapped to a Lecture-2 ICP failure mode with a one-line justification *from the scan content* (not just "ICP was bad").
- [ ] A root-cause paragraph that ties the drift to geometry: you can point at the trajectory plot and say "the drift accelerated *here*, in the corridor, because along-track motion was unconstrained."
- [ ] You confirm, with fitness numbers, that the high-drift steps had a *tell* — low fitness, high RMSE, or a fitness that looked fine but an implausible step (the wrong-local-minimum case).
- [ ] Committed to your Week 15 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The dangerous steps are not always the ones with *low* fitness. The wrong-local-minimum failure (Lecture 2 §2.1) produces a step with *decent* fitness but a wrong transform — ICP found consistent (wrong) correspondences in a repetitive scene. So "filter by low fitness" misses some of the worst drift contributors. You must cross-check fitness *and* the step's plausibility against the ground-truth incremental motion (which the harness does via `step_err`). A step with fitness 0.85 but a 40 cm error vs. the true motion is the silent failure, and it's the one that teaches the lesson: **fitness alone is not a trust signal — you need the plausibility check too.** Diagnosing the spikes purely by fitness, and missing the high-fitness-wrong-transform steps, is the mistake to avoid.

## Stretch

- **Add the constant-velocity guess vs. identity comparison.** Run the sequence once with `guess = T` (constant velocity) and once with `guess = np.eye(4)` (identity every step) and show the constant-velocity guess dramatically reduces drift — because it keeps ICP in the right basin. This is the single most important odometry trick.
- **Insert a synthetic loop closure.** If your sequence revisits a place, register the revisit scan against the earlier one with global registration, and show by hand how that one constraint would pull the drifted trajectory back — the Lecture-2 §3.3 fix, demonstrated on your own data.
- **Down/up-sample sweep.** Run the whole sequence at voxel sizes 0.1, 0.2, 0.4 m and plot drift vs. voxel size. There's a sweet spot — too coarse loses geometry, too fine is slow and over-fits noise.

## Why this matters

At the Week 16 midterm you defend your perception stack, and "how does your perception bound drift?" is a near-certain question. The honest, senior answer is a *number* you measured, a *location* you can point to on a trajectory plot, and an *understanding* of why pairwise odometry drifts and what (IMU fusion, loop closure, a pose-graph back-end) bounds it. This challenge gives you all three. Eight weeks of perception culminate in a fused state estimate that must drift < 0.5 m over 20 m for the capstone — and the first time you confront drift as a measured quantity is right here, on someone else's 100 scans, where the stakes are a grade and not a robot driving into a wall.

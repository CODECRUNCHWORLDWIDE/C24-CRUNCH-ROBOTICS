# Week 15 Homework

Six problems that drive the 3D-perception literacy into your fingers. The full set should take about **5 hours**. Work in your Week 15 Git repository (the same workspace as the exercises and the `crunchbot_perception3d` mini-project) so every problem produces at least one commit you can point to at the Week 16 midterm.

The headline deliverable is **Problem 4 — the ICP-drift quantification write-up**, the artifact that lets you answer "what's your drift, and why?" at the midterm. Treat it as a one-pager a reviewer reads.

Each problem includes a short **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

`pip install open3d numpy` and source ROS2 Jazzy where the problem is a ROS node. Have a dataset sequence (Newer College or KITTI) or your Week 14 cloud available.

---

## Problem 1 — The pipeline-stage point-count table

**Problem statement.** Take one cloud (dataset scan or your Week 14 frame) and run it through the full Lecture-1 pipeline. Record the point count *after each stage* — raw, downsampled, outlier-removed, ground (inliers), obstacles (outliers), and the per-cluster sizes. Build a table in `notes/week-15/pipeline-stages.md`.

**Acceptance criteria.**

- `notes/week-15/pipeline-stages.md` has the point count after every stage, with the voxel size and `eps` you used.
- You note the ground normal `(a, b, c)` and confirm it's near-vertical (or you fixed it).
- You report the cluster count and confirm (by visualization) it matches the number of distinct objects.
- Committed.

**Hint.** `len(pcd.points)` after each Open3D operation. If downsampling barely reduces the count, the voxel is too small for the density.

**Estimated time.** 35 minutes.

---

## Problem 2 — Tune the ground-segmentation normal constraint

**Problem statement.** Find (or construct) a scene where plain RANSAC `segment_plane` picks a *wall* instead of the floor (a scene with a large wall). Show the wrong pick (normal near-horizontal). Then add a normal constraint — loop the segmentation, rejecting planes with `|normal_z| < 0.9` — and show it now reliably picks the floor. Document both.

**Acceptance criteria.**

- `notes/week-15/ground-constraint.md` shows the un-constrained result (wall picked, normal near-horizontal) and the constrained result (floor picked, normal ≈ `(0,0,1)`).
- The constrained code is committed.
- You state in one sentence why a big wall can out-vote the floor in plain RANSAC (more inliers).
- Committed.

**Hint.** To force a wall-pick, use a scene with a wall larger than the visible floor, or crop so the floor is small. The fix is `while abs(plane_model[2]) < 0.9: re-segment on the remaining points`.

**Estimated time.** 40 minutes.

---

## Problem 3 — Point-to-point vs point-to-plane convergence

**Problem statement.** On a pair of overlapping clouds (Exercise-2 synthetic or a dataset pair), run point-to-point and point-to-plane ICP from the same initial guess. Record, for each: iterations to converge, final fitness, final inlier-RMSE, and the recovered transform. Confirm point-to-plane converges faster and/or tighter. Document the comparison.

**Acceptance criteria.**

- `notes/week-15/icp-comparison.md` has a table: method | iterations | fitness | RMSE | transform.
- You confirm point-to-plane's advantage and state why (it minimizes point-to-surface distance, letting the source slide along the surface).
- You confirm point-to-plane *fails* if you skip normal estimation, and explain why.
- Committed.

**Hint.** To count iterations, lower `max_iteration` until the result degrades, or read Open3D's verbose output (`o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Debug)`).

**Estimated time.** 45 minutes.

---

## Problem 4 — The ICP-drift quantification write-up (headline deliverable)

**Problem statement.** This is the artifact you defend at the midterm. Run scan-to-scan ICP odometry over a sequence (your Challenge-1 harness, or a fresh 30–100 scan run), measure the drift against ground truth, and write a one-page quantification at `notes/week-15/icp-drift.md`:

1. **Setup** — dataset, sequence length, path length, voxel size, ICP type, initial-guess strategy.
2. **The number** — final position error, drift as % of path length, and the per-step error distribution.
3. **Where it drifts** — the worst 3–5 steps, each mapped to an ICP failure mode (degenerate geometry, low overlap, wrong local minimum) *from the scan content*.
4. **The constant-velocity-guess effect** — run once with a constant-velocity guess and once with identity-every-step, and report how much the guess reduced drift. *This is the headline comparison.*
5. **What would bound it** — one paragraph: loop closure + pose-graph + IMU fusion, and which of your worst steps each would fix.

**Acceptance criteria.**

- `notes/week-15/icp-drift.md` exists, ~one page, hits all five headings.
- A real drift number tied to a real path length (not "it seemed fine").
- A trajectory plot (estimated vs. ground truth) and a per-step error plot.
- The constant-velocity-vs-identity comparison shows a concrete drift reduction.
- At least three worst-step diagnoses tied to scan content and a Lecture-2 failure mode.
- Committed.

**Hint.** The constant-velocity guess is the single biggest drift reducer in scan-to-scan odometry — feeding the previous motion as the initial guess keeps ICP in the right basin. If you can't get ground truth, compare against wheel odometry or sim ground truth and say so.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Break ICP and rescue it with global registration

**Problem statement.** Take two clouds related by a large rotation (≥ 45°). Show that ICP from the identity converges to the *wrong* local minimum (with plausible-looking fitness). Then rescue it with FPFH + RANSAC global registration seeding ICP, and recover the true transform. Document the trap and the fix.

**Acceptance criteria.**

- `notes/week-15/global-rescue.md` shows: the bare-ICP wrong result (transform error + fitness), the global-registration coarse result, and the refined-ICP correct result.
- You state in one sentence why fitness alone didn't catch the bare-ICP failure (it found consistent but wrong correspondences) and what did (the implausible transform).
- Committed.

**Hint.** Your Exercise-3 harness does exactly this — you can extend it or run it on a dataset pair. The asymmetry of the cloud matters: a symmetric cloud (a sphere) makes global registration ambiguous too.

**Estimated time.** 45 minutes.

---

## Problem 6 — Health-gate your odometry node

**Problem statement.** Take your mini-project `odom_node` (or a minimal version). Make it publish the per-scan ICP fitness/RMSE and inflate the odometry covariance when fitness drops below a threshold. Prove the gate is live: feed it a degenerate or low-overlap section and show the covariance grow and the health topic report low fitness.

**Acceptance criteria.**

- `notes/week-15/health-gate.md` shows the health topic output (fitness/RMSE) for a good section and a bad section.
- You demonstrate the covariance inflating on the bad section (echo the `Odometry` covariance, or log it).
- You state in one sentence why publishing registration confidence matters for the Week 16 EKF (so it de-weights a bad scan instead of corrupting on it).
- Committed.

**Hint.** A simple gate: `cov_scale = 1.0 if fitness > min_fitness else 100.0`, applied to the diagonal of the odometry covariance. The EKF in Week 16 reads that covariance and trusts the measurement less.

**Estimated time.** 30 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Pipeline-stage point counts | 35 min |
| 2 — Ground-segmentation normal constraint | 40 min |
| 3 — Point-to-point vs point-to-plane | 45 min |
| 4 — ICP-drift quantification (headline) | 1 h 15 min |
| 5 — Break ICP and rescue with global reg | 45 min |
| 6 — Health-gate the odometry node | 30 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_perception3d` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 16's fused perception node consumes its clusters and odometry. Then take the [quiz](./05-quiz.md) with your notes closed.

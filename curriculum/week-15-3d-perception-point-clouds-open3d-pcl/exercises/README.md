# Week 15 — Exercises

Three focused drills that take you from a raw cloud to clustered object proposals and a registered trajectory. Each takes 30–60 minutes. Do them in order — exercise 2 registers the clouds exercise 1 taught you to pre-process, and exercise 3 breaks the ICP from exercise 2 to teach you its failure mode. Run them against a **public dataset** (Newer College or KITTI), your **Week 14 RGB-D cloud** (real or sim), or the **synthetic clouds** each runnable exercise ships.

## Index

1. **[Exercise 1 — Downsample, filter, segment, cluster](exercise-01-downsample-filter-segment.md)** — take a cloud, voxel-downsample it, statistical-outlier-filter it, RANSAC-segment the ground, and Euclidean-cluster the rest into object proposals. Verify each stage's point count and the ground normal. (~50 min, guided)
2. **[Exercise 2 — ICP on two scans](exercise-02-icp-two-scans.py)** — register two overlapping clouds with point-to-point and point-to-plane ICP, compare iterations/fitness/RMSE, and apply the three-part trust test. (~50 min, runnable)
3. **[Exercise 3 — ICP failure and global registration](exercise-03-icp-failure-and-global.py)** — break ICP with a bad initial guess (watch it converge to the wrong local minimum with plausible-looking fitness), then rescue it with FPFH + RANSAC global registration. (~45 min, runnable)

## How to work the exercises

- **You debug 3D perception by looking.** Use `o3d.visualization.draw_geometries([...])` constantly — color the ground green, the clusters by label, the source/target clouds differently. A bug you can't find in numbers is obvious in the viewer.
- **Run `evaluate_registration` on every ICP result.** Fitness and inlier-RMSE are your ground truth. ICP returning without an error means nothing — the three-part trust test (high fitness, low RMSE, plausible transform) is the actual check (Lecture 2 §1.2).
- **Downsample before you register.** It's not just speed — uniform density is a correctness aid for ICP (Lecture 1 §2). "ICP is slow and wrong on the raw cloud" usually fixes itself with a voxel filter.
- **Mind the frame and the header.** When you convert `PointCloud2` ↔ Open3D, hold the header aside and reattach it — Open3D drops the stamp and frame (Lecture 1 §1.1).
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match, you're not done.

## Running the Python exercises

The two `.py` files are standalone — `pip install open3d numpy` (Open3D ships its own data, so no ROS2 is strictly required for these two, though the mini-project is a ROS2 node). Run them directly:

```bash
pip install open3d numpy        # if not already installed
python3 exercise-02-icp-two-scans.py
```

Both ship a **`--demo` mode** that synthesizes two overlapping clouds with a *known* ground-truth transform, so you can verify the registration recovers the right motion with no dataset download — then point the same script at a dataset pair to run it for real. Instructions are in each file's header.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-15` to compare.

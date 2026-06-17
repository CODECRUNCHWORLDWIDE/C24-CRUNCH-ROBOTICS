# Week 15 — 3D Perception: Point Clouds, Open3D, and PCL

Welcome to the week your robot stops seeing a *picture* of the world and starts seeing the *geometry* of it. Last week you produced a metric, confidence-gated point cloud. This week you do something *with* it: downsample it so it's tractable, strip the ground plane so the obstacles stand out, cluster the rest into object proposals, and — the centerpiece — *register* two clouds with ICP so the robot can tell how it moved by aligning what it saw. By Friday you will take two consecutive LiDAR scans from a public dataset, voxel-downsample, remove the ground, cluster, register them with point-to-plane ICP in Open3D, quantify the registration error, and then run the same pipeline over a 100-scan sequence and report the drift.

We assume you finished Week 14 — you have a `crunchbot_rgbd` bring-up that publishes a trustworthy `/crunchbot/points`, you know the `16UC1`/`32FC1` encodings cold, and you understand that a depth camera invents some of its points. This week's pipeline runs on *exactly* that cloud (and on LiDAR clouds and dataset clouds — a point cloud is a point cloud). If "what's a flying pixel" or "what does confidence-gating do" is fuzzy, re-read Week 14 first — a clustering pipeline fed un-gated garbage produces garbage clusters.

The two sentences to internalize before you read another line:

> **A point cloud is a list. A *registered* point cloud is a relationship.** A single cloud is `N` unordered points — it tells you the shape of the world *right now*, from *here*. The moment you align a second cloud to the first, you've recovered the *transform between the two viewpoints* — which is to say, how the robot moved, or where a second sensor sits relative to the first. Almost everything interesting in 3D perception is registration: scan-to-scan for odometry, scan-to-map for localization, cloud-to-cloud for multi-sensor fusion. And the workhorse algorithm of registration — **ICP** — is everywhere, brilliant when it converges, and silently, confidently wrong when it doesn't.

This is the week ICP becomes a tool you understand from the inside: why point-to-plane beats point-to-point, why a bad initial guess sends it into a wrong local minimum, and why a 100-scan sequence accumulates drift no matter how good each pairwise alignment is. That drift number is the thing you'll quantify, defend at the Week 16 midterm, and — eight weeks of perception later — the thing your fused state estimate has to keep under 0.5 m for the capstone.

## Learning objectives

By the end of this week, you will be able to:

- **Choose** the right point-cloud data structure for a task — a flat `Nx3` array, an Open3D `PointCloud`, a PCL cloud, or a `sensor_msgs/PointCloud2` — and convert between them without losing the stamp, the frame, or the precision.
- **Downsample** a cloud with a voxel grid and explain the resolution-vs-speed trade-off, and why downsampling *before* ICP is not just an optimization but often a correctness requirement.
- **Filter** a cloud: passthrough (crop to a region of interest), statistical outlier removal (drop the flying pixels and stragglers), and radius outlier removal — and state what each one removes and what it costs.
- **Segment the ground plane** with RANSAC, recover the plane model `ax + by + cz + d = 0`, and separate ground from obstacles — the single most useful pre-processing step in mobile-robot 3D perception.
- **Cluster** the non-ground points into object proposals with Euclidean (DBSCAN-style) clustering, tune the cluster tolerance and min-size, and turn clusters into oriented bounding boxes.
- **Register** two clouds with ICP — both point-to-point and point-to-plane — explain why point-to-plane converges faster and tolerates more, and quantify the alignment with fitness and inlier-RMSE.
- **Diagnose** ICP failure: a bad initial guess, insufficient overlap, a degenerate geometry (a flat corridor, a featureless plane), and the silent wrong-local-minimum convergence — and know when to reach for a global registration (RANSAC + FPFH features) to seed it.
- **Quantify drift** over a multi-scan sequence by chaining pairwise registrations, and explain why pairwise ICP accumulates error and what loop closure (Week 7's lesson, in 3D) does about it.

## Prerequisites

This week assumes you have completed **C24 weeks 1–14**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**. You can write an `rclpy` node and read a `sensor_msgs/PointCloud2`.
- **Week 14 RGB-D.** You have a metric point cloud (`/crunchbot/points`) and you understand confidence-gating, invalid pixels, and flying pixels. This week's filters *remove* the artifacts Week 14 taught you to recognize.
- **Week 1–2 SE(3) and tf2.** ICP outputs a `4×4` homogeneous transform; you must be fluent reading one, composing two, and inverting one. A registration result *is* an SE(3) transform — if homogeneous transforms are fuzzy, re-read Week 1.
- **Week 12 RANSAC.** You used RANSAC for outlier rejection in 2D. Ground-plane segmentation is RANSAC fitting a *plane* instead of a line — same algorithm, one more dimension. If RANSAC's "sample, fit, count inliers, repeat" loop isn't second nature, re-read Week 12.
- **NumPy fluency.** Point-cloud math is vectorized NumPy and Open3D tensors. A Python loop over a million points runs at a crawl.

You do **not** need a LiDAR or a depth camera for the dataset half. The ICP and drift labs run on **public datasets** — the Newer College Dataset (handheld LiDAR, indoor/outdoor) and KITTI (automotive LiDAR) — which we point you to and which everyone in robotics benchmarks against. The RGB-D half runs on your Week 14 cloud (real or sim).

## Topics covered

- **Point-cloud data structures.** The `sensor_msgs/PointCloud2` wire format (fields, `point_step`, organized vs. unorganized), Open3D's `PointCloud` (legacy and the tensor API), PCL's `PointCloud<PointT>`, and converting among them with `sensor_msgs_py.point_cloud2` and `open3d` without dropping the header.
- **Voxel downsampling.** The voxel-grid filter (one representative point per occupied voxel), choosing the voxel size, and why downsampling before ICP both speeds it up *and* regularizes the correspondences.
- **Filtering.** Passthrough / crop-box (region of interest), statistical outlier removal (drop points whose mean neighbour-distance is an outlier — kills flying pixels and stragglers), radius outlier removal, and normal estimation (needed for point-to-plane ICP and for plane segmentation).
- **Ground segmentation.** RANSAC plane fitting: the plane model, the distance threshold, the inlier count, and separating ground inliers from the obstacle outliers. Why the ground plane is the highest-value segmentation in mobile robotics, and where RANSAC plane fitting fails (ramps, multiple planes, clutter).
- **Euclidean clustering.** DBSCAN-style clustering on the non-ground points, the cluster tolerance (the `eps`) and min-points, turning clusters into axis-aligned and oriented bounding boxes, and the failure modes (under-segmentation when objects touch, over-segmentation on a sparse cloud).
- **ICP registration.** Point-to-point ICP (minimize point distances), point-to-plane ICP (minimize point-to-surface distances using normals), the iteration loop (correspondence → transform → repeat), convergence criteria, and the fitness / inlier-RMSE metrics that tell you whether it *actually* converged.
- **ICP failure and global registration.** The initial-guess sensitivity, the wrong-local-minimum trap, insufficient-overlap and degenerate-geometry failures, and the global-registration escape hatch: FPFH feature extraction + RANSAC-based feature matching to *seed* ICP from far away.
- **Drift over a sequence.** Chaining pairwise registrations into a trajectory, why error accumulates (each pairwise alignment has residual error that compounds), the drift metric (final-pose error over path length), and the bridge to loop closure and pose-graph optimization (Week 7 in 2D; the same idea in 3D, the foundation of FAST-LIO / LIO-SAM).

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Point-cloud structures; voxel downsampling; filtering           |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | RANSAC ground segmentation; Euclidean clustering; bounding boxes|    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | ICP: point-to-point, point-to-plane; fitness and RMSE          |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | ICP failure; global registration; FPFH+RANSAC seeding          |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Drift over a sequence; the 100-scan run; mini-project start     |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                          |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, drift write-up polish                            |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                                | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Open3D / PCL docs, the ICP and FPFH papers, the Newer College and KITTI datasets, and the talks worth your time |
| [lecture-notes/01-point-clouds-filtering-segmentation-clustering.md](./02-lecture-notes/01-point-clouds-filtering-segmentation-clustering.md) | Data structures, voxel downsampling, the filter chain, RANSAC ground segmentation, and Euclidean clustering into object proposals |
| [lecture-notes/02-icp-registration-global-registration-and-drift.md](./02-lecture-notes/02-icp-registration-global-registration-and-drift.md) | Point-to-point vs point-to-plane ICP, fitness/RMSE, ICP failure modes, FPFH+RANSAC global registration, and drift over a sequence |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-downsample-filter-segment.md](./03-exercises/exercise-01-downsample-filter-segment.md) | Voxel-downsample, statistical-outlier-filter, RANSAC ground-segment, and Euclidean-cluster a cloud; verify each stage |
| [exercises/exercise-02-icp-two-scans.py](./03-exercises/exercise-02-icp-two-scans.py) | Register two clouds with point-to-point and point-to-plane ICP; compare convergence, fitness, and RMSE; visualize the alignment |
| [exercises/exercise-03-icp-failure-and-global.py](./03-exercises/exercise-03-icp-failure-and-global.py) | Break ICP with a bad initial guess, then rescue it with FPFH+RANSAC global registration — see the wrong-local-minimum trap and the fix |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-drift-over-a-sequence.md](./04-challenges/challenge-01-drift-over-a-sequence.md) | Chain pairwise ICP over a 100-scan dataset sequence, quantify the accumulated drift, and diagnose where it spikes |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the ICP-drift quantification write-up |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunchbot_perception3d` pipeline: a ROS2 node from raw cloud to ground-removed, clustered object proposals with scan-to-scan odometry |

## The "it actually converged" promise

C24 uses a recurring marker for every exercise that ends in a registration you can trust. ICP *always* returns a transform — the question is whether that transform is *right*. A converged, trustworthy alignment looks like this:

```
$ python3 exercise-02-icp-two-scans.py
point-to-plane ICP: converged in 14 iterations
  fitness:      0.92   (fraction of source points with a correspondence)
  inlier RMSE:  0.021 m
  transform:    translation (0.48, -0.02, 0.01) m, yaw 3.1 deg
  [CONVERGED — high fitness, low RMSE, plausible motion]
```

High fitness (most points found a match), low inlier-RMSE (the matched points are close), and a *plausible* transform (the motion is physically reasonable). If fitness is 0.2, or the RMSE is 0.4 m, or ICP reports a 2-metre jump between consecutive 10 Hz scans, **it did not converge — it found a wrong local minimum and is lying to you with a confident-looking transform.** The point of Week 15 is to make "it actually converged" something you *verify* with fitness and RMSE, never something you assume because ICP returned without an error.

## Stretch goals

If you finish the regular work early and want to push further:

- Implement **point-to-point ICP from scratch** (NumPy only): nearest-neighbour correspondence with a KD-tree, the Procrustes/SVD solution for the optimal rigid transform, iterate. Compare your convergence to Open3D's. Implementing it once is how ICP stops being a black box.
- Add **Generalized-ICP (GICP)** from Open3D's contrib (or PCL) to your Exercise 2 comparison — it models the local surface covariance at *both* clouds and is the registration most modern LiDAR odometry uses. Compare its robustness to point-to-plane.
- Run your drift pipeline on **both** Newer College and KITTI and compare: handheld indoor LiDAR vs automotive LiDAR drift very differently, and seeing why teaches you what geometry ICP needs.
- Read the **FAST-LIO2** paper and identify exactly which parts of your week's pipeline (downsample, point-to-plane residual, the chaining) it uses — and what it adds (IMU pre-integration, an iterated-EKF back-end) to beat pairwise-ICP drift. This is the bridge from your hand-built pipeline to a production LiDAR-inertial odometry.

## Up next

Week 16 is the Phase 2 integration week and the **first midterm**. You compose Weeks 9–15 into one fused perception node — IMU + wheel odometry into an EKF, LiDAR into the 3D clustering you build this week, RGB-D into a YOLO detector — publish a unified `/perception/objects` in `map` frame, and hit a 30 ms end-to-end cycle. Then you defend the whole stack to a panel against a written rubric. Your clustering and your drift number are two of the things they'll point at. Push your mini-project before you start.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

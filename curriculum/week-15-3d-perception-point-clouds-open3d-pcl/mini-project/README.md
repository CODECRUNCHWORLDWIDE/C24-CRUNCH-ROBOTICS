# Mini-Project — `crunchbot_perception3d`: From Raw Cloud to Object Proposals + Odometry

> Build a ROS2 perception node that takes the raw point cloud (your Week 14 `/crunchbot/points`, or a LiDAR scan) and produces two things a planner needs: **labeled object proposals** (ground-removed, clustered, as `vision_msgs/Detection3DArray` with oriented bounding boxes) and **scan-to-scan ICP odometry** (a `nav_msgs/Odometry` with the per-scan fitness/RMSE published as a health signal). One node, the full Lecture-1 pipeline plus Lecture-2 registration, running live on a stream.

This is the artifact that turns "I can process a cloud in a notebook" into "my robot perceives in 3D, in ROS2, in real time." After this week, a point cloud is not a thing you analyze offline — it is a live stream your node turns into objects-and-motion that the rest of the autonomy stack consumes.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This node is **the LiDAR/RGB-D branch of the Week 16 fused perception node.** At the Week 16 midterm you compose this clustering (the 3D-detection input) and this odometry (one of the EKF's motion sources) with the IMU/wheel-odom EKF and the RGB-D YOLO detector into one `/perception/objects` topic inside a 30 ms cycle. The object proposals you publish here are *exactly* the 3D detections that node fuses. Build it well now; it's a graded input to the midterm in one week.

---

## What you will build

A small ament-python package `crunchbot_perception3d` with three deliverables:

1. **`crunchbot_perception3d/cluster_node.py`** — subscribes to a `PointCloud2`, runs the Lecture-1 pipeline (voxel downsample → crop → statistical outlier removal → RANSAC ground segmentation with a near-vertical normal constraint → Euclidean clustering), turns each cluster into an oriented bounding box, and publishes a `vision_msgs/Detection3DArray` plus a `visualization_msgs/MarkerArray` for rviz2.
2. **`crunchbot_perception3d/odom_node.py`** — subscribes to the same `PointCloud2`, runs point-to-plane ICP against the previous scan with a constant-velocity initial guess, accumulates the pose, and publishes `nav_msgs/Odometry` on `/perception/lidar_odom` plus the per-scan `fitness`/`inlier_rmse` on a `/perception/lidar_odom/health` topic (so a consumer can *reject* a bad registration instead of trusting it).
3. **The pipeline core** (`crunchbot_perception3d/pipeline.py`) — the pure functions (downsample, segment, cluster, register) with no ROS dependency, so they're unit-testable without a running graph.

By the end you have a public repo of ~400–500 lines of Python that any future crunchbot package can launch to get object proposals and 3D odometry from a cloud stream.

---

## Why publish the registration health, not just the odometry

The single most important design decision in this node: **`odom_node` publishes the ICP fitness and inlier-RMSE alongside the odometry, and a consumer is expected to gate on them.** Lecture 2 hammered that ICP always returns a transform and only sometimes a correct one. If `odom_node` published only the `Odometry` and silently passed a wrong-local-minimum transform downstream, the EKF in Week 16 would fuse garbage and the whole state estimate would corrupt. By publishing the health signal, the consumer (and you, in rviz2/PlotJuggler) can see when a registration is untrustworthy and drop it — exactly the "it actually converged" discipline from the README, wired into the graph. A perception node that hides its own confidence is a liability; one that publishes it is a teammate.

---

## Package layout

```
crunchbot_perception3d/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunchbot_perception3d
├── crunchbot_perception3d/
│   ├── __init__.py
│   ├── pipeline.py          # pure functions: downsample, segment, cluster, register
│   ├── cluster_node.py      # PointCloud2 -> Detection3DArray + MarkerArray
│   ├── odom_node.py         # PointCloud2 -> Odometry + health
│   └── conversions.py       # PointCloud2 <-> Open3D, header preserved
├── launch/
│   └── perception3d.launch.py
├── rviz/
│   └── perception3d.rviz
└── test/
    ├── test_pipeline.py     # ground normal, cluster count on a synthetic scene
    └── test_registration.py # ICP recovers a known transform; trust test
```

---

## Deliverable 1 — `cluster_node.py`

On every incoming cloud:

1. Convert `PointCloud2` → Open3D (`conversions.py`), holding the header aside.
2. Run the pipeline: voxel downsample → crop to ROI → SOR → RANSAC ground (constrain `|normal_z| > 0.9` so it picks the floor, not a wall) → `cluster_dbscan`.
3. For each cluster above `min_points`, compute the oriented bounding box (center, extent, orientation).
4. Publish a `vision_msgs/Detection3DArray` (each `Detection3D` carries the OBB as its `bbox`, the centroid, and a per-cluster id) **in the cloud's frame, stamped with the cloud's acquisition time.**
5. Publish a `visualization_msgs/MarkerArray` of the boxes for rviz2.

Parameters (declared, documented): `voxel_size`, `roi_bounds`, `sor_neighbors`, `sor_std_ratio`, `ground_distance_threshold`, `ground_normal_min_z`, `cluster_eps`, `cluster_min_points`.

---

## Deliverable 2 — `odom_node.py`

On every incoming cloud:

1. Convert and downsample (reuse `pipeline.py`); estimate normals (point-to-plane needs them).
2. Point-to-plane ICP against the *previous* downsampled cloud, seeded with the *previous motion* (constant-velocity guess).
3. Accumulate the pose: `pose = pose @ T`.
4. Publish `nav_msgs/Odometry` on `/perception/lidar_odom` (pose + the transform's frame discipline: `header.frame_id = odom`, `child_frame_id = base_link` — Week 5 §3.2).
5. Publish the per-scan `fitness` and `inlier_rmse` on `/perception/lidar_odom/health` (a small custom or `diagnostic_msgs` message), and **mark the odometry covariance large when fitness is low** so a downstream EKF de-weights an untrustworthy registration automatically.

Parameters: `voxel_size`, `icp_threshold`, `icp_max_iteration`, `min_fitness` (below which the registration is flagged untrustworthy).

---

## Deliverable 3 — the launch file

`launch/perception3d.launch.py` brings up both nodes and rviz2 with a saved layout showing the input cloud, the cluster boxes, and the odometry trajectory. A `source` argument selects the input cloud topic (`/crunchbot/points` from Week 14, a bag, or a sim LiDAR), so the node runs against any cloud stream.

```bash
ros2 launch crunchbot_perception3d perception3d.launch.py source:=/crunchbot/points
ros2 launch crunchbot_perception3d perception3d.launch.py source:=/scan_cloud   # LiDAR
```

---

## Rules

- **You may** read the ROS2 docs, the lecture notes, Open3D / PCL docs, and the Week 14 `crunchbot_rgbd` code.
- **You must** keep `pipeline.py` ROS-free — pure functions on Open3D clouds, so `test_pipeline.py` runs without a graph. A pipeline tangled into the node is untestable and fails the project's reason to exist.
- **You must** publish the ICP health (fitness/RMSE) and reflect low fitness in the odometry covariance. A node that publishes odometry without its confidence is the liability this project exists to prevent.
- **You must** constrain the ground-plane normal to near-vertical, or RANSAC will pick a wall on some scenes (Lecture 1 §4).
- **You must** preserve the header (stamp + frame) across the `PointCloud2` ↔ Open3D conversion (Lecture 1 §1.1) and stamp outputs with the *acquisition* time.
- Python 3.12 (Ubuntu 24.04 default), `rclpy` + `open3d` + NumPy on Jazzy. The pipeline must keep up with the cloud rate after downsampling; a per-point Python loop will not.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-15-crunchbot-perception3d-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_perception3d` succeeds with no warnings.
- [ ] `ros2 launch crunchbot_perception3d perception3d.launch.py source:=...` brings up both nodes and rviz2 in one command.
- [ ] `cluster_node` publishes a `vision_msgs/Detection3DArray` with one detection per object; the boxes appear in rviz2 around the right objects, in the right frame.
- [ ] The ground is removed (objects don't merge through the floor) and the ground normal is near-vertical, verifiable from the node's logs.
- [ ] `odom_node` publishes `nav_msgs/Odometry` and a health topic; `ros2 topic echo /perception/lidar_odom/health` shows fitness/RMSE per scan.
- [ ] When you feed a degenerate/low-overlap section, the health topic shows low fitness and the odometry covariance grows — the node *knows* when it's untrustworthy.
- [ ] `colcon test` passes, with at least:
  - `test_pipeline.py`: a synthetic floor+box scene yields a near-vertical ground normal and the right cluster count.
  - `test_registration.py`: ICP recovers a known transform and passes the three-part trust test; a bad-init case is flagged.
- [ ] A `README.md` with the launch commands, an rviz2 screenshot of the boxes, and a note on the health-gating design.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Pipeline correctness** | 25 | Voxel/SOR/ground/cluster in the right order; near-vertical ground normal; one cluster per object; OBBs published in the right frame. |
| **Registration + health** | 25 | Point-to-plane ICP with constant-velocity guess; fitness/RMSE published; low fitness reflected in covariance; the node knows when it's untrustworthy. |
| **ROS integration** | 20 | `Detection3DArray` + `MarkerArray` + `Odometry` + health; correct frames and acquisition stamps; sensor QoS on the input. |
| **Testability** | 15 | `pipeline.py` is ROS-free and unit-tested; `colcon test` green; registration trust test covered. |
| **Real-time** | 10 | Keeps up with the cloud rate after downsampling; vectorized, no per-point Python loops. |
| **Launch & docs** | 5 | One-command bring-up with `source`; clear README; rviz layout checked in; health-gating explained. |

**90+** is portfolio-grade and ready to drop into the Week 16 fused perception node. **70–89** works but hides its registration confidence or merges objects through the floor. **Below 70** means the node isn't trustworthy as an EKF input — fix the ground removal and the health-gating first.

---

## What "good" looks like at the demo

When you bring this node up and view it in rviz2, a *correct* result is unmistakable, and knowing what to look for is how you self-grade before submission:

- **The ground is gone, the objects stand apart.** You see the obstacle clusters as distinct colored blobs (or boxes), with no green ground carpet connecting them and no single giant blob spanning the floor. If everything is one cluster, your ground removal failed; if the floor is still there as obstacles, your normal constraint or distance threshold is off.
- **One box per object, sized right.** Each oriented bounding box hugs one real object — the cup gets a cup-sized box, the chair gets a chair-sized box — not two objects in one box (under-segmentation) and not one object split across three (over-segmentation). The box orientation roughly matches the object's.
- **The odometry trajectory is smooth and plausible.** As the robot (or the bag) moves, the published odometry traces a smooth path that matches the motion — no teleport jumps (wrong-local-minimum ICP), no frozen pose (ICP not converging). The health topic shows fitness > ~0.8 in good geometry.
- **The health drops where it should.** Drive (or play) through a featureless corridor and watch the ICP fitness fall and the covariance inflate — the node *knowing* it's in degenerate geometry. A node whose health is always green even in a corridor is a node that isn't actually measuring its registration quality.

If all four hold, your node is portfolio-grade and ready for Week 16. If any fails, the failure points you at the stage to fix — and that diagnostic clarity (knowing *which* stage broke from *what* you see) is itself a skill the week is teaching.

## Common failure modes and their fixes

The bugs this project produces are predictable, so here's the field guide:

- **"One giant cluster."** Ground not removed (or the distance threshold too tight, leaving a layer of ground points that bridge objects). Fix: check the ground normal is near-vertical and the inliers actually cover the floor; loosen the distance threshold slightly.
- **"The cloud is sideways / the ground normal points sideways."** The `PointCloud2`→Open3D conversion dropped the frame, or the input cloud is in the optical frame and you didn't transform to `base_link`. Fix: the Week-14 optical-frame discipline; verify with `tf2_echo`.
- **"ICP teleports."** Wrong-local-minimum from a bad initial guess, or you're not using the constant-velocity guess. Fix: seed ICP with the previous motion; check the per-scan fitness/RMSE and reject implausible transforms.
- **"The node can't keep up (2 Hz)."** A per-point Python loop, or clustering the raw cloud. Fix: vectorize with NumPy/`read_points_numpy`; downsample first.
- **"Far objects dissolve into noise."** `eps` smaller than the far-field point spacing after downsampling. Fix: a larger `eps`, or don't cluster beyond a range, or range-dependent `eps`.

Each failure has a distinct signature and a known fix, and recognizing them — rather than randomly tweaking parameters — is the difference between a frustrating Saturday and a working node. When something looks wrong, name the symptom, match it to this list, and apply the fix; that disciplined debugging is exactly what the Week 16 midterm tests when it hands you a stack and asks "what's wrong and how do you know?"

## Stretch goals

- **Stamp-age gate in the cluster node.** Add a runtime check that drops a cloud older than a tolerance before processing — the stale-perception guard you'll need in Week 16's pipeline. (Lecture-2 ideas applied to your own node.)
- **GICP instead of point-to-plane.** Swap in Generalized-ICP and compare the odometry drift on a bag — GICP is what production LiDAR odometry uses, and you'll see why on the degenerate sections.
- **Tracked clusters.** Associate clusters frame-to-frame (nearest-centroid) so each object keeps a stable id over time — the first step toward object tracking, which the capstone's "bring me the red cup" needs.
- **Drift readout.** Add a node that logs the accumulated odometry drift live (against wheel odom or sim ground truth) so you can watch the `Z²`-of-registration-drift grow — the Challenge-1 metric, live on your own stack.

---

## Implementation guidance — build it in this order

The order you build this node in determines whether it comes together cleanly or fights you. Bottom-up, each stage verified:

1. **`conversions.py` first.** Get `PointCloud2` ↔ Open3D working, with the header (stamp + frame) preserved on the round-trip, and unit-test it on a synthetic cloud. Everything downstream depends on this, and a dropped header is a silent bug that surfaces three stages later.
2. **`pipeline.py`, ROS-free, unit-tested.** Port your Exercise-1 pipeline (downsample, ground-segment, cluster) and Exercise-2 ICP into pure functions, and unit-test them on synthetic scenes *before* wiring them to ROS. A synthetic floor+box gives a known ground normal and cluster count; a synthetic cloud pair gives a known ICP transform. Prove the algorithms independent of the graph.
3. **`cluster_node.py` against a static cloud.** Wire the cluster pipeline to a single recorded cloud (or one live frame), publish the `Detection3DArray` + `MarkerArray`, and confirm the boxes appear around the right objects in rviz2, in the right frame, before going live-streaming.
4. **`odom_node.py` against a pair, then a stream.** Get scan-to-scan ICP working on two consecutive frames (verify the transform is plausible), then on the live stream with the constant-velocity guess and the accumulated pose.
5. **The health gating last.** Add the fitness/RMSE publication and the covariance inflation once the odometry itself is known-good. Verify it by feeding a degenerate section and watching the health topic and covariance respond.

The discipline is the same as Week 14's: build bottom-up, verify each stage, so a bug is always in the thing you just added. Top-down — wiring everything and then debugging a silent failure across five stages — is the slow path.

## A note on real-time: where the milliseconds go

This node has to keep up with the cloud rate, and Open3D in Python can be slow if you're careless. The hot spots and their fixes:

- **Don't convert the whole cloud to a Python list.** `point_cloud2.read_points_numpy` gives you an `Nx3` array directly; iterating points in Python is the #1 way to drop to 2 Hz.
- **Downsample early and aggressively.** The voxel filter is the cheapest way to make every later stage fast. A node that clusters a million raw points will not keep up; one that downsamples to 30k first will.
- **Estimate normals only on the downsampled cloud**, and only if you need them (point-to-plane ICP does; pure clustering doesn't). Normal estimation on a full-resolution cloud is a latency sink.
- **Reuse the KD-tree where you can.** Clustering and ICP both build spatial indices; on the downsampled cloud they're cheap, but don't rebuild them redundantly.

The reason this matters beyond "it's nice to be fast": the Week 16 fused perception node has a 30 ms *total* budget, and this clustering is one branch of it. If your clustering takes 25 ms, you've eaten most of the budget before fusion even starts. Profiling your node now — knowing it's, say, 8 ms for downsample+segment+cluster on the downsampled cloud — is the number you bring to the Week 16 latency budget. A node that's correct but takes 40 ms is a node you'll have to optimize next week under integration pressure; better to keep it lean now.

## How this connects to the rest of C24

- **Week 16 (Phase 2 integration + first midterm)** fuses this node's `Detection3DArray` (3D detections) and `lidar_odom` (a motion source) with the IMU/wheel-odom EKF and the RGB-D YOLO detector into one `/perception/objects` in `map` frame, inside 30 ms. Your health-gating is part of why the EKF doesn't corrupt on a bad scan.
- **Week 25+ (grasping)** consumes the object proposals: the antipodal grasp sampler runs on the clusters this node localizes. A grasp planner that trusts a flying-pixel cluster grasps at air — your filtering and clustering are the first defense.
- **Capstone** ("bring me the red cup") localizes the cup with exactly this clustering, and bounds its drift with exactly the registration-health discipline you build here.

When you've finished, push the repo and take the [quiz](../quiz.md). Before you do, run the four "what good looks like" checks one more time and confirm the health topic responds in a corridor — that responsiveness is the property the Week 16 EKF depends on, and it's the easiest one to forget to wire. Treat the checks and the failure-mode field guide as your pre-submission checklist: for anything that fails, match the symptom to the guide and apply the named fix rather than tweaking blindly. That symptom-to-fix discipline — name the symptom, match it to the field guide, apply the named fix — is exactly what the Week 16 midterm tests when it hands you a stack and asks "what's wrong, and how do you know?"

Build the node once, build it lean (it's one branch of next week's 30 ms budget), and build it honest (it publishes its own registration confidence so the EKF can de-weight a bad scan) — and it drops cleanly into the Week 16 fused perception node and carries forward to the capstone's object localization.

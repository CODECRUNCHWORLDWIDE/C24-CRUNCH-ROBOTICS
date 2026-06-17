# Exercise 1 — Downsample, Filter, Segment, Cluster

**Goal:** Take a raw point cloud and run the full Lecture-1 pipeline on it — voxel downsample, statistical outlier removal, RANSAC ground segmentation, Euclidean clustering — verifying each stage by its point count, the ground normal, and the cluster count. You will train the habit that makes 3D perception tractable: each stage exists to make the next one work, and you check each one before moving on.

**Estimated time:** 50 minutes. Guided.

---

## Setup

Pick a cloud. Any of these works:

- **A dataset scan.** Download one Newer College or KITTI scan (the resources link both). Load it with `o3d.io.read_point_cloud("scan.pcd")` (or `read_point_cloud` on the dataset's format).
- **Your Week 14 cloud.** Save one frame of `/crunchbot/points` to a `.pcd` (`ros2 run pcl_ros pointcloud_to_pcd` or a tiny subscriber that writes one frame), then load it.
- **Open3D's bundled demo cloud.** `o3d.data.PCDPointCloud().path` gives you a clean test cloud with no download.

```python
import numpy as np
import open3d as o3d

pcd = o3d.io.read_point_cloud(o3d.data.PCDPointCloud().path)
print(f"raw: {len(pcd.points)} points")
o3d.visualization.draw_geometries([pcd])     # LOOK at it first
```

Look at the raw cloud before you touch it. You should see the ground, some objects, and noise. This is your "before."

---

## Step 1 — Voxel downsample

```python
voxel = 0.05
down = pcd.voxel_down_sample(voxel_size=voxel)
print(f"downsampled ({voxel} m voxels): {len(down.points)} points "
      f"({100 * len(down.points) / len(pcd.points):.1f}% of raw)")
```

Record the point count. You should see a large reduction (often 5–30×) with the *shape* intact. Try `voxel = 0.02` and `voxel = 0.10` and watch the count and the visual fidelity trade off. **Write down the voxel size you'll use and why** (it should be ≈ the smallest feature you care about).

> If the count barely drops, your voxel is too small for the cloud's density. If small obstacles vanish, it's too large. The mini-project makes this a justified parameter.

---

## Step 2 — Statistical outlier removal

```python
clean, kept = down.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
removed = len(down.points) - len(clean.points)
print(f"outlier removal: dropped {removed} points "
      f"({100 * removed / len(down.points):.1f}%)")
# Visualize what was removed (red = outliers).
outliers = down.select_by_index(kept, invert=True)
outliers.paint_uniform_color([1, 0, 0])
o3d.visualization.draw_geometries([clean, outliers])
```

The red points are the flying pixels and stragglers — they should be isolated specks floating away from surfaces, exactly the Week 14 artifacts. If SOR is removing chunks of *real* surface, loosen `std_ratio` (try 3.0). If it leaves obvious flying pixels, tighten it (try 1.5).

---

## Step 3 — RANSAC ground segmentation

```python
clean.estimate_normals(
    o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
plane_model, inliers = clean.segment_plane(distance_threshold=0.03,
                                           ransac_n=3, num_iterations=1000)
a, b, c, d = plane_model
print(f"ground plane: {a:.2f}x + {b:.2f}y + {c:.2f}z + {d:.2f} = 0")
print(f"ground normal: ({a:.2f}, {b:.2f}, {c:.2f})   "
      f"{'[LEVEL]' if abs(c) > 0.9 else '[NOT VERTICAL — check frame!]'}")

ground = clean.select_by_index(inliers)
obstacles = clean.select_by_index(inliers, invert=True)
ground.paint_uniform_color([0.2, 0.8, 0.2])      # green ground
o3d.visualization.draw_geometries([ground, obstacles])
```

**The sanity check:** the ground normal `(a, b, c)` should be ≈ `(0, 0, 1)` (z-up) on a level floor. If `|c|` is small (the normal points sideways), either your cloud is in the wrong frame (the Week 14 optical-frame bug) or RANSAC picked a *wall* instead of the floor.

> **If RANSAC picks a wall**, constrain it: loop the segmentation, rejecting planes whose `|c| < 0.9`, or crop the cloud's z-range first so the floor dominates. This is the failure from Lecture 1 §4, and the fix is the normal constraint.

The green ground should now be visually separated from the obstacles. **This is the highest-value step** — without it, clustering merges everything through the floor.

---

## Step 4 — Euclidean clustering

```python
labels = np.array(obstacles.cluster_dbscan(eps=2 * voxel, min_points=20))
n_clusters = labels.max() + 1
n_noise = int(np.sum(labels < 0))
print(f"clusters: {n_clusters} objects, {n_noise} noise points")

# Color each cluster differently to inspect the segmentation.
import matplotlib.pyplot as plt
colors = plt.get_cmap("tab20")(labels / max(n_clusters, 1))
colors[labels < 0] = [0, 0, 0, 1]        # noise = black
obstacles.colors = o3d.utility.Vector3dVector(colors[:, :3])
o3d.visualization.draw_geometries([obstacles])
```

Each colored blob should be one object. Check:

- **Under-segmentation?** Two objects merged into one color → lower `eps`, or your ground removal left a bridging point.
- **Over-segmentation?** One object split into several colors → raise `eps`.
- **Objects dissolving into black (noise)?** `eps` smaller than the point spacing → raise `eps` or lower `min_points`.

Tune `eps` until each distinct object is its own cluster. Record the final `eps` and the cluster count.

---

## Step 5 — Clusters to bounding boxes

```python
for k in range(n_clusters):
    cluster = obstacles.select_by_index(np.where(labels == k)[0])
    obb = cluster.get_oriented_bounding_box()
    print(f"cluster {k}: center {np.round(obb.center, 2)}, "
          f"extent {np.round(obb.extent, 2)}, {len(cluster.points)} points")
```

Each oriented bounding box is an *object proposal* — a center, a size, and an orientation — exactly what you publish as a `vision_msgs/Detection3D` for the Week 16 fused perception node.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] You recorded the point count after downsampling and after outlier removal, with the reductions.
- [ ] The ground normal is ≈ `(0, 0, 1)` (or you diagnosed and fixed a sideways normal / wall-pick).
- [ ] The green ground is visually separated from the obstacles.
- [ ] Clustering produces one cluster per distinct object (you tuned `eps` until under/over-segmentation was resolved), and you recorded the final `eps` and cluster count.
- [ ] Each cluster has a printed oriented bounding box (center, extent).
- [ ] You can state, in one sentence, why ground segmentation must come *before* clustering (a single ground point bridges two objects into one cluster).

---

## Stretch

- **Constrain the ground normal.** Wrap `segment_plane` in a loop that re-samples until `|c| > 0.9`, so it reliably picks the horizontal floor over a vertical wall. Confirm it fixes a scene where the raw RANSAC picked a wall.
- **Range-dependent `eps`.** Far points are sparser (Week 14 `Z²`). Cluster near and far regions with different `eps` and show it reduces the far-object dissolving-into-noise failure.
- **Run it on your Week 14 cloud.** Pipe a live `/crunchbot/points` frame through this pipeline and confirm the gating you built last week makes the clustering cleaner than on an un-gated cloud — the two weeks compose.

---

When this feels comfortable, move to [Exercise 2 — ICP on two scans](./exercise-02-icp-two-scans.py).

# Week 15 — Resources

Every resource here is **free**. Open3D and PCL are open-source with open docs. The ICP, FPFH, and Generalized-ICP papers are openly available. The Newer College Dataset and KITTI are free for research use. No paywalled books are linked.

We standardize on **Open3D** for the labs (it's `pip install open3d`, pure-Python-friendly, and the API is clean), and we reference **PCL** because it is the C++ library most production ROS2 perception nodes use and you should be able to read it. The *algorithms* are identical across both — voxel grid, RANSAC plane, Euclidean cluster, ICP — only the API differs.

## Required reading (work it into your week)

- **Open3D — Point cloud tutorial** — load, visualize, voxel-downsample, estimate normals. Your starting point Monday:
  <https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html>
- **Open3D — ICP registration tutorial** — point-to-point, point-to-plane, the `evaluate_registration` fitness/RMSE, in runnable code:
  <https://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html>
- **Open3D — Global registration tutorial** — FPFH features + RANSAC to seed ICP from a bad initial guess:
  <https://www.open3d.org/docs/release/tutorial/pipelines/global_registration.html>
- **PCL — Plane segmentation with RANSAC** — the ground-segmentation algorithm in PCL's words (the same algorithm you run in Open3D):
  <https://pcl.readthedocs.io/projects/tutorials/en/master/planar_segmentation.html>
- **PCL — Euclidean cluster extraction** — clustering non-ground points into object proposals:
  <https://pcl.readthedocs.io/projects/tutorials/en/master/cluster_extraction.html>

## The papers (skim, then refer)

- **Besl & McKay (1992), "A Method for Registration of 3-D Shapes"** — the original ICP. Read §III (the algorithm) once; it's shorter and clearer than its reputation:
  widely mirrored; search "Besl McKay ICP 1992 PDF".
- **Chen & Medioni (1992), "Object modelling by registration of multiple range images"** — point-to-*plane* ICP. Why minimizing point-to-surface distance converges faster than point-to-point:
  search "Chen Medioni point-to-plane ICP".
- **Rusu et al. (2009), "Fast Point Feature Histograms (FPFH) for 3D Registration"** — the feature behind global registration:
  <https://www.cvl.iis.u-tokyo.ac.jp/~oishi/Papers/Alignment/Rusu_FPFH_ICRA2009.pdf>
- **Segal et al. (2009), "Generalized-ICP"** — GICP, the plane-to-plane variant most modern LiDAR odometry uses (the stretch goal):
  <https://www.roboticsproceedings.org/rss05/p21.pdf>
- **Pomerleau et al. (2015), "A Review of Point Cloud Registration Algorithms for Mobile Robotics"** — the survey that puts all of the above in context. The single best free overview:
  <https://hal.science/hal-01178661/document>

## Datasets (free, for the ICP and drift labs)

- **Newer College Dataset** — handheld Ouster LiDAR through Oxford's New College, indoor and outdoor, with ground truth. The recommended dataset for the ICP and drift labs — manageable size, clean ground truth:
  <https://ori-drs.github.io/newer-college-dataset/>
- **KITTI Odometry** — automotive Velodyne LiDAR, the most-benchmarked odometry dataset in robotics. Larger; use a few sequences for the drift run:
  <https://www.cvlibs.net/datasets/kitti/eval_odometry.php>
- **TUM RGB-D** — RGB-D sequences with ground truth, if you want to run the pipeline on depth-camera clouds with a trajectory to compare against:
  <https://cvg.cit.tum.de/data/datasets/rgbd-dataset>

## Open3D and PCL references (open all week)

- **Open3D — Geometry API (`PointCloud`, `voxel_down_sample`, `segment_plane`, `cluster_dbscan`)**:
  <https://www.open3d.org/docs/release/python_api/open3d.geometry.PointCloud.html>
- **Open3D — Registration API (`registration_icp`, `TransformationEstimationPointToPlane`, `evaluate_registration`)**:
  <https://www.open3d.org/docs/release/python_api/open3d.pipelines.registration.html>
- **PCL — the documentation root** (for reading production C++ perception nodes):
  <https://pcl.readthedocs.io/>
- **`pcl_ros` / `perception_pcl`** — the ROS2 bridge between `sensor_msgs/PointCloud2` and PCL clouds:
  <https://github.com/ros-perception/perception_pcl>

## ROS2 point-cloud plumbing

- **`sensor_msgs_py.point_cloud2`** — read/write `PointCloud2` in Python (`read_points`, `create_cloud`):
  <https://github.com/ros2/common_interfaces/tree/jazzy/sensor_msgs_py>
- **`open3d_ros_helper` / converting `PointCloud2` ↔ Open3D** — the conversion most people get subtly wrong (dropping the header or mangling the field order):
  search "PointCloud2 open3d conversion ros2"; the pattern is in the lecture notes.

## Tools you'll use this week

- **Open3D's visualizer** — `o3d.visualization.draw_geometries([...])`: see your clouds, your clusters (colored), and your ICP alignment. Indispensable; you debug 3D perception by *looking*.
- **rviz2 PointCloud2 + MarkerArray** — view the live ROS2 cloud and the cluster bounding boxes.
- **`ros2 topic echo /crunchbot/points --field width --once`** — quick point count for an unorganized cloud (watch it drop after downsampling).
- **`evaluate_registration(source, target, threshold, T)`** — Open3D's fitness/RMSE report; run it on *every* ICP result before you trust the transform.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Voxel downsampling** | Replace all points in each small cube (voxel) with one representative; shrinks the cloud, regularizes spacing. |
| **Passthrough / crop box** | Keep only points inside a region of interest (e.g. `0 < z < 2 m`). |
| **Statistical outlier removal** | Drop points whose mean distance to neighbours is an outlier — kills flying pixels and stragglers. |
| **Normal estimation** | Per-point surface normal (from the local neighbourhood); needed for point-to-plane ICP and plane segmentation. |
| **RANSAC plane** | Randomly sample 3 points, fit a plane, count inliers, repeat; the largest-inlier plane is the ground. |
| **Euclidean clustering** | Group points within a distance tolerance into clusters (DBSCAN-style); each cluster is an object proposal. |
| **ICP** | Iterative Closest Point: align two clouds by repeatedly matching nearest points and solving for the best transform. |
| **Point-to-point ICP** | Minimize distances between matched points. Simple, slower to converge. |
| **Point-to-plane ICP** | Minimize matched-point-to-target-*surface* distances (uses normals). Faster, more robust. |
| **Fitness** | Fraction of source points that found a correspondence within the threshold. Higher = better alignment. |
| **Inlier RMSE** | RMS distance of the matched (inlier) correspondences. Lower = tighter alignment. |
| **Initial guess** | The transform ICP starts from; a bad one sends ICP to the wrong local minimum. |
| **Global registration** | Initial-guess-free alignment via feature matching (FPFH + RANSAC) to *seed* ICP. |
| **FPFH** | Fast Point Feature Histogram: a local-geometry descriptor used to match points across clouds without an initial guess. |
| **Drift** | Accumulated pose error over a sequence; pairwise ICP error compounds without loop closure. |
| **Loop closure** | Recognizing a revisited place to add a constraint that cancels accumulated drift (Week 7, in 3D). |

---

*If a link 404s, please open an issue so we can replace it.*

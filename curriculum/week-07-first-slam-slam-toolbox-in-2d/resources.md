# Week 7 — Resources

Almost everything on this page is **free**. The ROS2 and `slam_toolbox` documentation, the REP specs, the Nav2 docs, and the foundational SLAM papers (Grisetti's graph-SLAM tutorial, Olson's correlative scan matching, the original `slam_toolbox` paper) are all freely available. One textbook (*Probabilistic Robotics*) is paid in print but the authors host the relevant chapters openly. No paywalled link is required to complete the week.

## Required reading (work it into your week)

- **`slam_toolbox` README and wiki** — the primary reference for the package you live in this week: the node variants, the parameter file, the RViz panel, the save/serialize services. Read it before you write a single launch file:
  <https://github.com/SteveMacenski/slam_toolbox>
- **Steve Macenski et al. — "SLAM Toolbox: SLAM for the dynamic world" (JOSS 2021)** — the short, readable paper that explains the *why* behind the three modes (mapping, localization, lifelong), the serialization format, and the design goals. This is the single most important reading of the week:
  <https://joss.theoj.org/papers/10.21105/joss.02783>
- **REP-105 — Coordinate Frames for Mobile Platforms** — defines `map`, `odom`, `base_link`, and the rule that `slam_toolbox` publishes `map → odom` (accurate, discontinuous) while your odometry publishes `odom → base_link` (continuous, drifting). This is the frame contract the whole week obeys:
  <https://www.ros.org/reps/rep-0105.html>
- **`nav_msgs/OccupancyGrid` message definition** — the exact fields the map lives in: `info.resolution`, `info.width/height`, `info.origin`, and the `int8[]` data with values `-1 / 0 / 100`:
  <https://docs.ros.org/en/jazzy/p/nav_msgs/interfaces/msg/OccupancyGrid.html>
- **Nav2 — "(SLAM) Navigating While Mapping" and the map-server docs** — how the saved map you produce is consumed by Nav2 and AMCL in Phase 3, and the PGM/YAML map format `map_saver_cli` writes:
  <https://docs.nav2.org/tutorials/docs/navigation2_with_slam.html>

## The SLAM canon

- **Grisetti, Kümmerle, Stachniss & Burgard — "A Tutorial on Graph-Based SLAM" (IEEE ITS Magazine, 2010).** The canonical, accessible explanation of pose-graph SLAM: nodes, edges, the information matrix, the front-end/back-end split, and the least-squares optimization. Read this and the whole week's vocabulary clicks. Freely available:
  <https://www.dfki.de/fileadmin/user_upload/import/8336_GraphSLAM-Tutorial-Grisetti.pdf>
- **Olson — "Real-Time Correlative Scan Matching" (ICRA 2009).** The scan-matching method at the heart of `slam_toolbox`'s front-end: brute-force-but-robust correlation over a search window, the multi-resolution acceleration, and the covariance estimate. Knowing this paper is knowing what the scan-match parameters actually do:
  <https://april.eecs.umich.edu/pdfs/olson2009icra.pdf>
- **Thrun, Burgard & Fox — *Probabilistic Robotics*, Chapters 9 (Occupancy Grid Mapping), 10 (SLAM), and 11 (GraphSLAM).** The textbook treatment of occupancy-grid log-odds, the full-SLAM posterior, and the graph formulation. The bridge from "the map is a probability field" to "SLAM is least squares on a graph":
  <https://probabilistic-robotics.org/>
- **Stachniss — "Robot Mapping / SLAM" lecture course (University of Bonn).** A free, complete video course (the "Cyrill Stachniss" YouTube channel) covering occupancy grids, EKF-SLAM, graph-SLAM, and least-squares on `SE(2)`. The graph-SLAM and least-squares lectures map directly onto this week:
  <https://www.ipb.uni-bonn.de/teaching/>
- **Kümmerle et al. — "g2o: A General Framework for Graph Optimization" (ICRA 2011).** The graph-optimization back-end whose ideas `slam_toolbox` and Ceres share. Background for what "optimize the pose graph" means computationally:
  <https://github.com/RainerKuemmerle/g2o>

## Occupancy grids and scan matching — going deeper

- **Konolige et al. — "Efficient Sparse Pose Adjustment for 2D Mapping" (IROS 2010).** The SPA back-end that `slam_toolbox` can use (and whose lineage runs through Karto, `slam_toolbox`'s ancestor). The "sparse" insight is why 2D SLAM scales to large buildings:
  <http://robots.stanford.edu/papers/Konolige10b.pdf>
- **Hess, Kohler, Rapp & Andor — "Real-Time Loop Closure in 2D LIDAR SLAM" (ICRA 2016) — the Cartographer paper.** A different (branch-and-bound scan matching, submap-based) approach to the same problem `slam_toolbox` solves; reading it sharpens your understanding of the loop-closure search and why thresholds matter:
  <https://research.google.com/pubs/archive/45466.pdf>
- **`open_karto` / `slam_toolbox` Karto scan-matcher source** — the actual correlative scan matcher you are tuning lives here. Read `Mapper.cpp` to see `loop_search_maximum_distance`, the response score, and the chain-matching logic as code:
  <https://github.com/SteveMacenski/slam_toolbox/tree/ros2/lib/karto_sdk>

## Official ROS2 docs (Jazzy)

- **`slam_toolbox` parameter reference** — every parameter you set in the YAML, grouped by front-end / loop-closure / back-end / mode. The single most-referenced page while you tune:
  <https://github.com/SteveMacenski/slam_toolbox#configuration>
- **`nav2_map_server` and `map_saver_cli`** — saving the occupancy grid to PGM + YAML, the format Nav2/AMCL load. Note the `--free_thresh` / `--occupied_thresh` flags and the `mode` field in the YAML:
  <https://docs.nav2.org/configuration/packages/configuring-map-server.html>
- **`sensor_msgs/LaserScan` message** — the input to `slam_toolbox`: `angle_min/max`, `range_min/max`, `ranges[]`. The `frame_id` must be in your TF tree or scan matching silently fails:
  <https://docs.ros.org/en/jazzy/p/sensor_msgs/interfaces/msg/LaserScan.html>
- **`tf2` and `view_frames`** — generate a PDF of your TF tree to confirm `map → odom → base_link` is present, singly-parented, and that `slam_toolbox` (not a stray static publisher) owns `map → odom`:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.html>
- **Gz Sim `gpu_lidar` sensor and `ros_gz_bridge`** — the simulator-side LiDAR plugin that fills `/scan`, and the bridge that carries it into ROS2. If `/scan` is empty, the bug is almost always here, not in `slam_toolbox`:
  <https://github.com/gazebosim/ros_gz/tree/jazzy/ros_gz_bridge>
- **`nav2_amcl`** — the particle-filter localizer you will run against this week's map in Week 11. Read it now to understand how `slam_toolbox` localization differs (pose-graph vs. particle filter):
  <https://docs.nav2.org/configuration/packages/configuring-amcl.html>

## Tools

- **RViz2 with the SlamToolbox plugin panel** — the `slam_toolbox` RViz panel exposes "Serialize Map", "Deserialize Map", "Clear Changes", and the interactive-marker pose correction. Add it via Panels → Add New Panel → SlamToolboxPlugin:
  <https://github.com/SteveMacenski/slam_toolbox#rviz-plugin>
- **`evo` — trajectory evaluation toolkit** — `evo_ape` compares your SLAM trajectory against Gz Sim ground truth, giving you an absolute-pose-error number to put next to the closure picture. Optional but rigorous:
  <https://github.com/MichaelGrupp/evo>
- **PlotJuggler** — from Week 6; useful here to plot the `map → odom` correction over time and *see* the discontinuous jumps when a loop closes:
  <https://github.com/facontidavide/PlotJuggler>
- **`ros2 bag`** — record a drive once (`/scan`, `/tf`, `/odom`, `/joint_states`) and replay it into `slam_toolbox` at different rates. This is how the LiDAR-rate-comparison exercise stays controlled — same trajectory, different scan rate:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html>

## Talks worth watching (all free, no account)

- **"On Use of SLAM Toolbox" / "Whole-Building Mapping" — Steve Macenski, ROSCon.** The author of `slam_toolbox` (and Nav2 maintainer) explaining the three modes, the serialization story, and the lifelong-mapping use case that motivated the package. Search YouTube for "Macenski slam_toolbox ROSCon."
- **"SLAM" — Cyrill Stachniss lecture series.** The graph-SLAM and least-squares-on-a-manifold lectures are the clearest free explanation of what `slam_toolbox`'s back-end is doing. Search YouTube for "Stachniss graph SLAM least squares."
- **"Cartographer: Real-Time Loop Closure in 2D LIDAR SLAM" — Google ICRA talk.** A contrasting approach to the same loop-closure problem; the branch-and-bound visualization makes the search-window idea concrete. Search YouTube for "Cartographer 2D LIDAR SLAM ICRA."
- **"Nav2 and the ROS2 navigation stack" — ROSCon deep dives.** Background for how the map you build this week is consumed in Phase 3. Search YouTube for "ROSCon Nav2."

## How to use this resource list

The lectures cite specific URLs from this page at decision points. When Lecture 1 says "see Olson 2009 for the correlative scan matcher," the URL is above. You do not need to read every link this week. The links to read end-to-end are:

1. **The `slam_toolbox` README and the Macenski JOSS paper.** Non-negotiable — they explain the package you spend the whole week inside.
2. **REP-105.** The frame contract; half of all Week 7 transform bugs are REP-105 violations.
3. **The Grisetti graph-SLAM tutorial.** ~40 minutes; it is the conceptual spine of Lecture 1.
4. **The `nav_msgs/OccupancyGrid` message definition and the Nav2 map-server docs.** You will reference both while saving and inspecting maps.
5. **Olson 2009, Sections II–III.** ~30 minutes; it is what the scan-match parameters actually control.

The rest are reference material — bookmark them and return when a specific question arises.

---

*Bookmarks decay. If a link rots, search the title — the REPs, the `slam_toolbox` repo, the Grisetti tutorial, and the Olson and Cartographer papers are canonical and reappear on the authors' and ROS's new homes.*

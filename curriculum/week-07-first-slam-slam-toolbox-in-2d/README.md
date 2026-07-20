# Week 7 — First SLAM: `slam_toolbox` in 2D

Welcome to **C24 · Crunch Robotics**, Week 7. Week 1 gave you the rigid-body math and `SE(3)`. Week 2 built your TF tree. Week 3 turned a URDF into a robot in Gz Sim. Week 4 taught you actions, lifecycle, and executors. Week 5 made you fluent in QoS and DDS. Week 6 made your robot answer "where am I?" with wheel odometry — and made you measure, in metres, exactly how badly that answer drifts. This week we hand your robot the thing that *fixes* the drift: a map, and the machinery that builds the map and the pose at the same time. **This is your first end-to-end SLAM.**

By Friday you will have driven your Week 3 diff-drive robot through a multi-room Gz Sim world with `slam_toolbox` running in mapping mode, watched a loop close in RViz — the moment the map snaps into alignment as the back-end re-optimizes — saved the resulting occupancy grid and the serialized pose-graph, restarted the robot in localization mode and watched it re-find itself against the saved map, and compared map quality at three different LiDAR update rates so you can defend a sensor-rate choice with a picture instead of a hunch. The saved, loop-closed map you produce this week is **not a throwaway**: it is the navigation target that Nav2 and AMCL reuse in Phase 3, and it is one of the artifacts you defend at the Week 8 architecture review. Build it like it ships, because it does.

The central engineering truth of the week, stated up front so you can hold it the whole way through: **SLAM is a loopy estimation problem dressed up as a map.** The map is the output you look at, but the *thing being solved* is a graph — nodes are robot poses, edges are constraints between poses, and the back-end finds the configuration of poses that best satisfies all the constraints at once. A scan-matching front-end produces those constraints by aligning consecutive LiDAR scans (sequential constraints, the "odometry edges" of the graph) and by recognizing a place the robot has visited before (a *loop-closure* constraint, the edge that ties a distant pose back to an earlier one). The back-end is a nonlinear least-squares optimizer that re-arranges all the poses to minimize the total constraint error. The occupancy grid you render at the end is just those optimized poses with their scans painted in. Confuse the map for the computation and you will tune the wrong knobs all week. Understand that the map is the *shadow* of an optimized pose graph and `slam_toolbox`'s every parameter suddenly makes sense.

The second truth: **loop closure is the only thing that bounds drift, and it is also the only thing that can wreck your map.** Without loop closures, SLAM is just scan-matched odometry — it drifts more slowly than wheel odometry (because scan matching is more accurate than dead reckoning) but it still drifts, unbounded, exactly as Week 6 predicted. A loop closure is the "fix" — the star sighting, the lighthouse — that resets the accumulated error by tying the present pose back to a known one. When a loop closes correctly, the back-end smears the accumulated drift back across the whole loop and the map becomes globally consistent. When a loop closure is *wrong* — a false positive, the front-end matching a corridor to the wrong identical-looking corridor — the back-end faithfully optimizes toward a lie and folds your map in half. The entire art of tuning a SLAM system is making true loop closures fire and false ones stay silent. This week's challenge is built around exactly that knife-edge.

The third truth: **mapping, localization, and lifelong mapping are three modes of the same machine, and choosing the wrong one is a deployment bug, not a preference.** `slam_toolbox` is one node that runs in three configurations. *Mapping mode* (synchronous or asynchronous) builds a fresh pose graph from scratch — you run it once, drive the building, save the map. *Localization mode* loads a saved pose graph and only adds a small rolling window of new constraints to find where you are *against* that fixed map — it is `slam_toolbox`'s answer to AMCL, and it is what your robot runs every day after the map exists. *Lifelong mapping* loads a saved graph and *keeps editing it* — adding new nodes, removing stale ones — so the map tracks a changing building over weeks. A robot that runs mapping mode in production rebuilds its world every boot and never benefits from yesterday's work; a robot that runs localization mode in a building that has been re-furnished slowly loses its mind. We teach all three and the decision rule for each.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** SLAM as a pose-graph estimation problem: nodes are poses, edges are constraints, the front-end produces constraints by scan matching, the back-end optimizes the graph, and the occupancy grid is the rendered output — not the state being solved.
- **Describe** the occupancy-grid representation: log-odds cells, the `nav_msgs/OccupancyGrid` message, resolution and origin, and the meaning of the `-1 / 0 / 100` cell values.
- **Trace** how a scan-match front-end (correlative scan matching plus the Ceres-based refinement `slam_toolbox` uses) turns two LiDAR scans plus an odometry prior into a relative-pose constraint with an information matrix.
- **Distinguish** sequential constraints (consecutive scans) from loop-closure constraints (revisited places), and explain why loop closure is the only mechanism that bounds SLAM drift.
- **Configure** `slam_toolbox` in **mapping mode** (synchronous vs. asynchronous) against your Week 3 robot and a multi-room world, and tune the core front-end parameters (`resolution`, `max_laser_range`, `minimum_travel_distance`, `minimum_travel_heading`, the scan-match search window).
- **Tune** the loop-closure parameters (`do_loop_closing`, `loop_search_maximum_distance`, `loop_match_minimum_response_*`, `loop_match_minimum_chain_size`) to make a true loop close while a false one stays silent.
- **Save** a map two ways: the `map_saver_cli` PGM/YAML occupancy grid (for Nav2/AMCL) and `slam_toolbox`'s serialized `.posegraph` + `.data` (for re-localization and lifelong editing), and explain why both exist.
- **Restart** the robot in **localization mode** against the saved serialized graph, set an initial pose, and verify AMCL-style convergence in RViz.
- **Compare** map quality at three different LiDAR update rates and articulate the trade-off between scan-match accuracy, CPU load, and drift between updates.
- **Read** the `map → odom → base_link` frame chain the way REP-105 intends: `slam_toolbox` publishes the `map → odom` correction; your Week 6 node publishes `odom → base_link`.

## Prerequisites

- **Weeks 1 through 6** of C24 complete. You can write an `rclpy` node, build a colcon workspace, author a URDF in xacro, spawn it in Gz Sim, reason about QoS, and — critically — your **Week 6 odometry node publishes `odom → base_link` with honest covariance**. `slam_toolbox` consumes that transform as its motion prior; bad odometry makes scan matching slower and loop closure less reliable. If your Week 6 square still drifts more than ~2% of path length, fix the calibration first.
- **REP-103 and REP-105 fluency from Week 6.** This week is *all* about the frame tree: who publishes `map → odom`, who publishes `odom → base_link`, why `map → odom` jumps and `odom → base_link` is smooth. You will debug a transform problem this week; the REPs are the manual.
- **A working ROS2 Jazzy install on Ubuntu 24.04** (or the Path B container). `ros2 --version` reports Jazzy. `gz sim --version` reports Harmonic. Your Week 3 diff-drive robot still spawns, publishes `/scan` and `/joint_states`, and drives under `ros2 topic pub /cmd_vel`.
- **`slam_toolbox` installed** — `sudo apt install ros-jazzy-slam-toolbox`. Confirm with `ros2 pkg prefix slam_toolbox`. We also use `nav2_map_server` (`sudo apt install ros-jazzy-nav2-map-server`) for `map_saver_cli`.
- **A working 2D LiDAR on your robot.** Your Week 3 URDF has a `gpu_lidar` (or `gpu_ray`) Gz Sim sensor publishing `sensor_msgs/LaserScan` on `/scan`, bridged through `ros_gz_bridge`. `ros2 topic hz /scan` reports a steady rate. If `/scan` is empty, fix the sensor before you touch SLAM — `slam_toolbox` with no scans does nothing and prints nothing useful.
- **A Python scientific stack** — `numpy`, `matplotlib` available in the same environment you run ROS2 from. The occupancy-grid analysis and the rate-comparison plots are rendered with matplotlib for the writeups.
- Nothing else. We start from your Week 6 robot and a blank `crunch_slam` package, and we end with a saved, loop-closed map and a localization launch config that Phase 3 reuses.

## Topics covered

- **The occupancy grid.** The `nav_msgs/OccupancyGrid` message: `info.resolution`, `info.width/height`, `info.origin`, and the `int8[]` data field with values `-1` (unknown), `0` (free), `100` (occupied). The log-odds cell model and why a map is a probability field, not a bitmap.
- **SLAM as a pose graph.** Nodes (poses), edges (constraints), the information matrix on each edge. The front-end / back-end split. Why "full SLAM" optimizes the whole trajectory, not just the latest pose, and how that differs from a filter (AMCL, EKF).
- **Scan matching.** Correlative scan matching (the brute-force-but-robust front-end `slam_toolbox` uses, after Olson 2009), the search window, the response score, and the Ceres-based pose refinement that polishes the match. The relationship between scan-match quality and LiDAR density.
- **Loop closure.** What a loop-closure constraint is, how `slam_toolbox` searches for candidates (a chain of nearby nodes within `loop_search_maximum_distance`), the match-response threshold that accepts or rejects a candidate, and the catastrophic failure mode of a false positive.
- **The back-end.** Sparse-pose-adjustment / nonlinear least squares (`slam_toolbox` uses Ceres by default, with SPA and other solvers selectable), what "optimizing the graph" means geometrically, and why a loop closure visibly *moves* the whole map when it fires.
- **`slam_toolbox` architecture.** The `SlamToolbox`, `AsynchronousSlamToolbox`, `SynchronousSlamToolbox`, and `LocalizationSlamToolbox` node variants; the lifecycle; the parameter file; the `/slam_toolbox/*` services (`save_map`, `serialize_map`, `deserialize_map`); the RViz panel.
- **The three modes.** Mapping (sync vs. async — when blocking is acceptable), localization (load a fixed graph, rolling-window measurement-only), and lifelong mapping (load + continuous edit + node decay). The decision rule for each.
- **Saving and loading maps.** `map_saver_cli` → PGM + YAML (the Nav2/AMCL format); `serialize_map` → `.posegraph` + `.data` (the `slam_toolbox` re-localization/lifelong format). Why you save both and which consumer wants which.
- **The frame chain.** `map → odom → base_link` per REP-105. `slam_toolbox` owns `map → odom` (accurate, discontinuous — it jumps on loop closure); your odometry owns `odom → base_link` (smooth, drifting). How the two compose.
- **LiDAR rate and map quality.** The trade-off: higher scan rate → less drift between scan matches and denser coverage, but more CPU and more redundant nodes; lower rate → cheaper but coarser and more drift between updates. How `minimum_travel_distance`/`minimum_travel_heading` decouple node creation from scan rate.

## Weekly schedule

The schedule adds up to approximately **36 hours**. Treat it as a target, not a contract. The mapping runs are best done when you can babysit a five-minute drive through a building without interruption — do not start a multi-room map with ten minutes left in your day, and never save a map you have not watched close at least one loop.

| Day       | Focus                                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | SLAM as a pose graph: front-end constraints, back-end optimize  |   2h     |   1.5h    |    0h      |   0.5h    |   1h     |    0h        |   0.5h     |   5.5h      |
| Tuesday   | Occupancy grids, scan matching, loop closure mechanics          |   2h     |   1.5h    |    0h      |   0.5h    |   1h     |    0h        |   0.5h     |   5.5h      |
| Wednesday | `slam_toolbox` modes; mapping run + save; localization restart  |   1.5h   |   1.5h    |    0h      |   0.5h    |   1h     |    0.5h      |   0.5h     |   5.5h      |
| Thursday  | LiDAR-rate comparison, the loop-closure challenge               |   0.5h   |   0h      |    2h      |   0.5h    |   1h     |    2h        |   0.5h     |   6.5h      |
| Friday    | Mini-project — the saved, loop-closed map + localization config |   0h     |   0h      |    1h      |   0.5h    |   1h     |    3h        |   0.5h     |   6h        |
| Saturday  | Mini-project deep work, map QA, results writeup                 |   0h     |   0h      |    0h      |   0h      |   0h     |    3h        |   0h       |   3h        |
| Sunday    | Quiz, review, polish                                           |   0h     |   0h      |    0h      |   1h      |   1h     |    1h        |   0h       |   3h        |
| **Total** |                                                                | **6h**   | **4.5h**  | **3h**     | **3.5h**  | **6h**   | **9.5h**     | **2.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The `slam_toolbox` docs and source, the Grisetti graph-SLAM tutorial, Olson's correlative scan-matching paper, REP-105, Nav2/AMCL docs, and the talks worth your time |
| [lecture-notes/01-slam-is-a-loopy-estimation-problem.md](./lecture-notes/01-slam-is-a-loopy-estimation-problem.md) | SLAM as a pose graph: occupancy grids, the front-end/back-end split, scan matching, loop closure, why the back-end optimization moves the whole map when a loop fires |
| [lecture-notes/02-slam-toolbox-modes-mapping-localization-lifelong.md](./lecture-notes/02-slam-toolbox-modes-mapping-localization-lifelong.md) | The three `slam_toolbox` modes derived and compared: mapping (sync/async), localization, lifelong; the parameter file; saving/loading; the frame chain |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-mapping-mode-close-a-loop.md](./exercises/exercise-01-mapping-mode-close-a-loop.md) | Guided: drive the multi-room world in mapping mode, watch a loop close in RViz, save the map — with launch files, a parameter file, and an expected-output block |
| [exercises/exercise-02-save-and-restart-in-localization.py](./exercises/exercise-02-save-and-restart-in-localization.py) | Runnable: a node that serializes the live map via the `slam_toolbox` service, then a localization launch that loads it and reports pose-convergence |
| [exercises/exercise-03-compare-lidar-update-rates.py](./exercises/exercise-03-compare-lidar-update-rates.py) | Runnable: re-throttle `/scan` to three rates, map the same world each time, and quantify map quality (coverage, edge sharpness, drift) with a metric and a plot |
| [challenges/README.md](./challenges/README.md) | Index of the challenge |
| [challenges/challenge-01-force-and-fix-a-loop-closure.md](./challenges/challenge-01-force-and-fix-a-loop-closure.md) | Build a world where a missed loop closure visibly folds the map, then tune `slam_toolbox` so the loop closes — and document the exact constraint that fixed it |
| [mini-project/README.md](./mini-project/README.md) | Full spec for the **crunch_slam map**: a saved, loop-closed occupancy grid of a multi-room world plus a localization-mode launch config — the navigation target Phase 3's Nav2 and AMCL reuse |
| [quiz.md](./quiz.md) | 13 questions on occupancy grids, pose graphs, scan matching, loop closure, and the three modes, with an answer key |
| [homework.md](./homework.md) | Five practice problems with deliverables and a rubric |

## The "map you can defend" promise

C24 treats your map the way Week 6 treats your odometry and the way Week 7 of C9 treats a benchmark: **a claim is worthless without a number or a picture.** "My map looks good" is not an engineering statement. "My map closed three loops, the largest of which corrected 0.8 m of accumulated drift; walls are single-cell-thick at 0.05 m resolution; coverage is 94% of the reachable free space; and the localization restart converged to within 4 cm of ground truth in under two seconds" *is* an engineering statement, and it is the one you will be able to make by Sunday. Every map claim in your homework and mini-project must be backed by a saved artifact, a loop-closure count, and an RViz screenshot or a matplotlib figure. The phrase "the SLAM worked" never appears in a robotics engineer's design review; the phrase "the back-end converged with a final cost of X over N constraints, including M accepted loop closures" does.

## A note on what's not here

Week 7 introduces *2D LiDAR SLAM in simulation* with `slam_toolbox`. It does **not** introduce:

- **3D SLAM.** LiDAR-inertial odometry (FAST-LIO, LIO-SAM), visual SLAM (ORB-SLAM3), and dense 3D mapping are later material. The README of the track lists them for Phase 2+; this week is strictly 2D occupancy-grid SLAM, the foundation everything else builds on.
- **The factor-graph math in full.** We treat the pose graph and the nonlinear least-squares back-end at the level you need to tune `slam_toolbox` and reason about loop closure. The GTSAM factor-graph deep dive — building a graph node by node, the marginals, the smoother — is Week 11. This week you use the back-end; Week 11 you build one.
- **Navigation.** Sending goals, planning paths, and following them on the map you build is Nav2, Week 17. This week you *produce the map and the localizer* that Nav2 consumes. We deliberately stop at "the robot knows where it is on a saved map" and hand the baton to Phase 3.
- **AMCL itself.** The particle filter (`nav2_amcl`) is Week 11's lab, where you run it against this week's map and watch the particle cloud converge. This week's localization is `slam_toolbox`'s *own* localization mode, which is a pose-graph measurement-only mode, not a particle filter. We name the distinction so you do not conflate them.
- **Hardware LiDAR bring-up.** Real RPLIDAR/Livox drivers, scan filtering, and motion distortion correction are Path A hardware concerns. In sim your scans are clean and undistorted; we note where reality diverges so the sim skill transfers.
- **Multi-robot / distributed SLAM.** Merging two robots' maps is Week 35. This week is one robot, one map.

The point of Week 7 is a sharp, narrow skill: run a real SLAM stack end-to-end, make a loop close on purpose, save a map a navigation stack can load, and re-localize against it — all measured, all defensible, all reusable in Phase 3.

## Up next

Continue to **Week 8 — Phase 1 integration + architecture review** once you have shipped this week's mini-project with a saved, loop-closed map and a working localization launch. Week 8 packages weeks 3–7 into one `bringup` package: one launch file brings up the robot, the sensors, `slam_toolbox`, and RViz with a saved layout, and you map a *new* world from scratch in under fifteen minutes. The map you build this week is the artifact you defend at the Phase 1 milestone review — alongside your TF tree (Week 2), your QoS choices (Week 5), and your odometry (Week 6). The habit you build this week — *run the real stack, force the loop closure, save the artifact, prove the localization* — is the habit that makes the integration week land. Integration only matters because each piece works; this week you made the last piece of Phase 1 work.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

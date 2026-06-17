# Mini-Project — `crunch_slam`: a saved, loop-closed map + a localization launch for Phase 3

> Produce a saved, loop-closed occupancy-grid map of a multi-room world, plus a localization-mode launch config that re-finds the robot against it. This map is **not a throwaway**: it is the navigation target that Nav2 and AMCL reuse in Phase 3 (Weeks 11 and 17). You ship one `colcon` package, `crunch_slam`, that brings up the robot, runs `slam_toolbox` mapping, saves the map two ways, and re-localizes against it — all reproducible, all measured, all documented. By the end you have the first artifact a navigation stack can actually consume.

This is the capstone of Phase 1's estimation arc. Week 6 made your robot answer "where am I?" with drifting wheel odometry. This week's mini-project makes it answer "where am I *on a map I built*?" — bounded, globally consistent, and reusable. Real robotics teams build exactly this artifact: a surveyed, loop-closed map of a deployment site plus a localization config, version-controlled and handed to the navigation team. This mini-project is that hand-off, in microcosm — and the receiving team is *you*, in Phase 3.

**Estimated time:** ~9.5 hours (split across Wednesday, Friday, Saturday, Sunday in the suggested schedule).

---

## What you will build

A `colcon` package `crunch_slam` that:

1. **Brings up the robot and sensors.** A launch file spawns your Week 3 diff-drive robot in a multi-room Gz Sim world, starts your Week 6 odometry node, and bridges `/scan`, `/clock`, and ground truth — one command, everything on sim time.
2. **Runs `slam_toolbox` in mapping mode** (async, online) with a tuned parameter file, against a multi-room world that contains **at least two genuine loops**.
3. **Closes the loops.** You drive (or replay a recorded drive of) the world so the robot revisits mapped areas, and you confirm — logged and visible in RViz — that the loops close and the back-end re-optimizes the map.
4. **Saves the map two ways.** The PGM/YAML occupancy grid (via `map_saver_cli`, for Nav2/AMCL) *and* the serialized pose graph (`.posegraph` + `.data`, via the `serialize_map` service, for `slam_toolbox` localization). Both are committed to the repo.
5. **Re-localizes against the saved map.** A localization-mode launch file loads the serialized graph, sets an initial pose, and a monitor node reports AMCL-style convergence against Gz Sim ground truth.
6. **Documents the map quality.** A `README.md` and a `docs/map_quality.md` with the loop-closure count, the largest drift a loop corrected, the wall-thickness and coverage metrics (exercise 3's analyzer), the localization convergence time, and RViz screenshots.

You ship **one package** with this layout:

```text
crunch_slam/
├── package.xml
├── CMakeLists.txt
├── config/
│   ├── mapper_params_online_async.yaml     # mapping mode, tuned
│   └── localization_params.yaml            # localization mode, points at the saved graph
├── launch/
│   ├── bringup.launch.py                   # robot + sensors + odom + bridges (sim time)
│   ├── online_async_mapping.launch.py      # bringup + slam_toolbox mapping + RViz
│   └── localization.launch.py              # bringup + slam_toolbox localization + monitor
├── worlds/
│   └── crunch_building.sdf                 # multi-room world with >= 2 real loops
├── maps/
│   ├── crunch_building.pgm                 # occupancy grid (Nav2/AMCL input)
│   ├── crunch_building.yaml                # grid metadata
│   ├── crunch_building.posegraph           # full pose graph (slam_toolbox input)
│   └── crunch_building.data                # stored scans
├── rviz/
│   └── slam.rviz                           # saved RViz layout: map + scan + tf
├── crunch_slam/
│   └── convergence_monitor.py              # the localization-convergence reporter (from ex.2)
├── docs/
│   └── map_quality.md                      # the measured map-quality report
└── README.md                               # the project writeup
```

---

## Rules

- **You may** read the ROS2/`slam_toolbox`/Nav2 docs, REP-105, the lecture notes, your Week 7 exercises and challenge, and the Grisetti/Olson papers.
- **You may NOT** use a pre-built map from anywhere — the map must be one *you* built with `slam_toolbox` mapping mode, with loops *you* closed. A downloaded map fails the project.
- **You may NOT** skip the serialized-graph save. The PGM alone is insufficient; localization mode needs the `.posegraph`/`.data` (Lecture 2, §2.4). Saving only one format is the most common project fail.
- **The world must contain at least two genuine loops.** A single open room has no loop to close and does not exercise the thing that makes SLAM work. You may extend exercise 1's three-room world, build your own, or compose a larger building.
- **Everything runs on sim time.** Every node in every launch file gets `use_sim_time: True`. A mixed-clock launch is a reject (it will not work anyway — Lecture 2, §2.3).
- **The map is the Phase 3 contract.** Build it as if Nav2 and AMCL will load it in Week 11, because they will. That means: correct `resolution` (0.05 m), correct `origin` in the YAML, single-thick walls, no spurious obstacles from false loop closures.

---

## Acceptance criteria

The grading rubric is below. Each box maps to a specific deliverable.

### Mapping and loop closure (35%)

- [ ] `ros2 launch crunch_slam online_async_mapping.launch.py` brings up the robot, sensors, odometry, `slam_toolbox` mapping, and RViz — all on sim time — with no transform errors.
- [ ] The multi-room world (`worlds/crunch_building.sdf`) contains at least two genuine loops.
- [ ] At least **two loop closures** fire during mapping (logged by `slam_toolbox`, visible as map snaps in RViz). You record the count.
- [ ] The final map shows single-thick walls and distinguishable rooms — no doubled walls, no folded geometry from a false loop closure.
- [ ] `view_frames` confirms `map → odom → base_link` with `slam_toolbox` owning `map → odom`, your odometry owning `odom → base_link`, no double-parented frame.

### Saving and localization (35%)

- [ ] The map is saved in **both** formats and **both** are committed: `crunch_building.pgm` + `.yaml` *and* `crunch_building.posegraph` + `.data`.
- [ ] The `.yaml` has correct `resolution: 0.05` and a plausible `origin` (the world pose of the bottom-left pixel — not `[0,0,0]` unless your map genuinely starts there).
- [ ] `ros2 launch crunch_slam localization.launch.py` loads the serialized graph, accepts an initial pose, and produces `map → odom`.
- [ ] The convergence monitor (from exercise 2) reports localization converging to **< 10 cm** of ground truth within a few seconds of motion. You record the convergence time and final error.
- [ ] You can re-localize from a *wrong* initial pose (set it 1 m off in RViz) and watch it still converge — or you document the failure if it does not (e.g. a symmetric region).

### Documentation (30%)

- [ ] `README.md` at the package root contains: a one-paragraph description, the exact commands to map / save / localize, and an RViz screenshot of the final map.
- [ ] `docs/map_quality.md` contains:
  - The **loop-closure count** and, for the largest, the approximate drift it corrected (from the map snap magnitude or the `map → odom` jump).
  - The **map metrics** from exercise 3's analyzer: coverage fraction, mean wall thickness, occupied fraction.
  - The **localization convergence**: time-to-converge and final position/heading error vs. ground truth.
  - At least one RViz or matplotlib figure.
- [ ] The writeup cites the relevant lecture sections and at least two resources.md URLs (e.g. REP-105 for the frame chain, the `slam_toolbox` README for the parameters you tuned).
- [ ] Every launch file sets `use_sim_time: True` on every node.

---

## Suggested implementation outline

The order matters: bring up, map, save, localize, document.

### Day 1 (Wednesday — ~0.5 h to start, continued Friday)

1. Scaffold `crunch_slam` (exercise 1, Step 1). Add the `config/`, `launch/`, `worlds/`, `maps/`, `rviz/`, `docs/` directories and the install rules.
2. Write `bringup.launch.py`: spawn the Week 3 robot into `crunch_building.sdf`, start the Week 6 odometry node, start the `ros_gz_bridge` for `/scan`, `/clock`, and ground truth. Every node gets `use_sim_time: True`. Test it standalone — confirm `/scan`, `/clock`, `tf2_echo odom base_link`, and the ground-truth topic all populate.
3. Build the multi-room world. Extend exercise 1's three-room world into something with **two** loops — e.g. a figure-eight of rooms, or a ring of four rooms with a central hub, so the robot can revisit two distinct mapped areas. Sanity-drive it.

### Day 2 (Friday — ~3 h)

4. Write `mapper_params_online_async.yaml` (start from exercise 1's tuned file). Write `online_async_mapping.launch.py` to compose `bringup` + `slam_toolbox` mapping + RViz with the saved layout.
5. Map the building. Drive (or record-then-replay) a route that revisits *two* mapped areas so two loops can close. Watch them close in RViz; note the count and which areas. If a loop does not close, apply the challenge's diagnosis (drift vs. search distance, response gate) — this is where the challenge skill pays off.
6. Iterate on parameters until the map is clean: single-thick walls, two+ loop closures, no false folds. Record a bag of the good drive so the result is reproducible (`ros2 bag record /scan /tf /tf_static /odom /joint_states /clock`).

### Day 3 (Saturday — ~3 h)

7. Save the map both ways (exercise 1, Step 7): `map_saver_cli` → PGM/YAML, and the `serialize_map` service → `.posegraph`/`.data`. Commit all four files. Open the PGM and the YAML; confirm the `origin` and `resolution` are right.
8. Write `localization_params.yaml` (`mode: localization`, `map_file_name` pointing at `maps/crunch_building`) and `localization.launch.py` (compose `bringup` + `slam_toolbox` localization + the convergence monitor).
9. Restart in localization mode. Set the initial pose in RViz. Drive a little. Confirm the monitor reports convergence < 10 cm within a few seconds. Then test the wrong-initial-pose case (1 m off) and record what happens.
10. Run exercise 3's analyzer on your saved PGM to get the coverage / wall-thickness / occupied metrics for the report.

### Day 4 (Sunday — ~1 h)

11. Write `README.md` and `docs/map_quality.md`. Include the loop-closure count, the metrics, the convergence numbers, and the screenshots. Cite the lectures and resources.
12. Final check: clone your repo fresh, `colcon build`, run the three launch files in order, confirm the map loads and localization converges. Push.

---

## Hints

- **Build `bringup.launch.py` once and include it everywhere.** Both the mapping and localization launches should `IncludeLaunchDescription(bringup.launch.py)` rather than duplicate the robot/sensor/odom setup. This is the Week 8 "your launch file is your README for operators" habit, started early.
- **Record the good drive as a bag.** A live drive is never exactly repeatable; a bag is. Once you have a drive that closes both loops cleanly, record it (or record `/scan /tf /odom /clock` during it) so you can rebuild the *same* map deterministically — and so the rate-comparison and challenge experiments stay controlled.
- **The `origin` in the YAML matters for Phase 3.** Nav2 and AMCL place the map in the world using the YAML `origin`. If it is wrong, the robot localizes onto a map that is offset from reality and every goal is off by the offset. `map_saver_cli` computes it for you — just do not hand-edit it to `[0,0,0]`.
- **Two loops, two distinct areas.** The point of *two* loops is to show the back-end handling more than one constraint — a figure-eight or a ring-with-hub forces the robot to revisit two different places, exercising the loop-closure search twice. A world where the only "loop" is driving back down the same corridor is one loop, not two.
- **Localization from a wrong pose is the interesting test.** Converging from a *correct* initial pose is easy. Converging from a 1 m-off guess shows the scan matcher actually pulling the estimate to the right place — that is the AMCL-style behavior Phase 3 depends on. If it fails to converge from 1 m off, that is a legitimate finding to document (and usually means a feature-poor or symmetric region near the start).
- **You will reuse this in Week 8 and Phase 3.** Week 8 packages this into a `bringup` super-package and maps a *new* world in 15 minutes. Week 11 runs AMCL against this PGM. Week 17 runs Nav2 against it. Build it to a standard you will be happy to load three times in the next ten weeks.

---

## Anti-goals

The following are explicitly **not** part of this mini-project. Do not pursue them; they distract from the lesson.

- **Navigation.** Sending goals and following paths is Nav2, Week 17. This project stops at "the robot knows where it is on a saved map." Do not wire a planner.
- **Lifelong mapping in production.** Lifelong mode is for changing buildings (Lecture 2, §2.6). Your deliverable is the production-normal pair: a mapping-mode map and a localization-mode launch. Mention lifelong in the writeup if you like; do not ship it as the deliverable.
- **3D SLAM.** This is 2D occupancy-grid SLAM. LIO/visual SLAM is Phase 2+.
- **Hardware LiDAR.** In sim your scans are clean and undistorted. Real-LiDAR motion-distortion correction and driver bring-up are Path A concerns; note where reality diverges, do not chase it here.
- **A custom scan matcher or back-end.** You *use* `slam_toolbox`'s front-end and Ceres back-end. Building your own factor-graph back-end is Week 11 (GTSAM). This week you operate the production tool, well.

---

## Submission

Push the package to your Week 7 GitHub repository at `mini-project/crunch_slam/`. The instructor reviews by:

1. Cloning the repo and `colcon build --packages-select crunch_slam`.
2. Running `ros2 launch crunch_slam localization.launch.py` against the committed map — localization must load the serialized graph and converge.
3. Re-mapping from your committed bag with `online_async_mapping.launch.py` — at least two loops must close and the map must match the committed PGM.
4. Reading `README.md` and `docs/map_quality.md`, checking the cited numbers against the artifacts.

A submission whose committed map loads, whose localization converges < 10 cm, and whose mapping run reproduces two loop closures is a pass. The most common review-fail is "the README claims two loop closures but the re-map shows zero" (you committed a map built before you tuned the loops) — verify your committed bag reproduces your committed map before submitting. The second most common is "the `.posegraph` is missing" — you saved only the PGM and localization mode has nothing to load.

---

## How this compounds

This map is a **Phase-3 dependency**, by design:

- **Week 8 (Phase 1 integration)** packages this into a `bringup` super-package and uses it to map a brand-new world in under fifteen minutes — the bring-up-package pattern, with this week's launches as the kernel.
- **Week 11 (AMCL / particle filters)** loads *this PGM* and runs `nav2_amcl` against it — you initialize the particle cloud and watch it converge, the filter counterpart to this week's pose-graph localization.
- **Week 17 (Nav2)** loads *this map* as the costmap's static layer and plans paths across it. The first goal you send Nav2 is a goal on the map you built this week.

The capstone's Phase 3 outcome — "autonomous nav of a multi-room map" — starts with the multi-room map you save right now. Build it like Phase 3 depends on it, because it does.

---

**References**

- `slam_toolbox` README and configuration: <https://github.com/SteveMacenski/slam_toolbox>
- Macenski et al. — "SLAM Toolbox: SLAM for the dynamic world" (the three modes): <https://joss.theoj.org/papers/10.21105/joss.02783>
- REP-105 — coordinate frames (the `map → odom → base_link` contract): <https://www.ros.org/reps/rep-0105.html>
- Nav2 — "(SLAM) Navigating While Mapping" and the map-server format your PGM uses: <https://docs.nav2.org/tutorials/docs/navigation2_with_slam.html>
- `nav2_map_server` / `map_saver_cli` (the PGM/YAML save): <https://docs.nav2.org/configuration/packages/configuring-map-server.html>
- Grisetti et al. — "A Tutorial on Graph-Based SLAM": <https://www.dfki.de/fileadmin/user_upload/import/8336_GraphSLAM-Tutorial-Grisetti.pdf>

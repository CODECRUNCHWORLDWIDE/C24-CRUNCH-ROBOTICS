# Week 7 — Exercises

Three exercises that build on each other into the mini-project. Do them in order — exercise 1 produces the map that exercise 2 serializes and re-localizes against, and exercise 3 reuses the same world to compare LiDAR rates. The mini-project is the production-grade version of all three. Run everything against your **Week 3 differential-drive robot** in Gz Sim Harmonic, with your **Week 6 odometry node** publishing `odom → base_link` (or, if your sim is down, the standalone bag-replay fallback each exercise documents).

## Index

1. **[Exercise 1 — Mapping mode: drive the multi-room world and close a loop](exercise-01-mapping-mode-close-a-loop.md)** — launch `slam_toolbox` in async mapping mode against a multi-room Gz Sim world, drive a loop, watch it close in RViz, and save the map two ways. Includes the world, the launch files, the parameter file, and an expected-output block. Guided. (~75 min)
2. **[Exercise 2 — Save and restart in localization mode](exercise-02-save-and-restart-in-localization.py)** — a node that serializes the live graph via the `slam_toolbox` service, then a localization restart that loads it and reports AMCL-style pose convergence against ground truth. Runnable. (~60 min)
3. **[Exercise 3 — Compare three LiDAR update rates](exercise-03-compare-lidar-update-rates.py)** — replay one recorded drive at three scan rates, map each, and quantify map quality (coverage, wall sharpness, trajectory drift) with a metric and a matplotlib plot. Runnable. (~60 min)

## How to work the exercises

- Have your **Week 3 robot** spawning in Gz Sim and your **Week 6 odometry node** running before you start. `ros2 topic hz /scan` should show a steady LiDAR rate and `ros2 run tf2_ros tf2_echo odom base_link` should print a transform that updates as you drive. If `/scan` is empty, fix the LiDAR sensor first — `slam_toolbox` with no scans does nothing and prints nothing useful.
- **Source your overlay in every new terminal:** `source /opt/ros/jazzy/setup.bash` then `source install/setup.bash`. Half of all "node not found" pain is an unsourced terminal — true in Week 5, still true now.
- **Set `use_sim_time: True` on every node.** This is the number-one simulation SLAM bug (Lecture 2, §2.3): one node on wall time while the rest are on sim time makes every TF lookup fail silently and the map never builds. Audit your launch files before you run them.
- **Read REP-105 before you touch frames.** `slam_toolbox` publishes `map → odom`; your odometry publishes `odom → base_link`. If `base_link` has two parents in `view_frames`, you have a duplicate publisher — kill it.
- **Watch a loop close before you save.** A map saved before any loop closure is just scan-matched odometry — it drifts. Drive a full loop, watch the map snap in RViz, *then* save. A map claim with zero loop closures is not an engineering artifact.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your numbers do not match the *shape* of the expected output (exact values depend on your robot, world, and drive), you are not done.

## Running the Python exercises

The two `.py` files are standalone — no extra `colcon` package required for the exercise itself (the mini-project packages everything properly). Source ROS2 Jazzy and run them directly:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-02-save-and-restart-in-localization.py
```

Each file's header explains what to launch alongside it (the Gz Sim robot and `slam_toolbox`, or the bag fallback) and how to verify the result. Exercise 2 expects exercise 1's mapping run to be live (so there is a graph to serialize); exercise 3 expects a recorded bag of one drive (it documents how to record one).

## A note on ground truth and worlds

In simulation you have a luxury you will never have on hardware: **perfect ground truth.** Gz Sim's pose-info topic (bridged through `ros_gz_bridge`) gives you the robot's true trajectory, so you can put a *number* on how far your SLAM pose strays from truth — not just "the map looks right." Use it shamelessly this week; on hardware you would substitute a motion-capture rig or a surveyed point, but the metric (absolute pose error, closure consistency) is identical.

The exercises need a **multi-room world** with at least one true loop (a corridor that returns to a room you have already mapped). Exercise 1 ships a small SDF world (`crunch_rooms.sdf`) you can drop into your Week 3 Gz Sim launch; if you have your own multi-room world, use it, as long as it has a genuine loop. A world that is a single open room has no loop to close and teaches you nothing about the thing that makes SLAM work.

There are no solutions checked in for exercises 2 and 3 — the course is open source and solutions live in forks. Exercise 1 includes its launch files, parameter file, and world inline because it is the load-bearing setup the rest of the week depends on. After you finish, search GitHub for `c24-week-07` to compare approaches.

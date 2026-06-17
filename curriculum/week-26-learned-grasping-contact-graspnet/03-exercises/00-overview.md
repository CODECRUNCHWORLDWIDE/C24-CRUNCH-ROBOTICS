# Week 26 — Exercises

Three focused drills that build the learned-grasping pipeline bottom-up. Each takes 30–60 minutes. Do them in order — exercise 3 plans against the poses you produce in 1 and 2. Run everything against your **week-23 MoveIt2 arm** and **week-14 RGB-D camera** in Gz Sim (or, where noted, against the synthetic cloud each exercise provides so you can work without the full sim up).

## Index

1. **[Exercise 1 — Reconstruct a grasp pose from raw outputs](./exercise-01-pose-reconstruction.md)** — given the network's `(contact, approach, baseline, width)`, assemble the `4x4 SE(3)` gripper transform, verify it is orthonormal, and overlay the gripper mesh in rviz2. (~45 min, guided)
2. **[Exercise 2 — Grasp inference and ranking](./exercise-02-grasp-inference.py)** — load a Contact-GraspNet checkpoint, run it on a point cloud, threshold by confidence, reconstruct poses, and apply grasp NMS to get a ranked shortlist. (~50 min, runnable)
3. **[Exercise 3 — The pick pipeline](./exercise-03-pick-pipeline.py)** — transform grasps to the planning frame, IK-filter the ranked list, and build the pre-grasp / approach / lift sequence for MoveIt2. (~45 min, runnable)

## How to work the exercises

- Have your **week-23 arm** planning to pose goals and your **week-14 camera** publishing synchronized color + depth + `camera_info` before you start. If the sim is down, every exercise ships a synthetic cloud or a stub so you can still make progress.
- The two `.py` files run **without a GPU** (CPU inference is slow but works) and **without the full checkpoint** (each ships a tiny randomly-initialized model so the *shapes and the pipeline* run end to end; swap in the real checkpoint when you have it).
- **Look at the cloud before you trust the grasp.** Every grasp failure this week starts as a cloud you did not inspect. Open it in Open3D first.
- **Units are meters.** Depth from RealSense/sim is often millimeters. The first thing to check when a grasp is 1000× off is the depth scale.
- Each runnable exercise ends with an **expected output** block. If your output doesn't match the *shape* (the exact numbers vary with the random init), you're not done.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package required for the inference/geometry parts. Source ROS2 Jazzy (for the message types) and run them directly:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-02-grasp-inference.py
```

Exercise 3's MoveIt2 calls degrade gracefully to a stub if `moveit_py` isn't importable, so you can develop the IK-filter and sequence logic without a live `move_group`. The file header explains the stub.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-26` to compare.

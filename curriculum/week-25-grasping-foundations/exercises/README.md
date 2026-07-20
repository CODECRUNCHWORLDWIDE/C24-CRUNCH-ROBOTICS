# Week 25 — Exercises

Three focused drills that build a grasp from the geometry up. Each takes 30–60 minutes. Do them in order — exercise 3 turns the candidates from exercise 2 into a pose, using the force-closure intuition from exercise 1. Exercise 1 is pen-and-paper-then-code; exercises 2 and 3 are runnable Python on a synthetic or real cloud.

## Index

1. **[Exercise 1 — Force closure by hand](exercise-01-force-closure-by-hand.md)** — determine, with the friction cone, whether four 2D grasps achieve force closure; then check your hand answers against a tiny `force_closure_2d` function. Build the intuition before you trust the code. (~45 min, guided)
2. **[Exercise 2 — The antipodal sampler](exercise-02-antipodal-sampler.py)** — sample antipodal contact pairs on a tabletop point cloud, score them with the friction-cone test, filter by gripper width, and print a ranked top-10. (~50 min, runnable)
3. **[Exercise 3 — Grasp to pose](exercise-03-grasp-to-pose.py)** — turn an antipodal pair into a gripper-frame SE(3) grasp pose with a standoff, and emit a `PoseStamped` ready for MoveIt2. (~45 min, runnable)

## How to work the exercises

- Have **Open3D** and **NumPy** installed: `pip install open3d numpy scipy`. Exercise 2 ships a synthetic-cloud generator so you can run it with no depth camera; if you have a RealSense capture or a Gz Sim cloud, point it at that instead.
- **Do Exercise 1 with pen and paper first**, then run the code. The whole point is that the friction-cone verdict is something you can compute in your head before you trust a function — that intuition is what lets you debug a grasp at 3 a.m.
- For Exercises 2 and 3, **visualize**. Open3D's `draw_geometries` and rviz2 markers are the fastest way to see whether a "high-scoring" grasp is actually sane. A grasp that looks wrong on screen is wrong, whatever the score says.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output's *shape* doesn't match (a ranked list with pose, width, score), you're not done.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package required. Run them directly:

```bash
pip install open3d numpy scipy
python3 exercise-02-antipodal-sampler.py            # uses a synthetic cloud by default
python3 exercise-02-antipodal-sampler.py --cloud my_capture.pcd   # or your own
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-25` to compare.

# Week 1 — Exercises

Three focused drills that take the rotation math out of the lecture and into your fingers, then onto your screen. Each takes 30–60 minutes. Do them in order — exercise 3 publishes the quaternion you implement in exercise 2, which builds on the hand math from exercise 1.

## Index

1. **[Exercise 1 — Rotate a vector three ways, by hand](exercise-01-rotation-by-hand.md)** — rotate a vector by a matrix, by Rodrigues axis-angle, and by a quaternion, on paper, and confirm all three agree in NumPy. (~50 min, guided)
2. **[Exercise 2 — The quaternion toolkit](exercise-02-quaternion-toolkit.py)** — implement `quat_mul`, `quat_conjugate`, `quat_rotate`, `quat_to_matrix`, and `axis_angle_to_quat` from scratch, and test every one against `scipy`. (~60 min, runnable)
3. **[Exercise 3 — The PoseStamped publisher](exercise-03-pose-publisher.py)** — a 50 Hz `PoseStamped` publisher whose orientation tumbles, built on your own quaternion math, ready to visualize in rviz2. (~45 min, runnable)

## How to work the exercises

- Have **NumPy and SciPy** installed: `pip install numpy scipy` (or `apt install python3-numpy python3-scipy`). The `.py` exercises import both.
- For exercise 3 you need **ROS2 Jazzy sourced**: `source /opt/ros/jazzy/setup.bash`. The first two exercises are pure Python and need no ROS.
- **Verify against the reference, always.** Every exercise ends by comparing your hand math to `scipy.spatial.transform.Rotation`. If `np.allclose(...)` fails, you have a bug isolated to your code — that's the point.
- Mind the **quaternion convention**: this course writes `(w, x, y, z)` in math, but `scipy` and `geometry_msgs/Quaternion` use `(x, y, z, w)`. Write it on a sticky note. A swapped scalar component is the single most common bug here.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match, you're not done.

## Running the Python exercises

The first two `.py` files are standalone — no ROS, no colcon. Run them directly:

```bash
python3 exercise-02-quaternion-toolkit.py
```

Exercise 3 is a ROS2 node; run it standalone with ROS2 sourced (no package required for the quick path):

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-03-pose-publisher.py
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-01` to compare.

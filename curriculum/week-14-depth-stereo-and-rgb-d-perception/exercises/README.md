# Week 14 — Exercises

Three focused drills that take you from "the camera is plugged in" to "I have a metric, filtered, trustworthy point cloud." Each takes 30–60 minutes. Do them in order — exercise 2 projects the synchronized streams from exercise 1, and exercise 3 filters the depth you learned to project. Run everything against a **RealSense D435i** if you have one, or the **simulated RGB-D camera** (Path B) on your week-3 robot, or the **recorded bag** the resources point to.

## Index

1. **[Exercise 1 — Bring up and synchronize](exercise-01-bringup-and-synchronize.md)** — launch the RGB-D camera (real or sim), set the correct sensor QoS on color, depth, and IMU, verify every stream with `ros2 topic info -v`, and synchronize color+depth+info with `message_filters`. Prove the streams are time-aligned. (~50 min, guided)
2. **[Exercise 2 — Depth to point cloud](exercise-02-depth-to-pointcloud.py)** — project a depth image into a metric `PointCloud2` by hand with the intrinsics, mask invalid pixels, stamp with the acquisition time, and verify your cloud against `depth_image_proc` point-for-point. (~50 min, runnable)
3. **[Exercise 3 — Temporal filter A/B](exercise-03-temporal-filter-ab.py)** — run the depth temporal filter on vs. off against a known flat plane and quantify the noise reduction with an RMS flatness metric, so you can state the cost/benefit in numbers. (~45 min, runnable)

## How to work the exercises

- Have the camera (or sim, or bag) **publishing before you start**. `ros2 topic hz /camera/depth/image_rect_raw` should show ~30 Hz. If it doesn't, fix the bring-up first.
- **Read `ros2 topic info -v` on every stream.** Depth, color, and IMU are sensor streams — they must be `BEST_EFFORT`. A `RELIABLE` subscriber against them silently receives nothing (Week 5). This is the #1 "the camera doesn't work" cause, and it's a QoS bug, not a camera bug.
- **Always read `image.encoding` before reading depth.** `16UC1` is millimetres; `32FC1` is metres. Branch on it; never assume. This is the #2 cause of wrong clouds.
- When a cloud looks wrong, run the **RGB-D debugging decision tree** from Lecture 2 §6 before you touch the math. Sideways → optical-frame TF. 1000× off → unit bug. Slab at origin → unmasked holes. Smeared color → unsynced or unaligned.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match, you're not done.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package required. Source ROS2 Jazzy and run them directly:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-02-depth-to-pointcloud.py
```

Both ship a **`--demo` mode** that synthesizes a depth image of a known scene (a flat floor + a wall + a box) so you can verify the *projection and filter logic* with no camera, sim, or bag — then point the same script at your live `/camera/...` topics to run it for real. Instructions are in each file's header.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-14` to compare.

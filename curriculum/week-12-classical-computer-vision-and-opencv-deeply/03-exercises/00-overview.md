# Week 12 — Exercises

Three drills on real images and real geometry. Each takes 40–60 minutes. Do them in order — Exercise 2 (ORB + RANSAC) and Exercise 3 (optical flow) both assume the calibrated-camera mental model from Exercise 1. Exercise 1 wants a real or Gz Sim camera; Exercises 2 and 3 are standalone — they synthesize their own images so they run with nothing but OpenCV.

## Index

1. **[Exercise 1 — Calibrate a camera](./exercise-01-calibrate-a-camera.md)** — collect checkerboard views from a real USB camera or your Gz Sim camera, run `cv2.calibrateCamera`, read the reprojection error, and undistort an image so straight lines stay straight. (~55 min, guided)
2. **[Exercise 2 — ORB matching with RANSAC outlier rejection](./exercise-02-orb-match-ransac.py)** — detect ORB features on two views of a synthetic scene, match with the ratio test, reject outliers with a RANSAC homography, and confirm a healthy inlier ratio. (~45 min, runnable)
3. **[Exercise 3 — Lucas-Kanade flow and velocity from flow](./exercise-03-lk-flow-velocity.py)** — track features across a synthetic forward-drive sequence with pyramidal LK, and estimate the forward velocity from the flow field alone. (~50 min, runnable)

## How to work the exercises

- Install OpenCV once: `pip install opencv-python numpy matplotlib` (use `opencv-python-headless` on a server with no display). The runnable exercises don't need a window — they print numbers and optionally save images.
- For Exercise 1, have a **checkerboard** (printed 9×6 inner-corner, or the Gz Sim textured plane) and know its **square size in meters** — calibration needs it for metric scale.
- **Read the "the geometry closed" promise from the week README before you start.** For calibration it's a reprojection error < 0.5 px; for matching it's a RANSAC inlier ratio above ~50%. If your numbers don't land there, you're not done — and the *bad* number is the lesson.
- Each runnable exercise (`.py`) ends with an **expected output** block. The synthetic scenes are deterministic (fixed seed), so your numbers should land in the stated range; if they're wildly off, debug before moving on.

## Running the Python exercises

The two `.py` files are standalone — no ROS, no camera:

```bash
pip install opencv-python numpy matplotlib
python3 exercise-02-orb-match-ransac.py
python3 exercise-03-lk-flow-velocity.py
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-12` to compare.

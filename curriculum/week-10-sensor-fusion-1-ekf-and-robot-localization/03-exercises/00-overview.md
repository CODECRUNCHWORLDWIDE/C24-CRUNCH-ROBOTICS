# Week 10 — Exercises

Three focused drills that take the Kalman filter from theory to a fused estimate on your robot. Each takes 30–60 minutes. Do them in order — exercise 3 (the real fusion) is far easier once you've internalized the covariance bookkeeping in exercise 2 and the config reading in exercise 1.

## Index

1. **[Exercise 1 — Read an EKF config](./exercise-01-read-an-ekf-config.md)** — given a real `ekf.yaml`, predict exactly what it fuses, which TF it publishes, and which footgun (if any) it contains — before running anything. (~45 min, guided)
2. **[Exercise 2 — The scalar Kalman filter](./exercise-02-scalar-kalman.py)** — implement a 1-D Kalman filter from scratch and watch the covariance shrink on update and grow on predict, verified against a known signal. (~60 min, runnable)
3. **[Exercise 3 — Fuse odom + IMU](./exercise-03-fuse-odom-imu.py)** — a `robot_localization` launch + config harness and a drift-comparison subscriber that measures fused vs. raw over a trajectory. (~60 min, runnable)

## How to work the exercises

- Have **`robot_localization` installed**: `sudo apt install ros-jazzy-robot-localization`. Exercises 1 and 3 use it.
- Have your **Week 6 wheel odometry** (`/odom` with an honest covariance) and **Week 9 calibrated IMU** (`/imu/data_calibrated`) running — exercise 3 fuses them.
- **Check `R` before you tune `Q`.** Echo `/odom`'s `pose.covariance` and the IMU's `angular_velocity_covariance`. Zeros are a lie; the EKF chokes on them.
- **`view_frames` is your friend.** After launching the EKF, run `ros2 run tf2_tools view_frames` and confirm exactly one publisher of `odom→base_link`. The #1 bug this week is two publishers.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match, you're not done.

## Running the Python exercises

Exercise 2 is standalone (NumPy + Matplotlib, no ROS):

```bash
python3 exercise-02-scalar-kalman.py
```

Exercise 3 is a ROS2 harness; source ROS2 and your robot's overlay:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
python3 exercise-03-fuse-odom-imu.py     # see the file header for the launch sequence
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-10` to compare.

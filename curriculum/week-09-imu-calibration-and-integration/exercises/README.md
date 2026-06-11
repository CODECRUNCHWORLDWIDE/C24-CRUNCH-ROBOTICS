# Week 9 — Exercises

Three focused drills that take IMU calibration from theory to a calibrated stream. Each takes 30–60 minutes. Do them in order — exercise 3 (the bias node) uses the bias estimate you learn to read in exercises 1 and 2.

## Index

1. **[Exercise 1 — Read an Allan plot](exercise-01-read-an-allan-plot.md)** — given a real Allan-deviation plot, identify the random walk (−½ slope), the bias instability (flat floor), and the rate random walk (+½ slope), and read off `N` and `B`. (~45 min, guided)
2. **[Exercise 2 — Compute the Allan variance](exercise-02-allan-variance.py)** — implement the overlapping Allan deviation from a stationary log, plot it, and extract `N` and `B` — verified against a synthetic signal with known parameters. (~60 min, runnable)
3. **[Exercise 3 — The bias-subtraction node](exercise-03-bias-subtraction-node.py)** — a `rclpy` node that estimates the stationary gyro/accel bias and re-publishes a calibrated `/imu/data_calibrated`, with honest covariance. (~60 min, runnable)

## How to work the exercises

- Have **NumPy and Matplotlib**: `pip install numpy matplotlib`. Exercise 3 also needs **ROS2 Jazzy sourced**.
- For exercises with real data, record a **30-minute stationary IMU log** first: `ros2 bag record /imu/data` with the robot truly still. If you don't have hardware, exercise 2 generates a *synthetic* signal with known `N` and `B` so you can verify your computation without a robot.
- **Verify against known-truth.** Exercise 2's synthetic signal has parameters you set, so your extracted `N` and `B` must match them — that's the check that your Allan code is right before you trust it on real data.
- **"Stationary" must be real** for the bias node. Vibration or a bump corrupts the bias estimate; the drift test in the challenge is how you catch it.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match, you're not done.

## Running the Python exercises

Exercise 2 is standalone (NumPy + Matplotlib, no ROS):

```bash
python3 exercise-02-allan-variance.py
```

Exercise 3 is a ROS2 node; run it standalone with ROS2 sourced:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-03-bias-subtraction-node.py
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-09` to compare.

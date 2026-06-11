# Week 6 — Exercises

Three exercises that build on each other into the mini-project. Do them in order — exercise 2 publishes the `/odom` and TF that exercise 3 records, and the mini-project is the production-grade version of all three. Run everything against your **Week 3 differential-drive robot** in Gz Sim Harmonic (or, if your sim is down, the standalone joint-state publisher each exercise ships as a fallback).

## Index

1. **[Exercise 1 — Diff-drive forward kinematics by hand](exercise-01-diff-drive-forward-kinematics.md)** — implement `vₓ = r(φ̇_R+φ̇_L)/2` and `ω = r(φ̇_R−φ̇_L)/L` in an `rclpy` node that consumes `/joint_states`, with starter code, a solution, and an expected-output block. Guided. (~75 min)
2. **[Exercise 2 — Publish `/odom` and the `odom → base_link` TF](exercise-02-odom-and-tf-publisher.py)** — integrate the body twist with the exact-arc integrator, fill a `nav_msgs/Odometry` message with honest covariance, and broadcast the `odom → base_link` transform. Runnable. (~60 min)
3. **[Exercise 3 — Drive the square, log the drift](exercise-03-drive-square-and-measure-drift.py)** — open-loop drive a 10×10 m square at three speeds, log your `/odom` against Gz Sim ground truth, compute closure error, and print it as a fraction of path length. Runnable. (~60 min)

## How to work the exercises

- Have your **Week 3 robot** spawning in Gz Sim before you start. `ros2 topic echo /joint_states` should show the two wheel joints with nonzero `velocity` (or `position`) when you drive it. If it does not, each `.py` exercise ships a standalone `JointState` publisher you can run instead.
- **Source your overlay in every new terminal:** `source install/setup.bash` (and `source /opt/ros/jazzy/setup.bash` first). Half of all "node not found" pain is an unsourced terminal — this was true in Week 5 and it is still true.
- **Read REP-103 and REP-105 before you touch frames.** The single most common Week 6 bug is a frame-convention error: `x` is forward, `z` is up, yaw is counter-clockwise-positive, `odom → base_link` is published by *you* and must be continuous. Get this wrong and your robot drives backwards in RViz.
- **Echo before you trust.** `ros2 topic echo /odom --once` and `ros2 run tf2_tools view_frames` are your ground truth. Confirm the message populates and the TF tree has `odom → base_link` singly-parented before you measure anything.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your numbers do not match the *shape* of the expected output (the exact values depend on your robot and your drive), you are not done.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package required for the exercise itself (the mini-project packages them properly). Source ROS2 Jazzy and run them directly:

```bash
source /opt/ros/jazzy/setup.bash
python3 exercise-02-odom-and-tf-publisher.py
```

Each file's header explains what to launch alongside it (the Gz Sim robot, or its own fallback publisher) and how to verify the result. Exercise 3 expects exercise 2's node to be running and publishing `/odom`.

## A note on ground truth

In simulation you have a luxury you will never have on hardware: **perfect ground truth.** Gz Sim's `OdometryPublisher` (or the model pose from `/world/<name>/dynamic_pose/info`, bridged through `ros_gz_bridge`) gives you the robot's true pose. Use it shamelessly this week — the entire point is to compare your *drifting* wheel odometry against the *true* trajectory and put a number on the gap. On hardware you would substitute a motion-capture system, a total station, or a tape-measured closure point; the metric (closure error as a fraction of path length) is identical.

There are no solutions checked in for exercises 2 and 3 — the course is open source and solutions live in forks. Exercise 1 includes its solution inline because it is the load-bearing derivation the rest of the week depends on. After you finish, search GitHub for `c24-week-06` to compare approaches.

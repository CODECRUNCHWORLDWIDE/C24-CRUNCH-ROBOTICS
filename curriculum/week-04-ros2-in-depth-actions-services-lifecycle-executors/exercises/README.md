# Week 4 — Exercises

Three exercises, in order. They build on each other: Exercise 1 gets the decision ladder into your hands and a service working; Exercise 2 writes the `Spin90` action server with closed-loop IMU yaw and preemption; Exercise 3 takes that server and runs it under a multi-threaded executor with the callback-group fix, after first reproducing the cancel deadlock so you feel it.

Do them in order. Do not skip Exercise 1 because it "looks easy" — the classification table is the part of this week you will be asked to defend in a design review, and the `ResetOdometry` service is the dependency the challenge and mini-project assume you can write in your sleep.

| # | File | Type | What you build | Est. time |
|---|------|------|----------------|-----------|
| 1 | [exercise-01-decision-ladder-and-service.md](./exercise-01-decision-ladder-and-service.md) | Guided (Markdown) | Classify ten problems on the topic→service→action→BT ladder, then write a `ResetOdometry` service server + async client in `rclpy`. | 90 min |
| 2 | [exercise-02-spin90-action-server.py](./exercise-02-spin90-action-server.py) | Runnable (`rclpy`) | A `Spin90` action server: subscribe to `/imu`, run a closed-loop proportional controller on heading error, publish `/cmd_vel`, stream feedback, honor a cancel mid-rotation, return the correct terminal status, and stop the robot on every exit path. | 120 min |
| 3 | [exercise-03-multithreaded-executor.py](./exercise-03-multithreaded-executor.py) | Runnable (`rclpy`) | Reproduce the single-threaded cancel deadlock, then fix it: run the server under a `MultiThreadedExecutor` with a `MutuallyExclusiveCallbackGroup` for execute and a `ReentrantCallbackGroup` for the cancel + IMU path. Includes a self-checking client that asserts the cancel takes effect in bounded time. | 120 min |

## Prerequisites for all three

- ROS2 Jazzy on Ubuntu 24.04, sourced (`source /opt/ros/jazzy/setup.bash`).
- The Week 3 differential-drive robot spawning in Gz Sim and publishing `sensor_msgs/Imu` on `/imu`, accepting `geometry_msgs/Twist` on `/cmd_vel`. If Gz Sim is not handy, the exercises include a `--fake-imu` flag that integrates a synthetic yaw from the commanded `cmd_vel`, so you can run them headless.
- A `colcon` workspace with a `crunch_motion_interfaces` package containing the `.action` and `.srv` files (the exercise files tell you exactly what to put in it and how to build it).

## How to run a `.py` exercise

These files are written to run two ways:

1. **Inside a colcon package** (the real way): drop the file into a `crunch_motion/` package's module directory, add an entry point in `setup.py`, `colcon build`, source, and `ros2 run crunch_motion <node>`.
2. **Standalone for fast iteration**: `python3 exercise-02-spin90-action-server.py --fake-imu`. The action and service interfaces still need to be built once into `crunch_motion_interfaces` and on your `PYTHONPATH`; everything else runs without a launch file.

Each file's header block has the exact commands.

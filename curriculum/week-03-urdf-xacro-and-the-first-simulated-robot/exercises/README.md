# Week 3 — Exercises

Three exercises that build, in order, the skills the mini-project assembles. Do them in sequence — Exercise 2 spawns the robot you built in Exercise 1, and Exercise 3 drives it.

## Index

1. **[Exercise 1 — Build the diff-drive body](exercise-01-build-the-diff-drive-body.md)** — author a chassis, two driven wheels, and two casters in xacro, with correct visual, collision, and inertial blocks. Visualize it in rviz2 and parse it with `check_urdf`. (~90 min)
2. **[Exercise 2 — Add a LiDAR and an IMU](exercise-02-add-lidar-and-imu.py)** — add the two sensor plugins, bridge their topics, and run a `rclpy` verifier node that asserts `/scan` and `/imu` are alive, at-rate, and well-formed. (~60 min)
3. **[Exercise 3 — Spawn and drive](exercise-03-spawn-and-drive.py)** — a `rclpy` node that drives the spawned robot in a 1 m square using `/cmd_vel` and `/odom`, and confirms it actually moved. (~60 min)

## How to work the exercises

- **Type the XML and the code yourself.** Copy-pasting a URDF teaches you nothing; the muscle memory of writing `<inertial>` blocks is the point.
- Build your workspace and source it every time you change a file in an installed package: `colcon build && source install/setup.bash`.
- Every exercise ends with a smell test — `check_urdf`, `ros2 topic hz`, or the robot visibly moving. If the smell test fails, the exercise is not done.
- Run every node and the simulator with `use_sim_time:=true`. Forgetting this is the single most common reason "everything looks right but tf2 throws."
- If you get stuck for more than 15 minutes, read the hints at the bottom of each file. Then read Lecture 1 §1.7 (the explode-on-spawn differential) — most stuck-points this week are an inertia or a joint-name bug.

## Prerequisites for all three

```bash
sudo apt install -y ros-jazzy-ros-gz ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher liburdfdom-tools
gz sim --version          # Gazebo Sim 8.x (Harmonic)
ros2 pkg list | grep ros_gz
```

You should have a `colcon` workspace (e.g. `~/crunch_ws/src/`) ready. Exercise 1 creates a `crunchbot_description` package inside it that Exercises 2 and 3 — and the mini-project — extend.

There are no solutions checked in. The course is open source; solutions live in forks. After you finish, search GitHub for `c24-week-03` to compare.

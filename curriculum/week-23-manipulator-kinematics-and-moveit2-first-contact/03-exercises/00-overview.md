# Week 23 — Exercises

Three drills that take you from kinematics-on-paper to a moving arm. Do them in order — exercise 2 reuses the FK and Jacobian you build in exercise 1, and exercise 3 sends goals to the MoveIt2 setup you bring up Thursday. Run everything against a **UR5e** (or your MyCobot 280) in MoveIt2 + Gz Sim; the math exercises also run standalone with no robot.

## Index

1. **[Exercise 1 — Forward kinematics by hand](./exercise-01-forward-kinematics.md)** — build the UR5e product-of-exponentials FK from the URDF, verify it against `tf2_echo` and the MoveIt2 `/compute_fk` service to numerical precision. (~60 min, guided)
2. **[Exercise 2 — Damped-least-squares IK from scratch](./exercise-02-damped-least-squares-ik.py)** — implement the DLS solver from Lecture 2, run it through a singular pose, and watch the damping keep it stable where the naive pseudoinverse diverges. (~50 min, runnable, standalone)
3. **[Exercise 3 — The pose-goal driver](./exercise-03-pose-goal-driver.py)** — a `rclpy` node that consumes `geometry_msgs/PoseStamped` from a topic and triggers a MoveIt2 plan-and-execute through the action interface, with the failed-plan path handled honestly. (~50 min, runnable, needs MoveIt2)

## How to work the exercises

- Bring up your **MoveIt2 arm** before Exercise 3. The exercise README's "bring-up" section walks the `ur_moveit_config` launch; confirm RViz shows the arm and you can drag-and-plan before you drive it from code.
- Source your overlay in every new terminal: `source install/setup.bash`. Half of all "node not found" pain is an unsourced terminal.
- For the math exercises (1 and 2), **`tf2_echo` and `/compute_fk` are your ground truth.** Your hand-built FK must agree with MoveIt2's; if it doesn't, you have a screw-axis or home-config bug, and finding it is the point.
- When a plan-and-execute fails, **read the `error_code.val` before you touch anything** (Lecture 2 §5.5). `-7` → reachability, `-2` → planning scene, `-4` → controllers. One number, one direction to look.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match the *shape*, you're not done.

## Running the Python exercises

Exercise 2 is pure NumPy — no ROS required:

```bash
python3 exercise-02-damped-least-squares-ik.py
```

Exercise 3 needs ROS2 Jazzy and a running `move_group`:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
# Terminal 1: bring up the MoveIt2 arm (see exercise-01 for the launch).
ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur5e
# Terminal 2: the driver, then publish a pose.
python3 exercise-03-pose-goal-driver.py
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-23` to compare.

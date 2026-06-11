# Week 8 — Exercises

Three exercises that build directly toward the mini-project. Unlike most weeks, these are not independent drills — they are the scaffolding of the `crunchbot_bringup` package. Do them in order; exercise 2 uses the package exercise 1 created, and exercise 3 times the bring-up exercise 2 produced.

## Index

1. **[Exercise 1 — Package weeks 3–7 into one bringup package](exercise-01-package-weeks-3-7.md)** — guided. Create the `crunchbot_bringup` package, lay out its directories, write `setup.py`, and migrate your week-3 URDF, week-6 odometry config, and week-7 `slam_toolbox` config into it. Ends with a single top-level launch file skeleton. (~90 min)
2. **[Exercise 2 — The top-level bring-up launch file](exercise-02-bringup-launch.py)** — runnable. A complete, correct top-level `robot.launch.py` that composes robot + sensors + `slam_toolbox` + `rviz2` with a saved layout, gated by arguments. Fill in three marked sections, then bring the robot up with one command. (~75 min)
3. **[Exercise 3 — Map a new world and time the run](exercise-03-map_a_new_world.py)** — runnable. A `rclpy` "map-run timer" node that watches for the first map message and the map-save service call, and reports the wall-clock duration of an end-to-end mapping run. Use it to time mapping a brand-new world. (~60 min)

## How to work the exercises

- Read the prompt. Skim, don't memorize.
- **Type the code yourself.** Do not copy-paste. The launch-substitution syntax in particular only sticks through your fingers.
- Build with `colcon build --packages-select crunchbot_bringup --symlink-install` and source `install/setup.bash` before every run.
- Run it. Watch the terminal. When a node dies, read *its* output — `output='screen'` exists so you can.
- Verify every bring-up with the three-command check: `ros2 node list`, `ros2 topic list`, `ros2 run tf2_tools view_frames`.
- If you get stuck for more than 10 minutes, peek at the hints at the bottom of each file.

## The acceptance bar for every exercise

Every exercise ends with the same promise from the week README — the robot comes up with **one command**, the TF tree is connected and rooted at `map` with no duplicate broadcasters, and `ros2 doctor` reports no QoS mismatches. If your bring-up needs a second terminal or a forgotten `ros2 run`, you are not done.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-08` to compare.

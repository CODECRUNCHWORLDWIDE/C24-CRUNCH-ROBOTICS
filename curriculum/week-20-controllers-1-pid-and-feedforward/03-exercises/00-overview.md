# Week 20 — Exercises

Three focused drills that build control intuition in your fingers. Each takes 30–60 minutes. Do them in order — exercise 3 reuses the controller you harden in exercises 1 and 2. The first two are pure-Python simulations (no robot needed); the third runs against your **week-3 differential-drive robot** in Gz Sim (with a simulated-plant fallback if your sim is broken).

## Index

1. **[Exercise 1 — Step response and tuning](./exercise-01-step-response-and-tuning.md)** — tune a PID for a second-order plant to hit a step-response spec, and read rise time, overshoot, and settling off the plot. Confirm the second-order formulas predict what you see. (~45 min, guided)
2. **[Exercise 2 — Anti-windup and derivative kick](./exercise-02-antiwindup-and-derivative-kick.py)** — reproduce integrator wind-up and derivative kick on purpose, then fix both with back-calculation and derivative-on-measurement. The simulation prints PASS only when both are fixed. (~45 min, runnable)
3. **[Exercise 3 — Yaw-rate PID on the robot](./exercise-03-yaw-rate-pid.py)** — a closed-loop yaw controller consuming IMU yaw and emitting `/cmd_vel`, with velocity feedforward, tuned to three step targets. (~50 min, runnable)

## How to work the exercises

- For Exercises 1 and 2 you need only `python3`, `numpy`, `scipy`, and `matplotlib`. No ROS, no robot. `pip install numpy scipy matplotlib` if you don't have them.
- For Exercise 3, have your **week-3 robot** spawning in Gz Sim before you start. `ros2 topic echo /imu/data` should show data and `ros2 topic pub /cmd_vel ...` should move the robot. If it doesn't, the built-in plant simulator in Exercise 3 is your fallback — every learning objective still lands.
- **Always plot.** Controls intuition is built by perturbing a gain and watching the response change. Run the step, change one gain, run it again, look at the two plots side by side. Do this dozens of times. It is the entire skill.
- When a response is wrong, name the symptom (overshoot? offset? chatter? slow?) and the gain that owns it (Lecture 2 §2.1's symptom→gain map) *before* you change anything.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match the *shape* (the exact numbers depend on your machine and timing), you're not done.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package required:

```bash
python3 exercise-02-antiwindup-and-derivative-kick.py
# Exercise 3 wants ROS sourced for the robot path, but falls back to a built-in
# simulator if rclpy import or the sim is unavailable:
source /opt/ros/jazzy/setup.bash
python3 exercise-03-yaw-rate-pid.py --sim    # force the built-in plant simulator
python3 exercise-03-yaw-rate-pid.py          # use the real robot over /imu/data + /cmd_vel
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-20` to compare.

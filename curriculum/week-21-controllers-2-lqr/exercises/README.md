# Week 21 — Exercises

Three focused drills that take you from a blank state-space model to an LQR controller racing the PID. Each takes 30–60 minutes. Do them in order — exercise 3 uses the gain you solve for in exercises 1 and 2. The first two are pure-Python (no robot needed); the third runs against your **week-3 differential-drive robot** in Gz Sim (with a simulated-plant fallback).

## Index

1. **[Exercise 1 — Controllability and Q/R design](exercise-01-controllability-and-qr-design.md)** — build the diff-drive path-tracking `A`/`B`, test controllability (and watch it fail at zero speed), and design `Q`/`R` with Bryson's rule. (~45 min, guided)
2. **[Exercise 2 — Solve and simulate LQR](exercise-02-solve-and-simulate-lqr.py)** — solve the algebraic Riccati equation for `K`, run the three sanity checks, simulate the closed loop, and cross-check against `python-control`. (~45 min, runnable)
3. **[Exercise 3 — LQR vs PID on a curve](exercise-03-lqr-vs-pid-tracking.py)** — an LQR path-tracking controller against the Week-20 PID on a curved trajectory, with cross-track and heading error quantified for both. (~50 min, runnable)

## How to work the exercises

- For Exercises 1 and 2 you need `python3`, `numpy`, `scipy`, `matplotlib`, and `control` (`pip install numpy scipy matplotlib control`). No ROS, no robot.
- For Exercise 3, have your **week-3 robot** spawning in Gz Sim before you start. If it's broken, the built-in kinematic simulator in Exercise 3 is your fallback — every learning objective still lands.
- **Run the three sanity checks every time you solve.** Controllable? `P` positive-definite? Closed loop stable? A gain that fails any of these does not go on a robot. Make the checks a reflex.
- When the closed loop misbehaves, look at the **eigenvalues of `A − BK`** first — they tell you immediately whether the gain is stabilizing and how fast/oscillatory the response is.
- Change `Q` and watch `K` and the eigenvalues move. Controls intuition for LQR is built by sweeping the `Q/R` ratio and watching the closed-loop poles, the same way PID intuition is built by sweeping gains.
- Each runnable exercise (`.py`) ends with an **expected output** block. Match the *shape*; exact numbers depend on your `Q`/`R` choices.

## Running the Python exercises

```bash
python3 exercise-02-solve-and-simulate-lqr.py
source /opt/ros/jazzy/setup.bash
python3 exercise-03-lqr-vs-pid-tracking.py --sim    # built-in kinematic simulator
python3 exercise-03-lqr-vs-pid-tracking.py          # real robot over /odom + /cmd_vel
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-21` to compare.

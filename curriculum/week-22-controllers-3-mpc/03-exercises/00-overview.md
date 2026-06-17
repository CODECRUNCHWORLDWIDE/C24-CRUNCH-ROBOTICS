# Week 22 — Exercises

Three focused drills that take you from formulating an MPC on paper to profiling a deployable bicycle MPC. Each takes 30–60 minutes. Do them in order — exercise 3 builds on the constrained MPC you assemble in exercises 1 and 2. All three are pure-Python (`cvxpy`); the bicycle MPC in exercise 3 has a built-in simulator and an optional real-robot path.

## Index

1. **[Exercise 1 — MPC formulation](./exercise-01-mpc-formulation.md)** — formulate a double-integrator MPC on paper and in `cvxpy`, then verify that with no constraints and the LQR terminal cost it produces the *same* first input as last week's LQR. (~45 min, guided)
2. **[Exercise 2 — Constrained double-integrator MPC](./exercise-02-constrained-double-integrator-mpc.py)** — add hard velocity and acceleration constraints and watch them *bind*: the input saturates at the limit instead of overshooting it, exactly where LQR would have violated it. (~45 min, runnable)
3. **[Exercise 3 — Bicycle MPC tracking](./exercise-03-bicycle-mpc-tracking.py)** — a kinematic-bicycle MPC tracking a figure-8 with hard velocity and steering-rate limits, compared to LQR, with the solve time profiled against a control-period budget. (~50 min, runnable)

## How to work the exercises

- You need `python3`, `numpy`, `scipy`, `matplotlib`, and **`cvxpy`** (`pip install cvxpy`). `cvxpy` ships OSQP, which is the solver we use. No ROS required for the graded path.
- **Check `prob.status` every solve.** A solution from an `infeasible` solve is `None` — using it sends garbage to the robot. Make the status check a reflex, the way `ros2 topic info -v` was in Week 5.
- **Profile honestly.** When you measure solve time, report the p95 and max, not just the mean — a control loop has a hard deadline every period, and the tail is what misses it.
- The unconstrained-MPC-equals-LQR check (Exercise 1) is your single best correctness test. If your unconstrained MPC's first input doesn't match `−Kx` from last week, you have a bug — fix it before adding constraints.
- Each runnable exercise (`.py`) ends with an **expected output** block. Match the *shape*; exact numbers depend on your weights, horizon, and machine.

## Running the Python exercises

```bash
pip install cvxpy numpy scipy matplotlib
python3 exercise-02-constrained-double-integrator-mpc.py
python3 exercise-03-bicycle-mpc-tracking.py --profile   # profile the solve time
python3 exercise-03-bicycle-mpc-tracking.py             # plot the tracking
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-22` to compare.

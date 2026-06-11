# Week 11 — Exercises

Three drills, one per estimator. Each takes 40–60 minutes. Do them in order — Exercise 3 (the factor graph) assumes the filter-vs-smoother mental model that Exercises 1 and 2 build by contrast. Exercise 1 runs against your **Week 7 map** in Gz Sim; Exercises 2 and 3 are standalone NumPy/GTSAM and need no robot.

## Index

1. **[Exercise 1 — AMCL on your Week 7 map](exercise-01-amcl-on-your-map.md)** — bring up `nav2_amcl` against your saved map, initialize the particle cloud with `/initialpose`, watch it converge in rviz2, and force-then-recover the kidnapped-robot problem. (~60 min, guided)
2. **[Exercise 2 — UKF vs EKF on a range-bearing problem](exercise-02-ukf-vs-ekf.py)** — run a UKF and an EKF on the *same* nonlinear tracking problem; compare RMSE and NEES consistency; see the EKF go overconfident where the UKF stays honest. (~50 min, runnable)
3. **[Exercise 3 — Your first GTSAM factor graph](exercise-03-two-pose-factor-graph.py)** — build, solve, and check a two-pose graph against a hand calculation, then add a third pose and a loop closure. (~45 min, runnable)

## How to work the exercises

- For Exercise 1, have your **Week 7 map** (`map.yaml` + `map.pgm`) and the multi-room Gz Sim world ready. AMCL needs the map served *and* a robot that moves and scans. If your sim is broken, fix it first — there is no standalone fallback for a localization lab.
- For Exercises 2 and 3, install the Python deps once: `pip install numpy scipy matplotlib gtsam`. `gtsam` ships manylinux wheels for Python 3.12 on x86_64; on Apple Silicon use a Linux container or build from source.
- **Read the "the estimate converged" promise from the week README before you start.** For a filter it's a NEES inside its chi-squared band; for a factor graph it's a final error near zero matching your hand calc. If your numbers don't land there, you're not done.
- Each runnable exercise (`.py`) ends with an **expected output** block. The exact decimals depend on the random seed and your `gtsam` build, but the *shape* of the answer is invariant. If your output disagrees in shape, debug before moving on.

## Running the Python exercises

The two `.py` files are standalone — no ROS, no `colcon`:

```bash
pip install numpy scipy matplotlib gtsam
python3 exercise-02-ukf-vs-ekf.py
python3 exercise-03-two-pose-factor-graph.py
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-11` to compare.

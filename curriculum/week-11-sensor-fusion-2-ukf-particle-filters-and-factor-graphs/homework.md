# Week 11 Homework

Six problems that drive the week's three estimators into your fingers. The full set should take about **5 hours**. Work in your Week 11 Git repository (the same workspace as the exercises and the `crunch_posegraph` mini-project) so every problem produces at least one commit you can point to at the Phase 2 midterm in Week 16.

The headline deliverable is **Problem 4 — the filter-vs-smoother decision memo**, the artifact a reviewer reads to decide whether you actually understand *which estimator to reach for*. Treat it as a one-page engineering memo, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**. Install the Python deps once: `pip install numpy scipy matplotlib gtsam`. For Problem 1, have your Week 7 map and Gz Sim world ready.

---

## Problem 1 — Tune AMCL until it localizes, and document why

**Problem statement.** Take the AMCL setup from Exercise 1 and tune it to reliably localize on your Week 7 map. Specifically: starting from a deliberately wrong `/initialpose`, find `alpha1..alpha4`, `max_particles`, and `z_hit`/`z_rand` values that let AMCL converge within ~5 m of driving, *and* recover from one kidnapping. Record the parameter values and a one-paragraph rationale for each non-default choice in `notes/week-11/amcl-tuning.md`.

**Acceptance criteria.**

- `notes/week-11/amcl-tuning.md` records your final `amcl_params.yaml` values and a rationale for each `alpha`, the particle count, and the `z_*` weights.
- A screen capture (or described sequence) showing the `/particle_cloud` converging from scattered to tight after `/initialpose` + driving.
- A description of one successful kidnapped-robot recovery and the `recovery_alpha_*` values that made it work.
- Committed.

**Hint.** The `alpha` values should reflect your *actual* Week 6 odometry quality — if your sim odometry is clean, smaller alphas converge faster; if it slips, larger alphas keep the true pose covered. Too-small alphas are the most common reason "AMCL loses the robot on a turn."

**Estimated time.** 50 minutes.

---

## Problem 2 — Swap the EKF for a UKF in `robot_localization` and measure the difference

**Problem statement.** Your Week 10 launch file ran `robot_localization`'s `ekf_node`. The package ships a `ukf_node` with the *same configuration shape*. Duplicate your Week 10 config, point it at `ukf_node`, run both on the same recorded drive (same bag), and compare `/odometry/filtered` from each. Quantify whether the UKF changed the estimate meaningfully on *your* robot.

**Acceptance criteria.**

- A `ukf.yaml` config (a copy of your `ekf.yaml` with the node swapped) and a launch that runs the `ukf_node`.
- `notes/week-11/ekf-vs-ukf.md` with a plot or table comparing EKF and UKF filtered output (position drift over a fixed drive), and a one-sentence verdict: did the UKF matter here, and *why or why not* given your robot's nonlinearity?
- You correctly predict, before running, whether you expect a big difference (mild planar nonlinearity → probably not) and check your prediction.
- Committed.

**Hint.** On a flat diff-drive robot fusing odometry + IMU, the EKF and UKF will be close — that's the *expected* answer (Lecture 1 §3.3), and saying so with evidence is the point. Don't manufacture a difference that isn't there.

**Estimated time.** 45 minutes.

---

## Problem 3 — A UKF for a range-bearing landmark, with a NEES plot

**Problem statement.** Extend Exercise 2: run the UKF and EKF for **50 Monte-Carlo trials** (different noise seeds) on the range-bearing problem, and produce a NEES plot that averages NEES *across trials* at each timestep, with the 95% chi-squared band drawn. This is the rigorous version of the consistency check — a single run is noisy; 50 runs reveal the systematic over/under-confidence.

**Acceptance criteria.**

- A script that runs 50 trials and saves `notes/week-11/nees-monte-carlo.png` showing UKF and EKF average NEES vs. timestep with the chi-squared band.
- A one-paragraph reading of the plot: which filter rides higher, and what that says about overconfidence on this nonlinear measurement.
- The script uses a *different* random seed per trial (don't accidentally run the same trial 50 times).
- Committed.

**Hint.** Average NEES at timestep `t` over the 50 trials, then compare to the *per-step* chi-squared band `chi2.ppf([0.025, 0.975], 3*50)/50` (dof = state-dim × trials). The single-run band from the exercise is wider; the 50-trial band is tight, so a small bias becomes visible.

**Estimated time.** 1 hour.

---

## Problem 4 — The filter-vs-smoother decision memo (headline deliverable)

**Problem statement.** Write a one-page engineering memo at `notes/week-11/filter-vs-smoother-memo.md` that a teammate could use to choose an estimator. For **each** of these four real C24 scenarios, name the estimator you'd use and justify it in 2–3 sentences against the decision tree (Lecture 2 §8):

1. A 100 Hz control loop needs the robot's current fused pose (odometry + IMU) with bounded latency; it never revisits the past.
2. The robot powers on in a known building and must figure out *where* it is, with no initial guess.
3. A measurement has a strongly nonlinear model (bearing to a beacon) and the heading uncertainty is large.
4. The robot drove a 200-meter loop; you need a globally-consistent trajectory and the loop closure must correct accumulated drift.

Then add a short section: *"What a filter throws away, and why that's usually fine — except when it isn't."*

**Acceptance criteria.**

- `notes/week-11/filter-vs-smoother-memo.md` exists, fits on roughly one page (400–600 words), and gives a *specific* estimator + justification for each of the four scenarios (expected: EKF/UKF, particle filter/AMCL, UKF, factor graph).
- Each justification references the *property* that drives the choice (revisit-the-past? multimodal? strong nonlinearity? global consistency?), not just a name.
- The "what a filter throws away" section correctly explains marginalization and why it's irreversible.
- Committed.

**Hint.** The four scenarios map exactly onto the four leaves of the Lecture 2 §8 decision tree. The memo is your chance to internalize that tree — the Week 16 reviewer *will* ask "filter or smoother, and why?" Write the memo as if it's that answer.

**Estimated time.** 1 hour.

---

## Problem 5 — Convert your factor graph to incremental iSAM2

**Problem statement.** Take the three-pose graph from Exercise 3 (Part B, with the loop closure) and re-implement it with `gtsam.ISAM2`: add the prior + `X(0)` and `update()`; add each between factor + new variable and `update()`; finally add the loop closure and `update()`. Confirm the final estimate matches the batch Levenberg-Marquardt solve.

**Acceptance criteria.**

- A script `isam2_version.py` that builds the same graph incrementally with `ISAM2.update()` and `calculateEstimate()`.
- `notes/week-11/isam2.md` showing the final `X(2)` from both the batch solve and the iSAM2 solve, confirming they agree to ~4 decimals.
- One sentence on *which* `update()` call (the loop closure) triggers the largest re-optimization, and why (it ripples back through the Bayes tree to earlier poses).
- Committed.

**Hint.** Each `update()` takes a *fresh small* `NonlinearFactorGraph` and `Values` containing only the new factors/variables — not the whole graph. Seed each new variable from `isam.calculateEstimate().atPose2(...)` composed with the new odometry, exactly as in the Lecture 2 §7 code.

**Estimated time.** 45 minutes.

---

## Problem 6 — Add `/odom` to the pose-graph backend and prove it corrects drift

**Problem statement.** Using the `crunch_posegraph` mini-project backend (or a minimal version), feed it the drifting square-loop odometry from Challenge 1's `make_world`, add the loop closure, optimize, and report the ATE before and after. Then prove the robust kernel matters: plant a false loop closure and show ATE under plain Gaussian vs. Huber.

**Acceptance criteria.**

- A script that builds the open chain, adds the good loop closure, and reports open-vs-closed ATE (expect a clear reduction, ~0.6 m → ~0.12 m on `SEED=1`).
- The same script plants a false loop closure and reports ATE under `robust=False` (blows up, > open-chain) vs. `robust=True` (recovers near the good-closure number).
- `notes/week-11/posegraph-drift.md` records all four ATE numbers and a one-sentence conclusion on why robust kernels are mandatory for automatic loop closures.
- Committed.

**Hint.** The numbers from Challenge 1's verification: open ≈ 0.63, good loop ≈ 0.12, false loop under Gaussian ≈ 1.67, false loop under Huber ≈ 0.21. If yours are wildly different, check that you're using the *true* closing relative pose for the good closure and a genuinely-wrong one for the false closure.

**Estimated time.** 35 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Tune AMCL | 50 min |
| 2 — EKF → UKF swap | 45 min |
| 3 — Monte-Carlo NEES plot | 1 h 0 min |
| 4 — Filter-vs-smoother memo (headline) | 1 h 0 min |
| 5 — Incremental iSAM2 | 45 min |
| 6 — Pose-graph drift correction | 35 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_posegraph` [mini-project](./mini-project/README.md) is in the same workspace — Week 16 imports its ideas. Then take the [quiz](./quiz.md) with your notes closed.

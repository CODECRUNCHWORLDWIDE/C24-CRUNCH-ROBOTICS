# Week 11 — Sensor Fusion 2: UKF, Particle Filters, and Factor Graphs

Last week you built an Extended Kalman Filter and let `robot_localization`'s `ekf_node` fuse wheel odometry and IMU into one `/odometry/filtered`. The EKF works, and it will keep working for the rest of this course. But it has a tell: it *linearizes*. Every prediction and update step, the EKF takes your nonlinear motion and measurement models and replaces them with their first-order Taylor approximation around the current mean. When the nonlinearity is mild, the lie is cheap. When the robot turns hard, or the heading covariance is large, or the measurement is a bearing to a far landmark, the linearization is wrong in a way that quietly corrupts your covariance — and a filter that is wrong about its own uncertainty is worse than no filter at all.

This week is about the three estimators that handle that nonlinearity better, each in a different way, and about knowing which one to reach for. The **Unscented Kalman Filter** keeps the Gaussian assumption but stops linearizing — it propagates a handful of carefully-chosen sample points through the *true* nonlinear model. The **particle filter** drops the Gaussian assumption entirely and represents the belief as a cloud of weighted samples; this is what AMCL — the localization you'll run against your Week 7 map — actually is under the hood. And the **factor graph** stops being a filter at all: instead of compressing the past into a single mean and covariance, it keeps the constraints and re-optimizes the whole trajectory whenever new information arrives. That is the structure under every modern SLAM back-end, and you'll build your first one in GTSAM by hand.

The one sentence to carry into the week, straight from the lecture title:

> **The EKF lies about nonlinearity. The UKF lies less. The factor graph stops lying.** A filter throws away the past to stay cheap; a smoother keeps it to stay correct. Knowing when you can afford the smoother is a senior skill.

## Learning objectives

By the end of this week, you will be able to:

- **Derive** the Unscented Transform: choose sigma points with the scaled-unscented parameters (α, β, κ), propagate them through a nonlinear function, and recover the predicted mean and covariance — and explain *why* this beats the EKF's Jacobian for strongly nonlinear models.
- **Implement** a UKF predict/update cycle in NumPy for a unicycle motion model fusing a range-bearing measurement, and compare its consistency (NEES/NIS) against an EKF on the same data.
- **Explain** the particle-filter algorithm end to end — sample, weight, resample — and name the two failure modes (particle deprivation and sample impoverishment) and the fixes (low-variance resampling, adaptive particle counts, KLD-sampling).
- **Operate** AMCL against your Week 7 map: initialize the cloud with `/initialpose`, watch it converge in rviz2, force the kidnapped-robot problem, and tune the motion and measurement models honestly.
- **Distinguish** a *filter* (Markov, forward-only, constant-time, throws away the past) from a *smoother* (keeps constraints, re-linearizes, gets the whole trajectory right) and state when each is the correct tool.
- **Build** a factor graph in GTSAM's Python bindings from scratch — pose variables, a prior factor, between factors — solve it with Levenberg-Marquardt, read the marginal covariances, and confirm the optimum matches a hand calculation.
- **Connect** all three to the SLAM you've already run: why `slam_toolbox` and modern LIO front-ends emit *factors*, not filtered means, and why iSAM2 makes incremental re-optimization cheap enough to run online.

## Prerequisites

This week assumes you have completed **C24 weeks 1–10**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or the same in a container / WSL2). `ros2 --version` works; `ros2 doctor` runs clean.
- The **Week 10 EKF** working: you configured `robot_localization`'s `ekf_node`, fused wheel odometry + IMU into `/odometry/filtered`, and tuned process noise. You should be able to explain the predict and update steps of a Kalman filter from memory.
- The **Week 7 map**: a saved `slam_toolbox` occupancy grid of a multi-room Gz Sim world, plus the ability to relaunch the robot in that world. AMCL needs both the map and a moving robot.
- **Linear algebra fluency** from Phase 1: covariance matrices are symmetric positive-(semi)definite; you can read a 3×3 covariance as an uncertainty ellipse; Cholesky and matrix square roots are not scary.
- Comfortable with **NumPy** — you'll write the UKF and a toy particle filter in plain NumPy before touching GTSAM, and with **`pip`/`colcon`** for installing `gtsam`.

You do **not** need prior factor-graph experience. We start from "what is a factor" and build to a solved two-pose graph with marginals. If you have only ever used SLAM as a black box that emits a map, this is the week the box becomes glass.

## Topics covered

- **The Unscented Transform**: the intuition (it is easier to approximate a distribution than an arbitrary nonlinear function), sigma-point selection via the matrix square root, the scaled-unscented weights for mean and covariance, and the (α, β, κ) tuning parameters and their sane defaults.
- **The UKF** predict/update cycle: augmenting the state with process and measurement noise (or the additive-noise shortcut), the cross-covariance and Kalman gain, and the practical reasons UKF beats EKF on heading-heavy and range-bearing problems — without ever computing a Jacobian.
- **Filter consistency**: NEES (Normalized Estimation Error Squared) and NIS (Normalized Innovation Squared), the chi-squared bounds, and how an *overconfident* filter (the classic EKF-divergence symptom) shows up as a NEES that walks out of its bound.
- **Particle filters**: the sequential-importance-resampling (SIR) algorithm, the proposal/weight/resample loop, the degeneracy problem and effective sample size (N_eff), **low-variance (systematic) resampling**, particle deprivation, KLD-adaptive particle counts.
- **AMCL** as a particle filter: the sample-motion-model (odometry alpha parameters), the likelihood-field measurement model, `/initialpose` initialization, the kidnapped-robot problem and recovery via random-particle injection, and the AMCL parameters that actually matter (`min_particles`, `max_particles`, `update_min_d`, `z_hit`/`z_rand`).
- **Filters vs. smoothers**: the Markov assumption, marginalization as information loss, why a filter is constant-time and a batch smoother is not, and where the EKF, UKF, PF, and factor graph each sit on that spectrum.
- **Factor graphs and GTSAM**: variables (`Pose2`, `Pose3`), factors (`PriorFactor`, `BetweenFactor`), noise models (`Gaussian`, `Diagonal`, robust/Huber), the `NonlinearFactorGraph` + `Values` + `LevenbergMarquardtOptimizer` workflow, reading `Marginals`, and why MAP estimation on a factor graph *is* a nonlinear least-squares problem.
- **iSAM2 and the bridge to SLAM**: incremental smoothing and mapping, the Bayes tree, fixed-lag smoothing, and why every modern back-end (`slam_toolbox`, GTSAM-based LIO, ORB-SLAM3's local BA) is a factor graph in disguise.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Unscented Transform; sigma points; UKF predict/update  |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | UKF vs EKF; NEES/NIS consistency; exercise 1 + 2        |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Particle filters; AMCL; resampling; exercise 3         |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Filters vs smoothers; GTSAM factor graphs              |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | iSAM2; the SLAM bridge; mini-project deep work          |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                 |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, writeup polish                           |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The UKF papers, the Probabilistic Robotics chapters, AMCL docs, and GTSAM tutorials worth your time |
| [lecture-notes/01-ukf-and-particle-filters.md](./lecture-notes/01-ukf-and-particle-filters.md) | The Unscented Transform, the UKF cycle, consistency metrics, particle filters, and AMCL |
| [lecture-notes/02-factor-graphs-and-gtsam.md](./lecture-notes/02-factor-graphs-and-gtsam.md) | Filters vs smoothers, factor graphs, GTSAM by hand, marginals, iSAM2, and the SLAM bridge |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-amcl-on-your-map.md](./exercises/exercise-01-amcl-on-your-map.md) | Run AMCL against the Week 7 map, initialize with `/initialpose`, force a kidnapped-robot recovery |
| [exercises/exercise-02-ukf-vs-ekf.py](./exercises/exercise-02-ukf-vs-ekf.py) | A UKF and an EKF on the same range-bearing problem; compare error and NEES |
| [exercises/exercise-03-two-pose-factor-graph.py](./exercises/exercise-03-two-pose-factor-graph.py) | Build, solve, and check a two-pose GTSAM factor graph against a hand calculation |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-pose-graph-from-odometry.md](./challenges/challenge-01-pose-graph-from-odometry.md) | Turn a noisy odometry trajectory + one loop closure into a solved GTSAM pose graph |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the filter-vs-smoother decision memo |
| [mini-project/README.md](./mini-project/README.md) | A GTSAM pose-graph optimizer that ingests `nav_msgs/Odometry` + loop closures and publishes an optimized trajectory |

## The "the estimate converged" promise

C24 uses a recurring marker for every estimation lab that ends in a believable answer. For a filter, it is the consistency check:

```
NEES over 200 steps: mean = 3.04  (3-DOF state, 95% bound = [2.37, 3.72])  -> CONSISTENT
```

For a factor graph, it is the optimizer landing on the answer your hand calculation predicted:

```
initial error: 9.1180e+00
final   error: 1.2436e-13
optimized x1: (2.0000, 0.0000, 0.0000)   # matches the hand calc to 4 decimals
```

A NEES that walks out of its chi-squared bound, or an optimizer whose final error is not near zero on a noise-free graph, means you are *not* done — the estimate is overconfident or the graph is mis-specified. The point of Week 11 is to make those numbers ordinary, and to make a *bad* number loud instead of a quietly-wrong map three weeks later.

## Stretch goals

If you finish the regular work early and want to push further:

- Implement the **square-root UKF** (van der Merwe) that propagates the Cholesky factor of the covariance directly, never forming the full covariance — the numerically-stable variant that ships in production estimators.
- Add a **robust (Huber) noise model** to your two-pose factor graph, plant one gross-outlier loop closure, and watch the robust kernel down-weight it while a plain Gaussian model gets dragged off the true trajectory.
- Run AMCL with **`max_particles` set to 50, then 5000**, and plot localization error vs. CPU time. Find the knee of the curve for your map — that is the number you'd actually ship.
- Convert your Exercise 3 batch graph to **iSAM2** (`gtsam.ISAM2`): add the factors incrementally, call `update()` each step, and confirm you get the same answer as the batch Levenberg-Marquardt solve at a fraction of the per-step cost.

## Up next

Week 12 leaves estimation for **classical computer vision**: the pinhole camera model, calibration, ORB features, Lucas-Kanade optical flow, and stereo depth. The RANSAC you'll meet there is the same robust-estimation idea you used to reject the outlier loop closure here — outlier rejection is a thread that runs through the whole perception phase. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

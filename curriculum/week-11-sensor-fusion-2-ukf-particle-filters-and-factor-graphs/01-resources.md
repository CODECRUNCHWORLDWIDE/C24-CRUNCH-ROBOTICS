# Week 11 — Resources

Every resource here is **free**. The estimation theory lives in two openly-readable books (Thrun's *Probabilistic Robotics* sample chapters and Barfoot's *State Estimation for Robotics*, which the author hosts as a free PDF), the AMCL and `nav2_amcl` docs are open, and GTSAM ships extensive free tutorials and Doxygen. No paywalled books are required.

Where a ROS package is versioned, the **Jazzy** link is given. The math (UKF, particle filters, factor graphs) is distro-independent; only the `nav2_amcl` and ROS API URLs move between distros.

## Required reading (work it into your week)

- **Thrun, Burgard, Fox — *Probabilistic Robotics*, Ch. 3 (Gaussian filters) and Ch. 4 (Nonparametric filters).** The canonical treatment of the UKF and the particle filter. The slides and sample chapters are posted free:
  <https://docs.ufpr.br/~danielsantos/ProbabilisticRobotics.pdf>
- **Barfoot — *State Estimation for Robotics* (free PDF from the author).** Chapter 4 covers the sigma-point / unscented methods rigorously; later chapters build to batch estimation and factor graphs:
  <http://asrl.utias.utoronto.ca/~tdb/bib/barfoot_ser_17.pdf>
- **Dellaert & Kaess — *Factor Graphs for Robot Perception* (Foundations and Trends, free PDF).** The definitive, readable introduction to factor graphs and GTSAM, by GTSAM's authors. Read §1–§3 this week:
  <https://www.cs.cmu.edu/~kaess/pub/Dellaert17fnt.pdf>

## The foundational papers (skim, don't memorize)

- **Julier & Uhlmann — "A New Extension of the Kalman Filter to Nonlinear Systems" (1997).** The original Unscented Transform paper:
  <https://www.cs.unc.edu/~welch/kalman/media/pdf/Julier1997_SPIE_KF.pdf>
- **Van der Merwe & Wan — "The Square-Root Unscented Kalman Filter."** The scaled, numerically-stable UKF that production code actually uses:
  <https://cse.sc.edu/~terejanu/files/tutorialUKF.pdf>
- **Kaess et al. — "iSAM2: Incremental Smoothing and Mapping Using the Bayes Tree" (IJRR 2012).** Why incremental factor-graph optimization is fast enough for online SLAM:
  <https://www.cs.cmu.edu/~kaess/pub/Kaess12ijrr.pdf>

## AMCL and Nav2 docs (the ones you'll have open all week)

- **`nav2_amcl` configuration guide** — every parameter (`min_particles`, `max_particles`, `update_min_d`, the `alpha1..alpha5` motion-model noise, `z_hit`/`z_rand`):
  <https://docs.nav2.org/configuration/packages/configuring-amcl.html>
- **Nav2 first-time-robot setup (localization)** — bringing up AMCL against a saved map:
  <https://docs.nav2.org/setup_guides/index.html>
- **`nav2_map_server`** — serving the Week 7 map to AMCL with the right latched QoS:
  <https://docs.nav2.org/configuration/packages/configuring-map-server.html>

## GTSAM references

- **GTSAM home + install** (`pip install gtsam` for the Python bindings on Ubuntu 24.04 / Python 3.12):
  <https://gtsam.org/get_started/>
- **GTSAM Python examples** — `Pose2SLAMExample`, `OdometryExample`, the ones the exercises are built from:
  <https://github.com/borglab/gtsam/tree/develop/python/gtsam/examples>
- **GTSAM tutorials** ("GTSAM Concepts," the factor-graph walkthrough):
  <https://gtsam.org/tutorials/intro.html>
- **GTSAM Doxygen** (`NonlinearFactorGraph`, `Values`, `LevenbergMarquardtOptimizer`, `Marginals`, `ISAM2`):
  <https://gtsam.org/doxygen/>

## The `robot_localization` UKF (UKF in a real ROS package)

- **`robot_localization` — `ukf_node`** — the package you used for the EKF in Week 10 also ships a UKF. Same config shape, different estimator:
  <https://docs.ros.org/en/melodic/api/robot_localization/html/state_estimation_nodes.html>
- **`robot_localization` GitHub** (read how `Ukf.cpp` chooses sigma points — production code, not a toy):
  <https://github.com/cra-ros-pkg/robot_localization>

## Talks worth your time (free, no signup)

- **Frank Dellaert — "Factor Graphs for Perception and Action"** — the author's own overview of why factor graphs unify SLAM, control, and learning; search the GTSAM channel and ROSCon archive:
  <https://www.youtube.com/@gtsamteam>
- **Cyrill Stachniss — Mobile Sensing & Robotics lectures (UKF, particle filters, AMCL, factor graphs)** — the best free university course on this material, all on YouTube:
  <https://www.youtube.com/@CyrillStachniss>
- **ROSCon SLAM / state-estimation sessions** — the OSRF posts every talk:
  <https://roscon.ros.org/>

## Tools you'll use this week

- **`gtsam`** (Python) — `pip install gtsam`. Factor graphs, optimizers, marginals.
- **`numpy`** / **`scipy`** — the UKF and particle filter are pure NumPy; `scipy.linalg.cholesky` gives the sigma-point matrix square root.
- **`nav2_amcl`** — `sudo apt install ros-jazzy-nav2-amcl ros-jazzy-nav2-map-server`.
- **`rviz2`** — the `PoseArray` display shows the AMCL particle cloud; the `2D Pose Estimate` button publishes `/initialpose`.
- **`matplotlib`** — plot NEES bands, particle clouds, and before/after trajectories for your writeups.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **UKF** | Unscented Kalman Filter — propagates sigma points through the true nonlinear model instead of linearizing. |
| **Sigma points** | A small deterministic set of samples (2n+1) capturing the mean and covariance of the state. |
| **Unscented Transform** | The map: pick sigma points → push through f() → recover mean + covariance. |
| **α, β, κ** | Scaled-unscented parameters: spread of sigma points, prior-knowledge term (β=2 for Gaussian), secondary scaling. |
| **Particle filter** | A nonparametric Bayes filter; the belief is a set of weighted samples (particles). |
| **SIR** | Sequential Importance Resampling — the sample/weight/resample particle-filter loop. |
| **N_eff** | Effective sample size; when it drops, resample. |
| **Low-variance resampling** | Systematic resampling that draws particles with one random offset; avoids deprivation. |
| **AMCL** | Adaptive Monte Carlo Localization — the ROS particle filter that localizes against a known map. |
| **Kidnapped robot** | The robot is teleported; the filter must recover from a wrong, confident estimate. |
| **NEES** | Normalized Estimation Error Squared — checks if the *true* error matches the *claimed* covariance. |
| **NIS** | Normalized Innovation Squared — the NEES of the measurement residual; computable without ground truth. |
| **Filter** | Markov, forward-only, constant-time; compresses the past into one mean + covariance. |
| **Smoother** | Keeps constraints, re-linearizes, recovers the whole trajectory; more accurate, more expensive. |
| **Factor graph** | A bipartite graph of variables and factors (constraints); MAP estimation = nonlinear least squares. |
| **BetweenFactor** | A relative-pose constraint (odometry, loop closure) between two pose variables. |
| **Marginals** | The per-variable covariances recovered from the optimized graph. |
| **iSAM2** | Incremental Smoothing and Mapping — re-optimizes a factor graph cheaply as factors arrive. |

---

*If a link 404s, please open an issue so we can replace it.*

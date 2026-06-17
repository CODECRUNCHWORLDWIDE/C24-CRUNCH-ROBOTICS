# Week 10 — Sensor Fusion 1: EKF and robot_localization

Last week you made your IMU honest. This week you *fuse* it. By Friday you will be able to configure `robot_localization`'s `ekf_node` to combine wheel odometry and the calibrated IMU into a single `/odometry/filtered` estimate, drive the same 10×10 m square you drove in Week 6, and *measure* that the fused drift is smaller than raw wheel odometry alone — and you'll be able to explain, in covariance terms, exactly why.

We assume you finished Week 9 (a calibrated `/imu/data` with honest covariance) and Week 6 (wheel odometry publishing `/odom` with an `odom→base_link` transform). You understand QoS, you have a diff-drive robot in Gz Sim (or on hardware), and you can read a `nav_msgs/Odometry` and a `sensor_msgs/Imu` message field by field, covariance included.

The one thing to internalize before you read another line: **sensor fusion is bookkeeping with covariance.** The Kalman filter is not magic and it is not AI — it is a disciplined accountant. Every sensor reports a value *and* a stated uncertainty (its covariance). The filter maintains a running estimate with its own covariance, and at each step it does exactly two things: it *predicts* the state forward through a motion model (growing the covariance, because prediction adds uncertainty), and it *corrects* the prediction with each new measurement (shrinking the covariance, weighted by how much it trusts the measurement versus the prediction). That weighting — the Kalman gain — is *entirely* determined by the covariances. State your covariances honestly and the filter is optimal; lie about them and it over- or under-trusts, and your estimate jitters or lags. `robot_localization` works exactly as well as the covariances you feed it.

This week is where the calibration discipline from Week 9 pays off, because the EKF *consumes* those covariance numbers directly.

## Learning objectives

By the end of this week, you will be able to:

- **Derive** the Kalman filter as recursive Bayesian estimation under linear-Gaussian assumptions — the predict step and the update step — and state what each line does to the mean and the covariance.
- **Explain** the Extended Kalman Filter: why a nonlinear motion model (a robot turning) breaks the linear KF, and how the EKF linearizes via the Jacobian at each step (and where that linearization lies).
- **Identify** the predict/update split, the Kalman gain `K`, the innovation, and the role of the process-noise `Q` and measurement-noise `R` matrices.
- **Configure** `robot_localization`'s `ekf_node`: the `odom0`/`imu0` inputs, the per-input boolean `_config` matrices (the famous 15-element grids), `two_d_mode`, `frequency`, `world_frame`/`odom_frame`/`base_link_frame`, and `publish_tf`.
- **Respect the REP 105 frame conventions** — `map → odom → base_link` — and configure the EKF to own the `odom→base_link` transform without fighting your wheel-odometry publisher.
- **Avoid the classic mistakes:** fusing absolute pose from two sources, double-counting a measurement, fusing yaw from both odometry and IMU wrongly, and feeding an IMU with a `-1` orientation covariance into an orientation-expecting config.
- **Tune** the process noise: drive the square, observe the drift and the covariance growth, and adjust `process_noise_covariance` with a documented rationale rather than by superstition.
- **Quantify** the improvement: compare fused `/odometry/filtered` drift against raw `/odom` over the same trajectory, with a plot and a number.

## Prerequisites

This week assumes you have completed **C24 weeks 1–9**, or have equivalent ROS2 + estimation fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**; a diff-drive robot (sim or real) publishing **wheel odometry** `/odom` (`nav_msgs/Odometry`) with an `odom→base_link` TF, from Week 6.
- A **calibrated IMU** `/imu/data` with **honest covariance**, from Week 9 — the EKF reads that covariance to weight the IMU.
- **`robot_localization` installed:** `sudo apt install ros-jazzy-robot-localization`.
- **tf2 fluency** from Week 2: you can read a TF tree, run `ros2 run tf2_tools view_frames`, and reason about `map → odom → base_link`.
- **NumPy + Matplotlib** for the drift comparison and a small hand-coded KF in the exercises.
- Comfort with `nav_msgs/Odometry` and `sensor_msgs/Imu` covariance fields (row-major 6×6 for odom pose/twist, 3×3 for IMU).

You do **not** need prior Kalman-filter experience. We derive the KF and EKF from Bayesian estimation. If the words "innovation" and "Kalman gain" are unfamiliar, this is the week they become tools you use, not jargon you nod at.

## Topics covered

- **Bayesian filtering recap:** state, belief, the predict/correct recursion; why "fuse two Gaussians" has a closed form and why that closed form *is* the Kalman update.
- **The Kalman filter, derived:** the predict step (`x̂⁻ = F x̂`, `P⁻ = F P Fᵀ + Q`) and the update step (`K = P⁻ Hᵀ (H P⁻ Hᵀ + R)⁻¹`, `x̂ = x̂⁻ + K(z − H x̂⁻)`, `P = (I − K H) P⁻`), term by term, with the covariance intuition.
- **The Extended Kalman Filter:** nonlinear `f` and `h`, linearization via the Jacobians `F = ∂f/∂x` and `H = ∂h/∂x`, and the honest caveat that the EKF *lies about nonlinearity* — the linearization error that motivates the UKF and factor graphs (Week 11).
- **`Q` and `R`:** process noise (how much you trust the motion model) and measurement noise (how much you trust each sensor); where `R` comes from (the sensor's reported covariance — your Week 9 IMU covariance, the wheel-odometry covariance).
- **`robot_localization` architecture:** `ekf_node`, the input topics (`odom0`, `imu0`, ...), the 15-state model (x, y, z, roll, pitch, yaw, and their velocities + linear accelerations), and the per-input `_config` boolean matrix that selects *which* fields of *each* sensor to fuse.
- **REP 105 frames:** `map → odom → base_link`, who publishes which transform, and why the EKF owns `odom→base_link` while a second EKF (or a localization source) owns `map→odom` (previewing Week 11/AMCL).
- **The fusion rules that keep you out of trouble:** fuse *velocity* from wheel odometry and *orientation/angular-velocity* from the IMU; never fuse the same absolute quantity from two sources; `two_d_mode` for planar robots; the `differential` and `relative` flags.
- **Tuning and validation:** reading the output covariance, growing/shrinking `process_noise_covariance`, and the raw-vs-filtered drift comparison over the Week 6 square.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Bayesian filtering; the linear Kalman filter derived   |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Tuesday   | The EKF; Jacobians; Q and R                            |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | robot_localization architecture; the config matrices   |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Thursday  | REP 105 frames; fusing odom + IMU; the launch + yaml    |    1h    |    2h     |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Tuning process noise; drive the square; mini-project    |    0h    |    0h     |     1h     |    0.5h   |   1h     |     2.5h     |    0.5h    |     5.5h    |
| Saturday  | Mini-project deep work                                  |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, tuning-rationale write-up polish          |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7h**    | **4h**     | **4h**    | **5h**   | **10.5h**    | **2.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The `robot_localization` docs, Kalman-filter references, REP 105, and the talks worth your time |
| [lecture-notes/01-kalman-and-ekf-from-scratch.md](./02-lecture-notes/01-kalman-and-ekf-from-scratch.md) | Bayesian filtering, the KF predict/update, the EKF and its Jacobians, Q and R |
| [lecture-notes/02-robot-localization-in-practice.md](./02-lecture-notes/02-robot-localization-in-practice.md) | `ekf_node` config, the boolean matrices, REP 105 frames, fusing odom + IMU, tuning |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-read-an-ekf-config.md](./03-exercises/exercise-01-read-an-ekf-config.md) | Read a real `ekf.yaml` and predict exactly what it fuses and what TF it publishes |
| [exercises/exercise-02-scalar-kalman.py](./03-exercises/exercise-02-scalar-kalman.py) | Implement a 1-D Kalman filter from scratch; watch covariance shrink on update, grow on predict |
| [exercises/exercise-03-fuse-odom-imu.py](./03-exercises/exercise-03-fuse-odom-imu.py) | A `robot_localization` launch + config harness and a drift-comparison subscriber |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-tune-and-quantify-fusion.md](./04-challenges/challenge-01-tune-and-quantify-fusion.md) | Tune process noise and prove fused drift beats raw odometry on the Week 6 square |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the EKF tuning-rationale write-up |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunch_localization` package: a tuned EKF fusing odom + IMU with a documented config and drift proof |

## The "filtered beats raw" promise

C24 uses a recurring marker for every exercise that ends in a measured improvement. This week's is a fused estimate that drifts *less* than its inputs:

```
$ ros2 run crunch_localization drift_compare
trajectory: 10x10 m square, returned to start
raw  /odom         end-point error:  0.83 m   (3.2% of path)
fused /odometry/filtered end-point error:  0.21 m   (0.8% of path)
improvement: 4.0x
```

If your fused estimate is *not* better than raw odometry, your config is wrong — usually fusing absolute pose from two sources, a `two_d_mode` mistake, or feeding the EKF an IMU whose covariance is a lie. The point of Week 10 is to make "filtered beats raw" real and explainable in covariance terms — and to make a *worse* fused estimate a signal you can immediately diagnose against the config.

## Stretch goals

If you finish the regular work early and want to push further:

- Add a **second `ekf_node`** for the `map→odom` transform (the dual-EKF pattern `robot_localization` is designed for), fed by a global source (you'll have AMCL in Week 11, GPS in later phases). Confirm the two EKFs don't fight over `odom→base_link`.
- Hand-derive the **diff-drive motion-model Jacobian** `F = ∂f/∂x` for the `(x, y, θ)` unicycle model and confirm it matches what `robot_localization`'s omnidirectional EKF does internally for the planar sub-state.
- Inject a **deliberately wrong IMU covariance** (10× too small) into the config and watch the filter over-trust the IMU and jitter; then fix it. This is the most instructive single experiment in the week.
- Compare `ekf_node` against `ukf_node` (also in `robot_localization`) on the same data — a preview of Week 11's "the EKF lies about nonlinearity, the UKF lies less."

## Up next

Week 11 takes the filter intuition you built here and broadens it: the **Unscented Kalman Filter** (which handles nonlinearity better than the EKF's linearization), **particle filters and AMCL** (for the `map→odom` global correction), and a first **factor graph** in GTSAM. Your tuned EKF and its honest covariance carry straight into it. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

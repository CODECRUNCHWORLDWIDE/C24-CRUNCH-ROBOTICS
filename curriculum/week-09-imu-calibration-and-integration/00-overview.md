# Week 9 — IMU Calibration and Integration

Welcome to Phase 2. The first eight weeks gave you a robot that moves in sim with a clean TF tree, honest QoS, and a saved map. Now you start *seeing the world properly* — and the first sensor you must learn to distrust, then trust, is the IMU. By Friday you will be able to take thirty minutes of stationary IMU data, compute an Allan-variance plot, read off the bias and noise parameters, subtract the bias in a live `rclpy` node, and *measure* that your integrated yaw drift dropped by a real factor.

We assume you finished Phase 1: you have a diff-drive robot publishing `/imu/data` (real BNO085 on Path A, or a simulated IMU plugin on Path B), you can write `rclpy` publishers and subscribers in your sleep, you understand QoS (sensor data is `BEST_EFFORT`), and you have the `crunch_rotations` library from Week 1 for the quaternion math you'll need to integrate angular velocity.

The one thing to internalize before you read another line: **an uncalibrated IMU is a random number generator with branding.** A MEMS gyroscope at rest does not read zero — it reads its bias, plus white noise, plus a slow random walk of that bias over temperature and time. Integrate that raw signal to get orientation and the bias becomes a *ramp*: a 0.5°/s gyro bias is 30° of phantom yaw per minute. The accelerometer is worse — integrate it twice for position and a tiny bias becomes a parabola that swallows your estimate in seconds. The discipline this week teaches is to *characterize* the noise (Allan variance), *remove* what you can (bias subtraction), and *respect* what remains (honest covariance, which Week 10's EKF will consume).

This week is where the IMU stops being a random number generator and becomes a sensor you can fuse.

## Learning objectives

By the end of this week, you will be able to:

- **State** the measurement models for a MEMS accelerometer and gyroscope — true signal plus bias plus scale-factor error plus white noise plus bias random walk — and name which error each calibration step removes.
- **Compute** an Allan-variance plot from a stationary IMU log, and **read** it: identify the angle/velocity random walk (the −1/2 slope), the bias instability (the flat floor), and the rate random walk (the +1/2 slope).
- **Extract** the noise-density and bias-instability numbers an estimator needs (`gyro_noise_density`, `gyro_random_walk`, and their accel counterparts) directly off the Allan plot.
- **Estimate** the static biases of a stationary IMU and **subtract** them in a live `rclpy` node that re-publishes `/imu/data_calibrated`.
- **Integrate** gyroscope angular velocity into an orientation estimate (quaternion integration, `q̇ = ½ q ⊗ (0,ω)`) and **quantify** how bias subtraction reduces integrated-yaw drift over a fixed window.
- **Explain** why dead-reckoning an IMU alone is hopeless over time, why accelerometer double-integration diverges fastest, and why gravity gives the roll/pitch a bounded reference that yaw lacks.
- **Populate** the covariance fields of a `sensor_msgs/Imu` message honestly from the Allan-variance numbers, so Week 10's `robot_localization` EKF can weight the IMU correctly.
- **Apply** a mid-stance / zero-velocity bias correction concept and articulate where it helps (legged/wheeled stationary intervals) and where it doesn't.

## Prerequisites

This week assumes you have completed **C24 weeks 1–8**, or have equivalent ROS2 fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**; `ros2 doctor` clean; a working diff-drive robot (real or sim) publishing `sensor_msgs/Imu` on `/imu/data`.
- The **`crunch_rotations`** library from Week 1 (quaternion multiply, normalize, integrate) — you'll integrate gyro data with it.
- **QoS literacy** from Week 5: IMU is a sensor stream (`BEST_EFFORT` / `KEEP_LAST` / small depth). You'll subscribe accordingly.
- **NumPy + Matplotlib** for the Allan-variance computation and plots. `pip install numpy matplotlib`.
- Comfort reading a `sensor_msgs/Imu` message: `orientation`, `angular_velocity`, `linear_acceleration`, and their three `*_covariance` 3×3 row-major arrays.

You do **not** need prior signal-processing or estimation theory. We build the IMU error model and Allan variance from scratch. If you've only ever `echo`'d `/imu/data` and shrugged at the numbers, this is the week those numbers become legible.

## Topics covered

- **The MEMS IMU error model:** the gyroscope and accelerometer measurement equations — `ω_meas = S·ω_true + b + n_white + (bias random walk)` — and the physical origin of each term (bias, scale factor, axis misalignment, white noise, temperature drift).
- **Bias, scale factor, and misalignment:** the constant offset, the gain error, and the cross-axis coupling; why bias is the dominant integrable error for a stationary or slow robot.
- **Allan variance:** the overlapping-bin computation, the log-log plot, and how to read **angle/velocity random walk** (slope −½), **bias instability** (the flat minimum), and **rate random walk** (slope +½) straight off it.
- **From Allan plot to estimator parameters:** reading `N` (random walk / noise density at τ = 1 s) and `B` (bias instability) and converting them into the `robot_localization` and `imu_filter_madgwick`-style noise inputs you'll use next week.
- **Static vs. dynamic calibration:** what you can estimate at rest (biases, noise) versus what needs motion (scale factor, misalignment, the full six-position tumble test).
- **Integration drift:** integrating gyro to orientation (`q̇ = ½ q ⊗ (0,ω)`), integrating accel twice to position, and *why* the latter is hopeless; gravity as a bounded reference for roll/pitch and the unobservability of yaw without a heading source.
- **Bias subtraction in ROS2:** a `rclpy` node that estimates the stationary bias, subtracts it, and re-publishes a calibrated `/imu/data`, with the drift-reduction measurement that proves it worked.
- **Honest covariance:** populating the `sensor_msgs/Imu` `*_covariance` fields from the Allan numbers so the downstream EKF trusts the IMU exactly as much as it should.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | IMU error model; bias, scale, misalignment             |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Allan variance: compute it, read it                    |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Wednesday | From plot to parameters; static vs dynamic calibration |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | Integration drift; gyro→orientation; the bias node     |    1h    |    2h     |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Honest covariance; mini-project deep work              |    0h    |    0h     |     1h     |    0.5h   |   1h     |     2.5h     |    0.5h    |     5.5h    |
| Saturday  | Mini-project deep work                                 |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, calibration-report polish                |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7h**    | **4h**     | **4h**    | **5h**   | **10.5h**    | **2.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The Allan-variance references, IMU datasheets, `imu_tools` docs, and the talks worth your time |
| [lecture-notes/01-imu-error-models-and-allan-variance.md](./02-lecture-notes/01-imu-error-models-and-allan-variance.md) | The error model, bias/scale/misalignment, and Allan variance from scratch |
| [lecture-notes/02-integration-drift-and-bias-correction.md](./02-lecture-notes/02-integration-drift-and-bias-correction.md) | Integration drift, gyro→orientation, the bias-subtraction node, and honest covariance |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-read-an-allan-plot.md](./03-exercises/exercise-01-read-an-allan-plot.md) | Read random walk, bias instability, and rate random walk off a real Allan plot |
| [exercises/exercise-02-allan-variance.py](./03-exercises/exercise-02-allan-variance.py) | Compute the overlapping Allan deviation from a stationary log and extract N and B |
| [exercises/exercise-03-bias-subtraction-node.py](./03-exercises/exercise-03-bias-subtraction-node.py) | A `rclpy` node that estimates stationary bias and re-publishes calibrated `/imu/data` |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-quantify-yaw-drift-reduction.md](./04-challenges/challenge-01-quantify-yaw-drift-reduction.md) | Integrate yaw raw vs calibrated and prove the drift drops by a measurable factor |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the one-page IMU calibration report |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunch_imu_calib` package: Allan analysis + a calibrated re-publisher with honest covariance |

## The "drift dropped by a factor" promise

C24 uses a recurring marker for every exercise that ends in a measurable improvement. This week's is a drift number that goes *down*:

```
$ ros2 run crunch_imu_calib drift_report
raw   yaw drift over 120 s stationary:  18.4 deg
calib yaw drift over 120 s stationary:   0.7 deg
reduction factor: 26.3x
```

If your calibrated drift is *not* meaningfully smaller than your raw drift, your bias estimate is wrong (too short a window, robot wasn't actually stationary, or you subtracted in the wrong frame). The point of Week 9 is to make that reduction factor real and repeatable — and to make a *non*-reduction a signal you can immediately diagnose.

## Stretch goals

If you finish the regular work early and want to push further:

- Run a **six-position static test** (IMU flat, inverted, on each of its four sides) and estimate the accelerometer **scale factor and misalignment**, not just bias — the full 3×3 calibration matrix plus offset vector.
- Add **temperature** to your bias model: log IMU temperature alongside the data over a warm-up, and show the gyro bias drifts measurably as the chip heats. This is why real systems re-estimate bias at every standstill.
- Compare your hand-rolled bias subtraction against **`imu_filter_madgwick`** (the `imu_tools` complementary/Madgwick filter): feed both raw and calibrated data and compare the orientation estimates.
- Implement a **zero-velocity update (ZUPT)** detector that flags stationary intervals automatically (from the accel/gyro magnitude variance) and re-estimates bias during them — the mid-stance correction concept, automated.

## Up next

Week 10 takes the calibrated IMU with honest covariance you produce here and **fuses** it with wheel odometry in `robot_localization`'s EKF, producing a single bounded-drift `/odometry/filtered`. The covariance you populate this week is *exactly* what that EKF reads to weight the IMU. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

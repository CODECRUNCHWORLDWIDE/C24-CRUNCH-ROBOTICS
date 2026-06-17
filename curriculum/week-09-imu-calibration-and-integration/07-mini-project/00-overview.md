# Mini-Project — `crunch_imu_calib`: From Raw IMU to a Fusion-Ready Stream

> Build a ROS2 package that takes a raw IMU, characterizes it (Allan variance → noise densities), estimates its biases, and re-publishes a calibrated `/imu/data_calibrated` with **honest covariance** — the exact stream Week 10's `robot_localization` EKF will fuse. Ship it with a calibration report and a drift-reduction proof.

This is the artifact that turns "I have an IMU" into "I have a *characterized* IMU." After this week, your robot's IMU isn't a mystery stream — it's a sensor whose noise density, bias, and residual uncertainty you measured and documented, and whose output is shaped exactly for downstream fusion.

**Estimated time:** ~10.5 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** The calibrated stream and its covariance become the **IMU input to your Week 10 EKF** (the Phase 2 sensor-fusion milestone). The `robot_localization` config you write next week reads the very covariance you populate here. Build it well now; you'll fuse it in seven days.

---

## What you will build

An `ament_python` package `crunch_imu_calib` with three deliverables:

1. **`crunch_imu_calib/allan.py`** — an offline analysis tool that loads a 30-minute stationary IMU log (from a bag or CSV), computes the overlapping Allan deviation per axis, extracts the noise density `N` and bias instability `B` for gyro and accel, and writes a `imu_noise.yaml` of the results.
2. **`crunch_imu_calib/corrector.py`** — the live `rclpy` node (a hardened Exercise 3) that estimates the stationary bias on startup, subtracts it, fills the `sensor_msgs/Imu` covariance from `imu_noise.yaml`, preserves the header, and re-publishes `/imu/data_calibrated`.
3. **A calibration report** (`CALIBRATION.md`) — the Allan plot, the measured `N`/`B` per axis, the bias estimate, and the drift-reduction factor from the challenge, written as the document a teammate (or a midterm panel) reads to trust your IMU.

By the end you have a public repo of ~300–400 lines that produces a fusion-ready IMU stream and the paperwork to defend it.

---

## Why characterize, not just calibrate

You could just subtract a bias and call it done. Don't stop there. A full characterization gives you:

- **The covariance numbers the EKF needs.** Without measured `N`, you'd guess the IMU covariance, and a guessed covariance is the #1 cause of a badly-tuned filter (Lecture 2 §3). Measure it.
- **A baseline to detect degradation.** Re-run the Allan analysis in six months; if the noise floor rose, the sensor is aging or mounting has loosened. The first characterization is your reference.
- **The paperwork that wins a review.** "I measured this unit's gyro noise density at 1.2e-3 rad/√s and a 26× drift reduction after bias subtraction" is a defensible, senior statement. A number with a method beats a vibe.

---

## Package layout

```
crunch_imu_calib/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_imu_calib
├── crunch_imu_calib/
│   ├── __init__.py
│   ├── allan.py            # offline Allan analysis -> imu_noise.yaml
│   ├── corrector.py        # live bias-subtraction + covariance node
│   └── drift_report.py     # the raw-vs-calibrated drift comparison
├── config/
│   └── imu_noise.yaml      # measured N, B per axis (written by allan.py)
├── launch/
│   └── corrector.launch.py # bring up the corrector with the config
├── CALIBRATION.md          # the report (Allan plot, biases, drift factor)
└── test/
    ├── test_allan.py       # Allan extraction vs a synthetic known-N signal
    └── test_covariance.py  # covariance fill is correct + orientation[-1] convention
```

---

## Deliverable 1 — `allan.py` (the analysis tool)

It must:

- Load a stationary IMU log — accept either a `ros2 bag` of `/imu/data` or a CSV with columns `t, gx, gy, gz, ax, ay, az`.
- Compute the overlapping Allan deviation per axis (reuse your Exercise 2 implementation).
- Extract `N` (random walk, off the −½ slope at τ=1 s) and `B` (bias instability, the floor / 0.664) for all six axes.
- Save `config/imu_noise.yaml`:

```yaml
# Measured from <bag/csv name>, <N samples> at <fs> Hz, on <date>.
gyro:
  noise_density:   [1.21e-03, 1.18e-03, 1.23e-03]   # rad/sqrt(s), xyz
  bias_instability: [6.8e-05, 7.1e-05, 6.9e-05]      # rad/s, xyz
accel:
  noise_density:   [2.0e-03, 1.9e-03, 2.1e-03]       # (m/s^2)/sqrt(s), xyz
  bias_instability: [1.0e-04, 1.1e-04, 1.0e-04]      # m/s^2, xyz
sample_rate: 100.0
```

- Save the Allan plot (`allan.png`) for the report.

> **Verify it on synthetic data first.** `test_allan.py` generates a signal with a *known* `N` and asserts your extraction recovers it within tolerance — exactly the Exercise 2 check. Never trust an Allan tool you haven't verified against a known-truth signal.

---

## Deliverable 2 — `corrector.py` (the live node)

A hardened version of the Exercise 3 node. It must:

- Read `config/imu_noise.yaml` for the covariance numbers (don't hard-code them).
- Estimate the stationary bias on startup (a parameter-configurable number of samples), with a log line announcing start and completion.
- Subtract the bias and re-publish `/imu/data_calibrated` with **sensor QoS** on both ends.
- Fill `angular_velocity_covariance` and `linear_acceleration_covariance` diagonals from the measured noise densities (`σ² = N²·fs`), and set `orientation_covariance[0] = -1` if the IMU is 6-DOF (no orientation), or pass through the orientation + its covariance if 9-DOF.
- **Preserve the header** (acquisition stamp + frame_id) from the input.
- Handle the gravity-removal frame correctly: document whether you assume z-up or measure the gravity direction from the stationary mean.

Run it:

```bash
ros2 launch crunch_imu_calib corrector.launch.py
# In another terminal, confirm it's calibrated:
ros2 topic echo /imu/data_calibrated --field angular_velocity   # ~0 when stationary
ros2 topic info /imu/data_calibrated -v                          # BEST_EFFORT both ends
```

---

## Deliverable 3 — the calibration report

`CALIBRATION.md` is the document that makes your IMU trustworthy to someone who didn't watch you build it. It must contain:

- The Allan plot (`allan.png`) with the regions annotated.
- A table of measured `N` and `B` per axis for gyro and accel.
- The estimated bias vector and the calibration window length.
- The **drift-reduction factor** from the challenge (raw vs. calibrated yaw over a held-out window), with the before/after plot.
- One paragraph on the gravity-removal assumption and any known limitations (e.g. "bias re-estimated only at boot; temperature drift uncorrected").

This is portfolio-grade documentation. The Week 16 midterm panel and a real interviewer both want exactly this.

---

## Rules

- **You may** read the ROS2 docs, the Kalibr/Allan references, `allan_variance_ros` source, and the lecture notes.
- **You must** verify the Allan extraction against a synthetic known-`N` signal in a test before trusting it on real data.
- **You must not** hard-code covariance numbers in the node — they come from `imu_noise.yaml`, which `allan.py` produced from real data. (Guessed covariance is the anti-pattern this whole week fights.)
- **You must** preserve the input header (acquisition stamp + frame_id) on the calibrated output.
- Python 3.12 (Ubuntu 24.04 default), `rclpy` on Jazzy, NumPy, Matplotlib.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-09-crunch-imu-calib-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_imu_calib` succeeds with no warnings.
- [ ] `allan.py` produces `imu_noise.yaml` with per-axis `N` and `B` and an `allan.png` plot.
- [ ] `colcon test` passes, with at least: `test_allan.py` (extraction matches a synthetic known `N` within 15%) and `test_covariance.py` (diagonal = `N²·fs`, `orientation_covariance[0] == -1` for 6-DOF).
- [ ] `corrector.py` re-publishes `/imu/data_calibrated`; stationary angular_velocity is near zero; covariance is populated from the YAML; the header is preserved.
- [ ] `ros2 topic info /imu/data_calibrated -v` shows `BEST_EFFORT` on both ends.
- [ ] `CALIBRATION.md` contains the Allan plot, the `N`/`B` table, the bias estimate, and the drift-reduction factor with its plot.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Allan analysis correctness** | 25 | Overlapping estimator correct (verified on synthetic known-`N`); `N` and `B` extracted per axis; plot annotated. |
| **Bias estimation & subtraction** | 20 | Stationary mean correct; gravity removed in the right frame; calibrated stream near-zero at rest. |
| **Honest covariance** | 20 | Diagonals = `N²·fs` from measured (not guessed) numbers; `orientation_covariance[0] = -1` convention; pulled from YAML. |
| **Header & QoS hygiene** | 10 | Acquisition stamp + frame_id preserved; sensor QoS on both ends. |
| **Drift-reduction proof** | 15 | Held-out raw-vs-calibrated yaw drift, real factor reported, before/after plot. |
| **Report & tests** | 10 | `CALIBRATION.md` is review-grade; `colcon test` green; synthetic-verification test present. |

**90+** is portfolio-grade and ready to feed the Week 10 EKF. **70–89** works but guesses a covariance or skips the held-out drift test. **Below 70** means the IMU isn't actually characterized — fix the Allan verification first, because next week's fusion quality is downstream of these numbers being right.

---

## Stretch goals

- **Six-position accel calibration.** Add a routine that, from six static orientations, solves the full 3×3 scale+misalignment matrix and bias vector for the accelerometer (Lecture 1 §5). Apply it in the corrector.
- **ZUPT auto-recalibration.** Detect stationary intervals automatically (low accel/gyro magnitude variance) and re-estimate gyro bias during them — so the correction tracks temperature drift instead of going stale after boot.
- **Madgwick comparison.** Pipe both raw and calibrated streams into `imu_filter_madgwick` and compare the orientation estimates; show the calibrated input yields less yaw drift.
- **CI.** A GitHub Actions workflow that runs `colcon test` (including the synthetic Allan verification) on every push.

---

## How this connects to the rest of C24

- **Week 10 (EKF + robot_localization)** fuses `/imu/data_calibrated` with wheel odometry. The covariance you populate here is *exactly* what the EKF reads to weight the IMU. A wrong covariance here produces a wrong filter there.
- **Week 11 (UKF, particle filters, factor graphs)** revisits the same fusion with smoothing back-ends; your honest covariance carries forward.
- **Week 16 (Phase 2 midterm)** grades your fused perception stack; the calibration report is part of the defense. This mini-project is that report, built early.

When you've finished, push the repo and take the [quiz](../05-quiz.md).

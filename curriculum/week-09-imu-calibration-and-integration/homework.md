# Week 9 Homework

Six problems that revisit the week's topics and force the IMU calibration workflow into your fingers. The full set should take about **5 hours**. Work in your Week 9 Git repository (the same workspace as the exercises and the `crunch_imu_calib` mini-project) so every problem produces at least one commit you can point to at the Phase 2 midterm in Week 16.

The headline deliverable is **Problem 4 — the one-page IMU calibration report**, which is the document a reviewer reads to trust your sensor. Treat it as an artifact, not a journal entry.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

Source ROS2 Jazzy in every terminal. Have an `/imu/data` source available — your week-3 sim IMU, a real IMU, or a recorded bag. The pure-analysis problems need only NumPy + Matplotlib.

---

## Problem 1 — Record and sanity-check a stationary log

**Problem statement.** Record at least **30 minutes** of stationary `/imu/data` (`ros2 bag record /imu/data`, robot truly still). Then sanity-check it: `ros2 topic hz` on the bag playback to confirm the rate, and a quick NumPy histogram of one gyro axis to confirm it's roughly Gaussian and centered on a *non-zero* mean (the bias). Write up the rate, the per-axis stationary mean (the bias), and the per-axis standard deviation.

**Acceptance criteria.**

- `notes/week-09/stationary-log.md` records the sample rate, the per-axis gyro bias (mean), and per-axis std.
- A histogram of one gyro axis is saved, showing a Gaussian centered off zero.
- You note your IMU model and whether it's real or simulated.
- Committed.

**Hint.** If your IMU is `BEST_EFFORT`, record with a QoS override (Week 5) or you may drop samples. Confirm the recorded count ≈ `rate × duration`. A mean of *exactly* zero on a real IMU is suspicious — either it's a simulated ideal IMU or you're reading the wrong field.

**Estimated time.** 40 minutes (plus the 30-min recording, which runs unattended).

---

## Problem 2 — Compute and annotate the Allan plot

**Problem statement.** Run your Exercise 2 / mini-project Allan tool on the Problem 1 log. Produce the log-log Allan-deviation plot for the z-axis gyro, and annotate it: mark the −½ region, the flat floor, and read off `N` (at τ=1 s) and `B` (floor / 0.664). Compare `N` to your IMU datasheet's quoted noise density.

**Acceptance criteria.**

- `notes/week-09/allan-analysis.md` contains the annotated plot and the extracted `N` and `B` with units.
- A one-line comparison of your measured `N` to the datasheet value (within a factor of ~2 is normal; a big gap is worth a sentence of explanation).
- Committed.

**Hint.** Remember to integrate the rate to angle (`cumsum`) before the second-difference estimator — skip that and your slopes shift. Verify your tool on the synthetic known-`N` signal first (Exercise 2) so you trust it on real data.

**Estimated time.** 45 minutes.

---

## Problem 3 — Predict drift from first principles, then check it

**Problem statement.** Using *only* your measured bias from Problem 1, predict the integrated yaw drift over 120 seconds (`θ = bias_z · t`). Then integrate the raw z-gyro over a held-out 120 s window and compare your prediction to the measured raw drift. They should match closely (the bias ramp dominates). Document the prediction, the measurement, and the agreement.

**Acceptance criteria.**

- `notes/week-09/drift-prediction.md` shows the predicted drift (`bias_z × 120 s` in degrees), the measured raw drift, and the percent agreement.
- A sentence explaining any discrepancy (random walk and bias instability cause the measured value to differ slightly from the pure-bias prediction).
- Committed.

**Hint.** Use a *held-out* window (not the one you estimated bias on). If prediction and measurement disagree by a lot, either the robot moved during the "stationary" window or the bias estimate is from too few samples.

**Estimated time.** 40 minutes.

---

## Problem 4 — The one-page IMU calibration report (headline deliverable)

**Problem statement.** Write a one-page calibration report at `notes/week-09/imu-calibration-report.md` that a teammate could read to trust your IMU. It must contain:

1. **Sensor & setup** — IMU model, mounting, sample rate, calibration window length.
2. **Noise characterization** — the Allan plot and the measured `N` and `B` for at least the gyro (all three axes if you have them).
3. **Bias estimate** — the per-axis gyro and accel bias, and the gravity-removal assumption you made.
4. **Covariance** — the `angular_velocity_covariance` diagonal you'd put in the message (`N²·fs`), and the `orientation_covariance[0] = -1` convention if 6-DOF.
5. **Validation** — the raw-vs-calibrated drift-reduction factor (from the challenge), with the number.
6. **Limitations** — one honest paragraph (e.g. "bias re-estimated only at boot; temperature uncorrected; single unit, not a population").

**Acceptance criteria.**

- `notes/week-09/imu-calibration-report.md` exists, fits ~one page, and hits all six headings.
- Every number traces to a measurement (Problem 1–3 or the mini-project), not a datasheet typical or a guess.
- The covariance values are stated and consistent with the measured `N`.
- The drift-reduction factor is a real measured number.
- Committed.

**Hint.** This is the document the Week 16 midterm panel — and a real interviewer — wants when they ask "how do you know your IMU is calibrated?" Make every claim defensible with a measurement. "Measured, not assumed" is the whole grade.

**Estimated time.** 1 hour.

---

## Problem 5 — Integrate gyro to orientation and watch it drift

**Problem statement.** Write a script (or node) that integrates the gyro into an orientation quaternion using the exponential-map integrator from Lecture 2 §1.2 (reuse `crunch_rotations`). Run it on the *raw* and on the *calibrated* gyro over the same window. Convert the final orientation to ZYX Euler degrees and report the yaw of each. Confirm the calibrated yaw is much closer to zero.

**Acceptance criteria.**

- A script using `crunch_rotations.axis_angle_to_quat` / `quat_mul` to integrate gyro to orientation.
- `notes/week-09/orientation-integration.md` reports the final yaw for raw vs. calibrated, and confirms calibrated is closer to the true (zero) heading.
- The integrator re-normalizes the quaternion each step (you note why).
- Committed.

**Hint.** Feed the integrator *bias-corrected* angular velocity for the calibrated run. If both runs drift identically, you forgot to subtract the bias on the "calibrated" path. Re-normalize each step or the quaternion norm slowly drifts and the orientation degrades for a second reason.

**Estimated time.** 45 minutes.

---

## Problem 6 — Populate and verify honest covariance on the stream

**Problem statement.** Extend your corrector node (or write a thin checker) so the calibrated `/imu/data_calibrated` carries the covariance computed from your measured `N`. Then *verify* it on the wire: `ros2 topic echo /imu/data_calibrated --field angular_velocity_covariance` and confirm the diagonal equals `N²·fs` and that `orientation_covariance[0]` is `-1` (6-DOF) or a real value (9-DOF).

**Acceptance criteria.**

- `notes/week-09/covariance-on-the-wire.md` shows the echoed covariance arrays and confirms the diagonal matches `N²·fs` from your Allan analysis.
- The orientation-covariance convention (`-1` for no-orientation) is correctly applied and shown.
- A one-line statement of why honest covariance matters for next week's EKF.
- Committed.

**Hint.** The covariance must come from the *measured* `N` (Problem 2 / `imu_noise.yaml`), not a round number. If the echoed diagonal doesn't match `N²·fs`, you either hard-coded a guess or used the wrong sample rate. This is the exact input the Week 10 EKF reads.

**Estimated time.** 30 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Stationary log | 40 min |
| 2 — Allan plot | 45 min |
| 3 — Drift prediction | 40 min |
| 4 — Calibration report (headline) | 1 h 0 min |
| 5 — Gyro→orientation integration | 45 min |
| 6 — Covariance on the wire | 30 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_imu_calib` [mini-project](./mini-project/README.md) is in the same workspace — Week 10 fuses its output. Then take the [quiz](./quiz.md) with your notes closed.

# Week 9 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 10. Answer key is at the bottom — don't peek.

---

**Q1.** A MEMS gyroscope at rest does not read zero. What does it read, and what is the dominant *integrable* error term for a slow robot?

- A) Pure white noise; nothing integrates.
- B) Its bias (zero-rate offset) plus white noise plus a slow bias random walk; the **bias** is the dominant integrable error.
- C) Exactly gravity, 9.81 m/s².
- D) The true rate, perfectly.

---

**Q2.** A gyro has a bias of 0.5°/s after warm-up. Roughly how much phantom yaw does integrating the raw signal accumulate over one minute?

- A) 0.5°
- B) 5°
- C) 30°
- D) 0° — bias doesn't integrate.

---

**Q3.** Why is pure-inertial *position* dead-reckoning hopeless for a ground robot?

- A) Accelerometers don't measure acceleration.
- B) Accel bias is double-integrated to position, growing as ½·b·t² — a tiny 0.05 m/s² bias gives 2.5 m of error in 10 s.
- C) Position can't be represented in ROS.
- D) It works fine; everyone does it.

---

**Q4.** With a 6-DOF IMU and no magnetometer, which orientation components are *bounded* and which *drifts unboundedly*, and why?

- A) All three drift equally.
- B) Roll and pitch are bounded (gravity gives an absolute tilt reference); yaw drifts unboundedly (rotating about vertical doesn't change gravity in the body frame).
- C) Yaw is bounded; roll and pitch drift.
- D) None drift; the IMU is exact.

---

**Q5.** On an Allan-deviation log-log plot, the **−½ slope** on the left represents:

- A) Bias instability.
- B) Angle/velocity random walk — the white noise, which averages down with longer τ.
- C) Rate random walk.
- D) Scale-factor error.

---

**Q6.** How do you read the random-walk coefficient `N` off the Allan plot?

- A) The peak value of the curve.
- B) The value of the −½ slope line extrapolated to τ = 1 s.
- C) The value at the largest τ.
- D) The slope of the flat region.

---

**Q7.** What does the **flat minimum** of the Allan plot give you?

- A) The scale factor.
- B) The bias instability `B ≈ σ_min / 0.664` — the noise floor past which averaging longer stops helping.
- C) The sample rate.
- D) The white-noise density.

---

**Q8.** Which calibration parameters can you estimate from a **stationary** log, and which require **motion**?

- A) Everything is estimable at rest.
- B) Bias and noise are estimable at rest; scale factor and misalignment require motion (they multiply the true signal, which is ~0 at rest).
- C) Only scale factor is estimable at rest.
- D) Nothing is estimable at rest.

---

**Q9.** When integrating gyro angular velocity into orientation, why subtract bias *before* integrating?

- A) It's optional; the integrator handles bias.
- B) Because integrating the bias produces a phantom ramp in orientation; subtracting it first removes the dominant drift term.
- C) Bias subtraction speeds up the integrator.
- D) The gyro can't be integrated with bias present.

---

**Q10.** In a `sensor_msgs/Imu` from a 6-DOF (no-orientation) IMU, what must `orientation_covariance[0]` be, and why?

- A) `0.0` — perfect orientation.
- B) `-1.0` — the ROS convention signaling "orientation unknown, don't use it"; zeros would falsely claim a certain identity orientation.
- C) `1.0` — unit variance.
- D) It doesn't matter.

---

**Q11.** You fill the IMU's `angular_velocity_covariance` diagonal. Given measured gyro noise density `N` and sample rate `fs`, the per-axis variance is:

- A) `N`
- B) `N / fs`
- C) `N² · fs`
- D) `fs / N²`

---

**Q12.** Your bias-corrector node re-publishes `/imu/data_calibrated` but stamps each message with `now()` at publish time. What's wrong?

- A) Nothing.
- B) It discards the *acquisition* stamp; the EKF then thinks the measurement happened later than it did, injecting timing error. Preserve `msg.header`.
- C) `now()` is too slow.
- D) Calibrated messages can't carry a header.

---

**Q13.** Your raw-vs-calibrated yaw-drift reduction comes out ~1× (no improvement). The single most likely cause is:

- A) The Allan variance is wrong.
- B) The robot wasn't actually stationary during calibration (or you calibrated and tested on the same window), so the bias estimate is meaningless or the test is leaked.
- C) Quaternions don't support yaw.
- D) The IMU is broken beyond repair.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Bias + white noise + slow bias random walk; bias is the dominant integrable error for a slow robot. (Lecture 1 §2.)
2. **C** — 0.5°/s × 60 s = 30°. Bias integrates to a linear ramp in yaw. (Lecture 1 §3.)
3. **B** — Accel bias double-integrates to position as ½·b·t²; 0.05 m/s² gives 2.5 m in 10 s. (Lecture 1 §3.)
4. **B** — Gravity bounds roll/pitch (absolute tilt reference); yaw has no reference without a magnetometer and drifts unboundedly. (Lecture 1 §3.)
5. **B** — The −½ slope is white noise / random walk, which averages down with τ. (Lecture 1 §4.3.)
6. **B** — `N` is the −½ line's value at τ = 1 s, by the definition of the Allan variance. (Lecture 1 §4.3.)
7. **B** — The flat minimum is the bias instability, `σ_min / 0.664`; the floor past which averaging longer hurts. (Lecture 1 §4.3.)
8. **B** — Bias and noise at rest; scale factor and misalignment need motion since they multiply the (zero-at-rest) true signal. (Lecture 1 §5.)
9. **B** — Integrating bias gives a phantom orientation ramp; subtract it first. (Lecture 2 §1.2.)
10. **B** — `-1.0` is the ROS "orientation unknown" convention; zeros would lie about a certain identity orientation. (Lecture 2 §3.1.)
11. **C** — `σ²_ω = N²·fs` (noise density squared times bandwidth). (Lecture 2 §3.2.)
12. **B** — Preserve the acquisition stamp via `msg.header`; a publish-time stamp injects timing error into the EKF. (Lecture 2 §2.2.)
13. **B** — A non-stationary calibration (or testing on the calibration window) makes the bias estimate meaningless or the test leaked; that's the ~1× factor. (Lecture 2 §2.2, Challenge 1 trap.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

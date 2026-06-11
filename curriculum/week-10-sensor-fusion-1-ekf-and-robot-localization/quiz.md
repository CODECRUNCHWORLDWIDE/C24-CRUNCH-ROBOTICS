# Week 10 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 11. Answer key is at the bottom — don't peek.

---

**Q1.** In the Kalman filter, what happens to the state covariance `P` during the **predict** step, and why?

- A) It shrinks, because prediction adds information.
- B) It grows (`P⁻ = F P Fᵀ + Q`), because the motion model is imperfect — predicting without measuring makes you *less* certain.
- C) It stays constant.
- D) It is reset to zero.

---

**Q2.** What happens to `P` during the **update** step?

- A) It grows.
- B) It shrinks (`P = (I − KH)P⁻`), because a measurement adds information.
- C) It stays constant.
- D) It becomes negative.

---

**Q3.** The Kalman gain `K` decides how much to trust the measurement vs. the prediction. It is determined by:

- A) A hand-tuned constant.
- B) The covariances alone — large when the measurement is precise (`R` small), small when it's noisy (`R` large).
- C) The robot's speed.
- D) The number of sensors.

---

**Q4.** Why does fusing two noisy Gaussian estimates produce a *less* noisy one?

- A) It doesn't; fusion always adds noise.
- B) The posterior is the precision-weighted average, and its variance `1/(P⁻¹ + R⁻¹)` is smaller than either input's variance.
- C) Averaging always halves the noise.
- D) Only if the two sensors are identical.

---

**Q5.** What does the Extended Kalman Filter do that the linear KF cannot, and what is its honest limitation?

- A) Nothing different; EKF and KF are identical.
- B) It linearizes nonlinear `f`/`h` via Jacobians at the current estimate each step; the limitation is that the linearization is approximate and can lie when curvature/uncertainty is large.
- C) It eliminates all nonlinearity exactly.
- D) It requires no covariance.

---

**Q6.** Where does the measurement-noise matrix `R` come from in `robot_localization`?

- A) You tune it like `Q`.
- B) From each sensor's reported covariance — the IMU's `angular_velocity_covariance` (your Week 9 number), the odom's `twist`/`pose` covariance. It's read, not guessed.
- C) It's always the identity.
- D) From the motion model.

---

**Q7.** In `odom0_config`, why are the absolute position fields (`x, y`) typically set to `false`?

- A) Odometry can't measure position.
- B) Wheel-odometry absolute position *drifts*; fusing it would import the drift. You fuse the non-drifting *velocity* instead.
- C) `false` means "fuse it."
- D) Position is fused from the IMU instead.

---

**Q8.** A planar diff-drive robot's EKF estimate wanders and jitters in z and tilt. The most likely config fix is:

- A) Increase `frequency`.
- B) Set `two_d_mode: true` so z, roll, pitch are zeroed and the filter doesn't chase noise in dimensions the robot can't move in.
- C) Remove the IMU.
- D) Fuse absolute position from odom.

---

**Q9.** Under REP 105, which transform does this week's `ekf_node` (`world_frame: odom`) publish, and what must be true about it?

- A) `map→odom`; many nodes can publish it.
- B) `odom→base_link`; exactly one node may publish it — if the wheel-odom node also broadcasts it, you get a TF conflict and a teleporting robot.
- C) `base_link→laser`; published by the URDF.
- D) None; the EKF publishes no transform.

---

**Q10.** Your fused `/odometry/filtered` is no better than raw `/odom`. You echo `/odom`'s `pose.covariance` and it's all zeros. What does that mean?

- A) The odom is perfect.
- B) A zero covariance claims infinite precision, so the EKF over-trusts the wheels and effectively ignores the IMU; set a realistic odom covariance.
- C) The EKF is broken.
- D) Zeros are required by `robot_localization`.

---

**Q11.** Why is fusing *absolute yaw* from BOTH wheel odometry and the IMU a mistake?

- A) It's fine; more sources is always better.
- B) You double-count the same absolute quantity, making the filter overconfident (its `P` shrinks faster than justified) and risking divergence. Fuse absolute yaw from one source.
- C) Yaw can't be fused at all.
- D) The IMU has no yaw.

---

**Q12.** Your fused heading lags the IMU during fast turns. Which tuning change addresses it?

- A) Decrease the IMU covariance to zero.
- B) Increase the `vyaw` (yaw-rate) entry of `process_noise_covariance`, so the filter trusts its motion model less and follows the IMU more.
- C) Turn off `two_d_mode`.
- D) Lower the EKF `frequency`.

---

**Q13.** Why does honest measurement timestamping (stamp at acquisition) matter specifically for the EKF?

- A) It doesn't; the EKF ignores timestamps.
- B) The EKF buffers and fuses measurements by their timestamp; a mis-stamped measurement is fused at the wrong point in the trajectory, corrupting the estimate.
- C) Timestamps only matter for logging.
- D) The EKF requires all sensors to share one clock and ignores stamps.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — `P⁻ = FPFᵀ + Q` grows the covariance; prediction adds uncertainty (`+Q`). (Lecture 1 §3.1.)
2. **B** — `P = (I−KH)P⁻` shrinks the covariance; measurement adds information. (Lecture 1 §3.2.)
3. **B** — `K` is set entirely by the covariances; precise measurements (small `R`) get a large gain. (Lecture 1 §3.2.)
4. **B** — The fused (precision-weighted) posterior has variance `1/(P⁻¹+R⁻¹)`, smaller than either input. (Lecture 1 §3.3.)
5. **B** — The EKF linearizes via Jacobians each step; the linearization is approximate and can lie under strong nonlinearity/uncertainty. (Lecture 1 §4.)
6. **B** — `R` is the sensor's reported covariance (your Week 9 IMU number, the odom covariance); read, not guessed. (Lecture 1 §5.1.)
7. **B** — Wheel absolute position drifts; fuse non-drifting velocity instead. (Lecture 1 §7, Lecture 2 §1.1.)
8. **B** — `two_d_mode: true` zeros z/roll/pitch on a planar robot. (Lecture 2 §1.2.)
9. **B** — This EKF owns `odom→base_link`; exactly one publisher, or a TF conflict. (Lecture 2 §2.)
10. **B** — A zero covariance = claimed infinite precision; the EKF over-trusts odom and ignores the IMU. (Lecture 2 §3.2.)
11. **B** — Double-counting an absolute quantity makes the filter overconfident and can diverge; one source per absolute. (Lecture 1 §7.)
12. **B** — Increase the `vyaw` process noise so the filter follows the IMU more. (Lecture 2 §3.3.)
13. **B** — The EKF fuses by timestamp; a mis-stamped measurement lands at the wrong trajectory point. (Lecture 2 §1.3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

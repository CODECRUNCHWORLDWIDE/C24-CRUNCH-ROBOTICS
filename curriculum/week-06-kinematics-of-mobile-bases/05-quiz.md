# Week 6 — Quiz

Thirteen questions on kinematics, integration, drift, and odometry publishing. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 7. Answer key at the bottom — don't peek.

---

**Q1.** A differential-drive robot has wheel radius `r` and wheel separation `L`. The left and right wheels spin at angular velocities `φ̇_L` and `φ̇_R`. What is the body forward velocity `vₓ`?

- A) `vₓ = r(φ̇_R − φ̇_L)/L`
- B) `vₓ = r(φ̇_R + φ̇_L)/2`
- C) `vₓ = (φ̇_R + φ̇_L)/(2r)`
- D) `vₓ = r·L·(φ̇_R + φ̇_L)`

---

**Q2.** Your odometry node reports the correct `vₓ` when driving straight, but during a pure spin-in-place the reported yaw rate `ω` has the **wrong sign**. What is the most likely cause, and the right fix?

- A) The integrator has a sign bug; negate `ω` in the integration step.
- B) The `left_joint` and `right_joint` parameters are swapped; swap the parameters (do not negate the equation).
- C) The wheel radius is negative; take its absolute value.
- D) The quaternion conversion is wrong; use `tf_transformations`.

---

**Q3.** A robot has a 1° (`0.0175 rad`) constant heading error. It then drives 10 m further. Approximately how much lateral (cross-track) position error does that heading error alone produce over those 10 m?

- A) ~1.75 mm
- B) ~17.5 mm
- C) ~0.175 m
- D) ~1.75 m

---

**Q4.** Why does a *wheelbase* (`L`) calibration error dominate odometry drift more than a *wheel-radius* (`r`) calibration error of the same percentage, on a path with turns?

- A) `L` is physically larger than `r`, so its error is larger in absolute terms.
- B) The wheelbase error lands in the heading channel (`ω ∝ 1/L`), and heading error multiplies the entire remaining path length, whereas a radius error is an along-track distance scale that grows only linearly.
- C) Radius errors cancel out over a closed loop; wheelbase errors do not.
- D) They contribute equally; the claim is false.

---

**Q5.** Which integration scheme is *exact* for a constant body twist `(vₓ, ω)` over a cycle, and coincides with the `SE(2)` matrix exponential?

- A) Euler (rectangular) integration.
- B) The exact-arc integrator (`x += (vₓ/ω)(sin(θ+ωΔt) − sin θ)`, etc.).
- C) Forward Euler with a half-step correction.
- D) Trapezoidal integration of the wheel velocities.

---

**Q6.** Your exact-arc integrator must guard `if |ω| > ε` and take a straight-line branch otherwise. Why?

- A) To save CPU when driving straight.
- B) Because at `ω = 0` the arc radius `R = vₓ/ω` is infinite and the arc formula divides by zero; the straight-line branch is the mathematical limit.
- C) Because the quaternion is undefined at zero yaw rate.
- D) Because `sin(θ + ωΔt)` overflows when `ω = 0`.

---

**Q7.** Per REP-105, which node publishes the `odom → base_link` transform, and what are its defining properties?

- A) The localizer (SLAM/AMCL); it is accurate but discontinuous (it jumps).
- B) The odometry source (your node); it is continuous and smooth but drifts.
- C) A static transform publisher; it never changes.
- D) The `map` server; it is latched and transient-local.

---

**Q8.** A mecanum base has four driven wheels — twice as many encoders as a diff-drive base. Why is its wheel odometry typically *worse* than diff-drive's?

- A) Mecanum wheels are heavier, so they slip more under load.
- B) The 3×4 mecanum Jacobian is non-square, so forward kinematics discards one dimension of wheel motion — the roller-slip mode — and the rollers slip sideways *by design* on every cycle; there is no no-skid channel to anchor the estimate.
- C) Four encoders produce four times the quantization noise.
- D) Mecanum bases cannot spin in place, so heading is unobservable.

---

**Q9.** In a `nav_msgs/Odometry` message from a diff-drive base, which covariance-diagonal assignment is *correct and honest*?

- A) All 36 entries set to `0.0` (we measure everything perfectly).
- B) All diagonal entries set to `1e6` (we trust nothing).
- C) Small on `x`, `y`, `vx`; **larger on yaw** than on `x`/`y`; `1e6` on `z`, `roll`, `pitch`, `vy`, `vz` (the unmeasured DOFs).
- D) Large on `x`, `y`; tiny on `z`, `roll`, `pitch`.

---

**Q10.** You stamp your `/odom` messages with `self.get_clock().now()` instead of the incoming `/joint_states` header stamp. What breaks downstream in Phase 2?

- A) Nothing; `now()` is always more accurate.
- B) The Week 10 EKF synchronizes inputs by timestamp; a `now()` stamp drifts against the IMU's acquisition stamp, so the filter fuses misaligned measurements and the estimate degrades.
- C) RViz cannot display the odometry.
- D) The TF tree becomes multiply-parented.

---

**Q11.** A `sensor_msgs/JointState` arrives with a populated `name[]` and `position[]` but an **empty** `velocity[]`. How should a robust odometry node compute wheel angular velocity?

- A) Treat the velocity as zero and skip the message.
- B) Difference the wheel `position[]` across consecutive messages and divide by the message `dt`.
- C) Read the velocity from `/cmd_vel` instead.
- D) Reject the message as malformed.

---

**Q12.** You drive a closed square and the **odom** closure error is 0.08 m (0.2%) while the **ground-truth** closure error is 0.56 m (1.4%). What is the correct interpretation?

- A) The odometry is excellent; trust the 0.2%.
- B) The robot integrated its own consistent, biased model and "thinks" it closed nearly perfectly; ground truth shows it actually ended 0.56 m from start. The gap between them is the real drift — odometry is optimistic about itself.
- C) The ground-truth sensor is broken.
- D) The two numbers should always be equal; one is a bug.

---

**Q13.** The UMBmark benchmark drives the square **clockwise and counter-clockwise**. What does the CW/CCW pair let you do that a single-direction square cannot?

- A) Average out quantization noise.
- B) Separate the two systematic errors: the wheelbase error (`Eb`) flips the closure point's angular offset between CW and CCW, while the unequal-wheel-diameter error (`Ed`) pushes it the same lateral way regardless of direction — so the two can be solved for independently.
- C) Measure the floor friction directly.
- D) Eliminate slip entirely.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Forward velocity is the *average* of the two wheel ground speeds: `vₓ = r(φ̇_R + φ̇_L)/2`. Option A is the *yaw rate* (a difference over `L`). The sum-vs-difference structure is the heart of diff-drive forward kinematics (Lecture 2, §2.3).

2. **B** — Correct `vₓ` (a sum, sign-insensitive to swapping) with wrong-sign `ω` (a difference, sign-sensitive) is the canonical swapped-joint signature. Swap the `left_joint`/`right_joint` parameters. Negating the equation (A) hides the real bug and breaks on the next robot whose joints are named the other way (Exercise 1, Step 3).

3. **C** — Cross-track error ≈ `distance × sin(Δθ) ≈ 10 m × 0.0175 = 0.175 m`. One degree of heading error becomes 17.5 cm over 10 m. This is why heading is the expensive error (Lecture 1, §1.3).

4. **B** — `ω ∝ r/L`, so `L` lives in the heading channel. A heading error multiplies the *remaining* path length (every subsequent segment is laid down rotated), so it compounds; a radius error is an along-track distance scale that grows only linearly. Lecture 1, §1.3 and §1.8's numerical decomposition show the wheelbase term producing ~6× the closure error of the radius term for comparable percentage errors.

5. **B** — The exact-arc integrator is exact for a constant twist over the cycle and is precisely the `SE(2)` matrix exponential expanded into coordinates (Lecture 2, §2.9). Euler (A) lays the increment along the start-of-cycle heading and accumulates a cross-track error proportional to `ω·Δt`.

6. **B** — At `ω = 0` the arc radius `R = vₓ/ω` is infinite and the formula `(vₓ/ω)(…)` divides by zero. The straight-line branch (`x += vₓ cos θ·Δt`) is the `ω → 0` limit of the arc formula. The guard is mandatory, not an optimization (Lecture 2, §2.9; Exercise 2).

7. **B** — Per REP-105, the **odometry source** publishes `odom → base_link`: continuous, smooth, drifting. The **localizer** publishes `map → odom`: accurate but discontinuous (it jumps when a scan match corrects accumulated drift). The split encodes the drift problem in the frame tree (Lecture 1, §1.5).

8. **B** — Mecanum's 3×4 Jacobian is non-square; forward kinematics squeezes 4D wheel motion through a 3D twist and discards the roller-slip mode, which is exactly where slip accumulates. The rollers slip sideways by design (that is how you get `v_y`), so every wheel contributes slip every cycle — there is no no-skid channel to anchor the estimate. More encoders measuring an unmodelable quantity do not help (Lecture 2, §2.7).

9. **C** — Honest covariance: small on the things you measure (`x`, `y`, `vx`), **larger on yaw** because heading is the weak point, and `1e6` on the DOFs you do not estimate (`z`, `roll`, `pitch`, `vy`, `vz`) to tell the EKF to ignore them. All-zero (A) claims perfection and makes the EKF over-trust drifting odometry; all-`1e6` (B) makes the EKF ignore the wheels entirely (Lecture 1, §1.7).

10. **B** — The EKF synchronizes its inputs by timestamp. The correct stamp is the *measurement acquisition time*, which is the `/joint_states` header stamp — not `now()`, which adds the node's processing/scheduling latency and drifts against the IMU's own acquisition stamp. Misaligned stamps desync the filter (mini-project, "Why this compounds").

11. **B** — `velocity[]` is optional in `sensor_msgs/JointState`; a robust node differences `position[]` across messages: `φ̇ = (φ_now − φ_prev)/dt`. You need at least two messages and a positive `dt` before you can produce a velocity (Exercise 1/2's `_wheel_velocities`).

12. **B** — Odometry integrates its own consistent, biased model, so a closed loop *looks* closed in the odom frame (it "returns to its believed start"). Ground truth reveals the robot actually ended 0.56 m away. The gap is the drift; the odom closure is optimistic about itself precisely because nothing external corrected it (Exercise 3, expected output).

13. **B** — Driving both directions exploits the direction-dependence of the two systematic errors: the wheelbase error (`Eb`) rotates the closure point oppositely for CW vs CCW (the turn signs flip), while the wheel-diameter error (`Ed`) curves the robot the same lateral way regardless of travel direction. Comparing the CW and CCW endpoint centroids lets you solve for `Ed` and `Eb` separately; the scatter around each centroid is the non-systematic error (Lecture 1, §1.6).

</details>

---

If you scored under 9, re-read the lectures for the questions you missed — especially Lecture 1, §1.3 (why heading dominates) and §1.7 (honest covariance), the two ideas that recur through Phase 2. If you scored 12 or 13, you're ready for the [homework](./06-homework.md) and the mini-project.

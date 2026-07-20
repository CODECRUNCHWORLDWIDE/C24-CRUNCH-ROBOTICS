# Week 1 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 2. Answer key is at the bottom — don't peek.

---

**Q1.** What two conditions define a matrix as an element of SO(3) (a proper 3D rotation)?

- A) `R = Rᵀ` and `trace(R) = 3`.
- B) `RᵀR = I` and `det(R) = +1`.
- C) `RᵀR = I` and `det(R) = −1`.
- D) `R⁻¹ = R` and `det(R) = 0`.

---

**Q2.** For a rotation matrix `R`, what is `R⁻¹`, and why does it matter in practice?

- A) `R⁻¹` requires a full matrix solve; it's expensive, so we cache it.
- B) `R⁻¹ = Rᵀ` — inverting a rotation is free, just a transpose.
- C) `R⁻¹ = −R`.
- D) `R⁻¹ = R / det(R)`.

---

**Q3.** Euler's rotation theorem states that any 3D rotation can be expressed as:

- A) A product of exactly three elementary rotations, always.
- B) A single rotation by some angle about some fixed axis.
- C) A reflection followed by a rotation.
- D) A unique set of ZYX Euler angles with no ambiguity.

---

**Q4.** In `q = (cos(θ/2), k·sin(θ/2))`, why the *half* angle? What's the observable consequence?

- A) It's a normalization trick with no physical meaning.
- B) Quaternions double-cover SO(3): a 360° rotation gives `q = (−1,0,0,0)`, not the identity; you must rotate 720° to return `q` to its start. `q` and `−q` are the same rotation.
- C) The half angle makes the quaternion non-unit on purpose.
- D) It only applies to rotations about the z-axis.

---

**Q5.** Why is quaternion multiplication (the Hamilton product) non-commutative?

- A) A floating-point rounding artifact.
- B) The vector part contains a cross product `v₁ × v₂`, which flips sign when operands swap — mirroring the fact that 3D rotations don't commute.
- C) It is actually commutative; the lecture was wrong.
- D) Only JPL-convention quaternions are non-commutative.

---

**Q6.** You read `v' = R₁ R₂ v`. Which rotation is applied to `v` *first*?

- A) `R₁`, because it's written first.
- B) `R₂`, because matrix products apply right-to-left (nearest the vector first).
- C) Neither; they apply simultaneously.
- D) It's ambiguous without knowing the frame.

---

**Q7.** Gimbal lock in a ZYX Euler representation occurs at:

- A) yaw = 0°.
- B) roll = 180°.
- C) pitch = ±90°, where the decomposition drops rank and a rotational DOF is lost.
- D) Never — Euler angles have no singularities.

---

**Q8.** What's the correct field order for `geometry_msgs/Quaternion` in ROS, and why does it bite people?

- A) `(w, x, y, z)` — same as most math, so no issue.
- B) `(x, y, z, w)` — scalar last; math is usually written `(w, x, y, z)`, so a careless tuple assignment swaps the scalar component and produces a wrong rotation.
- C) `(x, y, z)` only — ROS drops the scalar.
- D) Order doesn't matter; ROS normalizes internally.

---

**Q9.** Why is ROS1 considered dead for new robotics work?

- A) It used Python 2 and nobody likes Python 2.
- B) Its central master is a single point of failure, it has no QoS/real-time story, and weak multi-robot/security; ROS2 replaced master+TCP with DDS (no master, rich QoS). Noetic reached EOL in May 2025.
- C) It couldn't run on Linux.
- D) It had no concept of topics.

---

**Q10.** In the ROS2 layer cake, what does the `rmw` layer provide?

- A) The Python syntax for nodes.
- B) An abstraction over the DDS vendor, so the same `rclpy` code runs on Fast-DDS or CycloneDDS unchanged.
- C) The motor-control firmware.
- D) The rviz2 rendering engine.

---

**Q11.** Your `tumbling_pose` node publishes a `PoseStamped`, but in rviz2 the pose *snaps and stutters* instead of rotating smoothly. The most likely cause is:

- A) rviz2 is too slow to render 50 Hz.
- B) The quaternion isn't unit-norm (or `(w,x,y,z)` was assigned into the `(x,y,z,w)` slots), so each frame is a slightly-wrong rotation.
- C) The topic name has a typo.
- D) `frame_id` must be empty for Pose displays.

---

**Q12.** Why should a sensor message's `header.stamp` be set at *acquisition* time, not at publish time after processing?

- A) `now()` is slower than the acquisition clock.
- B) Downstream consumers (tf2, the EKF) trust the stamp; a late stamp tells them the data is newer than it is, injecting motion-proportional error that compounds.
- C) ROS rejects messages stamped after processing.
- D) It makes no difference on a stationary robot, so it never matters.

---

**Q13.** When validating your hand-written `quat_to_matrix` against `scipy`, your test fails for some random quaternions but passes for others. The *most likely* cause, given the math is otherwise right, is:

- A) scipy is buggy.
- B) You didn't handle the **double cover** — `q` and `−q` are the same rotation, so the test must compare up to sign (`np.allclose(M_mine, M_ref)` is fine for the matrix, but a *quaternion* comparison must allow `±`).
- C) NumPy's random seed is wrong.
- D) Rotation matrices are non-deterministic.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — `RᵀR = I` (orthonormal) and `det R = +1` (proper, not a reflection). A `det = −1` orthonormal matrix is a reflection. (Lecture 1 §2.)
2. **B** — The inverse of a rotation is its transpose; inverting is free. This is used constantly in transform math. (Lecture 1 §1–2.)
3. **B** — Euler's rotation theorem: every 3D rotation is a single rotation about a single axis (the axis-angle representation). (Lecture 1 §4.)
4. **B** — The half-angle is why quaternions double-cover SO(3); `q` and `−q` are the same rotation, and a 360° turn gives `−1`. (Lecture 1 §5.2.)
5. **B** — The Hamilton product's vector part has a `v₁ × v₂` cross product, which is anti-commutative; this mirrors 3D rotation non-commutativity. (Lecture 1 §5.4.)
6. **B** — Read products right-to-left: `R₂` (nearest the vector) applies first. (Lecture 1 §2.3.)
7. **C** — At pitch = ±90° the ZYX decomposition is singular: roll and yaw become `atan2(≈0, ≈0)` and a DOF is lost. (Lecture 1 §6.2.)
8. **B** — ROS uses `(x, y, z, w)`; math is usually `(w, x, y, z)`. Mixing them swaps the scalar and corrupts the rotation. (Lecture 1 §5.1, Lecture 2 §3.1.)
9. **B** — No master (DDS, distributed discovery), rich QoS, real-time and multi-robot capability; Noetic hit EOL May 2025. (Lecture 2 §1.2.)
10. **B** — `rmw` abstracts the DDS vendor, making `rclpy`/`rclcpp` code portable across Fast-DDS and CycloneDDS. (Lecture 2 §1.3.)
11. **B** — A non-unit quaternion (or a `(w,x,y,z)`/`(x,y,z,w)` slot swap) makes each frame a slightly-wrong rotation; the half-angle formula guarantees unit-norm, which is why correct math tumbles smoothly. (Lecture 2 §3.2.)
12. **B** — Stamp at acquisition; consumers trust the stamp, and a late one injects motion-proportional, compounding error. (Lecture 2 §3.1.)
13. **B** — The double cover: `q` and `−q` are the same rotation. Comparisons of *quaternions* must allow the sign flip. (Lecture 1 §5.2.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

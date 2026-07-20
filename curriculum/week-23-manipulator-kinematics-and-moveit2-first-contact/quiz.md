# Week 23 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 24. Answer key is at the bottom — don't peek.

---

**Q1.** Forward kinematics maps joints to pose; inverse kinematics maps pose to joints. Which statement is true?

- A) Both are functions: one input, one output.
- B) FK is a function (one answer, always defined); IK is a relation (up to 8 solutions for a 6-DOF arm, or none).
- C) IK is a function; FK is a relation.
- D) Both can have multiple solutions for a generic 6-DOF arm.

---

**Q2.** In the product-of-exponentials FK `T(θ) = exp([S₁]θ₁)···exp([Sₙ]θₙ)·M`, what is `M`?

- A) The mass matrix of the arm.
- B) The base-to-tool transform with all joints at zero (the home configuration).
- C) The manipulability measure.
- D) The product of the DH parameters.

---

**Q3.** Why does the modern literature often prefer product-of-exponentials over the DH convention?

- A) PoE is faster to compute at runtime.
- B) PoE reads its screw axes and home pose straight from the URDF geometry, with no per-link frame-placement ritual and no standard-vs-modified ambiguity.
- C) DH cannot represent prismatic joints.
- D) PoE finds all IK solutions; DH finds only one.

---

**Q4.** Each *column* of the manipulator Jacobian `J(θ)` represents:

- A) One DH parameter.
- B) The end-effector twist produced by moving one joint at unit velocity with the others frozen.
- C) The position of one link.
- D) A singular value of the arm.

---

**Q5.** A singularity is a configuration where:

- A) The arm reaches a joint limit.
- B) The Jacobian loses rank — its smallest singular value goes to zero — so the hand cannot move in some direction no matter the joint velocities.
- C) The IK solver runs out of iterations.
- D) Two links collide.

---

**Q6.** The Yoshikawa manipulability measure `w = sqrt(det(J Jᵀ))`:

- A) Is always 1 for a healthy arm.
- B) Equals the product of the Jacobian's singular values and goes to zero exactly at a singularity.
- C) Is the condition number of the Jacobian.
- D) Measures the arm's payload capacity.

---

**Q7.** Near a singularity, the naive pseudoinverse IK step `Δθ = J⁺e` becomes dangerous because:

- A) It rounds to zero and the arm stops.
- B) The pseudoinverse contains a `1/σ` factor, so as `σ_min → 0` the joint step → infinity — a tiny hand motion commands a huge, unsafe joint slew.
- C) `J⁺` is undefined for non-square Jacobians.
- D) It always converges to the wrong one of the 8 solutions.

---

**Q8.** What does the damping term in damped least squares `Δθ = Jᵀ(J Jᵀ + λ²I)⁻¹e` accomplish?

- A) It speeds up convergence far from singularities.
- B) It bounds the worst-case step amplification at roughly `1/(2λ)` instead of `1/σ_min`, trading a little accuracy for stability near a singularity.
- C) It guarantees finding all 8 IK solutions.
- D) It removes the need for a seed configuration.

---

**Q9.** Which IK family is fastest (microseconds) and returns *all* solutions with no seed, but only exists for arms with the right geometry?

- A) Numerical Jacobian (KDL).
- B) Closed-form analytic IK.
- C) Damped least squares.
- D) RRTConnect.

---

**Q10.** In MoveIt2, what does the `move_group` node do?

- A) It computes IK itself and nothing else.
- B) It orchestrates the kinematics plugin, the planning pipeline (OMPL), the smoother, time-parameterization, and execution behind ROS2 action/service interfaces.
- C) It is the URDF parser.
- D) It is the Gz Sim physics engine.

---

**Q11.** What information lives in the SRDF that the URDF lacks?

- A) Link masses and inertias.
- B) Planning groups, the virtual joint, named poses, and disabled collision pairs.
- C) The visual meshes.
- D) The DDS QoS profiles.

---

**Q12.** A plan-and-execute returns `error_code.val == -2` (`PLANNING_FAILED`). Where do you look first?

- A) The controller — it didn't track the trajectory.
- B) The planning scene and reachability — OMPL found no collision-free path in the time budget (often a stale collision object or an unreachable goal).
- C) The QoS profile of the action topic.
- D) The IMU calibration.

---

**Q13.** Why use the smallest singular value of the Jacobian (not just a SUCCESS/FAILURE flag) when an IK or plan fails?

- A) The flag is unreliable.
- B) The singular value distinguishes "failed because the pose is near a singularity (geometry — no solver tuning fixes it; pick a different goal)" from "failed for a fixable reason (a collision object, a controller)." One diagnosis sends you to a new goal; the other sends you to your URDF.
- C) Singular values are required by the ROS2 API.
- D) It tells you the arm's payload.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — FK is a well-defined function with one answer; IK is a relation with up to 8 solutions (elbow-up/down, wrist-flip, shoulder-left/right) or none. (Lecture 2 §1.)
2. **B** — `M` is the home configuration: the base-to-tool transform with all joints at zero, read straight off the URDF. (Lecture 1 §3.3.)
3. **B** — PoE takes its screw axes and `M` directly from URDF geometry, with no frame-placement rule and no standard-vs-modified DH ambiguity. (Lecture 1 §2–3.)
4. **B** — Column `i` is the end-effector twist from moving joint `i` at unit velocity, others frozen. (Lecture 1 §4.)
5. **B** — The Jacobian loses rank (smallest singular value → 0); some end-effector direction becomes unreachable regardless of joint speed. (Lecture 1 §5.)
6. **B** — `w = sqrt(det(J Jᵀ))` is the product of the singular values (up to the sqrt convention); it's zero exactly at a singularity. (Lecture 1 §5.2.)
7. **B** — The `1/σ` factor in `J⁺` blows up as `σ_min → 0`, commanding an enormous joint slew for a tiny hand motion. (Lecture 2 §3.2.)
8. **B** — `λ²I` keeps the inverse finite at a singularity, bounding amplification at ~`1/(2λ)`; a little accuracy for a lot of stability. (Lecture 2 §3.3.)
9. **B** — Closed-form analytic IK: microseconds, all solutions, no seed, but only for arms with the right geometry (e.g. a spherical wrist). (Lecture 2 §2.)
10. **B** — `move_group` aggregates and orchestrates the kinematics plugin, OMPL, the smoother, time-parameterization, and execution. (Lecture 2 §5.1.)
11. **B** — The SRDF carries planning groups, the virtual joint, named poses, and disabled collision pairs — the semantics the URDF doesn't. (Lecture 2 §5.2.)
12. **B** — `PLANNING_FAILED` means OMPL found no path; look at the planning scene (collision objects) and reachability before anything else. (Lecture 2 §5.5.)
13. **B** — The singular value tells you *why*: a near-singular failure is geometry (no tuning fixes it; pick a new goal); a fixable failure is a collision object or a controller. One number, one direction to look. (Lecture 1 §6.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

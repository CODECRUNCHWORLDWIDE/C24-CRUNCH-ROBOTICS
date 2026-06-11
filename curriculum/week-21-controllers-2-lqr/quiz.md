# Week 21 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 22. Answer key is at the bottom — don't peek.

---

**Q1.** In the state-space model `ẋ = Ax + Bu`, what does the `B` matrix encode?

- A) How the state evolves on its own with no input.
- B) How the control inputs enter the state derivatives — how your command pushes the state.
- C) Which states you can measure.
- D) The cost of control effort.

---

**Q2.** Why must you *linearize* the diff-drive kinematics before applying LQR?

- A) LQR is faster on linear systems.
- B) The true kinematics have `cos θ`/`sin θ` terms (nonlinear), but LQR requires constant `A`/`B`, so you take the Jacobian at an operating point.
- C) Linearization removes the need for a controller.
- D) The robot only moves in straight lines.

---

**Q3.** The controllability matrix `𝒞 = [B, AB, A²B, …]` for the diff-drive error model has full rank at `v_ref = 0.5` but rank-deficient at `v_ref = 0`. What does this mean physically?

- A) The code has a numerical bug at zero speed.
- B) A diff-drive robot cannot correct cross-track (lateral) error while standing still — it must drive forward to turn the error out.
- C) LQR is undefined for moving robots.
- D) The robot is unobservable at 0.5 m/s.

---

**Q4.** In the LQR cost `J = ∫(xᵀQx + uᵀRu) dt`, increasing `Q` while holding `R` fixed makes the controller:

- A) More aggressive — it cares more about killing state error.
- B) Less aggressive — it cares more about gentle actuation.
- C) Unstable.
- D) Unchanged — only `R` affects the gain.

---

**Q5.** What is the point of Bryson's rule (`Q_ii = 1/x_i,max²`, `R_jj = 1/u_j,max²`)?

- A) It guarantees the optimal gain.
- B) It normalizes each cost term by what "bad" means for that quantity, so terms in different units (meters, radians, rad/s) add up comparably — a principled, units-aware starting point.
- C) It eliminates the need to solve the Riccati equation.
- D) It sets all gains to 1.

---

**Q6.** The optimal LQR gain is recovered from the Riccati solution `P` by:

- A) `K = P`
- B) `K = R⁻¹BᵀP`
- C) `K = AᵀP + PA`
- D) `K = Q⁻¹P`

---

**Q7.** You solve LQR and the closed-loop eigenvalues of `A − BK` are `[+0.3, −2.1]`. What do you do?

- A) Ship it — one stable eigenvalue is enough.
- B) Do **not** put this gain on a robot — a positive-real-part eigenvalue means the closed loop is unstable; your model or cost is wrong.
- C) Increase the loop rate.
- D) Switch to discrete-time LQR.

---

**Q8.** Pure LQR leaves a steady-state error against a persistent disturbance. The fix, analogous to PID's integral term, is:

- A) Increase `R`.
- B) Augment the state with the integral of the tracking error and run LQR on the bigger system (LQI).
- C) Switch to `solve_discrete_are`.
- D) There is no fix; LQR cannot track.

---

**Q9.** Why does gain scheduling exist for the diff-drive LQR?

- A) To make the code run faster.
- B) Because the linearization (and therefore `A`, and therefore the optimal `K`) depends on the operating point — `v_ref` sits inside `A` — so one fixed gain is a compromise across the speed range.
- C) Because LQR is unstable at high speed.
- D) To avoid solving the Riccati equation.

---

**Q10.** When does LQR genuinely beat a heading-only PID on a *curved* path?

- A) Never; they're identical.
- B) When the cross-track and heading errors couple (the `v_ref` term) — LQR's model knows the coupling and trades the two errors off optimally, while a heading PID fights itself.
- C) Only on straight lines.
- D) Only when the PID has no integral term.

---

**Q11.** The Kalman filter (LQE) is described as the "dual" of LQR because:

- A) They are unrelated but both use matrices.
- B) The estimator's Riccati equation is the controller's with `A → Aᵀ`, `B → Cᵀ`, `Q → W`, `R → V` — the same machinery on the transposed system, with controllability becoming observability.
- C) The Kalman filter is slower.
- D) LQR estimates state and Kalman controls it.

---

**Q12.** The separation principle states that:

- A) You must co-design the estimator and controller jointly.
- B) You can design the optimal estimator and the optimal controller independently and combine them, and the result is still optimal — which is why estimation and control can be separate packages in your stack.
- C) The estimator and controller must run on separate computers.
- D) LQR and PID cannot be combined.

---

**Q13.** What is the one thing LQR fundamentally *cannot* do, that motivates MPC next week?

- A) Control multiple states at once.
- B) Respect hard constraints — the quadratic cost has no notion of a hard velocity/acceleration/obstacle limit, so LQR will happily command past the actuator's limit or steer through an obstacle.
- C) Achieve zero steady-state error.
- D) Run in real time.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — `B` is the input matrix: how your `m` commands enter the `n` state derivatives. (Lecture 1 §1.2.)
2. **B** — The true kinematics are nonlinear; LQR needs constant `A`/`B`, obtained by Jacobian linearization at an operating point. (Lecture 1 §2.)
3. **B** — Uncontrollability at zero speed is real physics: a diff-drive robot can't fix lateral error without driving forward. (Lecture 1 §3.1.)
4. **A** — Bigger `Q` → care more about state error → more aggressive. Only the `Q/R` ratio matters. (Lecture 1 §4.2.)
5. **B** — Bryson's rule normalizes each term by its "bad" value, making different-unit terms comparable; a units-aware starting point. (Lecture 1 §4.3.)
6. **B** — `K = R⁻¹BᵀP`, with `P` the Riccati solution. (Lecture 2 §1.1.)
7. **B** — A positive-real-part closed-loop eigenvalue means instability; don't deploy it — the model or cost is wrong. (Lecture 2 §1.3.)
8. **B** — State augmentation with the integral of error (LQI), the LQR analog of PID's I term. (Lecture 2 §2.2.)
9. **B** — `K` depends on the operating point (`v_ref` is inside `A`); scheduling interpolates solved gains across the envelope. (Lecture 2 §3.)
10. **B** — On a curve the errors couple; LQR's model exploits the coupling, a heading PID does not. (Lecture 2 §4 / Exercise 3.)
11. **B** — Same Riccati machinery on the transposed system; controllability ↔ observability. (Lecture 2 §5.1.)
12. **B** — Independent design of optimal estimator and controller; the basis for modular autonomy stacks. (Lecture 2 §5.2.)
13. **B** — LQR's quadratic cost can't express hard constraints; MPC re-optimizes with explicit constraints each step. (Lecture 2 §6 / Week 22.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

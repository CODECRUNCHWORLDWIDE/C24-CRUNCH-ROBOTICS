# Week 45 — Quiz

Thirteen questions on system-design method, the technical-interview categories, and the EKF. Take it with your lecture notes closed. Aim for 11/13 before Week 46. Answer key at the bottom — don't peek.

---

**Q1.** In a robotics system-design interview, what is the *first* thing you should do after hearing "design the autonomy stack for a warehouse AMR"?

- A) Start drawing the box diagram so the interviewer sees progress.
- B) Name the sensors you'd use.
- C) Ask clarifying questions to pin down payload, shared-space, and fleet size before designing anything.
- D) State that it depends and wait for more information.

---

**Q2.** Why is connecting the latency budget to stopping distance the highest-value move in the warehouse-AMR design?

- A) It shows you can do arithmetic under pressure.
- B) It ties software timing to physics and to *why the safety layer must be independent of the perception pipeline* — the core safety argument.
- C) Interviewers always ask for stopping distance explicitly.
- D) It lets you skip drawing the box diagram.

---

**Q3.** Why should the safety-rated LiDAR be a *separate* sensor from the perception LiDAR on a shared-space AMR?

- A) Two LiDARs give better coverage.
- B) Safety functions must ride on a certified, redundant path that can stop the robot regardless of the (uncertified) perception software stack.
- C) Perception LiDARs can't see obstacles.
- D) It's cheaper to use two cheap LiDARs than one good one.

---

**Q4.** In the EKF predict step, how is the *mean* propagated?

- A) Through the linearized model: `x̂⁻ = F x̂`.
- B) Through the full nonlinear motion model: `x̂⁻ = f(x̂, u)`.
- C) It isn't propagated; only the covariance changes.
- D) Through the measurement Jacobian `H`.

---

**Q5.** What is the EKF predict covariance equation, and what does each term do?

- A) `P⁻ = F P Fᵀ + Q` — `F P Fᵀ` reshapes uncertainty via the linearized dynamics; `Q` injects process noise. Uncertainty grows.
- B) `P⁻ = H P Hᵀ + R` — maps state into measurement space.
- C) `P⁻ = (I − K H) P` — the corrected covariance after a measurement.
- D) `P⁻ = P − K H P` — uncertainty always shrinks in predict.

---

**Q6.** The matrices `F` and `H` in an EKF are:

- A) Fixed constants chosen at design time.
- B) The Jacobians ∂f/∂x and ∂h/∂x, evaluated at the current state estimate each cycle.
- C) The process- and measurement-noise covariances.
- D) The Kalman gain and its inverse.

---

**Q7.** A candidate forgets to angle-wrap the bearing innovation in a range-bearing EKF. What happens?

- A) Nothing; the filter is robust to it.
- B) The filter runs slightly slower.
- C) When the true bearing residual crosses ±π, the unwrapped innovation jumps by ~2π, injecting a huge false correction that can diverge the filter.
- D) The covariance becomes non-symmetric.

---

**Q8.** When does EKF linearization break down, and what's a reasonable fix?

- A) It never breaks; the EKF is exact.
- B) When the model is strongly nonlinear over a timestep relative to the uncertainty — the first-order Taylor approximation misses curvature; fix with a shorter timestep or switch to a UKF.
- C) Only when `Q` is too large; fix by setting `Q = 0`.
- D) When the sensor rate exceeds the control rate; fix by downsampling.

---

**Q9.** "Why EKF instead of a factor graph?" — which answer demonstrates real understanding?

- A) "Factor graphs are too new to trust."
- B) "The EKF marginalizes the past into one Gaussian — constant-time, great for the 100 Hz on-robot estimate — while a factor graph smooths over a window and relinearizes for accuracy and loop closures, at higher cost. Use the EKF for the local estimate, the graph for the SLAM back-end."
- C) "EKF and factor graphs are the same thing."
- D) "Factor graphs can't handle nonlinear models."

---

**Q10.** Why would you pick MPC over LQR for a mobile base in a tight aisle?

- A) MPC is always more accurate than LQR.
- B) MPC handles hard constraints (actuator limits, lateral corridor bounds) inside the optimization; LQR is unconstrained and clamping its output breaks its optimality/stability guarantee.
- C) LQR can't be implemented in ROS 2.
- D) MPC needs no model.

---

**Q11.** What is a singularity of a manipulator Jacobian, and how do you handle it in IK?

- A) A point where `det(J) → 0`; the arm loses a Cartesian DOF and naive `J⁻¹` blows up — handle with damped least squares `q̇ = Jᵀ(J Jᵀ + λ²I)⁻¹ẋ`.
- B) A point where the arm has maximum reach and maximum precision.
- C) A software bug in the FK solver.
- D) A configuration where all joint angles are zero.

---

**Q12.** In the "five technical projects" résumé conversation, what is the single most common way candidates fail?

- A) Telling too few stories.
- B) Overclaiming — saying they did something ("I built a Kalman filter," "I used MPC") they cannot defend one level deeper than the story.
- C) Using the STAR structure.
- D) Mentioning specific latency numbers.

---

**Q13.** You hit the genuine edge of your knowledge during a deep-dive. What's the *passing* response?

- A) Confidently make something up that sounds plausible.
- B) "I'm not sure" and stop.
- C) "I didn't go deeper than X on that — here's how I'd find out: I'd measure Y."
- D) Change the subject to a project you know better.

---

## Answer key

**Q1 — C.** Requirements first. Designing before clarifying is the classic junior tell; the first five minutes are clarify + scope, no drawing.

**Q2 — B.** The latency→stopping-distance→independent-safety-layer chain is the single most senior connection you can make in a robotics system-design round. It grounds software timing in physics and motivates the entire safety architecture.

**Q3 — B.** Safety must not depend on the smart parts. The certified stop rides a separate, redundant, certifiable path; perception is rich but uncertified. Conflating them is disqualifying in a shared-space design.

**Q4 — B.** The mean is propagated through the *full nonlinear* model `f(x̂, u)`. Only the *covariance* uses the linearization. Propagating the mean with `F x̂` is the number-one EKF mistake and reveals you don't understand why it's "extended."

**Q5 — A.** `P⁻ = F P Fᵀ + Q`. The linearized dynamics reshape/rotate the uncertainty ellipse; `Q` adds process noise. Prediction always increases uncertainty. (B is the innovation covariance; C is the update covariance.)

**Q6 — B.** `F = ∂f/∂x`, `H = ∂h/∂x`, both evaluated at the current estimate every cycle. They are *not* constants (that would be a plain KF) and not the noise covariances (`Q`, `R`).

**Q7 — C.** Crossing ±π makes the unwrapped residual jump ~2π, a massive false innovation that corrupts the update and routinely diverges the filter. Always wrap the bearing innovation to (−π, π].

**Q8 — B.** Strong nonlinearity over a step relative to uncertainty breaks the first-order Taylor approximation; the covariance becomes wrong and the filter can get overconfident. Shorter timestep, UKF (sigma points), or iterated EKF are the fixes.

**Q9 — B.** EKF = marginalize (constant-time, real-time local estimate); factor graph = smooth/relinearize over a window (accurate, loop closures, more cost). Knowing the marginalize-vs-smooth trade-off and *where each lives in the stack* is the real-understanding answer.

**Q10 — B.** MPC encodes hard constraints inside the optimization. Clamping LQR's output after the fact breaks the optimality the Riccati solution assumed and can destabilize near saturation. That's the constraint-handling argument for MPC.

**Q11 — A.** `det(J) → 0` at a singularity (arm stretched/folded); a Cartesian DOF is lost and `J⁻¹` blows up. Damped least squares trades a little tracking error for bounded joint velocities near the singularity.

**Q12 — B.** Overclaiming. The interviewer's whole job is to find the gap between what you claim and what you can defend. Claim less, defend all of it.

**Q13 — C.** "Here's how I'd find out: I'd measure Y" reads as senior and is a *pass*. Bluffing (A) gets caught and is the real fail; bare "I'm not sure" (B) is weak; deflecting (D) is transparent.

---

*Score 11+/13 to move on. If you missed any EKF question (Q4–Q9), re-do `exercises/exercise-02-ekf-predict-on-the-board.py` before Thursday's technical mock — that material is the centerpiece of the round.*

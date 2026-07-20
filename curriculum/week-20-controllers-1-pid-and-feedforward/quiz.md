# Week 20 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 21. Answer key is at the bottom — don't peek.

---

**Q1.** A pure proportional controller settles *near* but not *on* the setpoint, leaving a permanent offset. Why?

- A) Proportional control is unstable by definition.
- B) At steady state the plant needs a nonzero input to hold position, but `Kp·e` is zero only when `e` is zero — so it settles at the error where `Kp·e` equals the needed input.
- C) The derivative term cancels the proportional term.
- D) The offset is measurement noise, not a real effect.

---

**Q2.** What does the **integral** term buy you, and what is its signature failure mode?

- A) It speeds up the response; its failure mode is noise amplification.
- B) It drives steady-state error to zero; its failure mode is integrator wind-up.
- C) It adds damping; its failure mode is derivative kick.
- D) It rejects high-frequency noise; its failure mode is instability.

---

**Q3.** In a discrete PID, you write `integral += error` instead of `integral += error * dt`. What goes wrong?

- A) Nothing; `dt` is a constant and cancels out.
- B) Your effective `Ki` secretly scales with the loop rate, so gains tuned at 50 Hz behave completely differently at 100 Hz.
- C) The integral overflows immediately.
- D) The derivative term stops working.

---

**Q4.** Integrator wind-up happens specifically when:

- A) The derivative gain is too high.
- B) The actuator saturates while the integral keeps accumulating error it can't act on, then has to unwind — causing large overshoot.
- C) The setpoint changes too slowly.
- D) The measurement is noisy.

---

**Q5.** Back-calculation anti-windup works by:

- A) Setting `Ki` to zero whenever the error is large.
- B) Feeding the difference between the saturated and unsaturated output back into the integral, so the integral is continuously corrected toward a value the actuator can actually deliver.
- C) Clamping the measurement instead of the command.
- D) Switching to a faster loop rate when saturated.

---

**Q6.** Derivative kick is caused by, and fixed by:

- A) Caused by noise; fixed by raising `Kd`.
- B) Caused by a setpoint step differentiating to an impulse; fixed by differentiating the measurement instead of the error.
- C) Caused by the integral; fixed by anti-windup.
- D) Caused by actuator saturation; fixed by a deadband.

---

**Q7.** Why is a raw (unfiltered) derivative term almost never shippable on real hardware?

- A) It uses too much CPU.
- B) Differentiation amplifies high-frequency measurement noise, injecting chatter into the actuators.
- C) The derivative is always zero in discrete time.
- D) It conflicts with the integral term.

---

**Q8.** What is the essential difference between **feedforward** and **feedback**?

- A) Feedforward uses the integral; feedback uses the derivative.
- B) Feedforward computes a command from the *reference* (predictive, before error exists); feedback reacts to the *error* (after it exists).
- C) They are two names for the same thing.
- D) Feedforward only works on linear plants.

---

**Q9.** Where do feedforward gains (like the velocity feedforward `Kv`) come from?

- A) From the same trial-and-error tuning as the PID gains.
- B) From a *model* of the plant — `Kv` is approximately the inverse of the plant's steady-state gain, `Ka` is approximately its inertia/mass — identified or computed, not tuned by feel.
- C) From the Ziegler–Nichols table.
- D) They are always 1.0.

---

**Q10.** Why does *tracking* a moving reference need feedforward while *regulation* of a fixed setpoint often does not?

- A) Regulation is a harder problem than tracking.
- B) Feedback alone always lags a moving target — it can only respond after error builds — whereas a fixed setpoint can be held by the integral; feedforward cancels the tracking lag at the source.
- C) Tracking doesn't use an integral term.
- D) Feedforward is illegal in regulation.

---

**Q11.** The honest take on Ziegler–Nichols tuning is:

- A) Its gains are conservative and safe to ship directly.
- B) It gives a fast starting point from one experiment, but its gains are aggressive (≈25% overshoot target), usually too hot to ship, and finding the ultimate gain means driving the system to sustained oscillation — do it in sim.
- C) It only works for first-order plants.
- D) It is more accurate than optimization-based tuning.

---

**Q12.** For a second-order system you measure ~8% overshoot. Using `overshoot ≈ exp(−πζ/√(1−ζ²))`, the effective damping ratio ζ is approximately:

- A) 0.1
- B) 0.62
- C) 0.95
- D) 1.4

---

**Q13.** In `ros2_control`, why write your controller as a plugin loaded by the `controller_manager` instead of a node that publishes `/cmd_vel`?

- A) Plugins run faster because they're written in C++.
- B) The manager owns the real-time update loop, hands `update` the true elapsed period, arbitrates exclusive access to `command_interface`s (so two controllers can't fight over the same wheel), and lets you switch controllers at runtime — none of which a `/cmd_vel`-racing node gets.
- C) Topics are deprecated in ROS2 Jazzy.
- D) It's the only way to read the IMU.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — At steady state the plant needs a nonzero input; `Kp·e=0` only at `e=0`, so it settles at the offset where the proportional push equals the needed input. (Lecture 1 §2.1.)
2. **B** — Integral zeroes steady-state error (it keeps pushing while any error remains); its signature failure is wind-up. (Lecture 1 §2.2, §4.)
3. **B** — Dropping the `dt` makes effective `Ki` rate-dependent; a controller tuned at one loop rate misbehaves at another. (Lecture 1 §3.)
4. **B** — Wind-up is the interaction of a saturated actuator and an integrator that keeps accumulating; the stored push then dumps as overshoot. (Lecture 1 §4.1.)
5. **B** — Back-calculation bleeds the saturation excess `(u − u_unsat)` back into the integral so it never exceeds what the actuator can justify. (Lecture 1 §4.3.)
6. **B** — A setpoint step → impulse in the error derivative; differentiate the measurement (`−dy/dt`) instead, since `de/dt = dr/dt − dy/dt` and `dr/dt` is the kick. (Lecture 1 §6.)
7. **B** — Differentiation amplifies high-frequency noise; you need a first-order filter on the derivative term. (Lecture 1 §5.)
8. **B** — Feedforward is predictive (from the reference); feedback is reactive (from the error). The two-DOF structure. (Lecture 2 §1.1.)
9. **B** — Feedforward gains come from the model/physics (identified or computed), not from tuning. This is the bridge to LQR/MPC. (Lecture 2 §1.3.)
10. **B** — Feedback always lags a moving reference; a fixed setpoint is held by the integral; feedforward cancels the tracking lag. (Lecture 2 §1.4.)
11. **B** — Z–N is a fast starting point with aggressive gains you back off; finding `Ku` means sustained oscillation, so do it in sim. (Lecture 2 §2.2.)
12. **B** — Solving `0.08 = exp(−πζ/√(1−ζ²))` gives ζ ≈ 0.62. (Lecture 1 §8.)
13. **B** — The manager gives you the real-time loop, the true `period`, exclusive interface arbitration, and runtime controller switching. (Lecture 2 §3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

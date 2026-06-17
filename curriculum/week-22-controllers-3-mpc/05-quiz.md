# Week 22 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 23. Answer key is at the bottom — don't peek.

---

**Q1.** The receding-horizon principle is:

- A) Solve once at startup and execute the whole plan open-loop.
- B) Predict `N` steps, optimize the whole input sequence, apply *only the first* input, then re-solve next step from the new measured state.
- C) Apply all `N` inputs, then re-plan after `N` steps.
- D) Use the last input forever.

---

**Q2.** Why does MPC apply only the *first* input of the optimized sequence and discard the rest?

- A) To save memory.
- B) The plan is optimal only given the (slightly wrong) model and the current state; re-solving every step from fresh state folds the latest reality back in — that's what makes MPC a feedback controller.
- C) Because the later inputs are always zero.
- D) The solver only returns the first input.

---

**Q3.** In the MPC QP, the dynamics `x_{k+1} = A x_k + B u_k` appear as:

- A) The objective function.
- B) Equality constraints linking consecutive predicted states.
- C) Inequality constraints.
- D) The terminal cost.

---

**Q4.** What is the categorical difference between a hard constraint and a soft penalty in the cost?

- A) None — they're interchangeable.
- B) A penalty *discourages* a behavior but the optimizer will accept it if it pays off; a hard constraint *forbids* it — the solver only searches feasible solutions. Safety limits need the hard version.
- C) A hard constraint is faster to solve.
- D) A soft penalty is only for the terminal state.

---

**Q5.** You call `prob.solve()` and `prob.status` is `"infeasible"`. What must you do?

- A) Use `u[:,0].value` anyway.
- B) Never send a command from an infeasible solve (it's `None`) — recover: soften a constraint, shrink the horizon, or fall back to a safe controller.
- C) Increase `Q`.
- D) Ignore it; infeasible means optimal.

---

**Q6.** Obstacle avoidance ("stay outside this disk") is non-convex. The standard MPC trick to keep the QP convex is:

- A) Ignore the obstacle.
- B) Linearize it into a half-plane (tangent-line) constraint each step, re-computed as the robot moves.
- C) Use a much bigger horizon.
- D) Switch to a hard velocity limit instead.

---

**Q7.** An unconstrained MPC with a long horizon and the LQR terminal cost produces:

- A) A random control law.
- B) Exactly the LQR control law — which is the standard correctness check for your MPC machinery.
- C) A more aggressive law than LQR.
- D) An infeasible problem.

---

**Q8.** Why is `cvxpy` excellent for *learning* MPC but wrong for the real-time inner loop?

- A) It can't express constraints.
- B) It's a modeling layer that re-canonicalizes the problem every solve (real overhead), which can blow a tight control budget; deployment moves to OSQP-direct or `acados`.
- C) It only runs on Windows.
- D) It doesn't support quadratic costs.

---

**Q9.** When profiling MPC solve time, why report the p95 / max and not just the mean?

- A) The mean is harder to compute.
- B) A control loop has a hard deadline *every* period; if the mean fits but the tail exceeds the budget, you miss the deadline periodically — a dropped/stale command. You budget for the tail.
- C) p95 is always equal to the mean.
- D) The max is irrelevant.

---

**Q10.** Warm-starting speeds up successive MPC solves because:

- A) It skips the constraints.
- B) The step `t+1` problem is nearly the step `t` problem shifted one step, so last solution (shifted) is an excellent initial guess and the solver converges in far fewer iterations.
- C) It uses a faster solver.
- D) It reduces the horizon automatically.

---

**Q11.** The `acados` real-time-iteration (RTI) scheme makes nonlinear MPC real-time by:

- A) Solving the problem exactly to convergence every step.
- B) Doing exactly *one* SQP iteration per control step (exploiting the warm start), so the solve always returns within a bounded time.
- C) Removing all constraints.
- D) Running on the GPU only.

---

**Q12.** Recursive feasibility is the guarantee that:

- A) The solver always returns `optimal`.
- B) If the MPC is feasible now, it stays feasible at every future step — it can't optimize itself into a state where no feasible plan exists. A terminal constraint set provides it.
- C) The MPC converges to the LQR.
- D) The horizon never changes.

---

**Q13.** When should you reach for MPC instead of LQR?

- A) Always — MPC is strictly better.
- B) When you genuinely need exact hard-constraint satisfaction (operating near limits, obstacles, people) or strong preview of an upcoming reference; otherwise the online solve, latency budget, and feasibility failure mode are unnecessary cost.
- C) Only for single-loop problems.
- D) Never — LQR can do everything MPC can.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Predict `N`, optimize the sequence, apply only `u₀`, re-solve from fresh state. (Lecture 1 §1.1.)
2. **B** — Re-solving from measured state every step is what makes it feedback; the plan is only locally trustworthy. (Lecture 1 §1.2.)
3. **B** — The dynamics are equality constraints linking consecutive predicted states. (Lecture 1 §2.2.)
4. **B** — Penalty discourages, constraint forbids; safety limits need hard constraints. (Lecture 1 §4.1.)
5. **B** — Never command from an infeasible solve; detect via status and recover. (Lecture 1 §3.1 / Lecture 2 §4.1.)
6. **B** — Linearize the obstacle into a per-step half-plane to keep the QP convex. (Lecture 1 §4.2.)
7. **B** — Unconstrained + long horizon + LQR terminal cost = LQR; the correctness check. (Lecture 1 §5.)
8. **B** — `cvxpy`'s per-solve canonicalization overhead can blow a tight budget; deploy with OSQP/`acados`. (Lecture 2 §3.1.)
9. **B** — Hard deadline every period; the tail misses it, so budget for p95/max. (Lecture 2 §3.2.)
10. **B** — Successive problems are nearly identical; the shifted last solution warm-starts the solver. (Lecture 2 §3.4.)
11. **B** — RTI does one SQP iteration per step, bounding the time and guaranteeing on-time return. (Lecture 2 §3.5 / §4.2.)
12. **B** — Recursive feasibility = stays feasible forever; terminal set provides it. (Lecture 2 §4.3.)
13. **B** — Reach for MPC when you need hard constraints or preview; else it's over-engineering. (Lecture 2 §2.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).

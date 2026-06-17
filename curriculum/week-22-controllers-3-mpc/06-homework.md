# Week 22 Homework

Six problems that drive the MPC concepts into your fingers. The full set should take about **5 hours**. Work in your Week 22 Git repository (the same workspace as the exercises and the `crunchbot_control` mini-project — MPC joins the PID and LQR) so every problem produces at least one commit you can point to at the Phase 3 milestone in Week 24.

The headline deliverable is **Problem 4 — the latency-budget writeup** (the syllabus-named artifact). Treat it as the document a reviewer reads.

Each problem includes a short **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Have `numpy`, `scipy`, `matplotlib`, and `cvxpy` installed (`pip install cvxpy numpy scipy matplotlib`). All six are pure-Python; the bicycle MPC from Exercise 3 is your base for several.

---

## Problem 1 — The horizon sweep

**Problem statement.** Take the bicycle MPC (Exercise 3) and sweep the horizon `N` over several values (e.g. 5, 10, 15, 20, 30). For each, record the RMS cross-track error on the figure-8 *and* the p95 solve time. Plot tracking quality and solve time against `N` on one figure (twin axes).

**Acceptance criteria.**

- A plot `horizon_sweep.png` with RMS cross-track error and p95 solve time vs. `N`.
- A note in `notes/week-22/horizon-sweep.md` identifying the "knee" — the `N` beyond which tracking barely improves but solve time keeps climbing.
- One sentence on the trade-off: longer horizon = more preview = better tracking, but a bigger, slower QP.
- Committed.

**Hint.** You'll see tracking error drop sharply then plateau as `N` grows (more preview helps, up to a point), while solve time climbs faster than linearly. The knee is where you'd set `N` in practice — enough preview, smallest solve. This *is* MPC tuning.

**Estimated time.** 45 minutes.

---

## Problem 2 — Make a constraint bind, then soften it

**Problem statement.** Using the constrained double-integrator MPC (Exercise 2), tighten the velocity limit until the QP becomes *infeasible* for a large step (the constraints can't all be met). Then convert the velocity limit to a *soft* constraint (slack + penalty, Lecture 1 §4.3) and show the QP is feasible again, with the slack staying near zero except when the hard version was impossible.

**Acceptance criteria.**

- A demonstration that the hard-constrained QP returns `infeasible` for your tightened case.
- The soft-constrained version returns `optimal` for the same case, with the slack variable's value logged (near zero normally, positive only when forced).
- A note in `notes/week-22/soft-constraints.md` explaining when you'd hard-constrain (truly inviolable) vs. soft-constrain (merely preferred).
- Committed.

**Hint.** Add `s = cp.Variable(nonneg=True)`, replace `x[1,k] <= v_max` with `x[1,k] <= v_max + s`, and add `1e4 * s` to the cost. Log `s.value` — it's the "how much did I have to cheat" signal.

**Estimated time.** 45 minutes.

---

## Problem 3 — MPC vs LQR vs PID, three-way

**Problem statement.** Run all three controllers — PID (Week 20), LQR (Week 21), MPC (this week) — on the same figure-8 reference, same start offset, same speed, same actuator saturation. Report RMS cross-track error and RMS control effort for all three, and note which respects a hard velocity limit and which merely clips at it.

**Acceptance criteria.**

- A table in `notes/week-22/three-way.md` with RMS cross-track, RMS effort, and "respects hard v-limit? (yes/clips/no)" for PID, LQR, MPC.
- A path-overlay plot of all three.
- A sentence on when each is the right choice (PID: single loop; LQR: coupled, unconstrained; MPC: constraints/preview).
- Committed.

**Hint.** The MPC respects the velocity limit as a true constraint; the PID/LQR can only *clip* their output at the limit after the fact (which is a crude, suboptimal approximation of a constraint). Make the difference visible by choosing a path segment that demands more than the limit allows.

**Estimated time.** 50 minutes.

---

## Problem 4 — The latency-budget writeup (headline deliverable)

**Problem statement.** This is the syllabus deliverable. Profile your bicycle MPC's solve time and write `notes/week-22/latency-budget.md` against this template:

1. **The setup** — horizon `N`, `dt`, state/input dimensions, constraint count, control rate, and therefore the per-step budget (e.g. 20 Hz → 50 ms). State the hardware you profiled on (your laptop, and what you'd expect on an Orin Nano — note the syllabus targets the Orin).
2. **The measurement** — mean / p95 / max solve time over a full figure-8 run, with the p95 compared to the budget as a percentage.
3. **The drivers** — how `N` and constraint count moved the solve time (reference Problem 1's sweep).
4. **The optimizations** — what you tried (warm-starting, shrinking `N`) and the before/after numbers.
5. **The verdict** — is this MPC deployable at this rate on this hardware? If not, what's the path (cut `N`, OSQP-direct, `acados`)?

**Acceptance criteria.**

- `notes/week-22/latency-budget.md` exists with all five sections, roughly one to two pages.
- The p95 (not just the mean) is reported and compared to a stated budget.
- At least one before/after optimization is documented with numbers.
- The verdict is concrete (a rate + horizon at which it's deployable, or a clear "needs `acados`").
- Committed.

**Hint.** Use Exercise 3's `--profile`. Be honest about `cvxpy`'s overhead — on a laptop it may already be near or over a tight budget, which is the *real lesson* and the reason `acados` exists. "Deployable after cutting `N` to 8 and warm-starting, or fully with `acados`" is a fine, honest verdict.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Infeasibility detection and recovery

**Problem statement.** Implement the infeasibility-recovery discipline (Lecture 2 §4.1). On the bicycle MPC, check `prob.status` every step. When the status is not `optimal`, fall back to a safe command (a braking law that decelerates within the limits, or hold the last feasible input). Force an infeasible step (tighten a constraint or place an unavoidable obstacle) and show the recovery fires.

**Acceptance criteria.**

- A controller that checks `prob.status` every step and never sends a command from a non-`optimal` solve.
- A demonstrated infeasible step where the fallback command is used instead, logged.
- A note in `notes/week-22/infeasibility.md` describing your recovery hierarchy (soft constraints → fallback controller → stop) and why "send nothing" is not an option on a moving robot.
- Committed.

**Hint.** The fallback must *always* produce a command — a braking law `a = −k·v` clamped to `[−A_MAX, A_MAX]` always returns something safe. The point: an MPC controller is the QP *plus* a guaranteed-available fallback, never the QP alone.

**Estimated time.** 45 minutes.

---

## Problem 6 — Read a production predictive controller

**Problem statement.** Open the Nav2 MPPI controller (linked in resources) or the `acados` bicycle/racecar example. Read enough to answer: how does it formulate the problem, how does it handle constraints, and how does it stay real-time? Write a short reading note contrasting it with your `cvxpy` QP-MPC.

**Acceptance criteria.**

- A note in `notes/week-22/production-mpc-read.md` that: names the controller you read; describes its approach to the prediction, constraints, and real-time guarantee; and contrasts it with your `cvxpy` QP-MPC (e.g. MPPI is sampling-based, not a QP; `acados` codegens and uses RTI).
- One sentence on what you'd adopt from it for a real deployment.
- Committed.

**Hint.** Nav2 MPPI is *sampling-based* (it rolls out many random control sequences and weights them) rather than solving a QP — a different MPC family worth understanding, and one that parallelizes well on a GPU. `acados` is the QP/SQP family you learned, made real-time. Either contrast is instructive.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Horizon sweep | 45 min |
| 2 — Bind then soften a constraint | 45 min |
| 3 — MPC vs LQR vs PID | 50 min |
| 4 — Latency-budget writeup (headline) | 1 h 15 min |
| 5 — Infeasibility recovery | 45 min |
| 6 — Read a production MPC | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_control` [mini-project](./07-mini-project/00-overview.md) now hosts all three controllers — PID, LQR, and MPC — for the Phase 3 milestone in Week 24. Then take the [quiz](./05-quiz.md) with your notes closed.

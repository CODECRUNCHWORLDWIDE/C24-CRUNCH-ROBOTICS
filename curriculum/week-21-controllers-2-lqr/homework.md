# Week 21 Homework

Six problems that drive the LQR concepts into your fingers. The full set should take about **5 hours**. Work in your Week 21 Git repository (the same workspace as the exercises and the `crunchbot_control` mini-project — LQR drops in beside last week's PID) so every problem produces at least one commit you can point to at the Phase 3 milestone in Week 24.

The headline deliverable is **Problem 4 — the LQR-vs-PID comparison writeup** (the syllabus-named artifact). Treat it as the document a reviewer reads.

Each problem includes a short **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Have `numpy`, `scipy`, `matplotlib`, and `control` installed (`pip install numpy scipy matplotlib control`). Problems 4 and 6 can run against your **week-3 robot** in Gz Sim; the rest are pure computation. Exercise 3's `--sim` is the fallback — say so in your writeup if you use it.

---

## Problem 1 — Sweep the cost, watch the poles move

**Problem statement.** For the diff-drive error model at `v_ref = 0.5`, solve LQR for a sweep of `Q[0,0]` values (cross-track penalty) spanning two orders of magnitude, holding `R` fixed. For each, record the gain `K` and the closed-loop eigenvalues. Plot the eigenvalue locations in the complex plane as `Q[0,0]` increases.

**Acceptance criteria.**

- A plot `pole_sweep.png` showing the closed-loop eigenvalues moving as `Q[0,0]` grows (they move left — faster, more aggressive).
- A table in `notes/week-21/cost-sweep.md` of `Q[0,0]` → `K` → eigenvalues for at least five values.
- A one-sentence note connecting "bigger `Q[0,0]`" to "poles further left" to "faster cross-track correction, bigger commands."
- Committed.

**Hint.** Reuse Exercise 2's `lqr` and the eigenvalue check. The poles starting near the imaginary axis (sluggish) and marching left (snappy) as you raise `Q` is the LQR analog of raising `Kp` in PID — and you get to *see* it.

**Estimated time.** 40 minutes.

---

## Problem 2 — Verify the Riccati solution by substitution

**Problem statement.** Solve LQR for the diff-drive model, then *verify* that the `P` returned by `solve_continuous_are` actually satisfies the algebraic Riccati equation `AᵀP + PA − PBR⁻¹BᵀP + Q = 0` by substituting it back in and checking the residual is ~0. Also verify `K = R⁻¹BᵀP` matches `control.lqr`.

**Acceptance criteria.**

- A script `verify_riccati.py` that computes the Riccati residual matrix and asserts its norm is below a small tolerance (e.g. `1e-8`).
- The script confirms your `K` matches `control.lqr`'s `K`.
- A note in `notes/week-21/riccati-verify.md` with the residual norm and the two gains side by side.
- Committed.

**Hint.** `residual = A.T @ P + P @ A - P @ B @ np.linalg.inv(R) @ B.T @ P + Q`; check `np.linalg.norm(residual)`. If it's not ~0, you mis-typed the equation — a great way to internalize it.

**Estimated time.** 30 minutes.

---

## Problem 3 — Add integral action and reject a disturbance

**Problem statement.** Build the LQI controller (Lecture 2 §2.2): augment the state with the integral of cross-track error and solve LQR on the augmented system. Inject a *constant* cross-track disturbance (a simulated wheel-calibration bias). Show that plain LQR leaves a steady-state offset and LQI drives it to zero.

**Acceptance criteria.**

- A plot showing cross-track error vs. time for plain LQR (settles to a nonzero offset under the disturbance) and LQI (settles to zero).
- The steady-state cross-track error reported for both, in `notes/week-21/lqi-disturbance.md`.
- A sentence connecting this to PID's I term — same job, expressed as state augmentation.
- Committed.

**Hint.** The disturbance enters as a constant added to `ẋ`. Plain LQR has no integrator so it can't cancel a constant; LQI's augmented integral state accumulates until the offset is gone — exactly like the PID integral, derived differently.

**Estimated time.** 50 minutes.

---

## Problem 4 — The LQR-vs-PID comparison writeup (headline deliverable)

**Problem statement.** This is the syllabus deliverable. Run your LQR (ideally with integral action and gain scheduling) head-to-head against your tuned Week-20 PID on a curved trajectory, and write `notes/week-21/lqr-vs-pid.md` against this template:

1. **Model and cost** — `A`/`B` at the operating point, `Q`/`R` with the Bryson tolerances, and the three sanity-check results (rank, `P` positive-definite, closed-loop eigenvalues).
2. **Fair-test statement** — same reference, start, speed, saturation; PID running its tuned gains.
3. **Numbers table** — RMS and max cross-track error, RMS heading error, RMS control effort, for PID and LQR.
4. **Tracking plots** — cross-track error vs. time and the path overlay.
5. **The verdict** — where the LQR wins, by how much, and *why* (the coupling); where it doesn't; whether you'd ship it.

**Acceptance criteria.**

- `notes/week-21/lqr-vs-pid.md` exists with all five sections, roughly one to two pages.
- The fairness of the test is asserted and defensible.
- The numbers are real (from a run), not invented.
- The verdict is honest about where the LQR does *not* help.
- Committed.

**Hint.** This overlaps Challenge 1 — if you did the challenge, this is its writeup. Use Exercise 3 as the harness. The curve is where the LQR's coupling-awareness shows; a straight line will look like a tie, and saying so is the right call.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Gain scheduling across the speed range

**Problem statement.** Solve LQR at four speeds (0.2, 0.5, 1.0, 1.5 m/s), store the gains, and interpolate at runtime (Lecture 2 §3). Run a trajectory whose speed *varies* across that range with (a) a single fixed-speed gain and (b) the scheduled gain. Compare tracking error.

**Acceptance criteria.**

- A plot of the four gains vs. speed (showing they *do* change with speed — the reason scheduling exists).
- A comparison of tracking error for fixed-gain vs. scheduled-gain on a varying-speed run, in `notes/week-21/gain-scheduling.md`.
- A sentence on the caveat: scheduling assumes the operating point moves slowly relative to the dynamics.
- Committed.

**Hint.** Plot `gains[:,0]` and `gains[:,1]` vs. `speeds` to see them change — if they were constant, scheduling would be pointless, and seeing them move is the justification. Use `np.interp` for the runtime interpolation.

**Estimated time.** 45 minutes.

---

## Problem 6 — The Kalman dual by hand

**Problem statement.** Demonstrate the LQR/LQE duality (Lecture 2 §5). Take your diff-drive `A` and a measurement matrix `C` (say you measure cross-track error directly). Build a Kalman gain by calling your *LQR solver* on the transposed system `(Aᵀ, Cᵀ, W, V)` and confirm the result matches a Kalman filter built the standard way (e.g. `control.lqe`).

**Acceptance criteria.**

- A script `kalman_dual.py` that computes the Kalman gain `L` via `solve_continuous_are(A.T, C.T, W, V)` and via `control.lqe` (or a standard Kalman construction), and asserts they match.
- A note in `notes/week-21/kalman-dual.md` showing the two gains side by side and stating the substitution (`A→Aᵀ`, `B→Cᵀ`, `Q→W`, `R→V`).
- One sentence on what observability (vs. controllability) means here.
- Committed.

**Hint.** `control.lqe(A, G, C, W, V)` gives the Kalman gain directly; build the same thing with `solve_continuous_are` on the transposed system and compare. The point is to *feel* that estimation and control are one piece of math.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Cost sweep, pole movement | 40 min |
| 2 — Verify Riccati by substitution | 30 min |
| 3 — Integral action, disturbance rejection | 50 min |
| 4 — LQR-vs-PID writeup (headline) | 1 h 15 min |
| 5 — Gain scheduling | 45 min |
| 6 — The Kalman dual by hand | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_control` [mini-project](./mini-project/README.md) now hosts both the PID and the LQR — Week 22 adds MPC to the same package. Then take the [quiz](./quiz.md) with your notes closed.

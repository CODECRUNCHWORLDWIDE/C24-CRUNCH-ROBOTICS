# Challenge 1 — Beat the PID on a Curve

**Time estimate:** ~90 minutes.

## Problem statement

The syllabus lab for this week is explicit: *"Linearize a diff-drive model around v = 0.5 m/s. Solve the LQR gain numerically with `scipy.linalg.solve_continuous_are`. Implement the controller in ROS2. Compare path-tracking error against the week-20 PID on a curved trajectory."* This challenge is that lab, made rigorous with a harder reference and a defense.

You will design an LQR path-tracking controller — with **integral action** (LQI, for zero steady-state error) and **gain scheduling** (so it's optimal across the speed range) — and demonstrate that it tracks a **figure-8** reference with lower cross-track error than your tuned Week-20 PID, at comparable or lower control effort. Then you write the comparison report that *defends the cost you chose* and is honest about where the LQR wins and where it doesn't.

## Why a figure-8

A figure-8 has a sign-changing curvature (it curves left, then right, through a crossing), variable speed demand, and a sustained curved section. It's where a controller that ignores the cross-track/heading coupling (a heading-only PID) struggles the most, and where the LQR's model-awareness should pay off. It's also a standard robotics tracking benchmark — the same one the syllabus uses for MPC next week, so your figure-8 harness carries forward.

## Setup

Use **Exercise 3** (`exercise-03-lqr-vs-pid-tracking.py`) as your harness, with the reference path swapped for a figure-8 (a lemniscate: `x = a·sin(t)`, `y = a·sin(t)·cos(t)`). Run both controllers against the **same** reference, the **same** start offset, the **same** speed, and the **same** actuator saturation — fairness is the entire point. Use your tuned PID gains from Week 20 (don't re-tune the PID to lose on purpose; that's not a fair fight).

## Your task

1. **Design the LQR.** Build `A`/`B` for the figure-8's representative speed, design `Q`/`R` with Bryson's rule (Lecture 1 §4.3), solve with `solve_continuous_are`, and run the three sanity checks (Lecture 2 §1.3). The controllability check and stable closed-loop eigenvalues must pass before you run anything.
2. **Add integral action (LQI).** Augment the state with the integral of cross-track error (Lecture 2 §2.2) so a persistent disturbance — inject a constant cross-track bias to simulate a wheel-calibration error — is driven to zero steady-state. Show the LQI rejects it and the plain LQR does not.
3. **Add gain scheduling.** Solve LQR at 3–4 speeds, interpolate at runtime (Lecture 2 §3). Demonstrate that the scheduled controller tracks better than a single fixed-speed gain when the figure-8's speed demand varies.
4. **Run the fair comparison** and report the numbers.
5. **Write the comparison report** (`lqr-vs-pid-report.md`).

## The comparison report (`lqr-vs-pid-report.md`)

This is the deliverable a reviewer reads. It must contain:

1. **The model and cost** — your `A`/`B` at the representative speed, your `Q`/`R` with the Bryson tolerances that produced them, and the three sanity-check results (rank, `P` positive-definite, closed-loop eigenvalues).
2. **The fair-test statement** — one paragraph asserting the test is fair: same reference, start, speed, saturation, and the PID running its *tuned* gains.
3. **The numbers table** — RMS cross-track error, max cross-track error, RMS heading error, and RMS control effort (`|ω|`), one column for PID and one for LQR (and one for LQI if it differs).
4. **The tracking plots** — cross-track error vs. time and the path overlay (reference + both robot paths), for the figure-8.
5. **The integral-action evidence** — the constant-bias test with LQR vs. LQI, showing LQI drives the steady-state cross-track to zero and LQR leaves an offset.
6. **The gain-scheduling evidence** — scheduled vs. fixed-gain tracking error across the speed range.
7. **The honest verdict** — three to five sentences. Where did the LQR win, by how much, and *why* (the coupling)? Where did it *not* win (likely the straight crossing section, where coupling is weak and PID is fine)? Would you ship the LQR, and what would change your mind?

## Acceptance criteria

- [ ] `lqr-vs-pid-report.md` exists with all seven sections.
- [ ] The LQR passes all three sanity checks, shown explicitly.
- [ ] On the figure-8, the LQR's RMS cross-track error is lower than the tuned PID's, at comparable or lower RMS effort. (If it isn't, your report must explain why honestly — that's an acceptable outcome with a good explanation; a rigged win is not.)
- [ ] The LQI rejects the constant cross-track bias to zero steady-state; the plain LQR leaves a measurable offset. Both shown.
- [ ] Gain scheduling beats a single fixed gain across the speed range, shown with numbers.
- [ ] The verdict is honest about where the LQR does *not* help.
- [ ] Committed to your Week 21 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The trap is the **unfair comparison**, in either direction. The dishonest-win version: you detune the PID, or give the LQR a finer reference projection, or let the LQR use the *future* path while the PID only sees the present. The dishonest-loss version: you compare a fixed-speed LQR (designed for 0.5 m/s) against a PID on a path that mostly runs at 1.5 m/s, so the LQR's linearization is stale and it looks bad — when gain scheduling would have fixed it. A fair comparison gives both controllers the same information and the same tuning effort, and that is the only comparison a reviewer will respect. State explicitly what information each controller has access to. The second trap is **forgetting that a straight section has little coupling** — don't be surprised when the LQR's advantage shrinks to near zero through the figure-8's crossing; that's the theory working, not a bug, and saying so in the verdict is exactly the kind of honesty that demonstrates you understand *why* LQR helps.

## Stretch

- **LQR on a Kalman-estimated state (separation principle).** Instead of feeding the LQR the true error state, run a small Kalman filter (Lecture 2 §5) on noisy position measurements and feed the LQR the *estimate*. Confirm the combination is still stable and tracks well — you've demonstrated the separation principle on your own robot.
- **Finite-horizon LQR.** Implement the time-varying gain from the backward differential Riccati recursion and watch it converge to the infinite-horizon steady-state gain. This is the literal conceptual bridge to next week's MPC, which is finite-horizon optimal control re-solved every step.
- **The discrete solve.** Re-solve with `solve_discrete_are` at your actual control rate and compare the gains to the continuous solution. Quantify the difference and state at what loop rate it starts to matter.

## Why this matters

At the Phase 3 milestone in Week 24, a reviewer will ask "you have a PID and an LQR — which did you ship, and why?" This challenge *is* that conversation, rehearsed, with data. Every serious robotics shop eventually faces "the PID we have works; is the fancier controller worth the complexity?" The engineer who can answer with a fair benchmark and an honest verdict — including "no, not here, and here's why" — is the one whose technical judgment gets trusted with the next, harder controller. A rigged demo wins a meeting and loses the moment the robot meets the real path.

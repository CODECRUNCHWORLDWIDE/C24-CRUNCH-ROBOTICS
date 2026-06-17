# Week 20 Homework

Six problems that drive the PID and feedforward concepts into your fingers. The full set should take about **5 hours**. Work in your Week 20 Git repository (the same workspace as the exercises and the `crunchbot_control` mini-project) so every problem produces at least one commit you can point to at the Phase 3 milestone in Week 24.

The headline deliverable is **Problem 4 — the tuning log** (the syllabus-named artifact). Treat it as the document a reviewer reads, not a journal entry.

Each problem includes a short **problem statement**, **acceptance criteria** so you know when you're done, a **hint** if you get stuck, and an **estimated time**.

Have `numpy`, `scipy`, and `matplotlib` installed (`pip install numpy scipy matplotlib`). Problems 4 and 6 run against your **week-3 differential-drive robot** in Gz Sim; the rest are pure simulation. If the sim is broken, Exercise 3's `--sim` plant is your fallback — say so in your writeup.

---

## Problem 1 — Prove the `dt` bug bites

**Problem statement.** Take the discrete PID from Lecture 1 §3. Tune it to a clean step response at 50 Hz (`dt = 0.02`). Now, *without changing the gains*, run the same controller at 200 Hz (`dt = 0.005`) — but in one version keep the `dt` in the integral and derivative, and in a second version drop it (the `integral += error` bug). Plot all three step responses (50 Hz correct, 200 Hz correct, 200 Hz buggy) on one axes.

**Acceptance criteria.**

- A plot `dt_bug.png` with three traces, clearly labeled.
- The two *correct* versions (50 Hz and 200 Hz) produce nearly identical responses — proving correct `dt` handling makes the controller rate-independent.
- The *buggy* 200 Hz version is visibly different (its effective `Ki`/`Kd` are off by the rate ratio).
- A one-paragraph note in `notes/week-20/dt-bug.md` explaining why the buggy version's effective `Ki` is `Ki_nominal × (dt_tuned / dt_actual)`.
- Committed.

**Hint.** Reuse Exercise 1's `simulate` and `analyze_step`. The buggy version will be roughly 4× too aggressive on the integral at 200 Hz (because `0.02/0.005 = 4`).

**Estimated time.** 30 minutes.

---

## Problem 2 — Wind-up, two fixes, head to head

**Problem statement.** Using Exercise 2's plant and a large saturating step, implement **both** anti-windup methods — conditional integration (clamping) and back-calculation — and compare them against the naive integrator on the same step. Plot all three outputs and all three integral-term traces over time.

**Acceptance criteria.**

- A plot showing the naive integrator winding up (its integral trace spikes far above where it ends) and both fixes keeping the integral bounded.
- A table in `notes/week-20/antiwindup-compare.md` with overshoot and settling time for naive / clamping / back-calculation.
- One sentence on the qualitative difference: clamping is abrupt (the integrator switches on/off), back-calculation is smooth (it bleeds continuously).
- Committed.

**Hint.** Log `pid.integral` each tick into a separate array so you can plot it. The naive integral's peak value is the "stored push" that becomes overshoot — point at it in the plot.

**Estimated time.** 45 minutes.

---

## Problem 3 — Quantify the feedforward win on a ramp

**Problem statement.** A step setpoint hides feedforward's value (the integral eventually gets you there). A *moving* reference exposes it. Drive your yaw controller (Exercise 3) with a reference that **ramps** from 0 to 90° over 2 seconds, then holds. Measure the **tracking error** (the gap between reference and measurement *during* the ramp) with `USE_FEEDFORWARD = True` vs. `False`. Plot reference and both responses.

**Acceptance criteria.**

- A plot `feedforward_ramp.png` with the reference and the two tracked responses.
- A reported reduction in peak tracking error and in RMS tracking error from turning feedforward on, in `notes/week-20/feedforward-win.md`.
- A sentence explaining *why* the feedforward helps the ramp but barely changes the final held value (the integral handles the hold; feedforward handles the motion).
- Committed.

**Hint.** The velocity feedforward `Kv·ref_rate` should be most active during the ramp (constant nonzero `ref_rate`) and zero during the hold (`ref_rate = 0`). That's exactly the shape of where it helps.

**Estimated time.** 45 minutes.

---

## Problem 4 — The tuning log (headline deliverable)

**Problem statement.** This is the syllabus deliverable. Tune your yaw controller to the three step targets (45°, 90°, 180°) against the spec from Challenge 1, on the real robot if you can. Then write `notes/week-20/tuning-log.md` against this template:

1. **Plant and setup** — what you tuned against (robot or sim), loop rate, actuator limit.
2. **Final gains** — `Kp`, `Ki`, `Kd`, filter `Tf`, feedforward `Kv`, in a table.
3. **Metrics table** — one row per setpoint, columns rise/overshoot/settling/steady-state, each PASS/FAIL against the spec. All PASS.
4. **The three step-response plots** — setpoint, measured, 2% band.
5. **Anti-windup evidence** — the 180° step with anti-windup on vs. off, the two overshoot numbers, one sentence on the mechanism.
6. **The defense** — which metric was the binding constraint (the one that stopped you raising `Kp`), and why you chose these gains over hotter ones, referencing the symptom→gain map.

**Acceptance criteria.**

- `notes/week-20/tuning-log.md` exists with all six sections, roughly one to two pages.
- All three setpoints PASS all four metrics with **one** gain set.
- The anti-windup on/off comparison is shown with two numbers and the mechanism named.
- The defense identifies the binding constraint specifically, not "I tuned until it looked good."
- Committed.

**Hint.** This overlaps heavily with Challenge 1 — if you did the challenge, this is the writeup of it. Use Exercise 3 to generate the logs and Exercise 1's `analyze_step` to score them. The binding constraint on most robots is overshoot on the 180° step (the saturating case) — if anti-windup is working, it's usually `Ki` you can't push further.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Auto-tune and compare to your hands

**Problem statement.** Use `scipy.optimize.minimize` (Nelder–Mead) to auto-tune `Kp`, `Ki`, `Kd` for the Exercise 1 plant against an **ITAE** cost. Compare the auto-tuned gains and step response to your hand-tuned ones from Problem 4 / Exercise 1.

**Acceptance criteria.**

- A script `autotune.py` that minimizes the ITAE cost and prints the resulting gains.
- A plot overlaying the auto-tuned and hand-tuned step responses.
- A note in `notes/week-20/autotune.md` answering: did the optimizer beat your hands on the metrics? Did it produce a `Kd` (or any gain) you would *not* ship, and why? What does that tell you about your cost function?
- Committed.

**Hint.** Constrain gains to be non-negative (return a huge cost for negative gains, as in Lecture 2 §2.3). The optimizer often finds a slightly faster response than you did but may exploit the perfect sim with a `Kd` that would chatter on noisy hardware — note that.

**Estimated time.** 45 minutes.

---

## Problem 6 — Read the production PID and find the anti-windup

**Problem statement.** Open the `control_toolbox::Pid` source (`control_toolbox` repo, linked in resources). Find where it implements anti-windup. Confirm it matches the back-calculation you implemented in Exercise 2 (or identify which anti-windup strategy it uses if different). Write a short reading note.

**Acceptance criteria.**

- A note in `notes/week-20/control-toolbox-read.md` that: links the specific file/function implementing the integral and its anti-windup; quotes the few lines that do the clamping/back-calculation; and states whether it matches your Exercise 2 implementation or differs (and how).
- One sentence on the `i_min`/`i_max` (integral clamp) parameters and how they relate to the wind-up discussion.
- Committed.

**Hint.** Look in `src/pid.cpp` for the `computeCommand` method and the handling of `i_term_` against `i_max_`/`i_min_`. The toolbox uses integral clamping (a form of conditional integration / output limiting on the integral term); compare that to the back-calculation in your code and note the trade-off.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — The `dt` bug | 30 min |
| 2 — Anti-windup head to head | 45 min |
| 3 — Feedforward win on a ramp | 45 min |
| 4 — Tuning log (headline) | 1 h 15 min |
| 5 — Auto-tune and compare | 45 min |
| 6 — Read the production PID | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_control` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 21 imports it to compare LQR against this PID. Then take the [quiz](./05-quiz.md) with your notes closed.

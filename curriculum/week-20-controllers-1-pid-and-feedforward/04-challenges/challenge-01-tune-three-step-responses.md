# Challenge 1 — Tune One Controller to Three Step Responses

**Time estimate:** ~90 minutes.

## Problem statement

The syllabus lab for this week is explicit: *"Tune for three target step responses (45°, 90°, 180°). Plot rise time, overshoot, settling. Then add a feedforward term proportional to commanded angular velocity; quantify improvement."* This challenge is that lab, made rigorous with a spec and a defense.

You will tune **one** yaw controller (one set of gains, plus one feedforward gain) so that **all three** step commands — 45°, 90°, 180° — land inside the specification below. The catch, and the whole point, is that a gain set tuned to look perfect on the 90° step will often **wind up and overshoot on the 180° step** (because the larger step saturates the actuator for longer) and may look **sluggish on the 45° step**. Making one controller work across the whole range is the actual job.

## The spec (must hold for all three setpoints)

| Metric | Target |
|---|---|
| Rise time (10–90%) | ≤ 1.2 s |
| Percent overshoot | ≤ 12 % |
| Settling time (2% band) | ≤ 2.5 s |
| Steady-state error | ≤ 1.0° |

## Setup

Use **Exercise 3** (`exercise-03-yaw-rate-pid.py`) as your controller and logger — either against the real week-3 robot or with `--sim`. Use **Exercise 1**'s `analyze_step` to compute the four metrics from each `yaw_step_<deg>.csv` log. If your robot's dynamics differ from the sim plant, tune against the *robot* — the sim is a fallback, not the target.

## Your task

1. **Tune the feedback gains** (`Kp`, `Ki`, `Kd`) so all three step logs pass all four metrics. Work the structured loop (Lecture 2 §2.1): one gain at a time, watch the plot, name the symptom.
2. **Confront the 180° case explicitly.** The large step saturates the base's angular velocity (`W_MAX`). Confirm that *with* the back-calculation anti-windup from Exercise 2 the overshoot stays in spec, and that *removing* the anti-windup (temporarily set `self.kb = 0`) blows the overshoot past spec. Capture both plots. This is the load-bearing evidence that your anti-windup works.
3. **Add and quantify feedforward.** With `USE_FEEDFORWARD = True`, feed a *moving* yaw reference (a ramp from 0 to the target over ~1 s instead of an instantaneous step) and measure the tracking error with feedforward on vs. off. Report the reduction. (On a pure step the integral hides the feedforward's value; on a ramp it's obvious.)
4. **Write the tuning log** (`tuning-log.md`) that defends every choice.

## The tuning log (`tuning-log.md`)

This is the deliverable a reviewer reads. It must contain:

1. **Final gains** — `Kp`, `Ki`, `Kd`, filter `Tf`, feedforward `Kv` — in a table.
2. **The metrics table** — one row per setpoint (45°/90°/180°), four columns (rise/overshoot/settling/steady-state), each marked PASS/FAIL against the spec. All must PASS.
3. **The three step-response plots** (setpoint + measured yaw + the 2% band), embedded or linked.
4. **The anti-windup evidence** — the 180° step with anti-windup on vs. off, the two overshoot numbers, one sentence explaining the mechanism (the integral wound up during saturation; back-calculation bled it off).
5. **The feedforward evidence** — the ramp-tracking error with feedforward on vs. off, and the percent reduction.
6. **The defense** — three to five sentences answering: "why these gains and not hotter ones?" Reference the symptom→gain map. State which metric was the binding constraint (the one that stopped you raising `Kp` further).

## Acceptance criteria

- [ ] `tuning-log.md` exists with all six sections above.
- [ ] All three setpoints PASS all four metrics with **one** gain set.
- [ ] The 180° overshoot is in spec *with* anti-windup and out of spec *without* it, demonstrated with two plots and two numbers.
- [ ] The feedforward-on vs. feedforward-off tracking error on the ramp is reported with a percent reduction.
- [ ] The defense names the binding constraint and the gain it limited.
- [ ] Committed to your Week 20 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The trap is **over-tuning to the middle case.** It's tempting to nail the 90° step, declare victory, and find the 45° is sluggish and the 180° overshoots. When that happens, do **not** add gain scheduling yet (that's the stretch). First ask: is the 180° overshoot *wind-up* (fix it with anti-windup, not by detuning) or is it genuinely too much `Kp`/`Ki` (detune)? Diagnose before you detune. A common wrong move is to slash `Ki` to fix the 180° overshoot and then watch the 45° steady-state error creep out of spec. The right move is almost always "anti-windup is doing its job; the overshoot I'm seeing is `Ki` that's slightly too hot across the board" — a small, even reduction, not a panic cut.

## Stretch

- **Gain scheduling.** If one gain set genuinely can't cover the range, schedule the gains on the *magnitude of the error*: gentler `Kp` for large errors (to avoid saturating hard), more aggressive near the setpoint. Switch smoothly (interpolate, don't step the gains). This is a direct preview of next week's LQR gain scheduling and a legitimate senior-engineer technique. Document the schedule and show it beats the single gain set.
- **Auto-tune the gains** with `scipy.optimize.minimize` over a *combined* ITAE cost summed across all three setpoints (so the optimizer can't cheat by nailing one and failing another). Compare the auto-tuned gains to your hand-tuned ones and discuss which you'd actually ship.
- **Disturbance rejection.** Inject a constant yaw-rate disturbance (a simulated wheel-slip bias) and confirm the integral term rejects it to zero steady-state error. Measure how long rejection takes and connect it to `Ki`.

## Why this matters

At the Phase 3 milestone in Week 24, a reviewer will point at your controller and ask "why those gains, and how do you know they hold across the operating range?" This challenge *is* that conversation, rehearsed. Every robot you ship will be tuned by someone who either (a) found one operating point that worked and got lucky, or (b) characterized the envelope and chose gains with a defensible trade-off. The second engineer is the one whose robot doesn't surprise the customer at the edge of its range — and the one who gets to write the controller for the next robot too.

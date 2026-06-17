# Challenge 1 — Defend Your Stack Through Three Layers of "Why"

**Type:** Open-ended, adversarial, paired (you need a human prober).
**Estimated time:** 90 minutes (prep 45, drill 30, write-up 15).
**Difficulty:** Hard — this is the skill that separates "built a robot" from "is a roboticist."

---

## The setup

Pick **one** real design decision from your own capstone. Not a textbook decision — *yours*, the one in your actual repo. Then have a peer (or senior engineer) probe it with the question "why?" recursively, at least three layers deep. Your job: hold up. No collapsing into "it's what the tutorial used," "it's the ROS 2 default," or "the diffusion-policy paper did it that way." Those are non-answers and the prober is instructed to pounce on them.

Good decisions to defend (pick the one you're *least* sure about — that's where the growth is):

- **Why PID or MPC for the base controller?** (And if MPC: why not LQR? Why hard constraints?)
- **Why OpenVLA / your chosen VLA for the policy?** (Why not a scripted grasp? Why not pure imitation learning?)
- **Why an EKF for local state estimation?** (Why not a UKF? Why not a factor graph?)
- **Why AMCL for global localization?** (Why not pure LiDAR SLAM at runtime?)
- **Why Nav2's behavior-tree navigator?** (Why a BT and not a state machine?)
- **Why TensorRT INT8 for the detector?** (Why not FP16? What did you give up?)

---

## How the three-layer drill works

The prober asks "why?" and you answer. Then they ask "why?" *about your answer*, and you answer again. Three times minimum. Here's a worked example so you know what "holding up" looks like — and what failing looks like.

### Worked example: "Why MPC for the base?"

**Layer 0 — the prober:** "Why did you use MPC for the base controller?"

> **You:** "The base drives constrained aisles where I have hard actuator limits and a lateral corridor bound. MPC lets me put those constraints directly in the optimization and respect them; a PID couldn't enforce the lateral bound and an unconstrained LQR would happily command a velocity the motors can't deliver."

**Layer 1 — the prober:** "Why not just clamp the LQR output to the actuator limits? Cheaper, simpler."

> **You:** "Clamping after the fact breaks LQR's optimality guarantee and can drive the system unstable — the clamped input is no longer the optimal one the Riccati solution assumed, so the stability proof doesn't hold near saturation. MPC reasons about the limit *inside* the horizon, so it plans a feasible trajectory instead of planning an infeasible one and then mangling it."

**Layer 2 — the prober:** "Fine, but MPC re-solves an optimization every cycle. How do you know it fits your control-rate budget? Why is that worth the compute?"

> **You:** "I budgeted 8 ms for the controller in my 48 ms loop and measured the solver at p95 of 5.2 ms with a 1.5-second horizon at 10 Hz — I have the Foxglove panel from Week 43 that logs solve time. It fits because I kept the model kinematic, not dynamic, so the QP is small. It's worth it because the alternative — a deadlocked or saturated base in a shared aisle — is a safety event, and the safety case (Week 41) lists corridor-bound violation as a hazard I had to mitigate."

**Layer 3 — the prober:** "And if the solver blows its budget one cycle — misses the deadline?"

> **You:** "The control thread has priority and a watchdog: if the QP doesn't return in time I fall back to the previous solution's next step (warm-start continuity) for one cycle, and if it misses twice I trigger a controlled stop through the safety layer rather than command a stale input. I'd rather stop than act on a stale plan in a shared space."

That's four layers held. Notice: it ends not at "I don't know" but at a *measured, safety-grounded* answer, and twice it connected back to artifacts you actually built (the Foxglove panel, the safety case). That's the bar.

### What failing looks like

> **Prober:** "Why MPC?"
> **You:** "It's what the controls lecture used and it worked in sim."
> **Prober:** "Why did it work?"
> **You:** "Uh... it tracked the trajectory better?"
> **Prober:** "Better than what, measured how?"
> **You:** "...I'm not sure."

Two layers and you're done. That's the gap this challenge closes.

---

## Acceptance criteria

You pass the challenge if, on **one** decision, with a real human prober:

- [ ] You hold up through **at least three** "why" layers without a non-answer.
- [ ] At least one layer connects to **a measurement, number, or artifact you actually have** (a benchmark, a Foxglove panel, an eval-suite result, a safety-case line).
- [ ] You correctly name the **alternative you rejected** and *why* you rejected it (MPC-vs-LQR, EKF-vs-factor-graph, VLA-vs-scripted, etc.).
- [ ] When you hit the genuine edge of your knowledge, you say **"I didn't go deeper than X; here's how I'd find out"** instead of bluffing. (This is a *pass*, not a fail — bluffing is the fail.)
- [ ] The prober signs off that you did **not** lean on "it's the default / the tutorial / the paper" as a load-bearing answer.

---

## Deliverable

Write a one-page `defend-<decision>.md` capturing the drill:

1. The decision you defended (one line).
2. The four-layer Q&A transcript (your prober's questions + your answers).
3. The layer where you hit your real edge, and the "here's how I'd find out" answer you gave.
4. Two sentences: what you learned about a hole in your own understanding, and what you'll go read to close it.

Commit it next to your capstone. It is *exactly* the rehearsal for the Week 48 defense panel, who will do this to you for real.

---

## Stretch

- Defend **three** different decisions back to back. Fatigue is real; the third one is where you find out whether you actually know your stack or were just well-rested for the first.
- Have the prober deliberately assert something **false** mid-drill ("but an EKF is exact for nonlinear systems, right?") and see if you catch and correct it. Interviewers do this. Catching it scores enormous points; agreeing to be agreeable is a quiet fail.
- Record it and watch yourself back with the sound off. Where do your hands go when you don't know? That tell is what a good interviewer reads.

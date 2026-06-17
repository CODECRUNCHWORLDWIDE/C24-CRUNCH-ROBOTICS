# Challenge 1 — Same Robot, Same Patrol, Two Sims

**Time estimate:** ~2–3 hours.

## Problem statement

Your team is deciding whether to do the capstone's final integration in Gz Sim or to move to Isaac Sim, and your lead wants data, not opinion. You will run the **identical** robot and the **identical** patrol behavior in two simulators (Path A: Gz Sim and Isaac Sim; Path B: Gz Sim under two physics engines), measure the four metrics that matter, and produce a one-page write-up that recommends a simulator *for a stated purpose* with the trade-off explicit. This is the syllabus lab for Week 33, done to design-review standard.

## The fixed parts (do not vary these)

- **Robot:** your week-3 differential-drive base. Same URDF/description in both worlds. (Path A: import it to USD; the kinematics transfer, the sensor plugins you re-author — that's the cross-import reality from Exercise 3.)
- **Behavior:** one patrol — three waypoints, or "drive a 4 m square and return," driven by your Week 19 behavior tree or a small fixed routine. **Bit-identical** across runs.
- **Window:** the same duration (e.g., 60 s) and the same drive pattern in each sim.
- **Measurement:** the Exercise-2 metrics node, unchanged, against `/clock` and `/scan`. Same tool both runs.

The **only** independent variable is the simulator (Path A) or the physics engine (Path B). That is what makes it a comparison and not two anecdotes (Lecture 2 §3.1).

## What to measure

For each sim/engine, capture the four metrics (Lecture 2 §3.2):

1. **Real-time factor (RTF)** — from the Exercise-2 node.
2. **Mean step-time (ms)** — from the Exercise-2 node.
3. **Sensor fidelity** — `/scan` rate (Hz) from the node; plus a qualitative note on the scan's noise/quality.
4. **Contact behavior** — qualitative: does the robot sit flush, sink, jitter, bounce off walls? Count contacts if you can.

## Deliverables

### 1. The comparison table (`challenges/challenge-01/comparison.md`)

```
=== SIM COMPARISON: crunchbot patrol (3 waypoints, 60 s) ===
sim / engine          RTF     step (ms)   /scan Hz   contact note
Gz Sim / DART         ____    ____        ____       ____
<2nd point>           ____    ____        ____       ____
```

(Path A second row is `Isaac Sim / PhysX`; Path B second row is `Gz Sim / Bullet`.)

### 2. The one-page write-up (`challenges/challenge-01/sim-selection.md`)

~400–600 words covering:

- **The numbers** — the table above, in prose: which sim/engine was faster, where sensor rates held, where contact differed.
- **The trade-off** — place each sim on the throughput-vs-fidelity curve. What did each give up?
- **The recommendation** — for *two distinct purposes*: (a) "debug the autonomy stack for the capstone integration" and (b) "train a PPO policy with domain randomization next week." Name a simulator for each and justify with a metric or a capability, not a preference.
- **Path B honesty (if applicable)** — explicitly state which Isaac-only capabilities (RTX rendering, GPU-parallel envs) you reasoned about rather than measured, and why that's an acceptable substitution for the *comparison skill*.

## Acceptance criteria

- [ ] The robot description and the patrol behavior are demonstrably **identical** across both runs (link the same files; note any unavoidable cross-import differences and why they don't invalidate the comparison).
- [ ] `comparison.md` has the four metrics for both sims/engines, captured with the Exercise-2 node.
- [ ] `sim-selection.md` (~400–600 words) recommends a simulator for **each** of the two stated purposes, justified by measurements/capabilities.
- [ ] At least one metric or behavior **differs** between the two runs, and you explain *why* (engine contact model, GPU vs CPU, render cost).
- [ ] Path B submissions clearly mark which capabilities were reasoned-about vs measured.
- [ ] Committed under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The seductive mistake is concluding "Isaac Sim is faster, so we should use it for everything" (or, on Path B, "Bullet is faster, use Bullet"). A higher RTF on *one robot* does **not** mean Isaac is the right choice for capstone integration — Isaac's weight, GPU requirement, and slower iteration make it the *wrong* tool for debugging a behavior tree, even if it steps faster. Conversely, Gz Sim's lower throughput does not disqualify it for RL — it disqualifies it because it can't run *thousands of parallel envs*, which is a different axis entirely (a single high RTF tells you nothing about parallel-env throughput). **The recommendation must be per-purpose.** A write-up that names one winner for all jobs has missed the entire point of the week. State the purpose, then the tool.

## Stretch

- Add a **third point**: Gz Sim under ODE, or (Path A) Isaac at a different render setting. Three points make the throughput/fidelity curve visible rather than a single line segment.
- **Sensor overlay.** Capture one `/scan` from each sim of the same wall and overlay them (matplotlib). Where do the ranges/noise disagree? That visual gap is exactly what Week 34's domain randomization exists to bridge.
- **Boot-time** as a fifth metric. Time "launch command → first `/scan`" for each sim. Iteration speed is a real engineering cost the four physics metrics hide, and it's a big part of why Gz Sim stays the debugging default.

## Why this matters

Week 34 (next week) randomizes over many worlds *because* of the throughput lesson you just measured, and Week 40 stands up the full capstone system in sim. The "which sim, for what" judgment — backed by a table you produced — is the difference between an engineer who has an opinion about simulators and one who has evidence. In a real planning meeting, evidence wins.

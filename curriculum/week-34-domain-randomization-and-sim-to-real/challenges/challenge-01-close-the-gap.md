# Challenge 1 — Close the Gap

**Time estimate:** ~3–4 hours (including one randomized training run of ~30 min on a parallel sim, longer on Path B episode-level).

## Problem statement

You are the sim-to-real engineer. Your lead says: *"Our reach policy is 90% in sim. Before we put it on hardware, prove it'll survive a world it hasn't seen — and tell me, with one number, how much domain randomization buys us."* That is this challenge. You will:

1. Train a **nominal** policy on one fixed world (your Week 28 baseline — reuse it if you still have it).
2. Train a **randomized** policy on the *same* task with the Exercise-2 randomization config wired in.
3. Author a **held-out "real-style" world** with parameters neither policy trained on.
4. Evaluate **both** policies on that held-out world (and on the nominal world for the sanity line).
5. Report the **gap-closure metric** with its sanity line and a confidence interval.

This is the syllabus lab for Week 34, done to the standard the Phase 5 milestone expects.

## Setup

- Your Week 28 PPO task (reach or navigate) in Isaac Lab (Path A) or Gymnasium + Gz Sim (Path B).
- The Exercise-2 `DomainRandomizer` and config; the Exercise-3 gap-metric script.
- Path A: an NVIDIA GPU + Isaac Lab (apply randomization via the event manager, per parallel env). Path B: randomize per Gymnasium episode in Gz Sim — slower, fewer samples; document the scale difference.

## Part 1 — Train both policies

- **Nominal:** the Week 28 run (one fixed world). Reuse the checkpoint if you have it.
- **Randomized:** the *same* PPO config and reward, with `randomizer.sample()` applied on every env reset (Lecture 2 §2.1). Use the recipe you justified in Exercise 1 — visual **and** dynamics families at minimum.

Watch the reward curves. The randomized run should be **noisier and slower** than nominal (the task is genuinely harder across worlds). A randomized run that converges identically to nominal means your ranges are too narrow — widen them.

## Part 2 — The held-out world

Author one evaluation world whose parameters are **not** drawable from your training config (Lecture 2 §4.1):

- Textures/colors not in your training texture set.
- Lighting outside the training intensity/position range.
- A specific floor/object friction distinct from training (ideally a value you'd expect in reality).
- Realistic sensor noise.

**State explicitly** how you guaranteed each held-out parameter is outside the training distribution. A reused training parameter contaminates the result.

## Part 3 — Evaluate and report

Run a fixed `n` (≥ 100 if you can; ≥ 50 minimum) for each (policy × world) cell. Feed the success counts into the Exercise-3 gap-metric script:

```
=== SIM-TO-REAL GAP: <task>, held-out 'real-style' world (n=___) ===
nominal-trained      held-out: __/__  (__%)   CI[__,__]
randomized-trained   held-out: __/__  (__%)   CI[__,__]
GAP CLOSED: +__ pts
(sanity) on the nominal world:  nominal __% | randomized __%
sanity verdict: ___
```

## Acceptance criteria

- [ ] Two policies trained on the same task, differing **only** in randomization; the randomized run used the Exercise-2 config with ≥ 2 families.
- [ ] A held-out world with documented out-of-training parameters (state how each is held out).
- [ ] `challenges/challenge-01/gap-results.md` with the full table: both policies on both worlds, explicit `n`, the gap-closed number, and the CI.
- [ ] The **sanity verdict is OK** (randomized worse-or-equal on nominal, better on held-out) — or, if SUSPECT, you diagnosed why and fixed it.
- [ ] A 200–350-word note: which randomization families carried the gap closure for your task, and one honest limit (what the randomization could *not* close).
- [ ] Committed under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The seductive failure is a gap number that's *too good* because the held-out world leaked. If your randomized policy beats nominal on **both** worlds by a margin (the Exercise-3 sanity check flags this as SUSPECT), do **not** report the gap as a win — your held-out world almost certainly reuses a parameter the policy trained on, or your nominal policy under-fit. The whole credibility of a sim-to-real result rests on the held-out world being genuinely unseen. The senior move is to *want* the sanity check to pass, not to explain it away: a healthy result is randomized slightly worse on the easy world (it paid for robustness) and much better on the hard one. If you can't reproduce that pattern, your experiment is broken, not your policy.

## Stretch

- **Ablate the families.** Train visual-only, dynamics-only, and both; eval each on the held-out world. Report which family carried the gap closure — usually visual for vision-based tasks, dynamics for state-based. This turns "randomization helped" into "*visual* randomization closed 40 of the 53 points."
- **ADR.** Replace fixed ranges with Automatic Domain Randomization (start narrow, widen on success). Plot range-width vs. step and compare final held-out success to fixed-range. Does the curriculum reach a wider usable distribution?
- **Find the cliff.** Widen the ranges until the policy can't learn (reward flatlines low). Report the over-randomization boundary — the practical upper bound on how wide is too wide for your task.

## Why this matters

In Week 40 you stand up the full capstone system in sim, and in Week 41 you write its safety case. A panel will ask "you trained this in sim — why should we believe it works?" The honest answer is a gap-closure number against a held-out world plus the acknowledgment that the safety filter still matters because randomization narrows but never erases the gap. This challenge produces exactly that answer. An engineer who says "randomization closed 53 points of the held-out gap, here's the sanity check, and here's why I still ship the safety wrapper" is the one a safety reviewer trusts.

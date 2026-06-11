# Challenge 1 — Quantify BC vs. BC+DAgger, and Explain the Gap

**Time estimate:** ~90 minutes.

## Problem statement

Run **behavior cloning** and **behavior cloning + DAgger** on the reach task (real Gz Sim, or the synthetic env from Exercise 2), evaluate **both on the same fixed protocol**, report success rates with confidence intervals, classify every failure, and **explain the covariate-shift gap with state-visitation evidence** — not with adjectives.

This mirrors the real skill: you rarely just "get a policy working." You run a fair head-to-head, report a number a skeptic can reproduce, and explain *why* one method beats the other in mechanistic terms. "DAgger is better" is a vibe; "DAgger is +30 points because it covered the 7 drift-states BC never saw, here is the state-visitation plot" is a finding.

## Your task

1. **Fix the eval protocol first, before training anything.** Pre-state: the success predicate (e.g., end-effector within 3 cm of the block, no safety clamp), the set of start states (include starts *not* in the demos), and the number of trials (≥ 20). Write it down. Both policies are scored on *this exact protocol* — same starts, same predicate.

2. **Train BC** on the demonstrations (50 demos, or the synthetic expert). Evaluate on the protocol. Record the success rate, the per-trial failure classification (drift / underfit / safety-clamp), and at least one *rollout trace* showing the track-then-drift signature.

3. **Train BC+DAgger** (1–3 rounds, aggregating each round). Evaluate on the *same* protocol. Record the success rate, the failure classification, and how the previously-drifting trials now behave.

4. **Report with intervals.** A success rate from 20 trials has a wide interval (15/20 ≈ 75% ± 19% at 95%). Report rate ± interval for both, so the reader knows whether the difference is real or noise. (If the intervals overlap heavily, run more trials.)

5. **Explain the gap with evidence.** Project the demo states, the BC-rollout states, and the DAgger-rollout states to 2D (PCA or t-SNE). Show: BC rollouts wander *off* the demo manifold (covariate shift, visualized), and DAgger rollouts stay *on* it (because DAgger added those off-manifold states to the training data). This plot *is* the explanation.

## Acceptance criteria

- [ ] A file `challenge-01-bc-vs-dagger.md` with the pre-stated eval protocol (predicate, starts, trial count) written *before* the results.
- [ ] BC and BC+DAgger success rates, each with a 95% confidence interval, on the *same* protocol.
- [ ] Per-trial failure classification for both (how many drift / underfit / safety-clamp).
- [ ] At least one BC rollout trace showing the track-then-drift covariate-shift signature.
- [ ] A state-visitation plot (demos vs. BC rollouts vs. DAgger rollouts) that visually shows BC wandering off the manifold and DAgger staying on it.
- [ ] A paragraph explaining the gap *mechanistically* — DAgger added the policy's own drifted states to the data, closing the covariate-shift gap; more BC epochs could not, because they have no data about those states.
- [ ] Committed to your Week 27 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The subtle error is comparing BC and DAgger on **different start states** — say, BC on the demo starts and DAgger on novel starts, or vice versa. If the protocols differ, the comparison is meaningless: you could "show" either method winning just by choosing favorable starts. **Fix the protocol once, before training, and score both policies on it identically.** Also resist relaxing the success predicate to make a number look better after you see it — a predicate decided after the results is not a predicate, it's a rationalization. The whole point of the pre-stated protocol is that it binds you the same way it binds the reader.

A second trap: reporting a bare success rate with no interval. 12/20 vs. 15/20 *looks* like a clear win, but with 20 trials the intervals overlap substantially — it might be noise. Report the interval, and if it's inconclusive, run more trials. An honest "inconclusive at 20 trials, ran 50, now clearly +25 points" beats a confident "DAgger won 15-12" that doesn't survive scrutiny.

## Stretch

- **Multiple DAgger rounds.** Run 3–5 rounds and plot success rate vs. round. Note where it plateaus — the round after which the expert queries stop adding new information because the policy no longer drifts into novel states.
- **The multimodal demo.** Collect demos that approach the block from *two* sides (some left, some right). Watch BC's MSE loss average them into a *straight-into-the-block* action that satisfies neither — the multimodal-averaging failure (Lecture 2 §4) that even DAgger doesn't fix, and that Diffusion Policy (Week 29) does. Document it as a forward reference.
- **Pure-BC-with-more-data control.** To prove the gap is covariate shift and not just "DAgger has more data," train a *plain BC* policy on a dataset of the same final size as the DAgger dataset, but all from *expert* rollouts (not policy rollouts). Show it does *not* match DAgger — proving the gap is about *which* states the data covers, not how many.

## Why this matters

In Weeks 29 and 30 you compare Diffusion Policy and ACT against this BC+DAgger baseline on the same demonstrations. That comparison decides which method you'd ship — and it is only meaningful if your baseline numbers come from a fair, fixed protocol with honest intervals. Every robot-learning result you'll ever read or produce hinges on the eval protocol; a great method on a rigged protocol is worthless, and a modest method on an honest one is publishable. The engineer who fixes the protocol first, reports intervals, and explains the gap mechanistically is the one whose results other people trust — which is the only kind of result worth having.

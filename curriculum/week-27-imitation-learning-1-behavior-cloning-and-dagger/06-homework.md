# Week 27 Homework

Six problems that revisit the week's imitation-learning topics and force the BC-and-DAgger intuition into your fingers. The full set should take about **5 hours**. Work in your Week 27 Git repository (the same workspace as the exercises and the `crunch_il` mini-project) so every problem produces at least one commit you can point to when you compare against Diffusion Policy and ACT in Weeks 29–30.

The headline deliverable is **Problem 4 — the covariate-shift postmortem**. Treat it as the artifact a reviewer reads, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — Read the loss curves and the rollout, and label the failure

**Problem statement.** Train three BC policies that fail in three different ways on the reach task: (a) an underfit policy (tiny network, few epochs), (b) an overfit policy (huge network, no early stopping, few demos), and (c) a healthy-loss-but-drifting policy (the Exercise-2 default). For each, capture the loss curves *and* a rollout, and correctly label the failure.

**Acceptance criteria.**

- `notes/three-failures.md` has, for each policy: the train/val loss curves, a rollout trace, and the correct label (underfit / overfit / covariate shift).
- You state, for the covariate-shift case specifically, why the loss curves *cannot* reveal it (the loss is on the expert's states; the policy is tested on its own).
- You can distinguish them from the *rollout symptom* alone: underfit fails everywhere, overfit fails on novel in-distribution starts, covariate shift tracks-then-drifts.
- Committed.

**Hint.** To force underfitting, use a 1-layer 8-unit net for 10 epochs. To force overfitting, use a huge net, 10 demos, and no early stopping (val loss will rise). The healthy-but-drifting case is just Exercise 2 as written. The lesson is that two of the three are diagnosable from the loss and one is not.

**Estimated time.** 50 minutes.

---

## Problem 2 — The horizon experiment (compounding error)

**Problem statement.** Take a fixed BC policy and evaluate its *per-step* action accuracy and its *trajectory-level* success rate as you vary the task horizon `T` (the number of steps to reach the block — make the block farther away for longer horizons). Show that a high per-step accuracy does *not* imply a high trajectory success rate, and that the gap widens with `T`.

**Acceptance criteria.**

- `notes/horizon-experiment.md` has a table: `horizon T | per-step accuracy | trajectory success rate`.
- The data shows per-step accuracy roughly constant while trajectory success *drops* as `T` grows — the compounding-error signature.
- A one-line conclusion connecting this to the `O(εT²)` argument (Lecture 2 §1.1): errors compound, so a 95%-per-step policy fails most long-horizon rollouts.
- Committed.

**Hint.** Per-step accuracy = fraction of steps where the policy's action is within a tolerance of the expert's. Trajectory success = the success predicate at the end. The point is that the first looks great and the second collapses with horizon — exactly why per-step metrics lie about policies.

**Estimated time.** 45 minutes.

---

## Problem 3 — Multiple DAgger rounds to plateau

**Problem statement.** Run DAgger for 4–5 rounds on the reach task, plotting success rate and dataset size vs. round. Identify the round where success *plateaus* and explain why the expert queries stop adding new information.

**Acceptance criteria.**

- `notes/dagger-rounds.md` has the success-vs-round plot and the dataset-size-vs-round numbers.
- You identify the plateau round and explain it: once the policy stops drifting into novel states, the new rollouts visit states already in the dataset, so the expert's labels add nothing new.
- A one-sentence note on the cost of DAgger (the expert must be in the loop every round) and when that cost is worth paying.
- Committed.

**Hint.** Reuse Exercise 3 with `--rounds 5`. The plateau is where the policy's state distribution has converged onto the expert's manifold — further rounds sample the same states. That convergence *is* the closing of the covariate-shift gap.

**Estimated time.** 45 minutes.

---

## Problem 4 — The covariate-shift postmortem (headline deliverable)

**Problem statement.** Reproduce a clean covariate-shift failure of a BC policy, then write a one-page postmortem that diagnoses it, fixes it with DAgger, and proves the fix — with state-visitation evidence, not adjectives.

**Acceptance criteria.**

- `notes/covariate-shift-postmortem.md` exists, fits roughly one page (350–550 words), and has these sections:
  1. **Summary** — one sentence: the BC policy looked healthy (low train+val loss) but failed by drifting.
  2. **The symptom** — the track-then-drift rollout signature, with a trace, and the observation that it succeeds near demo starts and fails from novel ones.
  3. **Why the loss didn't catch it** — the loss is on `d_expert`; the policy is tested on `d_policy`; the gap is invisible to the loss.
  4. **Root cause** — covariate shift, stated as the distributional mismatch and the compounding-error mechanism.
  5. **Fix** — DAgger: the policy's visited states, expert-labeled, aggregated; the success-rate jump (with numbers).
  6. **Evidence** — a state-visitation plot showing BC rollouts off the manifold and DAgger rollouts on it.
- The diagnosis is *specific* — "covariate shift: the policy drifted into 7 off-manifold states the demos never covered; DAgger added them and success went 55% → 85%," not "the policy was bad."
- Committed.

**Hint.** This is the synthesis of the whole week. The strongest evidence is the state-visitation plot (Challenge 1 / Lecture 2 §2): the picture of BC rollouts wandering off the demo manifold *is* the root cause, and DAgger rollouts staying on it *is* the fix. A postmortem with that plot is unanswerable.

**Estimated time.** 60 minutes.

---

## Problem 5 — Wrap the policy in the safety leash

**Problem statement.** Take your trained policy and wrap it in the Week-24 safety pattern: a velocity/workspace clamp on the policy's output, and a classical fallback (a scripted reach or the Week-25 grasp planner) that takes over after the policy's action is clamped three times in a row. Demonstrate the leash catching a drifting policy.

**Acceptance criteria.**

- A `crunch_il/safety_wrap.py` (or a function) that clamps the policy's output to velocity/workspace bounds and counts consecutive rejections.
- `notes/safety-wrap.md` shows: a drifting policy whose wild action is clamped (not executed), and the fallback taking over after three rejections.
- One sentence stating the "ship the learned policy with a leash" principle and why a learned policy near a person needs it.
- Committed.

**Hint.** The clamp is the Week-24 velocity/workspace clamp applied to the policy's output. The fallback is *why* you built the analytic grasp planner in Week 25 — it is the classical controller that takes over. This is the Week-32 "learned policy + classical fallback" pattern, prototyped here.

**Estimated time.** 40 minutes.

---

## Problem 6 — The multimodal demo and why MSE fails it

**Problem statement.** Collect (or synthesize) demos that solve the task two different ways (approach the block from the left in half, from the right in half). Train a BC policy with MSE and show that at the fork it produces a *bad* averaged action. Document why, and note which Week-29 method fixes it.

**Acceptance criteria.**

- `notes/multimodal-failure.md` shows the two-mode demo set and the BC policy's averaged (bad) action at the fork.
- You explain why MSE regression averages multimodal targets into a non-solution (the mean of "go left" and "go right" is "go straight," which hits the obstacle).
- You note that this failure persists *even with no covariate shift and perfect data*, and that Diffusion Policy (Week 29) fixes it by modeling a *distribution* over actions instead of a mean.
- Committed.

**Hint.** Make the "block" something the agent must go around, with left-approach demos and right-approach demos. The MSE-trained policy's action at the decision point will be the average of the two — straight into the obstacle. This is the cleanest demonstration of why a unimodal regression loss is fundamentally limited, independent of covariate shift.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Three failures, labeled | 50 min |
| 2 — Horizon experiment | 45 min |
| 3 — DAgger rounds to plateau | 45 min |
| 4 — Covariate-shift postmortem (headline) | 1 h 0 min |
| 5 — Safety leash around the policy | 40 min |
| 6 — Multimodal demo, MSE failure | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_il` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 29 trains a Diffusion Policy on the same demonstrations and compares against your BC+DAgger baseline. Then take the [quiz](./05-quiz.md) with your notes closed.

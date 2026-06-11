# Week 28 Homework

Six problems that drive the PPO and SAC math and engineering into your fingers. The full set should take about **5 hours**. Work in your Week 28 Git repository (the same workspace as the exercises and the mini-project) so every problem produces at least one commit you can point to at the Phase 4 midterm in Week 32.

The headline deliverable is **Problem 4 — the training report**, the artifact a reviewer reads to decide whether your policy is trustworthy. Treat it as a report, not a journal.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Source your Python env in every terminal (`source .venv/bin/activate`) and have the mini-project's training set up runnable — Problems 4 and 6 run against it. Path B learners: every problem is doable on a laptop; say so in your writeup where the sim is the bottleneck.

---

## Problem 1 — Variance reduction, measured

**Problem statement.** Take the Exercise 2 PPO and run three configurations on CartPole, each for the same number of updates: (a) full-trajectory return (REINFORCE-style, no baseline, no GAE), (b) reward-to-go with the value baseline but $\lambda = 1$ (Monte-Carlo advantage), (c) GAE with $\lambda = 0.95$. Log the gradient-norm variance and the updates-to-solve for each. Tabulate.

**Acceptance criteria.**

- `notes/week-28/variance.md` with a three-row table: config, updates-to-solve (or "did not solve"), and a variance proxy (e.g. std of the per-update gradient norm).
- A one-paragraph reading: GAE-0.95 should solve fastest and most stably; pure-return should be slowest/noisiest or fail.
- Committed.

**Hint.** You don't need to change much — config (a) is "set advantages = returns − mean(returns)" with no critic baseline; (b) is GAE with `lam=1.0`; (c) is the default. Log `torch.nn.utils.clip_grad_norm_`'s return value (it's the pre-clip norm) each step.

**Estimated time.** 45 minutes.

---

## Problem 2 — Derive and verify the `tanh` log-prob correction

**Problem statement.** On paper, derive the change-of-variables correction for $a = \tanh(u)$ with $u\sim\mathcal{N}(\mu,\sigma)$: show that $\log\pi(a) = \log\mathcal{N}(u) - \sum_i\log(1-\tanh^2 u_i)$. Then write a tiny numerical check: sample many $u$, compute the corrected log-prob, and confirm via a histogram that $\exp(\log\pi(a))$ integrates to ~1 over $[-1,1]$ (a Monte-Carlo or fine-grid estimate is fine).

**Acceptance criteria.**

- `notes/week-28/tanh-correction.md` with the derivation (the Jacobian of `tanh` is $1-\tanh^2 u$) and the numerical check showing the squashed density normalizes to ~1.
- You explicitly state what goes wrong if the correction is omitted (the entropy estimate is biased, so automatic-α tuning chases a phantom).
- Committed.

**Hint.** The stable form `2*(log(2) - u - softplus(-2*u))` equals $\log(1-\tanh^2 u)$ negated and summed; verify the two agree numerically away from saturation before trusting it near saturation.

**Estimated time.** 50 minutes.

---

## Problem 3 — On-policy vs off-policy, head to head

**Problem statement.** Run the Exercise 2 PPO and the Exercise 3 SAC on the *same* task (use `Pendulum-v1` for both — adapt PPO to continuous actions with a Gaussian head, or use stable-baselines3's `PPO` and `SAC`). Plot episodic return vs **environment steps** (sample efficiency) for both on one axis. Then plot return vs **wall-clock seconds** on another.

**Acceptance criteria.**

- `notes/week-28/onpolicy-vs-offpolicy.md` with both plots and a paragraph: SAC should reach a given return in *fewer env steps* (more sample-efficient); the wall-clock winner depends on your sim speed and parallelism.
- You connect the result to Lecture 2 §1.6: when would you pick each on a real robot vs a parallel sim?
- Committed.

**Hint.** Use `gymnasium`'s `RecordEpisodeStatistics` wrapper so both log returns the same way. Hold total env steps equal for the sample-efficiency plot.

**Estimated time.** 1 hour.

---

## Problem 4 — The training report (headline deliverable)

**Problem statement.** Write the one-page `TRAINING_REPORT.md` for your mini-project reach policy (or, if the mini-project isn't done yet, for a reach/CartPole/Pendulum run that hits a clear success bar). It must include: the reward function with a sentence defending each term, the hyperparameter table, the five TensorBoard traces (reward, success rate or return, KL, clip fraction, explained variance) each with a one-line reading, the throughput (steps/sec) and wall-time-to-target, and an honest "what I'd tune next."

**Acceptance criteria.**

- `TRAINING_REPORT.md` exists, fits ~one page, and hits all six sections.
- Each of the five traces has a *specific* reading ("KL held at 0.012, so the clip was binding correctly"), not "it went up."
- The success/return claim is backed by the actual trace, not prose.
- The "what I'd tune next" item is concrete (a hyperparameter or a reward term), not "train longer."
- Committed.

**Hint.** A reviewer reads this in three minutes and decides whether to trust your policy. The trace readings are what build that trust — a report that says "explained_variance climbed to 0.94, so the critic learned the returns" reads like an engineer; "the graphs look good" reads like a student.

**Estimated time.** 1 hour.

---

## Problem 5 — Reward-hacking postmortem

**Problem statement.** Take one of the three hacks from Challenge 1 (or engineer your own). Reproduce the *rising reward curve + wrong behavior*. Write a short postmortem against this template: (1) the symptom — reward up, task not solved; (2) the rollout evidence — the `dist`/`speed` trace that proves the exploit; (3) the root cause — which reward term was farmable and why the optimizer found it; (4) the fix — the corrected reward, ideally potential-based, with the property that closes the exploit; (5) prevention — one process change (e.g. "always plot true-success alongside reward; always watch a rollout before a long run").

**Acceptance criteria.**

- `notes/week-28/reward-hacking-postmortem.md` with all five sections, fitting ~one page.
- The root cause names a *specific* term and the laziest way to maximize it.
- The fix has the three good-reward properties from Challenge 1 where relevant (potential-based guidance, effort penalty, settled-gated success).
- Committed.

**Hint.** The strongest evidence is the graph where *reward rises while true success stays flat* — generate that plot. It's exactly what a reward hack looks like on a dashboard, and recognizing it is the whole skill.

**Estimated time.** 45 minutes.

---

## Problem 6 — Deterministic deployment and the obs-mismatch trap

**Problem statement.** Take your trained policy and run it through the mini-project's ROS2 inference node (or a minimal stand-in) in two ways: (a) sampling actions stochastically, (b) using the mean (deterministic). Measure success rate and action jerk (sum of squared action differences) for each. Then *deliberately* introduce an observation mismatch — permute two entries of the obs vector the node assembles versus training — and document how the policy degrades.

**Acceptance criteria.**

- `notes/week-28/deployment.md` with the deterministic-vs-stochastic comparison (success rate + jerk) and the obs-mismatch experiment.
- You confirm deterministic deploy is smoother (lower jerk) and state why we explore stochastically but act deterministically.
- You document that the obs mismatch silently wrecks the policy (no crash, just bad actions) — the #1 deployment bug — and a guard against it (export and assert the obs spec).
- Committed.

**Hint.** The obs mismatch is the most realistic deploy bug and it's *silent* — the node runs, the policy outputs plausible-looking actions, the robot does the wrong thing. Asserting the obs layout against a spec saved with the checkpoint is the cheap insurance.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Variance reduction, measured | 45 min |
| 2 — Derive the tanh correction | 50 min |
| 3 — On-policy vs off-policy | 1 h 0 min |
| 4 — Training report (headline) | 1 h 0 min |
| 5 — Reward-hacking postmortem | 45 min |
| 6 — Deterministic deployment | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the mini-project's training run and ROS2 node are in the same workspace — Week 32 compares against them. Then take the [quiz](./quiz.md) with your notes closed.

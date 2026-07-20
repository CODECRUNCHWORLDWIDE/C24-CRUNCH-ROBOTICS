# Week 29 Homework

Six problems that drive the diffusion math and the Diffusion Policy engineering into your fingers. The full set should take about **5 hours**. Work in your Week 29 Git repository (the same workspace as the exercises and the mini-project) so every problem produces at least one commit you can point to at the Phase 4 midterm in Week 32.

The headline deliverable is **Problem 4 — the eval report**, the artifact a reviewer reads to decide whether your Diffusion Policy actually beats BC and why. Treat it as a report, not a journal.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Source your Python env in every terminal. Have the mini-project's training set up runnable — Problems 3, 4, and 6 build on it. Path B learners: every problem runs on a laptop; note where sim throughput is the bottleneck.

---

## Problem 1 — Derive the closed-form noising, then verify

**Problem statement.** Reproduce the Exercise 1 Part A derivation of $x_t = \sqrt{\bar\alpha_t}x_0 + \sqrt{1-\bar\alpha_t}\epsilon$ from the per-step recursion, writing every step. Then write a numpy script that builds $x_t$ both ways — (a) by iterating the per-step process $t$ times, and (b) by the closed form — for $t = 1\dots T$ and confirms they produce the same *distribution* (match the mean and variance over many samples).

**Acceptance criteria.**

- `notes/week-29/closed-form.md` with the derivation and the numpy verification: mean and variance of the iterated vs closed-form $x_t$ agree (to sampling error) for several $t$.
- You state the practical consequence: training needs the closed form, not the iteration.
- Committed.

**Hint.** The iterated version accumulates noise step by step; the closed form jumps directly. They won't match *sample for sample* (different random draws) but their *distributions* (mean ≈ $\sqrt{\bar\alpha_t}x_0$, var ≈ $1-\bar\alpha_t$) must agree. Average over ~10k samples.

**Estimated time.** 45 minutes.

---

## Problem 2 — The DDIM step-count latency curve

**Problem statement.** Take the Exercise 2 (or 3) trained model. Sample with DDIM at step counts {2, 4, 8, 16, 32, 64} and, for each, measure (a) wall-clock inference time per sample and (b) a sample-quality proxy (for the bimodal toy: the fraction of mass correctly in the two modes vs the empty middle; for the policy: success rate). Plot quality vs latency.

**Acceptance criteria.**

- `notes/week-29/ddim-steps.md` with the quality-vs-latency table and plot.
- You identify the **knee** — the fewest steps that hold quality — and state which step count you'd deploy and why.
- You connect it to the latency budget: a 30 Hz / receding-horizon controller's re-plan window.
- Committed.

**Hint.** Quality usually saturates well before 64 steps — often by 16. The point is to *measure* the knee on your model, not assume it. Time only the denoise loop, excluding model load.

**Estimated time.** 45 minutes.

---

## Problem 3 — Execution-horizon sweep (reactivity vs smoothness)

**Problem statement.** With your mini-project Diffusion Policy at a fixed prediction horizon $T_p$, run receding-horizon rollouts at execution horizons $T_a \in \{1, 2, 4, 8\}$. For each, measure success rate and action jerk (sum of squared consecutive-action differences). Plot both vs $T_a$.

**Acceptance criteria.**

- `notes/week-29/exec-horizon.md` with the success-and-jerk-vs-$T_a$ plot.
- You confirm the Lecture 2 §3.2 trade: short $T_a$ is reactive but can be jerky at chunk seams; long $T_a$ is smooth but stale/less reactive. State your chosen $T_a$ and why.
- Committed.

**Hint.** Jerk at the seams comes from consecutive chunks disagreeing slightly. If you see *no* trade-off, your task may be too easy (no disturbances to react to) — add a small disturbance mid-rollout so reactivity matters.

**Estimated time.** 50 minutes.

---

## Problem 4 — The eval report (headline deliverable)

**Problem statement.** Write the one-page `EVAL_REPORT.md` for your mini-project: the task and demo mode-split, the policy config ($T_p$/$T_a$/$T_o$/DDIM steps with reasoning), the head-to-head success table (Diffusion Policy vs BC vs BC+DAgger on a fixed protocol), the multimodality scatter captioned with success rates, the measured deployment latency with the budget arithmetic, and an honest "what I'd try next."

**Acceptance criteria.**

- `EVAL_REPORT.md` exists, ~one page, all six elements present.
- The head-to-head used the *same demos and baselines* as Week 27 and a protocol fixed before training (state both).
- The success gap (if any) is interpreted correctly — and if the task turned out unimodal and BC did fine, you say so honestly rather than inventing a gap.
- The multimodality scatter is included and its connection to the success gap is stated.
- Committed.

**Hint.** A reviewer trusts the *controlled* comparison and the *measured* latency. "Diffusion Policy scored 0.91 vs BC's 0.58 on 50 fixed-seed episodes; the scatter shows why — BC's mean lands in the obstacle" reads like an engineer; "Diffusion Policy worked better" reads like a learner.

**Estimated time.** 1 hour.

---

## Problem 5 — Visualize the denoising trajectory

**Problem statement.** For the Exercise 2 bimodal toy (or your policy at a fixed state), take a *single* noise seed and record the sample $x_t$ at every DDIM step from pure noise to the final action. Plot the trajectory (the value at each step). Do this for several seeds and overlay them. Show how different seeds get *pulled toward different modes* as denoising proceeds.

**Acceptance criteria.**

- `notes/week-29/denoising-trajectory.md` with the multi-seed denoising-trajectory plot.
- A paragraph explaining what you see: early steps (high noise) look similar across seeds; late steps *fork* toward the modes — this is the mechanism by which a regression-trained model produces multimodal samples (Lecture 1 §3).
- Committed.

**Hint.** This is the visual companion to Q5 on the quiz. The fork is the answer to "how does an MSE loss give multimodal samples?" — the noise seed selects the mode, and you can *watch* the selection happen across denoising steps.

**Estimated time.** 50 minutes.

---

## Problem 6 — The observation-mismatch trap, on purpose

**Problem statement.** Take your mini-project ROS2 deployment node. Run it correctly and confirm the arm reaches the goal. Then *deliberately* introduce an observation mismatch — permute two entries of the obs vector the node assembles versus training, or skip the normalization — and document exactly how the policy degrades (silently). Then add a guard: export the obs spec (order + normalization stats) with the checkpoint and `assert` the node's assembled obs against it at startup.

**Acceptance criteria.**

- `notes/week-29/obs-mismatch.md` with: the working baseline, the degraded behavior under the mismatch (no crash, just wrong actions), and the guard you added.
- You state why this is the #1 silent deployment bug and how the spec-assert catches it before the robot moves.
- Committed.

**Hint.** The mismatch is silent — the node runs, the policy outputs plausible-looking action chunks, the arm does the wrong thing. The cheap insurance is a spec saved alongside the checkpoint that the node asserts against; this is the same discipline as Week 28's deploy problem, now with chunked actions.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Closed-form noising + verify | 45 min |
| 2 — DDIM step-count latency curve | 45 min |
| 3 — Execution-horizon sweep | 50 min |
| 4 — Eval report (headline) | 1 h 0 min |
| 5 — Denoising-trajectory visualization | 50 min |
| 6 — Observation-mismatch trap | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the Diffusion Policy, its eval harness, and the ROS2 node are in the same workspace — Week 30 compares ACT against them on the same measuring stick. Then take the [quiz](./quiz.md) with your notes closed.

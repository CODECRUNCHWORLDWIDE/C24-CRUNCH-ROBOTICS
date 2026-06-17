# Week 30 Homework

Six problems that drive ACT's math and the benchmarking discipline into your fingers. The full set should take about **5 hours**. Work in your Week 30 Git repository (the same workspace as the exercises and the mini-project) so every problem produces at least one commit you can point to at the Phase 4 midterm in Week 32.

The headline deliverable is **Problem 4 — the comparison table**, the portfolio-grade artifact a reviewer (and an interviewer) reads to judge whether you can *choose* between policies, not just train them. Treat it as a decision document.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Source your Python env in every terminal. Have the mini-project's ACT and your Week-29 Diffusion Policy runnable — Problems 2, 4, and 6 use both. Benchmark on your deployment target if you have a Jetson; otherwise dev GPU + CPU, documented.

---

## Problem 1 — Derive the KL and find the collapse boundary

**Problem statement.** Reproduce the Exercise 1 derivation of the closed-form KL $-\tfrac{1}{2}(1 + \log\sigma^2 - \mu^2 - \sigma^2)$ from the definition. Then write a numpy sweep: fix a reconstruction loss of ~0.3 and, for $\beta \in \{0.1, 1, 10, 100\}$, compute what posterior the optimizer is pushed toward (qualitatively) and at which $\beta$ the KL term so dominates that collapse ($z\to$ prior) is the rational outcome.

**Acceptance criteria.**

- `notes/week-30/kl-collapse.md` with the derivation and the $\beta$ sweep reasoning.
- You state the collapse boundary qualitatively and connect it to "ACT mode-averages like BC when collapsed."
- Committed.

**Hint.** You don't need to train to reason about this — at high $\beta$, the cheapest way to reduce the loss is to drive the KL to 0 (set $\mu=0$, $\sigma=1$), even though that destroys the latent's usefulness. That's the collapse incentive.

**Estimated time.** 45 minutes.

---

## Problem 2 — The fair latency benchmark

**Problem statement.** Benchmark ACT (single pass) and your Week-29 Diffusion Policy ($N$-step DDIM) on the same device, following all five rules (warm-up, sync, batch-of-one, deploy precision, median + p99). Then *deliberately* run an UNFAIR version (no warm-up, no sync) and show how the numbers change — demonstrating why the methodology matters.

**Acceptance criteria.**

- `notes/week-30/benchmark.md` with the fair benchmark (median + p99, device, precision) for both policies, and the unfair version alongside.
- ACT's fair latency is clearly lower than $N$-step Diffusion Policy's.
- You document how the unfair version (no sync) produces absurd/equal numbers, and why.
- Committed.

**Hint.** The unsynced version will report microsecond "latencies" that are roughly equal for both — because you measured kernel launches, not compute. Seeing the wrong number makes the right methodology stick.

**Estimated time.** 45 minutes.

---

## Problem 3 — Temporal-ensembling decay sweep

**Problem statement.** Using the Exercise 3 ensembler (or your deployed ACT), sweep the decay $m \in \{0.001, 0.05, 0.5, 5.0\}$ and measure jerk and reactivity (e.g. how fast the action responds to a mid-rollout disturbance). Plot both vs $m$.

**Acceptance criteria.**

- `notes/week-30/m-sweep.md` with the jerk-and-reactivity-vs-$m$ plot.
- You confirm the trade: large $m$ → reactive but jerkier (trust newest); small $m$ → smooth but laggy (average all). State your chosen $m$ and why.
- Committed.

**Hint.** Inject a step disturbance into the simulated policy output partway through the rollout and measure how many timesteps the ensembled action takes to track it. Small $m$ tracks slowly (laggy); large $m$ tracks fast (reactive).

**Estimated time.** 50 minutes.

---

## Problem 4 — The comparison table (headline deliverable)

**Problem statement.** Write the one-page `COMPARISON.md`: the five-axis ACT-vs-Diffusion-Policy table filled with *your measured numbers* (success rate, latency median+p99, deploy-time multimodality, jerk, training cost), and a budget-referenced shipping recommendation that notes at least one condition under which the choice would flip.

**Acceptance criteria.**

- `COMPARISON.md` exists, ~one page, with the five-axis table from measured numbers (same demos, same eval protocol for both).
- The recommendation references the 30 Hz / 33 ms budget explicitly and is derived from the table.
- At least one flip condition is stated (e.g., "if the task were more ambiguous, Diffusion Policy's deploy-time multimodality would override ACT's latency edge").
- The latency entries state device + precision (so the numbers are interpretable).
- Committed.

**Hint.** This is the artifact an interviewer respects. "We shipped ACT: equal success, 7 ms p99 vs 35 ms, fits the budget with headroom for perception" reads like an engineer who measured; "ACT is the deployment-friendly one" reads like someone who read the abstract.

**Estimated time.** 1 hour.

---

## Problem 5 — The CVAE-vs-plain-regressor ablation

**Problem statement.** Train your miniature ACT (Exercise 2) twice on the multimodal toy: once as the CVAE (with the latent), once with the latent *disabled* (force $z=0$ during training too, making it a plain L1 chunk regressor). At the multimodal state, sample/inspect the predicted chunk from each. Show the plain regressor mode-averages (a chunk that does *neither* style — the invalid middle), while the CVAE-trained model produces a coherent chunk.

**Acceptance criteria.**

- `notes/week-30/cvae-ablation.md` with the two models' predicted chunks at the multimodal state and a plot or numbers showing the plain-regressor average vs the CVAE's coherent output.
- You connect this to Week 29's multimodal-action lesson: the CVAE is ACT's answer to the same problem Diffusion Policy solved with denoising.
- Committed.

**Hint.** Disabling the latent (always $z=0$ at train and test) turns ACT into exactly the plain regressor that mode-averages. The contrast is the cleanest possible demonstration of *why* the CVAE is there.

**Estimated time.** 50 minutes.

---

## Problem 6 — Deploy and document the budget

**Problem statement.** Run your ACT through the mini-project ROS2 node (or a minimal stand-in) with temporal ensembling at 30 Hz. Measure the actual per-tick wall time (inference + ensembling). Document the latency budget arithmetic: per-tick budget (33 ms), measured inference, remaining headroom for perception/control. Then reproduce the obs-mismatch trap (from Week 29) once more to confirm the guard catches it.

**Acceptance criteria.**

- `notes/week-30/deploy.md` with the measured per-tick time, the budget arithmetic, and confirmation the node drives the arm at 30 Hz.
- The obs-spec assert is in place and demonstrated to catch a deliberate mismatch before the robot moves.
- Committed.

**Hint.** ACT's single-pass inference should leave comfortable headroom at 30 Hz — that headroom is the whole point, and quantifying it ("6 ms inference, 27 ms headroom") is the deployment-engineer's habit. The obs-mismatch guard is the same discipline as Weeks 28 and 29; it never stops being the #1 silent bug.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Derive the KL + collapse boundary | 45 min |
| 2 — The fair latency benchmark | 45 min |
| 3 — Temporal-ensembling decay sweep | 50 min |
| 4 — The comparison table (headline) | 1 h 0 min |
| 5 — CVAE-vs-plain-regressor ablation | 50 min |
| 6 — Deploy and document the budget | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure your ACT, your Week-29 Diffusion Policy, and the comparison table are in the same workspace — Week 32 wraps your *chosen* policy in a safety filter, and Week 39 profiles the integrated graph against these baselines. Then take the [quiz](./05-quiz.md) with your notes closed.

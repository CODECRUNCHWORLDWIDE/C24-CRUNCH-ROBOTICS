# Mini-Project — Train ACT on the Week-27/29 Demos, Benchmark Latency, Compare to Diffusion Policy, Deploy in ROS2

> Train an **Action Chunking Transformer (ACT)** on the *same* demonstrations as Weeks 27 and 29, **benchmark its inference latency** on your deployment target (Jetson Orin or dev GPU) against the Week-29 Diffusion Policy, **compare success rate at a fixed latency budget**, and **deploy** ACT as a `rclpy` node with temporal ensembling. Produce a one-page, portfolio-grade comparison table.

This is the artifact that proves you can not only *build* a modern imitation policy but *choose* between two of them on the axis a robotics company actually cares about — success at a fixed latency budget. It's the capstone of the Phase-4 policy-learning arc (BC → DAgger → RL → Diffusion Policy → ACT) and the direct input to the Week-32 midterm, where one of these policies gets wrapped in a safety filter and shipped.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** the trained ACT, the latency benchmark, and the comparison table feed **Week 32** (you wrap your *chosen* policy — ACT or Diffusion Policy — in a runtime safety filter with a classical fallback) and **Week 39** (you profile and quantize the integrated graph, and the latency numbers you measure here are the baseline). The comparison table itself is a portfolio piece — it's exactly the kind of measured, defensible artifact that wins a robotics interview.

---

## What you will build

Five deliverables:

1. **A trained ACT** — on the Week-27/29 demos (the same set), with chunking + the CVAE, hitting a clear success bar on the *same* eval harness as Week 29.
2. **A rigorous latency benchmark** — ACT (single pass) vs Diffusion Policy ($N$-step DDIM) on the same device, following the five benchmarking rules (warm-up, sync, batch-of-one, deploy precision, median + p99).
3. **A head-to-head comparison** — ACT vs Diffusion Policy on the fixed eval protocol: success rate, latency, jerk.
4. **A ROS2 deployment node** (`act_policy_node.py`) — loads the checkpoint, runs **temporal ensembling**, drives the arm in Gz Sim at 30 Hz, with Week-5 QoS.
5. **A one-page comparison table** (`COMPARISON.md`) — the five-axis ACT-vs-Diffusion-Policy table and the budget-referenced shipping recommendation.

---

## Use LeRobot for ACT (don't reimplement the transformer)

You built the *core* (CVAE + chunk decoder) in Exercise 2. For the mini-project, use the maintained implementation so your time goes into training, the *fair benchmark*, the comparison, and deployment:

- **LeRobot — the `act` policy** (`pip install lerobot`) — a clean ACT with the ResNet image backbone, the CVAE, and temporal ensembling, trainable on the *same standardized dataset* you used for the Week-29 Diffusion Policy. This is what makes the comparison genuinely apples-to-apples.
- **or the original ACT repo** (Tony Zhao) if you prefer.
- **or your scaled Exercise-2 model** — acceptable, but reimplementing the transformer is *not* where the marks are. The marks are in the fair benchmark, the comparison, and the deployment.

Be ready to point at where the CVAE loss, the temporal ensembling, and the chunk decoder live in the code you used.

---

## Deliverable 1 — train ACT

Reuse the Week-29 dataset (the same demos, same format). Train with the same train/eval split so the comparison is fair.

```bash
# LeRobot sketch (flags vary by version; check the docs you pinned):
python -m lerobot.scripts.train \
    policy=act env=<your_task> dataset_repo_id=<your_demos> \
    training.offline_steps=100000
```

Choose the chunk size $k$ (e.g. 16 — the same horizon as your Diffusion Policy's $T_p$, for fairness) and the temporal-ensembling decay $m$. Watch the L1 reconstruction *and* the KL during training: if the KL crashes toward 0, you have **posterior collapse** ($\beta$ too high) and ACT will mode-average like BC — lower $\beta$. Run the eval rollout periodically; success climbing is the ground truth, not the loss alone.

---

## Deliverable 2 — the rigorous latency benchmark

This is where the week's benchmarking discipline lands. Benchmark on your deployment target (Jetson Orin if you have one; otherwise dev GPU *and* CPU, documented):

- **ACT**: one forward pass. **Diffusion Policy**: $N$-step DDIM (the step count you chose in Week 29).
- Follow all five rules (Lecture 2 §2.1): warm up (~20, discarded), `torch.cuda.synchronize()` before reading the clock, batch of one, deploy precision (FP16 if shipping FP16), 100+ runs reporting **median and p99**.

```python
results = {
    "act": benchmark(act_model, sample_obs, device="cuda"),
    "diffusion": benchmark_n_step(diffusion_model, sample_obs, n_ddim=16, device="cuda"),
}
# Report median + p99 for both; state the device and precision.
```

If ACT isn't clearly faster, your benchmark is unfair — fix it (you almost certainly forgot the sync or the warm-up). The single-pass advantage is real; an honest benchmark shows it.

---

## Deliverable 3 — the head-to-head

On the fixed Week-29 eval protocol (same N, same seeds, same criterion), measure success rate and jerk for both ACT and Diffusion Policy. Report honestly — on many tasks the two are within a few points on success, and the *latency* is where they diverge. If ACT's success is meaningfully lower, that matters more than latency and you say so.

---

## Deliverable 4 — the ROS2 deployment node

Reuse the Week-29 deployment skeleton, swapping the receding-horizon controller for **temporal ensembling** (Lecture 2 §4):

1. Load the checkpoint (`torch.jit.load`) and the (un)normalization stats.
2. Each control tick (30 Hz): assemble the obs (same layout as training — the #1 silent bug), run ACT *once* to get a fresh chunk, feed it to the `TemporalEnsembler`, and publish the ensembled action.
3. Week-5 QoS: `RELIABLE`/`KEEP_LAST(1)` for commands, `BEST_EFFORT` for sensor state. Un-normalize the action (the #2 silent bug).

Because ACT inference is single-pass and fast, you predict a fresh chunk *every* tick and ensemble — no action queue needed. Document the *measured* per-tick inference time and confirm it fits the 33 ms budget with margin.

---

## Deliverable 5 — the comparison table

`COMPARISON.md`, one page, the five-axis table filled with *your measured numbers*:

| Axis | ACT | Diffusion Policy |
|---|---|---|
| Success rate (N=___) | | |
| Inference latency (median / p99 ms, device, precision) | | |
| Deploy-time multimodality | no (z=0) | yes (re-sample) |
| Jerk (smoothness) | | |
| Training cost (wall-clock) | | |

Plus the **recommendation**: which ships at a 30 Hz budget and why, derived from the table and referencing the budget explicitly. Note at least one condition under which the choice would flip.

---

## Rules

- **You must** train ACT on the *same demos* and evaluate on the *same protocol* as the Week-29 Diffusion Policy. Different data or different eval invalidates the comparison.
- **You must** benchmark fairly (the five rules) and report median + p99. An unsynchronized GPU benchmark fails this deliverable.
- **You must** deploy ACT with temporal ensembling and correct QoS, and report measured latency.
- **You must not** make a shipping recommendation that isn't derived from your measured table.
- Python 3.12, PyTorch ≥ 2.3, ROS2 Jazzy.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-30-act-<yourhandle>`.
- [ ] A reproducible ACT training command; ACT hits a clear success bar on the Week-29 eval harness.
- [ ] A latency benchmark following all five rules, reporting median + p99 for ACT and Diffusion Policy on a stated device + precision.
- [ ] A head-to-head success + jerk table on the fixed protocol.
- [ ] `act_policy_node.py` runs temporal ensembling, drives the arm in Gz Sim at 30 Hz, correct QoS, measured inference time fitting the budget.
- [ ] `COMPARISON.md` with the five-axis table and a budget-referenced recommendation.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Benchmark rigor** | 25 | All five rules followed (warm-up, sync, batch-of-one, deploy precision, median+p99); device + precision stated; ACT's single-pass advantage shown honestly. |
| **Fair comparison** | 25 | Same demos, same eval protocol, same horizon; honest success + jerk table; gap interpreted correctly. |
| **Deployment** | 25 | Temporal ensembling implemented; correct QoS; (un)normalization right; measured per-tick latency fits the budget; obs spec asserted. |
| **Training & config** | 15 | Sensible $k$ and $m$ and $\beta$; no posterior collapse (KL stayed useful); success climbed on the eval rollout. |
| **The table & recommendation** | 10 | Five-axis table from measured numbers; recommendation references the 30 Hz budget; a flip condition noted. |

**90+** is portfolio-grade — the comparison table is interview-ready, and the chosen policy is ready for the Week-32 safety wrap. **70–89** trains and deploys but the benchmark is soft or the recommendation isn't derived from the numbers. **Below 70** usually means the benchmark was unfair (no sync/warm-up) or the comparison wasn't controlled (different demos/eval).

---

## Stretch goals

- **$\beta$ ablation.** Train ACT at several $\beta$ values; show posterior collapse at high $\beta$ (KL → 0, ACT mode-averages) and instability at low $\beta$. Plot KL and success vs $\beta$, and connect to Week-29's multimodality lesson.
- **Chunk-size sweep.** Train ACT at $k \in \{1, 8, 16, 32\}$ and plot success vs $k$. Confirm the compounding-error story: larger $k$ shrinks the effective horizon, but huge $k$ chunks get harder to predict coherently.
- **$m$ sweep on the real policy.** Sweep the temporal-ensembling decay on your deployed ACT and plot jerk vs reactivity (with a mid-rollout disturbance so reactivity matters). Find the knee.
- **Quantize.** FP16 (and INT8 if you can) both policies and re-benchmark; reason about which benefits more — the Week-39 setup.

---

## What "done" looks like (a self-check before you submit)

Run through this before you call the mini-project finished:

- I can re-run ACT training from one documented command and get a policy that hits the success bar on the Week-29 eval harness.
- My latency benchmark warms up, synchronizes, runs batch-1 at deploy precision, and reports median + p99 — and ACT is clearly faster than $N$-step Diffusion Policy.
- The head-to-head used the same demos, the same eval protocol, and the same horizon for both policies, and I stated the controls explicitly.
- The ROS2 node runs temporal ensembling (with the buffer cleared on reset), correct QoS, and (un)normalization — and the measured per-tick latency fits the budget.
- My `COMPARISON.md` table is filled with measured numbers, and the recommendation references the 30 Hz budget and names a flip condition.
- The KL stayed useful during training (no posterior collapse), confirmed by the logged KL curve.

If any line is "no," that's your next task. The most common gaps are an unfair benchmark (no sync) and a comparison that drifted (different data or precision) — both invalidate the headline result, so guard them first.

## Suggested timeline (the 12 hours)

| Block | Hours | What you do |
|---|---:|---|
| Thursday | 2h | Point LeRobot's `act` at the Week-29 dataset; launch training; watch the L1 + KL (catch posterior collapse early) |
| Friday | 3h | Run the eval; build the fair latency benchmark (the five rules); run the head-to-head against Diffusion Policy |
| Saturday | 3h | Build the ROS2 node with temporal ensembling; measure per-tick latency; confirm it drives the arm |
| Spread across | 4h | Write `COMPARISON.md`; the $\beta$/$k$/$m$ sweeps if time; push the repo |

Front-load the benchmark methodology (Friday): a sloppy benchmark is the single most common way this week's headline result comes out wrong, and you want to validate your timing harness (warm-up + sync) on a known case before you trust its numbers.

## A note on fairness, restated

The comparison is only evidence if it's *controlled*. The control is: same demonstrations, same eval protocol, same chunk horizon, same precision, same device. The variable is the policy architecture. If you let any of the controls drift — train ACT on more data, evaluate it on different seeds, benchmark it at a different precision — the comparison stops meaning anything, and a reviewer will (correctly) discount it. When you write the table, state the controls explicitly: "both trained on the same 200 demos, evaluated on the same 50 fixed-seed episodes, both FP16 on an RTX 4070, chunk horizon 16." That sentence is what makes the numbers trustworthy.

## Common pitfalls (read before you start)

In rough order of frequency:

1. **Unfair benchmark — the disqualifier.** No warm-up, or no `torch.cuda.synchronize()` before reading the clock. You measure kernel launches (microseconds), get absurdly low and near-equal numbers, and ACT's whole advantage vanishes. Warm up ~20 passes, sync before every timing read, batch of one, report median + p99. If your two latencies look suspiciously close and small, you forgot the sync.
2. **Posterior collapse.** $\beta$ too high → the KL crushes the latent to the prior → ACT mode-averages like BC. Watch the KL during training; if it crashes toward 0, lower $\beta$. (You'll see this in Exercise 2 if you crank $\beta$.)
3. **Apples-to-oranges comparison.** ACT trained on different demos, a different eval protocol, or a different chunk horizon than the Diffusion Policy. Then the comparison means nothing. Same data, same protocol, same horizon — that's what makes it evidence.
4. **Observation mismatch / forgotten un-normalization.** The same two silent deploy bugs as Weeks 28–29. Assert the obs spec; keep the (un)normalization stats with the checkpoint.
5. **Wrong $m$ for temporal ensembling.** Too small and the motion lags (old predictions drag it); too large and you recover the chunk-switching jerk. Sweep it with a mid-rollout disturbance so reactivity matters.
6. **Comparing different precisions.** ACT at FP16 vs Diffusion Policy at FP32 (or vice versa) is not a fair latency comparison. Match the precision you'd deploy, and state it.

Each of these is in the lectures; this is the "what actually bites people" digest. Walk it before changing anything fundamental.

## How this connects to the rest of C24

- **Week 31 (Octo / OpenVLA)** moves to generalist, language-promptable policies that also emit action chunks; the deployment-latency reasoning you sharpened here is exactly what decides whether a billion-parameter VLA fits the control loop.
- **Week 32 (Phase 4 midterm)** wraps your *chosen* policy (from this comparison) in a runtime safety filter with a classical fallback and a hazard-log update.
- **Week 39 (edge ML)** profiles and quantizes the integrated graph; your benchmark numbers here are the baseline it improves on.

## A reminder on what makes this portfolio-grade

The trained ACT is table stakes — plenty of people can run `lerobot train`. What makes this repo something to put in front of an interviewer is the *comparison*: a fair, rigorous, controlled head-to-head between two modern policies with a defensible shipping recommendation. The benchmark methodology (warm-up, sync, batch-1, p99) and the controlled comparison (same data, same eval, stated controls) are the rare skills. Lead the README with the comparison table and the recommendation, not the training command.

When you've finished, push the repo and take the [quiz](../quiz.md).

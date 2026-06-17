# Mini-Project — Train a Diffusion Policy on the Week-27 Demos, Beat BC and DAgger, Deploy It Receding-Horizon in ROS2

> Train a **Diffusion Policy** on the demonstrations you collected in Week 27 (augmentable to ~200 trajectories), beat both **BC** and **BC+DAgger** on a fixed eval protocol, **visualize the action distribution** at a known multimodal state to prove the multimodality, and **deploy** the policy as a `rclpy` node with a real-time receding-horizon controller driving the arm in Gz Sim.

This is the artifact that proves you can take a modern imitation-learning method from paper to a robot: shape the data, train a conditioned denoiser, sample it fast with DDIM, run it inside a real-time control loop, and *measure* that it wins — not because you tuned it, but because the task is multimodal and diffusion handles that. It's also the direct setup for the Week 30 head-to-head against ACT.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** the trained Diffusion Policy, its eval harness, and its ROS2 deployment node are reused **directly in Week 30** (you train ACT on the same demos and compare at a fixed latency budget) and in **Week 32** (the Phase 4 midterm, where this policy gets wrapped in a safety filter with a classical fallback). Build the eval harness cleanly now — Week 30 imports it.

---

## What you will build

Four deliverables:

1. **A trained Diffusion Policy** — on the Week-27 demos (augment to ~200 if your set is smaller), with action chunking and DDIM sampling, hitting a clear success bar on the eval set.
2. **A head-to-head eval** — Diffusion Policy vs BC vs BC+DAgger on a *fixed* protocol (same seeds, same success criterion), with a success-rate table.
3. **A multimodality visualization** — the action-distribution scatter at a known multimodal state, showing Diffusion Policy's modes against BC's collapsed mean.
4. **A ROS2 deployment node** (`diffusion_policy_node.py`) — loads the checkpoint, runs the receding-horizon action-queue controller, and drives the arm in Gz Sim, with the DDIM step count tuned to fit the control loop's latency budget.

Plus a one-page **eval report** (`EVAL_REPORT.md`).

---

## Use LeRobot (don't reimplement the U-Net)

You implemented the *core* in Exercise 3. For the mini-project, use a maintained implementation so your time goes into the *data, eval, and deployment* — the parts that actually demonstrate the skill:

- **LeRobot** (`pip install lerobot`) — its `diffusion` policy is a clean Diffusion Policy with the 1D U-Net + FiLM, DDPM/DDIM schedulers from `diffusers`, and a training entrypoint. Wrap your Week-27 demos into its dataset format and train.
- **or `diffusion_policy`** (Chi et al.'s reference repo) if you prefer the original.
- **or your own** Exercise-3 architecture scaled up — acceptable, but reimplementing the U-Net is *not* where the marks are. The marks are in data, eval, multimodality evidence, and deployment.

Whatever you choose, you must understand it: be ready to point at where the ε-loss, the DDIM sampler, the action chunking, and the FiLM conditioning live in the code you used.

---

## Deliverable 1 — the trained policy

### Data

Take your Week-27 demos. If you have ~50, augment toward ~200 by collecting more teleop trajectories (the syllabus explicitly allows this) — and **make sure the set contains the multimodality you'll later visualize.** If every demo solves the task the same way, you have nothing to show; deliberately demonstrate the *two ways* (left/right, or two grasp faces) so the modes exist in the data. Normalize actions to ~$[-1, 1]$ for training; keep the (un)normalization stats with the checkpoint.

### Train

```bash
# LeRobot sketch (flags vary by version; check the docs you pinned):
python -m lerobot.scripts.train \
    policy=diffusion env=<your_task> dataset_repo_id=<your_demos> \
    training.offline_steps=100000
```

Watch the training loss fall and — more importantly — periodically run the eval rollout and watch the success rate climb. A falling loss with flat success means the policy is fitting the data but not *solving the task* (often a normalization or horizon bug); the eval rollout is the ground truth.

### Choose horizons and DDIM steps

Set the prediction horizon $T_p$ (e.g. 16), execution horizon $T_a$ (e.g. 8), and observation horizon $T_o$ (e.g. 2). Pick a DDIM step count (start at 16) and confirm inference fits your control loop's budget (see Deliverable 4). Document the choices and one sentence of reasoning each.

---

## Deliverable 2 — the head-to-head eval

Define the eval protocol **before** you train (so you can't tune to it): N episodes (≥ 50), fixed seeds, an explicit success criterion. Run Diffusion Policy, your Week-27 BC, and your Week-27 BC+DAgger through the *same* protocol. Report:

| Policy | Success rate (N=___) | Notes |
|---|---|---|
| BC | | from Week 27 |
| BC + DAgger | | from Week 27 |
| Diffusion Policy | | this week |

On a genuinely multimodal task, Diffusion Policy should clearly lead. If it *doesn't*, either your task isn't multimodal (BC does fine on unimodal tasks — that's expected, and you should say so honestly) or your Diffusion Policy has a bug. Either way, *report what you actually measured*; a smaller-but-honest gap beats a fabricated large one.

---

## Deliverable 3 — the multimodality visualization

This is the week's signature artifact. At a state you *know* is multimodal:

```python
# Sample the first action 512 times from different noise seeds.
acts = torch.stack([policy.predict_action_chunk(obs)[0, 0] for _ in range(512)])
plt.scatter(acts[:, 0], acts[:, 1], s=4, alpha=0.3, label="Diffusion Policy")
plt.scatter([bc_action[0]], [bc_action[1]], c="r", marker="x", s=120, label="BC mean")
```

Diffusion Policy's scatter should show **≥ 2 clusters**; the BC point sits in the **invalid valley** between them. Caption it with the success rates. This single figure is the most convincing thing in your report — it's *why* the success-rate gap exists, made visible.

---

## Deliverable 4 — the ROS2 deployment node

Mirror the Week-28 deployment pattern, with the receding-horizon action queue in the middle (Lecture 2 §3.3). The node:

1. Loads the checkpoint (`torch.jit.load`) and the (un)normalization stats.
2. Maintains an **observation history** of length $T_o$ from `/joint_states` (and images if your task is visuomotor).
3. Runs a **`RecedingHorizonController`**: when the action queue drains to $T_a$, DDIM-denoise a fresh chunk, keep the first $T_a$ actions, pop one per control tick.
4. Publishes commands at a fixed control rate (e.g. 30 Hz), with the Week-5 QoS (`RELIABLE`/`KEEP_LAST(1)` for commands, `BEST_EFFORT` for sensor state) and the un-normalization applied.

**The latency budget you must compute and document:**

- Control rate (e.g. 30 Hz → 33 ms/tick). Pops are ~free.
- Re-plan period = $T_a$ ticks. The DDIM denoise (your step count) must finish inside that window with margin.
- If it doesn't: reduce DDIM steps (the latency knob) or shorten $T_p$ — and **measure** the new inference time, don't guess. Report the measured per-chunk inference time and confirm it fits.

**The #1 deployment bug is an observation mismatch** — the node assembling the obs in a different order/scale than training. Export the obs spec with the checkpoint and assert on it. The #2 bug is forgetting to un-normalize the action, so the arm barely moves.

---

## Deliverable 5 — the eval report

`EVAL_REPORT.md`, one page:

1. **Task + data** — the task, the demo count, the *mode split* (proof the data is multimodal).
2. **Policy config** — $T_p$, $T_a$, $T_o$, DDIM steps, backbone, training budget; one sentence of reasoning each.
3. **Head-to-head table** — the three policies on the fixed protocol.
4. **The multimodality scatter** — the figure, captioned with success rates.
5. **Deployment** — measured per-chunk inference time, the latency budget arithmetic, confirmation the node drives the arm.
6. **Honest limits** — what failed, what you'd try next.

---

## Rules

- **You may** use LeRobot, the `diffusion_policy` reference, or your scaled Exercise-3 model. Use a real implementation; the marks are in data/eval/deployment.
- **You must** reuse your Week-27 demos and your Week-27 BC and BC+DAgger baselines for the head-to-head. A comparison against freshly-trained, differently-tuned baselines isn't a controlled comparison.
- **You must** fix the eval protocol before training and state that you did.
- **You must** deploy with the receding-horizon action queue and correct QoS, and report the *measured* latency.
- **You must not** claim a success gap without the eval table and the multimodality scatter to back it.
- Python 3.12, PyTorch ≥ 2.3, ROS2 Jazzy.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-29-diffusion-policy-<yourhandle>`.
- [ ] A reproducible training command another learner can run.
- [ ] A head-to-head success-rate table (Diffusion Policy vs BC vs BC+DAgger) on a fixed protocol with N ≥ 50.
- [ ] The multimodality scatter showing ≥ 2 modes for Diffusion Policy vs BC's collapsed mean.
- [ ] `diffusion_policy_node.py` runs the receding-horizon action queue, drives the arm in Gz Sim, uses correct QoS, and reports measured per-chunk inference time fitting the control budget.
- [ ] `EVAL_REPORT.md` with all six sections.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Multimodality evidence** | 25 | The data is provably multimodal (mode split reported); the scatter shows ≥ 2 modes; the BC mean sits in the invalid valley. This is the thesis, demonstrated. |
| **Head-to-head eval** | 25 | Fixed protocol stated up front; same demos and baselines as Week 27; honest table; gap (if any) interpreted correctly. |
| **Deployment** | 25 | Receding-horizon action queue; correct QoS; (un)normalization right; *measured* latency fits the control budget; obs spec asserted. |
| **Training & config** | 15 | Sensible $T_p$/$T_a$/$T_o$/DDIM-step choices with reasoning; success climbed on the eval rollout, not just loss fell. |
| **Report & hygiene** | 10 | One-page report; reproducible command; checkpoint stored sensibly; honest limits. |

**90+** is portfolio-grade and ready for the Week 30 ACT comparison and the Week 32 safety wrap. **70–89** trains and deploys but the multimodality evidence or the latency accounting is thin. **Below 70** usually means the success gap was claimed without the controlled comparison, or the policy never made it into a real-time ROS2 loop.

---

## Stretch goals

- **DDIM step sweep.** Plot success rate vs inference latency for 4/8/16/32 steps. Find the knee — the fewest steps that hold success. This is the real deployment decision.
- **Execution-horizon sweep.** Plot success and jerk vs $T_a \in \{1,2,4,8\}$ at fixed $T_p$. Confirm the short-$T_a$-reactive / long-$T_a$-smooth trade from Lecture 2 §3.2.
- **Transformer backbone.** Swap the U-Net for the transformer variant and compare on the same demos; report which wins on your horizon/observation dimensionality.
- **Image observations.** If your task is visuomotor, condition on camera frames with a ResNet+spatial-softmax encoder and confirm the policy still works — the step toward the capstone's real perception.

---

## What "done" looks like (a self-check before you submit)

Run through this before you call the mini-project finished:

- I can re-run training from one documented command and get a policy that hits the success bar.
- My demo set's mode-split is reported, and the *demonstrated* actions at the multimodal state form ≥ 2 clusters (the data is genuinely multimodal).
- The head-to-head table uses the same demos, same protocol, and same baselines as Week 27, and the protocol was fixed before training.
- The multimodality scatter shows Diffusion Policy's modes vs BC's collapsed mean, captioned with the success rates.
- The ROS2 node drives the arm with the receding-horizon queue, correct QoS, and (un)normalization — and I measured the per-chunk inference time and it fits the budget.
- The eval report's six sections are all present, and the "honest limits" section names something real.

If any line is "no," that's your next task. The most common gap is the multimodality evidence — without it, the whole week's thesis is unsupported, so prioritize it.

## Suggested timeline (the 12 hours)

| Block | Hours | What you do |
|---|---:|---|
| Thursday | 2h | Wrap the Week-27 demos into the training format; verify the mode-split; launch the first training run |
| Friday | 3h | Read the dashboard; tune $T_p$/$T_a$/DDIM steps; run the head-to-head eval; make the multimodality scatter |
| Saturday | 3h | Build and test the ROS2 deployment node with the receding-horizon queue; measure latency |
| Spread across | 4h | Write the eval report; the stretch sweeps if time allows; push the repo |

Front-load the data check (Thursday): if the demos aren't multimodal, *nothing else this week demonstrates the thesis*, and you want to discover that on Thursday, not Saturday night.

## Common pitfalls (read before you start, save yourself the afternoon)

These are the failures we see every cohort, in rough order of frequency:

1. **Forgot to un-normalize the action.** You trained on actions scaled to ~$[-1,1]$ and the sampled chunk comes out at that scale; you publish it raw and the arm barely twitches. Keep the (un)normalization stats with the checkpoint and apply them at deploy. (The §7 decision tree from Lecture 2 leads here first for a reason.)
2. **Observation layout mismatch.** The node assembles the obs vector in a different order or scale than training. Silent — the policy runs and outputs plausible chunks that do the wrong thing. Export the obs spec with the checkpoint and `assert` it at startup.
3. **Unimodal data, then surprise the scatter is one blob.** If your demos all solve the task the same way, the policy *correctly* learns one mode — there's nothing multimodal to show. Verify the demo mode-split *before* you train; deliberately demonstrate both ways.
4. **DDIM step count too low for quality, or too high for the loop.** Too few steps and the sampled chunk is sloppy (success drops); too many and inference blows the re-plan budget. Sweep it (the stretch goal) and pick the knee.
5. **Re-encoding the observation every denoising step.** The obs doesn't change during the denoise; encode it once per chunk and reuse the embedding across the DDIM steps, or you waste compute you can't afford in the loop.
6. **Claiming a success gap you can't back.** If you tuned the eval after seeing results, the comparison is contaminated. Fix the protocol first, run all three policies through it unchanged, report what you measured.

Each of these is in the lectures; this list is just the "what actually bites people" digest. If your policy misbehaves, walk it top to bottom before you start changing the architecture.

## How this connects to the rest of C24

- **Week 30 (ACT)** trains an Action Chunking Transformer on *these* demos and compares against *this* Diffusion Policy at a fixed latency budget — your eval harness is the shared measuring stick.
- **Week 32 (Phase 4 midterm)** wraps your best policy (this one or ACT) in a runtime safety filter with a classical fallback.
- **Week 39 (edge ML)** profiles the integrated graph including this policy and asks you to cut its latency — the DDIM step count you tuned here is the first lever.

When you've finished, push the repo and take the [quiz](../05-quiz.md).

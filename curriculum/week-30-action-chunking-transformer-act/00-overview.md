# Week 30 — Action Chunking Transformer (ACT)

This is the week imitation learning becomes *deployment-friendly*. By Friday you will have trained an **Action Chunking Transformer (ACT)** on the same demonstrations as Weeks 27 and 29, benchmarked its inference latency against Diffusion Policy on the same hardware, and produced the one-page comparison table that a senior engineer actually uses to decide which policy to ship.

We assume you finished **Week 29 (Diffusion Policy)** and have: a demonstration set, a trained Diffusion Policy with an eval harness reporting success rate, and a ROS2 deployment node with a receding-horizon controller. ACT reuses *all* of it — the same demos, the same eval harness, the same deployment skeleton. The intellectual move this week is comparative: you already have one action-chunking policy (Diffusion Policy); now you build a *different* one (ACT) and learn to choose between them on the axis that matters in production — **success rate at a fixed latency budget**.

The one sentence to carry in: **ACT predicts a chunk of actions in a single forward pass through a transformer, trained as a conditional VAE, and smooths execution with temporal ensembling — making it the most deployment-friendly imitation architecture today.** Where Diffusion Policy needs an iterative denoising loop (a latency knob you tune), ACT needs *one* forward pass. That single-shot inference is its headline advantage, and temporal ensembling is the trick that buys it smooth execution without a receding-horizon re-plan cadence.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** ACT's three load-bearing ideas — **action chunking** (predict $k$ future actions per inference), the **CVAE** training formulation (a latent variable that absorbs the multimodality/style of demonstrations), and **temporal ensembling** (overlapping chunks averaged with an exponential weighting) — and why each exists.
- **Derive** the conditional-VAE objective: the reconstruction term, the KL term against the latent prior, the role of the $\beta$ weight, and why the encoder is used *only at training time* and discarded at inference.
- **Build** the ACT architecture: the transformer encoder that tokenizes observations (image patches via a CNN backbone + proprioception + the latent), the transformer decoder that emits an action chunk, and the CVAE "style" encoder that produces the latent $z$ from the demonstrated action sequence.
- **Implement** temporal ensembling: maintain overlapping predicted chunks, weight each timestep's competing predictions with $w_i = \exp(-m\cdot i)$, and emit the weighted average — and explain why this smooths execution better than receding-horizon chunk-switching.
- **Profile** inference latency rigorously on the deployment target (Jetson Orin or your dev GPU): single-pass ACT vs multi-step Diffusion Policy, with the methodology to make the comparison fair.
- **Choose** between ACT and Diffusion Policy for a given task and latency budget, and defend the choice with measured numbers, not vibes.
- **Train** ACT via the **LeRobot** library on the Week-27/29 demos and deploy it in a `rclpy` node, reusing the Week-29 deployment skeleton.
- **Produce** a one-page, portfolio-grade comparison table of ACT vs Diffusion Policy: success rate, inference latency, training cost, smoothness, and the deployment recommendation.

## Prerequisites

This week assumes you have completed **C24 weeks 1–29**, or have equivalent fluency. Specifically:

- **Week 29**: the demo set, a trained Diffusion Policy, the eval harness, and the ROS2 deployment node with a receding-horizon controller. This week's comparison and deployment reuse every one of those.
- **Transformers**: you can read multi-head attention, an encoder–decoder transformer, and positional encodings. (C5 / applied-ML background.) We re-explain how ACT *uses* a transformer, not how attention works.
- **VAEs**: helpful but not assumed — we derive the CVAE objective from scratch, including the reparameterization trick (which you also met in Week 28's SAC actor).
- **ROS2 Jazzy** on Ubuntu 24.04 with a manipulation sim you can drive and reset for eval rollouts.
- **A GPU** for training (ACT is a modestly-sized transformer — an 8 GB card or the ~USD 25/month cloud budget is plenty). For the latency benchmark, a **Jetson Orin** is ideal (the syllabus's deployment target); if you don't have one, benchmark on your dev GPU and CPU and document the substitution.

You do **not** need prior ACT experience. We start from "you already have one action-chunking policy" and build the second one. If your only exposure to ACT is the ALOHA bimanual-manipulation videos, this is the week you build and ship it.

## Topics covered

- **The ACT formulation** (Zhao et al. 2023, "Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware" / ALOHA): action chunking as the answer to compounding errors in imitation, and why predicting $k$ actions per inference reduces the effective task horizon by a factor of $k$.
- **The CVAE training objective**: ACT is trained as a *conditional variational autoencoder*. The encoder (a transformer that sees the observation + the *demonstrated* action sequence) produces a latent $z$ capturing the "style" of that demonstration; the decoder reconstructs the action chunk from observation + $z$. The loss is reconstruction (L1 on actions) + $\beta\cdot$KL$(q(z)\,\|\,\mathcal{N}(0,I))$.
- **Inference**: at deployment the encoder is *discarded*; the latent is set to its prior mean ($z = 0$), and the decoder produces the chunk in **one forward pass**. No latent sampling, no iteration — this is the single-pass property.
- **Temporal ensembling**: because inference is cheap (one pass), ACT can predict a *fresh overlapping chunk every timestep*; at each timestep multiple chunks (predicted at different past times) propose an action; ACT averages them with weights $w_i = \exp(-m\cdot i)$ (older predictions down-weighted by $m$). This produces smooth, non-jerky execution without committing to a fixed execution horizon.
- **The transformer architecture**: a ResNet image backbone producing feature tokens, proprioceptive state as a token, the CVAE latent as a token, sinusoidal/learned positional encodings, a transformer encoder over the observation tokens, and a transformer decoder with fixed position queries emitting the $k$-step action chunk.
- **Latency profiling**: how to benchmark inference fairly (warm-up runs, GPU sync, batch-of-one, the right precision), single-pass ACT vs $N$-step DDIM Diffusion Policy, and reading the result against a control-loop budget on a Jetson Orin.
- **The deployment-latency-aware policy choice**: a structured comparison — success rate, inference latency, smoothness (jerk), training cost, sample efficiency — and the decision framework for "which policy ships."
- **LeRobot for ACT**: training ACT with the maintained `act` policy on the same standardized dataset as the Diffusion Policy, so the comparison is genuinely apples-to-apples.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Chunking vs compounding error; the CVAE objective           |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Implement the CVAE loss; reparameterization; β ablation     |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | The ACT transformer; observation tokenization; the decoder  |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Temporal ensembling; train ACT on the demos                 |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Latency profiling; ACT vs Diffusion Policy; deploy node     |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                      |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, comparison-table polish                       |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                             | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The ACT/ALOHA paper, the CVAE references, LeRobot, the ACT reference repo, and the talks worth your time |
| [lecture-notes/01-act-architecture-and-the-cvae.md](./02-lecture-notes/01-act-architecture-and-the-cvae.md) | Action chunking vs compounding error, the CVAE objective, and the ACT transformer architecture |
| [lecture-notes/02-temporal-ensembling-latency-and-the-policy-choice.md](./02-lecture-notes/02-temporal-ensembling-latency-and-the-policy-choice.md) | Temporal ensembling, fair latency profiling, and the ACT-vs-Diffusion-Policy decision framework |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-cvae-and-ensembling-math.md](./03-exercises/exercise-01-cvae-and-ensembling-math.md) | Derive the CVAE objective and the KL term; compute the temporal-ensembling weights by hand |
| [exercises/exercise-02-act-cvae.py](./03-exercises/exercise-02-act-cvae.py) | A runnable miniature ACT (CVAE + transformer chunk decoder) on a multimodal toy; you fill the KL term, the reparameterization, and the inference latent |
| [exercises/exercise-03-temporal-ensembling.py](./03-exercises/exercise-03-temporal-ensembling.py) | A runnable temporal-ensembling controller; you fill the exponential weighting and the per-timestep weighted average; measure the jerk reduction |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-latency-shootout.md](./04-challenges/challenge-01-latency-shootout.md) | Profile ACT vs Diffusion Policy fairly and pick the winner at a fixed latency budget |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the comparison-table writeup with a rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Train ACT on the Week-27/29 demos, benchmark latency, compare to Diffusion Policy, deploy in ROS2 |

## The "one pass, smooth output" promise

C24 uses a recurring marker for every ACT exercise: the moment you see ACT produce a full action chunk in a *single* forward pass, and temporal ensembling turn a sequence of overlapping chunks into smooth motor commands.

```
$ python3 benchmark_inference.py --policy act --device cuda
# ACT (single forward pass):     inference  6.2 ms   chunk of 16 actions
# Diffusion Policy (16 DDIM):     inference 31.8 ms   chunk of 16 actions
#
$ python3 measure_jerk.py --controller temporal_ensemble
# raw chunk-switching jerk : 0.214
# temporal-ensembled jerk  : 0.061   (3.5x smoother)
# success_rate: act 0.88   diffusion 0.91   (at a 33 ms / 30 Hz budget: ACT has margin)
```

If ACT's inference is *not* faster than Diffusion Policy's, your benchmark is unfair (cold cache, no GPU sync, wrong batch size) — fix the methodology, because the single-pass advantage is the entire reason ACT exists. The point of Week 30 is to make that benchmark rigorous and the policy choice defensible.

## Stretch goals

If you finish the regular work early and want to push further:

- Ablate the **CVAE $\beta$** (KL weight): too high and the latent collapses to the prior (ACT becomes a deterministic chunk predictor that, like BC, can mode-average); too low and training is unstable. Find the band that keeps the latent useful, and connect it to the multimodality lesson from Week 29.
- Ablate **chunk size $k$** (1, 8, 16, 32) and plot success vs $k$. Larger $k$ shrinks the effective horizon (fewer compounding-error opportunities) but makes each chunk harder to predict coherently. Find your task's sweet spot.
- Sweep the temporal-ensembling **decay $m$** and plot jerk vs reactivity. $m\to\infty$ recovers "use only the newest chunk" (reactive, jerkier); $m\to 0$ averages all chunks equally (smooth, laggy). Find the knee.
- Benchmark ACT and Diffusion Policy on a **Jetson Orin** at FP16 and INT8 and reason about which policy benefits more from quantization — the setup for Week 39's edge-ML optimization.

## Up next

Week 31 leaves task-specific policies behind for **generalist policies — Octo and OpenVLA** — cross-embodiment models you *prompt* with language and *fine-tune* on your demos. The action-chunking and deployment instincts you built across Weeks 29–30 carry directly: OpenVLA emits action chunks too, and the deployment-latency reasoning you just sharpened is exactly what decides whether a multi-billion-parameter VLA fits your robot's control loop. Push your ACT-vs-Diffusion comparison table and your ROS2 policy node before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

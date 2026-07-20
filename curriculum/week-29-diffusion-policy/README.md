# Week 29 — Diffusion Policy

This is the week imitation learning stops averaging. By Friday you will have trained a **Diffusion Policy** on the demonstrations you collected in Week 27, watched it beat plain behavior cloning *and* BC+DAgger on the same eval set, and — most importantly — visualized the moment that explains *why*: at a state where there are two equally-good things to do, BC outputs the average of the two (which is a third, wrong, thing), and Diffusion Policy outputs *both modes* and commits to one.

We assume you finished **Week 27 (Behavior Cloning and DAgger)** and have a demonstration set — call it ~50 teleoperated trajectories of a manipulation task, augmentable to ~200 — plus a trained BC baseline and an eval harness that reports success rate. We also assume **Week 28 (PPO/SAC)** gave you PyTorch-training fluency, a feel for reading a loss/eval dashboard, and the ROS2-policy-node deployment pattern. Diffusion Policy reuses every bit of that.

The one sentence to carry in: **Diffusion Policy ate the multimodal-action problem by predicting a *short sequence* of future actions as the output of an iterative denoising process, conditioned on recent observations.** A Gaussian-MLP policy (BC, and even an RL actor) models $p(a\mid s)$ as a single blob and collapses on multimodal data. A diffusion model represents *arbitrary* distributions — multiple modes, sharp boundaries, correlations across an action chunk — because it learns to turn noise into actions a little at a time. That representational power is the whole game, and this week is where you wield it.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** the multimodal-action problem precisely — why minimizing mean-squared error against multimodal demonstrations forces a unimodal policy to predict the (often invalid) mean — and recognize it in a real demo set.
- **Derive** the DDPM forward (noising) and reverse (denoising) processes, state the closed-form $q(x_t\mid x_0)$, and write the simplified $\epsilon$-prediction training loss.
- **Distinguish** DDPM sampling (stochastic, many steps) from DDIM sampling (deterministic, few steps) and explain the latency trade that makes DDIM the deployment default.
- **Implement** the Diffusion Policy training loop in PyTorch: sample a chunk of ground-truth actions, add noise at a random timestep, condition on the observation embedding, and regress the noise.
- **Build** the two canonical Diffusion Policy backbones — the 1D temporal **U-Net** with FiLM observation conditioning, and the **transformer** variant — and say when each is preferred.
- **Apply** the architecture's three load-bearing ideas: **action-chunk prediction** (predict $T_p$ future actions at once), **receding-horizon execution** (execute only the first $T_a < T_p$, then re-plan), and **observation conditioning** over a short history.
- **Deploy** a trained Diffusion Policy as a `rclpy` node with a real-time receding-horizon controller, and reason about the inference-latency budget that denoising imposes.
- **Visualize and evaluate** a learned action distribution at a known multimodal state, and compare success rate against BC and BC+DAgger on a fixed eval protocol.

## Prerequisites

This week assumes you have completed **C24 weeks 1–28**, or have equivalent fluency. Specifically:

- **Week 27**: a demonstration set and a BC baseline with a working eval harness reporting success rate. Diffusion Policy is trained on those *same* demos and graded against that *same* harness.
- **Week 28**: PyTorch training-loop fluency, comfort reading a training/eval dashboard, and the ROS2-policy-node deployment pattern (you'll reuse `reach_policy_node.py`'s structure).
- **C5 / applied-ML background**: you can read a `nn.Module`, you've seen a U-Net or a transformer, and you understand a Gaussian. We re-derive the diffusion math, but the deep-learning vocabulary should be familiar.
- **ROS2 Jazzy** on Ubuntu 24.04 with a manipulation sim (Gz Sim or Isaac Sim) you can drive and reset for eval rollouts.
- **A GPU** for training (the temporal U-Net is modest — an 8 GB card or the ~USD 25/month cloud budget is plenty). Inference can be CPU but is comfortably real-time on a small GPU.

You do **not** need prior diffusion-model experience. We start from the multimodal-action problem and build DDPM, then DDIM, then the policy. If your only exposure to diffusion is "the thing that makes images," this is the week it becomes a robot controller.

## Topics covered

- **The multimodal-action problem**: why MSE-regressed BC predicts the *mean* of multimodal demonstrations (and why the mean is often an invalid action — e.g. the average of "go left around the obstacle" and "go right" is "drive into it"); the explicit-vs-implicit-policy framing from Chi et al.
- **DDPM** (Ho et al. 2020): the forward process $q(x_t\mid x_{t-1}) = \mathcal{N}(\sqrt{1-\beta_t}\,x_{t-1}, \beta_t I)$, the closed-form $q(x_t\mid x_0)$ via $\bar\alpha_t$, the reverse process parameterized as $\epsilon$-prediction, and the simplified MSE training loss $\|\epsilon - \epsilon_\theta(x_t, t)\|^2$.
- **DDIM** (Song et al. 2021): the deterministic, non-Markovian sampler that produces the same marginals in **far fewer steps** (e.g. 10–16 vs 100), and why that's the difference between a deployable policy and a slideshow.
- **Conditioning**: how the policy denoises actions *conditioned* on an observation embedding — FiLM (feature-wise linear modulation) for the U-Net, cross-attention or token concatenation for the transformer; the optional **classifier-free-guidance**-style conditioning strength.
- **Diffusion Policy architecture** (Chi et al. 2023): the CNN/U-Net 1D temporal backbone over the action-chunk dimension, the transformer alternative, the observation encoder (ResNet for images, MLP for low-dim state), and the position-encoding of the diffusion timestep.
- **Action chunking and receding horizon**: predict a chunk of $T_p$ future actions; execute the first $T_a$; re-observe and re-plan. The interplay between chunk length, execution horizon, smoothness, and reactivity — and why short execution horizons stay reactive while long prediction horizons stay coherent.
- **Deployment and latency**: running the denoising loop inside a real-time control node, the receding-horizon buffer, why DDIM's step count is a latency knob, and the action-queue pattern that decouples inference rate from control rate.
- **Evaluation**: a fixed eval protocol (same seeds, same success criterion) comparing Diffusion Policy vs BC vs BC+DAgger; visualizing the predicted action distribution at a deliberately multimodal state to *see* the multimodality the other methods lose.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                    | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The multimodal problem; DDPM forward/reverse; the loss   |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | DDIM sampling; implement a 1D toy diffusion model        |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Diffusion Policy: chunking, receding horizon, U-Net+FiLM |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Conditioning, observation encoders; train on the demos   |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Eval vs BC/DAgger; visualize multimodality; deploy node  |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                   |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, eval-report polish                         |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                          | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The Diffusion Policy + DDPM/DDIM papers, the LeRobot library, the diffusers docs, and the talks worth your time |
| [lecture-notes/01-the-multimodal-problem-and-ddpm.md](./lecture-notes/01-the-multimodal-problem-and-ddpm.md) | The multimodal-action problem, DDPM forward/reverse processes, the ε-prediction loss, and DDIM sampling |
| [lecture-notes/02-diffusion-policy-chunking-and-deployment.md](./lecture-notes/02-diffusion-policy-chunking-and-deployment.md) | The Diffusion Policy architecture, action chunking, receding-horizon execution, conditioning, and ROS2 deployment |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-ddpm-ddim-math.md](./exercises/exercise-01-ddpm-ddim-math.md) | Derive the closed-form $q(x_t\mid x_0)$, the ε-loss, and the DDIM update; predict step-count effects |
| [exercises/exercise-02-toy-diffusion.py](./exercises/exercise-02-toy-diffusion.py) | A runnable 1D diffusion model that learns a bimodal distribution; you fill the noising and the ε-loss |
| [exercises/exercise-03-diffusion-policy.py](./exercises/exercise-03-diffusion-policy.py) | A runnable Diffusion Policy on a 2D multimodal toy task with chunking + receding horizon; you fill the conditioned loss and the DDIM action sampler |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-multimodal-showdown.md](./challenges/challenge-01-multimodal-showdown.md) | Build a deliberately multimodal task, show BC collapses to the mean, show Diffusion Policy doesn't |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the eval-report writeup with a rubric |
| [mini-project/README.md](./mini-project/README.md) | Train a Diffusion Policy on the Week-27 demos, beat BC and BC+DAgger, deploy it receding-horizon in ROS2 |

## The "the distribution had two modes" promise

C24 uses a recurring marker for every Diffusion Policy exercise: the moment you visualize the predicted action distribution at a known multimodal state and *see two modes* where BC shows one (wrong) blob.

```
$ python3 visualize_action_dist.py --state multimodal_junction --policy diffusion
# Scatter of 512 sampled action chunks at the junction state:
#   diffusion : two tight clusters  ->  "go left"  and  "go right"   (multimodal — correct)
#   bc        : one blob centered between them  ->  "drive into the obstacle" (the mean — wrong)
# eval/success_rate:  diffusion 0.91   bc 0.58   bc+dagger 0.74
```

If your Diffusion Policy's sampled actions at a multimodal state form a *single* blob, something is wrong — your conditioning leaked the answer, your chunk is too short to express the choice, or you trained on unimodal data. The point of Week 29 is to make those two clusters ordinary, and to make a *collapsed* distribution legible instead of mysterious.

## Stretch goals

If you finish the regular work early and want to push further:

- Sweep the **DDIM step count** (4, 8, 16, 32) and plot success rate vs inference latency. Find the knee — the fewest steps that hold success. This is the deployment decision you'll make for real in the mini-project.
- Sweep the **execution horizon** $T_a$ (1, 2, 4, 8) at a fixed prediction horizon $T_p$ and plot success vs jerk. Short $T_a$ is reactive but jerky at the seams; long $T_a$ is smooth but stale. Find your task's sweet spot.
- Swap the **U-Net backbone for the transformer** variant and compare on the same demos. The transformer often wins on long horizons and high-dimensional observations; confirm on yours.
- Read the **EDM / consistency-model** line of work and reason about one-step or few-step diffusion samplers — the frontier of cutting Diffusion Policy's latency, and a live research area you'll meet again when you profile the integrated graph in Week 39.

## Up next

Week 30 takes the action-chunking idea you build here and pairs it with a *different* generative backbone: the **Action Chunking Transformer (ACT)**, a CVAE that predicts action chunks in a single forward pass — no iterative denoising — and uses **temporal ensembling** to smooth execution. You'll train ACT on the *same* demos and compare it head to head with this Diffusion Policy at a fixed latency budget. Push your eval report and your ROS2 policy node before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

# Week 34 — Resources

Every resource here is **free**. The domain-randomization papers are on arXiv; the Isaac Lab and Gz Sim docs are public; the randomization tooling is open-source. No paywalled material is linked.

Where a version matters: this week assumes **Isaac Lab** (2026-current) for the parallel-randomization path and **Gz Sim Harmonic + Gymnasium** for the Path B episode-level path. The randomization *concepts* are simulator-independent; only the API names move.

## The foundational papers — read these first

- **Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World** — Tobin et al., 2017. *The* domain-randomization paper; the textbook texture/lighting/camera recipe. Read it Monday:
  <https://arxiv.org/abs/1703.06907>
- **CAD2RL: Real Single-Image Flight without a Single Real Image** — Sadeghi & Levine, 2016. The "train on randomized renderings, fly in reality" result that predates and motivates Tobin:
  <https://arxiv.org/abs/1611.04201>
- **Learning Dexterous In-Hand Manipulation** (OpenAI Dactyl) — 2018. Dynamics randomization + the original Automatic Domain Randomization (ADR) for a real robot hand:
  <https://arxiv.org/abs/1808.00177>
- **Solving Rubik's Cube with a Robot Hand** — OpenAI, 2019. The fuller ADR writeup (widening ranges as a curriculum):
  <https://arxiv.org/abs/1910.07113>

## Going deeper (skim for context)

- **Sim-to-Real Transfer in Deep Reinforcement Learning for Robotics: a Survey** — Zhao et al., 2020. A map of the techniques (DR, domain adaptation, system ID) and where each fits:
  <https://arxiv.org/abs/2009.13303>
- **Active Domain Randomization** — Mehta et al., 2019. Learning *which* randomizations matter instead of uniform sampling — the next idea after ADR:
  <https://arxiv.org/abs/1904.04762>
- **Closing the Sim-to-Real Loop (RCAN / sim-to-real via canonical images)** — for the "adapt the image" alternative to "randomize the image":
  <https://arxiv.org/abs/1812.07252>

## Isaac Lab — the parallel-randomization path

- **Isaac Lab documentation home** — environments, tasks, training:
  <https://isaac-sim.github.io/IsaacLab/>
- **Isaac Lab events / randomization API** — how to apply randomization terms (mass, friction, material, lighting) per-environment, the event-manager pattern:
  <https://isaac-sim.github.io/IsaacLab/main/source/features/index.html>
- **Isaac Lab domain-randomization tutorial** — the worked example of randomizing a task's physics and visuals across parallel envs:
  <https://isaac-sim.github.io/IsaacLab/main/source/how-to/index.html>

## Gz Sim — the Path B episode-level path

- **Gz Sim world/SDF + plugins** — how to set physics parameters (friction, mass) you'll randomize per-episode:
  <https://gazebosim.org/docs>
- **Gymnasium** — the RL environment API your Path B training loop uses to reset a randomized world each episode:
  <https://gymnasium.farama.org/>
- **`ros_gz` bridge** — getting randomized sim sensors onto ROS2 for eval (Week 33 carries over):
  <https://github.com/gazebosim/ros_gz>

## RL training context (carried from Week 28)

- **Stable-Baselines3 / RL training** — if your Week 28 PPO used SB3, the same trainer consumes the randomized env:
  <https://stable-baselines3.readthedocs.io/>
- **rsl_rl / Isaac Lab PPO** — the GPU-parallel PPO that Isaac Lab tasks train with:
  <https://github.com/leggedrobotics/rsl_rl>
- **Week 28 lecture notes (parallel-sim RL)** — your own prior work; the reward curve and the parallel-env setup you augment this week.

## Talks worth your time (free, no signup)

- **OpenAI "Solving Rubik's Cube" / Dactyl talks** — the clearest exposition of ADR-as-curriculum from the people who shipped it to hardware:
  search the OpenAI YouTube channel.
- **NVIDIA GTC sim-to-real / Isaac Lab sessions** — the parallel-randomization-at-scale pitch and worked examples:
  <https://developer.nvidia.com/isaac/sim>
- **CoRL/RSS sim-to-real workshop talks (2023–2025)** — the honest "what randomization can and cannot close" discussions:
  search the CoRL / RSS proceedings.

## Tools you'll use this week

- **Isaac Lab event manager** (Path A) — apply randomization terms per parallel env on reset.
- **Gymnasium `reset(seed=...)`** (Path B) — re-roll a randomized world each episode.
- **TensorBoard** — watch the reward curve under randomization (it's noisier and slower than nominal — that's expected).
- **The Exercise-3 gap-metric script** — compute the gap-closure number from two held-out evals.
- **`numpy.random.default_rng`** — the seeded sampler behind your randomization config (reproducibility matters).

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Sim-to-real gap** | The performance drop when a sim-trained policy meets reality (or a held-out world). |
| **Domain randomization (DR)** | Training over a distribution of randomized sims so reality looks like one more sample. |
| **Visual DR** | Randomizing textures, lighting, colors, camera pose — for vision policies. |
| **Dynamics DR** | Randomizing mass, friction, damping, motor gains, latency — for control policies. |
| **Sensor-noise injection** | Adding noise/bias/dropout to observations so the policy doesn't overfit clean sim sensors. |
| **ADR** | Automatic Domain Randomization — widening ranges as the policy improves (a curriculum). |
| **Over-randomization** | Ranges so wide the policy goes maximally conservative and solves nothing. |
| **Held-out "real-style" world** | An eval world with mismatched textures/lighting/friction the policy never trained on. |
| **Gap-closure metric** | (randomized held-out success) − (nominal held-out success): the evidence DR worked. |
| **System ID** | Measuring real parameters to narrow the sim distribution — the alternative/complement to DR. |
| **CAD2RL** | Sadeghi-Levine: train a flight policy on randomized renderings, deploy on a real drone. |
| **Dactyl** | OpenAI's in-hand manipulation result via dynamics randomization + ADR. |

---

*If a link 404s, please open an issue so we can replace it.*

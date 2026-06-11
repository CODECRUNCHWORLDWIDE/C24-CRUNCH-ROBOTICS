# Week 29 — Resources

Every resource here is **free**. The Diffusion Policy, DDPM, and DDIM papers are on arXiv. LeRobot (Hugging Face) and `diffusion_policy` (Chi et al.) are open source. The `diffusers` library is open source with public docs. No paywalled books are linked.

Pin yourself to **LeRobot** (the Hugging Face robot-learning library — the 2026-current home of maintained Diffusion Policy / ACT / VLA implementations and standardized datasets) and the original **`diffusion_policy`** reference repo. Where a version matters, the current one is noted.

## Required reading (work it into your week)

- **Diffusion Policy: Visuomotor Policy Learning via Action Diffusion** — Chi, Feng, Du, Xu, Cousineau, Burchfiel, Song (2023). The paper this week is built on. Read §3 (the formulation), §4 (chunking + receding horizon), and the U-Net vs transformer ablation:
  <https://arxiv.org/abs/2303.04137>
- **Denoising Diffusion Probabilistic Models** — Ho, Jain, Abbeel (2020). DDPM. The closed-form $q(x_t\mid x_0)$ is Eq. 4; the simplified loss is Eq. 14:
  <https://arxiv.org/abs/2006.11239>
- **Denoising Diffusion Implicit Models** — Song, Meng, Ermon (2021). DDIM — the deterministic few-step sampler that makes Diffusion Policy deployable:
  <https://arxiv.org/abs/2010.02502>
- **The Diffusion Policy project page** — videos, the multimodal-action visualizations, and the code links. Watch the multimodal-pushing video before Lecture 1; it's the whole intuition in 30 seconds:
  <https://diffusion-policy.cs.columbia.edu/>

## The implementations to read (code that gets it right)

- **LeRobot** — Hugging Face's robot-learning library. Its `diffusion` policy is a clean, maintained Diffusion Policy you can train on standardized datasets with one command. This is the 2026 default for "I want to train a real Diffusion Policy without reimplementing it":
  <https://github.com/huggingface/lerobot>
- **`diffusion_policy`** — the original reference implementation from Chi et al. Read `diffusion_policy/policy/diffusion_unet_lowdim_policy.py` and the 1D U-Net in `diffusion_policy/model/diffusion/`:
  <https://github.com/real-stanford/diffusion_policy>
- **`diffusers`** — Hugging Face's diffusion library. Its `DDPMScheduler` and `DDIMScheduler` are exactly the schedulers LeRobot's Diffusion Policy uses; read them to see the $\beta$-schedule and the sampling loop in production form:
  <https://huggingface.co/docs/diffusers/index>

## Diffusion-model background (the math, built up gently)

- **Lilian Weng — "What are Diffusion Models?"** — the single best from-scratch derivation of DDPM and DDIM online, with every step of the closed-form $q(x_t\mid x_0)$ written out. Read it alongside Lecture 1:
  <https://lilianweng.github.io/posts/2021-07-11-diffusion-models/>
- **"The Annotated Diffusion Model"** (Hugging Face) — DDPM implemented line by line in PyTorch with the math beside the code; the U-Net and the training loop you'll mirror:
  <https://huggingface.co/blog/annotated-diffusion>
- **Yang Song — "Generative Modeling by Estimating Gradients of the Data Distribution"** — the score-based view that unifies diffusion; optional but it makes DDIM click:
  <https://yang-song.net/blog/2021/score/>

## Imitation-learning context (where Diffusion Policy sits)

- **Implicit Behavioral Cloning** — Florence et al. (2022). The energy-based-model predecessor that framed the multimodal problem Diffusion Policy then solved more cleanly:
  <https://arxiv.org/abs/2109.00137>
- **Behavior Transformers (BeT)** — Shafiullah et al. (2022). Another multimodal-imitation approach (action discretization + offset); useful contrast for the challenge:
  <https://arxiv.org/abs/2206.11251>

## Talks worth your time (free, no signup)

- **Cheng Chi / Shuran Song — Diffusion Policy talks (RSS / CoRL)** — the authors walking through the multimodal motivation and the chunking/receding-horizon design. Search the RSS and CoRL archives:
  <https://roboticsconference.org/>
- **Hugging Face LeRobot tutorials / livestreams** — training a Diffusion Policy end to end on a real dataset; the deployment patterns map directly to the mini-project:
  <https://www.youtube.com/@HuggingFace>

## Tools you'll use this week

- **`torch`** — PyTorch ≥ 2.3, CUDA build for training.
- **`diffusers`** — `pip install diffusers`; the `DDPMScheduler` / `DDIMScheduler` you'll use rather than hand-rolling the noise schedule in the mini-project.
- **`lerobot`** — `pip install lerobot` for the maintained Diffusion Policy + standardized datasets.
- **`matplotlib`** — for the action-distribution scatter plots that make multimodality visible.
- **`einops`** — `pip install einops`; the `rearrange` calls that keep the chunk/time/feature dimensions legible in the U-Net.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Multimodal action** | A state where several different actions are all good; the *mean* of them is usually bad. |
| **DDPM** | Denoising Diffusion Probabilistic Model — learns to reverse a gradual noising process. |
| **Forward process** $q(x_t\mid x_0)$ | Gradually add Gaussian noise to data over $t$ steps; closed-form via $\bar\alpha_t$. |
| **Reverse process** | Learn to denoise: predict the noise $\epsilon$ that was added, step by step. |
| **ε-prediction** | The network predicts the noise, not the clean sample; the simplified DDPM loss. |
| **$\beta_t$ schedule** | How much noise is added per forward step; $\alpha_t = 1-\beta_t$, $\bar\alpha_t = \prod\alpha$. |
| **DDIM** | A deterministic, non-Markovian sampler giving the same marginals in far fewer steps. |
| **Denoising steps** | How many reverse iterations to run; the latency knob (DDPM ~100, DDIM ~10–16). |
| **Action chunk** | A short sequence of $T_p$ future actions predicted together. |
| **Prediction horizon** $T_p$ | How many future actions the policy predicts in one chunk. |
| **Execution horizon** $T_a$ | How many of those it actually executes before re-planning ($T_a < T_p$). |
| **Receding horizon** | Predict $T_p$, execute $T_a$, re-observe, repeat — the MPC-style loop. |
| **FiLM** | Feature-wise Linear Modulation — condition a network by scaling/shifting features. |
| **Observation conditioning** | Denoising the action chunk *given* an embedding of recent observations. |
| **Conditional vs joint** | Diffusion Policy conditions actions on obs (vs jointly diffusing obs+actions). |

---

*If a link 404s, please open an issue so we can replace it.*

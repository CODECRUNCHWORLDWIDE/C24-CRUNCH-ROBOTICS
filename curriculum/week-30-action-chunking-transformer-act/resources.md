# Week 30 — Resources

Every resource here is **free**. The ACT/ALOHA paper is on arXiv. LeRobot (Hugging Face) and the original ACT repo are open source. The CVAE and transformer references are open. No paywalled books are linked.

Pin yourself to **LeRobot** (the maintained 2026 home of ACT, Diffusion Policy, and VLA implementations with standardized datasets) and the original **ACT** reference repo. Where a version matters, the current one is noted.

## Required reading (work it into your week)

- **Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware** — Zhao, Kumar, Levine, Finn (2023). The ACT paper (the ALOHA system). Read §IV (the ACT method): action chunking, the CVAE formulation, and temporal ensembling:
  <https://arxiv.org/abs/2304.13705>
- **The ALOHA / ACT project page** — videos and the architecture diagram. Watch a bimanual-manipulation clip before Lecture 1 to see what chunk-level imitation buys:
  <https://tonyzhaozh.github.io/aloha/>
- **Auto-Encoding Variational Bayes** — Kingma, Welling (2013). The VAE paper; the reparameterization trick and the KL term you implement are §2.3–2.4:
  <https://arxiv.org/abs/1312.6114>
- **Attention Is All You Need** — Vaswani et al. (2017). The encoder–decoder transformer ACT is built on; skim if you need a refresher on multi-head attention and the decoder's query mechanism:
  <https://arxiv.org/abs/1706.03762>

## The implementations to read (code that gets it right)

- **LeRobot — the `act` policy** — Hugging Face's maintained ACT. Clean, trainable on standardized datasets with one command; the 2026 default for "train a real ACT without reimplementing it." Read `lerobot/common/policies/act/`:
  <https://github.com/huggingface/lerobot>
- **ACT (original reference repo)** — Tony Zhao's implementation. Read `policy.py` (the CVAE wrapper), `detr/models/detr_vae.py` (the transformer + CVAE), and the temporal-ensembling logic in the eval loop:
  <https://github.com/tonyzhaozh/act>
- **`diffusers`** (for the comparison) — you'll re-use your Week-29 Diffusion Policy here; its DDIM scheduler is the latency baseline ACT is measured against:
  <https://huggingface.co/docs/diffusers/index>

## CVAE / VAE background (the math, built up gently)

- **Lilian Weng — "From Autoencoder to Beta-VAE"** — the clearest online derivation of the VAE objective, the reparameterization trick, and what $\beta$ does to the latent. Read alongside Lecture 1:
  <https://lilianweng.github.io/posts/2018-08-12-vae/>
- **"Tutorial on Variational Autoencoders"** — Doersch (2016). A longer, careful treatment of the ELBO and the conditional variant; optional but it makes the KL term click:
  <https://arxiv.org/abs/1606.05908>

## Imitation-learning context (where ACT sits)

- **Diffusion Policy** — Chi et al. (2023). Your Week-29 comparison point; ACT is the single-pass alternative to its iterative denoising:
  <https://arxiv.org/abs/2303.04137>
- **Behavior Transformers (BeT)** — Shafiullah et al. (2022). Another transformer-based chunk/sequence imitation method; useful contrast:
  <https://arxiv.org/abs/2206.11251>
- **A Survey on Imitation Learning for Robotics** (search for a current survey) — to place BC, DAgger, Diffusion Policy, and ACT on one map before the Week-32 midterm.

## Talks worth your time (free, no signup)

- **Tony Zhao / ALOHA talks (RSS / CoRL / robot-learning seminars)** — the authors walking through chunking, the CVAE, and temporal ensembling. Search the RSS and CoRL archives:
  <https://roboticsconference.org/>
- **Hugging Face LeRobot tutorials** — training ACT end to end on a real dataset and deploying it; maps directly to the mini-project:
  <https://www.youtube.com/@HuggingFace>

## Tools you'll use this week

- **`torch`** — PyTorch ≥ 2.3, CUDA build for training.
- **`lerobot`** — `pip install lerobot` for the maintained ACT + standardized datasets.
- **`torchvision`** — the ResNet image backbone ACT tokenizes observations with.
- **`numpy` / `matplotlib`** — for the temporal-ensembling weight plots and the jerk measurements.
- **A profiler** — `torch.cuda.Event` (or `time.perf_counter` with `torch.cuda.synchronize()`) for *honest* latency numbers; `nsys` if you're on a Jetson.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **ACT** | Action Chunking Transformer — single-pass chunk-predicting imitation policy. |
| **Action chunk** | The $k$ future actions ACT predicts per inference. |
| **Compounding error** | Imitation errors accumulate over a long horizon; chunking shrinks the effective horizon by $k$. |
| **CVAE** | Conditional Variational Autoencoder — ACT's training framework. |
| **Latent $z$** | A variable capturing demonstration "style"; produced by the encoder at train time, set to 0 at inference. |
| **Encoder (CVAE)** | A transformer that sees obs + the *demonstrated* action sequence and outputs $z$'s mean/var. Train-only. |
| **Decoder (ACT)** | The transformer that emits the action chunk from obs (+ $z$). The deployed network. |
| **Reparameterization** | Sampling $z=\mu+\sigma\epsilon$ so gradients flow through the latent sample. |
| **KL term** | Penalty pulling the latent posterior $q(z)$ toward the prior $\mathcal{N}(0,I)$. |
| **$\beta$ (KL weight)** | Trades reconstruction vs latent regularization; too high → latent collapse. |
| **Temporal ensembling** | Average overlapping chunks per timestep with weights $w_i=\exp(-m\cdot i)$ for smooth output. |
| **Decay $m$** | Temporal-ensembling weight decay; large $m$ → trust newest chunk; small $m$ → average all. |
| **Single-pass inference** | ACT produces a chunk in one forward pass (vs Diffusion Policy's $N$ denoising steps). |
| **Latency budget** | The per-tick time a control loop allows for inference (e.g. 33 ms at 30 Hz). |

---

*If a link 404s, please open an issue so we can replace it.*

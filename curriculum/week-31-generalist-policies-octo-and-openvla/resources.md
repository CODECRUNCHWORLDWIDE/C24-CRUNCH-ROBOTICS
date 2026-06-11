# Week 31 — Resources

Every resource here is **free** and **open**. The Octo and OpenVLA papers are on arXiv; the checkpoints are on HuggingFace under permissive licenses; Open X-Embodiment is public; LeRobot is Apache-2.0. No paywalled material is linked. Where a library version matters, the 2026-current API is noted — pin your environment to what the lecture notes assume (`torch >= 2.2`, `transformers >= 4.40`, `lerobot` latest).

When a checkpoint or repo URL moves (model hubs reorganize), search HuggingFace for the model name; the architectures and the math in the lecture notes are stable even when a URL is not.

## The two papers — read these first

- **OpenVLA: An Open-Source Vision-Language-Action Model** — Kim, Pertsch, Karamcheti et al., 2024. The model you fine-tune this week. Read §3 (architecture) and §4 (training) closely:
  <https://arxiv.org/abs/2406.09246>
- **Octo: An Open-Source Generalist Robot Policy** — Octo Model Team, 2024. The transformer-with-diffusion-head generalist. Read §3 (model) and the fine-tuning section:
  <https://arxiv.org/abs/2405.12213>

## The cross-embodiment lineage (skim for context)

- **Open X-Embodiment: Robotic Learning Datasets and RT-X Models** — Open X-Embodiment Collaboration, 2023. The dataset and the positive-transfer result that makes generalists possible:
  <https://arxiv.org/abs/2310.08864>
- **RT-1: Robotics Transformer for Real-World Control at Scale** — Brohan et al., 2022. Where action-tokenization-for-robots started:
  <https://arxiv.org/abs/2212.06817>
- **RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control** — Brohan et al., 2023. The "VLM-as-policy" idea OpenVLA open-sourced:
  <https://arxiv.org/abs/2307.15818>
- **OpenVLA-OFT: Optimized Fine-Tuning** — the follow-up that attacks inference latency (parallel decoding, continuous-action head). Read after the main paper for the Week 37/39 connection:
  <https://arxiv.org/abs/2502.19645>

## Code and checkpoints (you will have these open all week)

- **OpenVLA repository** — training, fine-tuning (LoRA), and inference scripts:
  <https://github.com/openvla/openvla>
- **`openvla/openvla-7b` checkpoint** on HuggingFace — the base model you fine-tune:
  <https://huggingface.co/openvla/openvla-7b>
- **Octo repository** — JAX/Flax model, pretrained checkpoints, fine-tuning notebook:
  <https://github.com/octo-models/octo>
- **Prismatic VLMs** — the VLM backbone OpenVLA is built on (DINOv2 + SigLIP fusion + Llama-2):
  <https://github.com/TRI-ML/prismatic-vlms>

## LeRobot — the dataset format and training library

- **`lerobot` repository** — HuggingFace's robot-learning library; the `LeRobotDataset` format you convert your Week 29 demos into:
  <https://github.com/huggingface/lerobot>
- **LeRobot dataset format docs** — episodes, frames, the `meta/` stats, the observation/action key convention:
  <https://huggingface.co/docs/lerobot/index>
- **The Open X-Embodiment → LeRobot conversion scripts** — how OXE's RLDS/TFDS data is converted; useful when you want to mix in OXE data:
  <https://github.com/huggingface/lerobot/tree/main/lerobot/common/datasets>

## The visual encoders and the LLM backbone (reference)

- **DINOv2** — the self-supervised visual features (the "where are the objects, geometrically" half of OpenVLA's encoder):
  <https://arxiv.org/abs/2304.07193>
- **SigLIP** — the sigmoid-loss CLIP variant (the "what is this, semantically" half):
  <https://arxiv.org/abs/2303.15343>
- **LoRA: Low-Rank Adaptation of Large Language Models** — Hu et al., 2021. The parameter-efficient fine-tuning method you use Thursday:
  <https://arxiv.org/abs/2106.09685>
- **PEFT library** — HuggingFace's LoRA/adapter implementation (`get_peft_model`, `LoraConfig`):
  <https://huggingface.co/docs/peft/index>

## How-to and tutorials

- **OpenVLA fine-tuning guide** (in-repo `README`/`finetune.md`): the LoRA recipe, the dataset stats requirement, the launch command:
  <https://github.com/openvla/openvla#fine-tuning-openvla-via-lora>
- **HuggingFace `transformers` — `AutoModelForVision2Seq`** — how the OpenVLA checkpoint loads and `predict_action` works:
  <https://huggingface.co/docs/transformers/index>
- **bitsandbytes 4-bit quantization** — for the stretch goal of running the 7B model in ~half the VRAM:
  <https://huggingface.co/docs/bitsandbytes/index>

## Talks worth your time (free, no signup)

- **CoRL / RSS 2024 OpenVLA & Octo sessions** — the authors present the models; the Q&A on "why fine-tuning is mandatory" is the most useful 10 minutes:
  search the **CoRL 2024** and **RSS 2024** proceedings/YouTube channels.
- **Physical Intelligence and the generalist-policy landscape** — context on where π0-style flow-matching VLAs sit relative to OpenVLA/Octo in 2026:
  <https://www.physicalintelligence.company/blog>
- **HuggingFace LeRobot community** — walkthroughs of dataset conversion and fine-tuning on consumer hardware:
  <https://www.youtube.com/@HuggingFace>

## Tools you'll use this week

- **`torch` + CUDA** — the fine-tuning and inference runtime. Confirm `torch.cuda.is_available()` before you rent a GPU for an hour and find it's CPU-only.
- **`transformers` `AutoModelForVision2Seq` / `AutoProcessor`** — loading OpenVLA and running `predict_action`.
- **`lerobot`** — `LeRobotDataset` for the dataset, and its training utilities.
- **`peft`** — `LoraConfig`, `get_peft_model` for the LoRA fine-tune.
- **`wandb`** (optional, free tier) — to watch the fine-tuning loss and the action-token accuracy curve live.
- **`nvidia-smi` / `nvtop`** — watch VRAM during fine-tuning; OOM is the #1 first-run failure.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **VLA** | Vision-Language-Action model — a policy that maps an image + a text instruction to robot actions. |
| **OXE** | Open X-Embodiment — the ~1M+-trajectory, 22-embodiment open dataset generalists pretrain on. |
| **Octo** | A transformer generalist policy with a diffusion action head; small (27M/93M); JAX. |
| **OpenVLA** | A 7B VLM-as-policy: Llama-2-7B + DINOv2+SigLIP encoder, predicts discrete action tokens. |
| **Prismatic** | The VLM family OpenVLA's backbone comes from (fused dual visual encoder + LLM). |
| **DINOv2 / SigLIP** | The two visual encoders OpenVLA fuses: geometric features + semantic features. |
| **Action tokenization** | Discretizing each continuous action dim into 256 bins mapped onto rare LLM vocab tokens. |
| **Un-normalization** | Mapping a normalized action back to real units using the dataset's per-dim stats. The #1 silent bug. |
| **LoRA** | Low-Rank Adaptation — fine-tune by learning small rank-`r` weight deltas, freezing the base. |
| **LeRobot** | HuggingFace's robot-learning library and its `LeRobotDataset` format. |
| **EE-delta action** | The lowest-common-denominator action space: 6-DOF end-effector pose delta + 1 gripper command. |
| **Zero-shot** | Running the pretrained model on your task with **no** fine-tuning. Usually 30–50% at best. |
| **Positive transfer** | The RT-X finding: training on many embodiments improves performance on each, vs. single-robot. |
| **Readout token** | Octo's learned token whose output embedding feeds the action head (like a [CLS] for actions). |

---

*If a link 404s, please open an issue so we can replace it.*

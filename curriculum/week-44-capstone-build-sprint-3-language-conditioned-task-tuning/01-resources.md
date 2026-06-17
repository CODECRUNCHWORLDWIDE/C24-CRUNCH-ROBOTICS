# Week 44 — Resources

Everything linked here is free and public. The papers are on arXiv; the code is on GitHub; the docs are open. No paywalled material. Where a link is version-specific, we pin to the 2026-current line (OpenVLA, LeRobot `v2`, ROS2 Jazzy).

## Required reading (work it into your week)

- **OpenVLA: An Open-Source Vision-Language-Action Model** — the base policy class this week tunes, including the LoRA fine-tuning recipe in the appendix:
  <https://arxiv.org/abs/2406.09246> · code: <https://github.com/openvla/openvla>
- **OpenVLA fine-tuning guide** — the canonical LoRA recipe (rank, target modules, learning rate, dataset format) we adapt for fifty demos:
  <https://github.com/openvla/openvla#fine-tuning-openvla>
- **LeRobot — Hugging Face's robot-learning library** — the `v2` dataset format we record demos into and the trainer scaffolding:
  <https://github.com/huggingface/lerobot> · dataset format: <https://huggingface.co/docs/lerobot/en/lerobot-dataset-v2>
- **RT-2 / RT-X and the "scaling robot learning" line** — read for the *evaluation methodology*, especially the per-instruction success-rate tables and held-out generalization splits:
  <https://robotics-transformer2.github.io/> · Open X-Embodiment: <https://robotics-transformer-x.github.io/>
- **LoRA: Low-Rank Adaptation of Large Language Models** — the adaptation method, applied here to the VLA backbone:
  <https://arxiv.org/abs/2106.09685>

## Evaluation methodology (the heart of this week)

- **"Reproducibility in robot learning" / the eval-rigor discussion in CoRL** — why fixed scene resets, seeded RNG, and N-trial reporting are not optional. Search the CoRL 2024/2025 proceedings for the eval-methodology track:
  <https://www.corl.org/>
- **SIMPLER — Simulated Manipulation Policy Evaluation for Real Robots** — a reproducible eval harness for manipulation policies; read for how they freeze scenes and score binary success:
  <https://simpler-env.github.io/> · code: <https://github.com/simpler-env/SimplerEnv>
- **CALVIN — a benchmark for language-conditioned long-horizon manipulation** — read for the *instruction stratification* idea: tasks grouped by what skill/grounding they exercise:
  <http://calvin.cs.uni-freiburg.de/> · code: <https://github.com/mees/calvin>
- **The Wilson score interval** — how to put an honest confidence interval on a `k/N` success rate (do not use the naive normal approximation at small N):
  <https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval>

## OpenVLA / VLA ecosystem

- **OpenVLA model card and checkpoints** (Hugging Face):
  <https://huggingface.co/openvla/openvla-7b>
- **Octo — an alternative open generalist policy** — useful if your capstone base is Octo rather than OpenVLA; same eval discipline applies:
  <https://octo-models.github.io/> · code: <https://github.com/octo-models/octo>
- **`prismatic-vlms`** — the VLM backbone OpenVLA builds on; read if you need to touch the tokenizer or action-detokenizer:
  <https://github.com/TRI-ML/prismatic-vlms>
- **PEFT (Hugging Face)** — the LoRA implementation we use; the `LoraConfig` docs:
  <https://huggingface.co/docs/peft/en/index>

## ROS2 Jazzy (the integration layer)

- **`rclpy` action client/server** — the eval-runner issues instructions to the policy through an action; this is the API reference:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html>
- **ROS2 Jazzy documentation root**:
  <https://docs.ros.org/en/jazzy/index.html>
- **`ros2 bag` (rosbag2)** — record raw teleop sessions before you convert them to LeRobot episodes; the recovery path if your converter has a bug:
  <https://github.com/ros2/rosbag2>
- **`BehaviorTree.CPP` v4** — your task BT wraps the policy action; the eval-runner triggers the same BT the deployed robot uses:
  <https://www.behaviortree.dev/>

## Data collection and teleop

- **LeRobot teleoperation + recording walkthrough** — the reference flow for recording demonstration episodes:
  <https://huggingface.co/docs/lerobot/en/getting_started_real_world_robot>
- **Open X-Embodiment dataset format (RLDS)** — the TFDS-based episode schema; read if you prefer RLDS over LeRobot parquet:
  <https://github.com/google-research/rlds>

## Tooling you'll use this week

- **PyTorch 2.x** (CUDA build matching your driver) — the training and inference runtime:
  <https://pytorch.org/get-started/locally/>
- **Hugging Face `accelerate`** — the multi-precision / device-placement wrapper LeRobot and OpenVLA training use:
  <https://huggingface.co/docs/accelerate/en/index>
- **`wandb` or TensorBoard** — track train/eval curves; the mini-project asks for a screenshot of the eval-success curve, not just the loss:
  <https://docs.wandb.ai/> · <https://www.tensorflow.org/tensorboard>
- **Foxglove** — replay a failed eval trial to diagnose the failure mode; you wired this in week 43:
  <https://foxglove.dev/>

## Free talks and videos (no signup)

- **OpenVLA project talk / CoRL presentation** — the authors walk through the fine-tuning recipe and eval splits:
  search "OpenVLA CoRL talk" on YouTube (the official robotics-transformer channel reposts).
- **"How to evaluate a robot policy honestly"** — the eval-rigor talks from the RSS / CoRL workshop tracks; search the RSS 2025 workshop "Reproducibility in Robot Learning":
  <https://roboticsconference.org/>

## Open-source projects to read this week

You learn more from one hour reading a real eval harness than from three hours of slides. Pick one and scroll:

- **`openvla/openvla`** — read `vla-scripts/finetune.py` end to end; it is the template for exercise 3:
  <https://github.com/openvla/openvla/blob/main/vla-scripts/finetune.py>
- **`huggingface/lerobot`** — read `lerobot/scripts/eval.py` for how they structure a policy eval loop:
  <https://github.com/huggingface/lerobot/tree/main/lerobot/scripts>
- **`simpler-env/SimplerEnv`** — read how they reset scenes deterministically and score success; the pattern transfers directly to your `rclpy` runner:
  <https://github.com/simpler-env/SimplerEnv>

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **VLA** | Vision-Language-Action model — takes images + an instruction, outputs robot actions. OpenVLA is the open one. |
| **Eval suite** | The frozen set of instructions + scene resets + rubric you score the policy against. The contract. |
| **Frozen suite** | The acceptance suite you may not edit after running. Editing it voids your numbers. |
| **Dev slice** | A *separate* set of instructions you may iterate on (checkpoint selection, debugging). Never the frozen suite. |
| **Scene reset** | The procedure that puts the world back to a fixed start state before each trial. Sim: a service. Real: a taped template + photo. |
| **k/N** | k successes out of N trials. We use N=5 per instruction. The honest unit of a success rate. |
| **Wilson interval** | The confidence interval for a `k/N` proportion that behaves at small N. Use it, not the naive normal one. |
| **LoRA** | Low-Rank Adaptation — fine-tune a big model by training small adapter matrices, leaving the base frozen. A few hundred MB, not 14 GB. |
| **Adapter** | The LoRA weights. Hot-loaded or merged into the base policy at inference. |
| **Episode** | One demonstration: a sequence of (observation, action) steps plus the instruction and a success flag. |
| **RLDS / LeRobot v2** | The two common on-disk episode formats. We use LeRobot v2 (parquet). |
| **Grounding error** | The policy attended to the wrong object. One of the four failure modes. |
| **Language-binding error** | The policy ignored the instruction and did a generic behavior. The most embarrassing failure mode. |

---

*If a link 404s, please open an issue so we can replace it.*

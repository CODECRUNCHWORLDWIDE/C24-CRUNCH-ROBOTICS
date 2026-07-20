# Week 31 — Generalist Policies: Octo and OpenVLA

Welcome to the week where the policy stops being something you train from scratch on fifty demos and starts being something you *download* — a model pretrained on a million trajectories across a thousand robots, that you then bend to your task with a fraction of the data. By Friday you will be able to take an open-weight **OpenVLA** checkpoint, fine-tune it on the demonstrations you collected in Week 29, and state — with numbers, not vibes — exactly how much zero-shot transfer buys you and where it falls on its face.

You finished Week 30 with an **Action Chunking Transformer** that you trained yourself on a single task, profiled on the Orin, and compared against Diffusion Policy. That was a *specialist*. It does one thing, learned from your data, and it knows nothing about any object, instruction, or embodiment it didn't see. This week is the opposite philosophy: a **generalist** — one network, pretrained on the **Open X-Embodiment** collection (the largest open robot-learning dataset assembled to date, ~1M+ trajectories from 22 embodiments), conditioned on a *natural-language instruction*, that you adapt to your robot with parameter-efficient fine-tuning on a cloud GPU.

The one thing to internalize before you read another line: **a generalist robot policy is not magic and it is not zero-shot.** The marketing says "foundation model for robots." The reality, in 2026, is closer to: *a strong visual-language prior that gets you to maybe 30–50% success on your task out of the box, and to 80–90% after one epoch of fine-tuning on 50–150 of your own demos.* The pretraining bought you data efficiency and language grounding. It did not buy you your gripper, your camera mounting, your lighting, or your objects. Fine-tuning is **mandatory**, not optional. The engineer who ships an OpenVLA-based policy is the engineer who fine-tuned it honestly and measured the gap.

This week is where you learn to do exactly that.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** the cross-embodiment dataset story: what Open X-Embodiment (OXE) is, why pooling 22 robots' data into one model works at all, and what the **RT-X** result actually demonstrated (positive transfer across embodiments).
- **Describe** the Octo architecture — a transformer with a diffusion action head, block-wise attention over tokenized observations + language, and readout tokens — and contrast it with OpenVLA's "VLM-backbone-as-policy" design.
- **Explain** OpenVLA's architecture precisely: a **Prismatic-7B** vision-language backbone (Llama-2-7B + a fused DINOv2 + SigLIP visual encoder), and the **action-tokenization** scheme that discretizes each continuous action dimension into one of 256 bins mapped onto the least-used tokens of the LLM vocabulary.
- **Tokenize** a 7-DOF action vector by hand into the discrete bins OpenVLA predicts, and **de-tokenize** the model's output tokens back into a `(Δx, Δy, Δz, Δroll, Δpitch, Δyaw, grip)` end-effector command — including the un-normalization step that bites everyone.
- **Fine-tune** OpenVLA with **LoRA** (low-rank adaptation) on your Week 29 demonstrations using the **LeRobot** dataset format, on a single cloud GPU, and explain every hyperparameter that matters (rank, learning rate, action-un-normalization stats, batch size, image augmentation).
- **Evaluate** zero-shot vs. fine-tuned success rate on a held-out eval set, and produce an **honest failure analysis** that separates perception failures, grounding failures, and control failures.
- **Decide**, as a senior engineer would, when a generalist VLA is the right tool versus when last week's ACT or Diffusion Policy is the better, cheaper, lower-latency choice.

## Prerequisites

This week assumes you have completed **C24 weeks 1–30**, the entire Manipulation & Learning phase up to here. Specifically:

- You have the **Week 29 demonstrations** — at least 50 (ideally 200, augmented) trajectories of a tabletop manipulation task (e.g., "reach for the red block" / "pick up the cube") collected via teleop in Gz Sim, with synchronized RGB, proprioception, and actions. *Every fine-tuning run this week consumes that dataset.* If it's gone, re-collect it; the VLA work is meaningless without your own task data.
- You can train and evaluate an imitation policy (BC, Diffusion Policy, ACT) and read a success-rate eval the way Weeks 27–30 taught.
- You can fine-tune a transformer and reason about loss curves, learning rate, and overfitting (the C5 prerequisite). We do **not** re-teach gradient descent.
- You have a **cloud GPU** with **≥ 24 GB VRAM** available for the fine-tuning lab (an A100-40GB, an L40S, or a 4090/4090-class card via Lambda/RunPod). OpenVLA-7B fine-tunes with LoRA in ~16–24 GB; full fine-tuning needs far more. The ~USD 25/month cloud-GPU budget from the track README covers this week.
- You have `conda`/`venv`, `torch` ≥ 2.2 with CUDA, `transformers`, and can install `lerobot` and the OpenVLA repo from source.

You do **not** need to have read the Octo or OpenVLA papers yet — Lecture 1 walks you through both. You **do** need your Week 29 data and a GPU you can rent.

## Topics covered

- **The cross-embodiment story:** Open X-Embodiment (OXE), the RT-1 → RT-2 → RT-X lineage, what "positive transfer across embodiments" means and the evidence for it, and the limits (action-space heterogeneity, the proprioception problem, the "everything is a 7-DOF EE-delta" lowest-common-denominator hack).
- **Octo (Octo Model Team, 2024):** a transformer policy with **block-wise causal attention** over tokenized image + language + proprio observations, **readout tokens**, and a **diffusion action head** that predicts action chunks. Pretrained on 800k OXE trajectories; designed to be fine-tuned with new observation/action heads. Octo-Small (~27M) and Octo-Base (~93M).
- **OpenVLA (Kim et al., 2024):** a **7B-parameter** vision-language-action model built on the **Prismatic VLM** (Llama-2-7B language model + a *dual* visual encoder fusing **DINOv2** and **SigLIP** features). The policy *is* the VLM: it ingests an image and an instruction and autoregressively emits **action tokens**.
- **Action tokenization in depth:** how OpenVLA discretizes each of the 7 continuous action dimensions into **256 uniform bins** over the (1st, 99th)-percentile range computed from the training data, and maps those bins onto the **256 least-frequently-used tokens** of the Llama tokenizer — turning continuous control into next-token prediction.
- **The prompt-as-task pattern:** `In: What action should the robot take to {instruction}?\nOut:` — the exact prompt template, why the instruction is the task specification, and how the model grounds language to a grasp.
- **Fine-tuning with LoRA:** parameter-efficient fine-tuning, the rank/alpha/target-modules choices, why you fine-tune rather than zero-shot, the **action un-normalization statistics** (the single most common silent bug), and image augmentation.
- **The LeRobot dataset format:** HuggingFace's `lerobot` library, the `LeRobotDataset` schema (episodes, frames, observation/action keys), converting your Week 29 demos into it, and why this format is becoming the lingua franca of open robot learning in 2026.
- **Honest evaluation:** zero-shot vs. fine-tuned A/B, the eval-set discipline (held-out objects, held-out positions, held-out instructions), and a failure taxonomy that separates *perception* (didn't see the object), *grounding* (saw it, misread the instruction), and *control* (right intent, bad trajectory) failures.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | OXE + RT-X; Octo architecture; the generalist premise  |    2h    |    1h     |     0h     |    0.5h   |   1h     |     0h       |    1h      |     5.5h    |
| Tuesday   | OpenVLA architecture; action tokenization by hand      |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Wednesday | LeRobot format; zero-shot inference; un-normalization  |    1h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | LoRA fine-tuning; launch the cloud run; eval protocol  |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Zero-shot vs fine-tuned A/B; failure taxonomy          |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work (the VLA eval harness)          |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, failure-analysis writeup polish          |    0h    |    0h     |     0h     |    1h     |   0h     |     1.5h     |    0h      |     2.5h    |
| **Total** |                                                        | **6h**   | **6.5h**  | **4h**     | **4h**    | **5h**   | **12.5h**    | **2.5h**   | **36.5h**   |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The Octo/OpenVLA papers, OXE, LeRobot docs, the checkpoints, and the talks worth your time |
| [lecture-notes/01-cross-embodiment-octo-and-openvla.md](./lecture-notes/01-cross-embodiment-octo-and-openvla.md) | OXE + RT-X, the Octo architecture, the OpenVLA architecture, and action tokenization in full |
| [lecture-notes/02-finetuning-lerobot-and-honest-evaluation.md](./lecture-notes/02-finetuning-lerobot-and-honest-evaluation.md) | LoRA fine-tuning, the LeRobot dataset format, un-normalization, and the honest-evaluation discipline |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-octo-vs-openvla.md](./exercises/exercise-01-octo-vs-openvla.md) | Read both architectures and answer a precise comparison worksheet; run a zero-shot OpenVLA forward pass |
| [exercises/exercise-02-action-tokenization.py](./exercises/exercise-02-action-tokenization.py) | Implement OpenVLA's action tokenizer/de-tokenizer end to end and round-trip a real action vector |
| [exercises/exercise-03-lerobot-conversion.py](./exercises/exercise-03-lerobot-conversion.py) | Convert your Week 29 demos into a `LeRobotDataset` and validate the schema |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-zero-shot-vs-finetuned.md](./challenges/challenge-01-zero-shot-vs-finetuned.md) | Run the zero-shot vs. fine-tuned A/B and produce a publishable failure analysis |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the headline VLA failure-analysis writeup |
| [mini-project/README.md](./mini-project/README.md) | The `crunchbot_vla_eval` harness: a reproducible zero-shot-vs-fine-tuned evaluator with a failure taxonomy |

## The "honest number" promise

C24 uses a recurring marker for every learned-policy week: the **honest number**. Not "it works," not "it's pretty good" — a success rate, on a named eval set, with a denominator you can defend.

```
=== VLA EVAL: pick_red_cube (held-out positions) ===
checkpoint: openvla-7b  (zero-shot)        success: 11/40  (27.5%)
checkpoint: openvla-7b  (LoRA, 1 epoch)    success: 33/40  (82.5%)
gap closed: +55.0 pts
failure breakdown (zero-shot): perception 4 | grounding 18 | control 7
```

If you cannot produce a table like that for your task, you have not finished the week. A VLA you didn't evaluate against a held-out set is a demo, not a result — and demos don't survive the Phase 4 midterm in Week 32, where you defend exactly this policy.

## Stretch goals

If you finish the regular work early and want to push further:

- Fine-tune **Octo-Small** on the same Week 29 data using Octo's native fine-tuning recipe (new action head + frozen-or-not transformer) and compare its data efficiency and inference latency against OpenVLA-7B. Octo is ~270× smaller; the latency story is dramatic.
- Run OpenVLA's **action-token entropy** analysis: at a known multimodal state (two valid grasps), inspect the per-dimension token logits and confirm the model is *uncertain* in exactly the dimension where the task is ambiguous. This is the VLA analogue of Week 29's multimodal-action visualization.
- Quantize the OpenVLA backbone to **4-bit (bitsandbytes NF4)** for inference and measure the latency and success-rate delta. This previews Week 39's edge-ML optimization and answers "can a 7B VLA run on an Orin at all?" (Short answer in 2026: barely, quantized, slowly — which is why the field is racing toward smaller VLAs.)
- Read the **OpenVLA-OFT** (optimized fine-tuning) follow-up and note which of its tricks — parallel decoding, continuous actions, an L1 regression head instead of token prediction — attack the latency problem you'll hit in Week 37.

## Up next

Week 32 is the **Phase 4 integration and second midterm**. You take your best policy from Weeks 27–31 — quite possibly the fine-tuned OpenVLA you build this week — and wrap it in a runtime safety filter with a classical fallback, then defend the whole learned-policy stack to a panel. The eval discipline and the honest failure analysis you build this week are exactly what the midterm rubric grades. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

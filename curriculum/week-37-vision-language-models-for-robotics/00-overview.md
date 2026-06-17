# Week 37 — Vision-Language Models for Robotics

This is the week your robot learns to take instructions in English. Up to now every behavior has been wired by hand — a behavior tree you authored, a policy you trained on one task, a goal pose you typed. This week you put a **natural-language steering wheel** on the robot: a text instruction goes in, and a vision-language model grounds it against what the camera sees and emits actions. By Friday you will understand the VLA-as-policy pattern (RT-2, OpenVLA, π0-class models), wire your Week-31 fine-tuned OpenVLA into the mobile manipulator so "bring the red cup" becomes a sequence of grasp poses and base motions, evaluate it on a small instruction suite, and — most importantly — **document where it hallucinates**, because that honesty is the difference between a demo and a deployment.

We assume Phase 4 is behind you: you have a learned policy (Diffusion Policy / ACT from weeks 29–30), a fine-tuned **OpenVLA** checkpoint from week 31, a MoveIt2 arm (week 23), Nav2 on the base (weeks 17–24), and a behavior tree that wires perception to motion (week 19). This week does not re-teach those; it puts a language model *on top* of them. If your week-31 OpenVLA fine-tune is broken or missing, recover it first — every exercise this week feeds a VLA.

The one thing to internalize before you read another line: **a VLM gives your robot a natural-language steering wheel, but steering is not driving.** A vision-language-action model is genuinely able to map "pick up the tool" to a plausible grasp — that is real and it is new and it is 2026's biggest shift in robot autonomy. But it is *also* a model that will confidently grasp the wrong object, ground "red" to an orange under warm light, or emit an action that drives the gripper through the table, and it will do all of that with no error and no uncertainty flag unless you build one. The engineering this week is half "wire the VLA in" and half "build the leash" — the safety scaffold, the confidence gate, the classical fallback (the week-32 pattern) that catches the VLA when it lies.

This is the week language meets wheels and grippers — and the week you learn to never trust it blindly.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** what a vision-language-action (VLA) model is and how it differs from a VLM: the architecture lineage from VLMs (CLIP, PaLI-X, vision-language pretraining) to VLAs (RT-2, RT-X, OpenVLA, π0/OpenPI), and the "discretize actions into language tokens" trick that lets a VLM emit motor commands.
- **Articulate** the cross-embodiment story (Open-X Embodiment, the RT-X dataset) and why a model trained across many robots transfers — and where the transfer breaks.
- **Implement** the VLA-as-policy integration: text instruction + image observation in, action chunk out, behavior tree dispatches the chunk through MoveIt2 / Nav2 — with the action de-tokenization and frame conventions correct.
- **Ground** open-vocabulary language to the scene: how "the red cup" becomes a specific object via the VLA's internal grounding, and how an *explicit* open-vocab detector (OWL-ViT / Grounding-DINO + SAM) gives you a verifiable, debuggable grounding you can gate on.
- **Evaluate** a language-conditioned policy on an instruction suite: per-instruction success rate, the eval protocol, and honest reporting (the syllabus's three instructions: "bring the red cup," "move the blue block to the left," "pick up the tool").
- **Diagnose** VLA failure modes: grounding errors (wrong object), spatial errors (wrong relation — "left" vs "right"), affordance errors (ungraspable pose), distribution shift (lighting/viewpoint the fine-tune never saw), and hallucinated confidence.
- **Build** the safety leash: a confidence/verification gate that rejects a VLA action when the open-vocab grounding disagrees with the instruction, and a classical fallback (week-32 pattern) that takes over after repeated rejections.
- **Reason** about edge-compute reality: VLA inference latency on a Jetson Orin, why a 7B-parameter VLA at 5–10 Hz is a design constraint, and the action-chunking / async-inference tricks that make it usable.

## Prerequisites

This week assumes you have completed **C24 weeks 1–36**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**; a GPU (local ≥ 8 GB VRAM, or cloud) — a 7B VLA does not run on a CPU at a usable rate.
- The **Week 31 fine-tuned OpenVLA** checkpoint (or an open-weight OpenVLA/π0 you can load). You can load it and run a forward pass.
- **MoveIt2** (week 23) and **Nav2** (weeks 17–24) on the mobile manipulator, and the **behavior tree** integration pattern (week 19).
- The **learned-policy + classical-fallback** pattern from **week 32** — the safety wrapper you'll extend with a grounding gate this week.
- Comfort with PyTorch, Hugging Face `transformers`, and loading a large checkpoint. We do not re-teach how to run a transformer forward pass.

You do **not** need to have trained a VLA from scratch (nobody does that on this track — you fine-tune an open-weight one). This week is about *integrating and gating* a VLA, not pretraining it.

## Topics covered

- **From VLM to VLA.** Vision-language pretraining (CLIP-style contrastive, captioning); the VLM backbone (PaLI-X, Prismatic/Llava-style); the leap to VLA — RT-2's "actions as text tokens," RT-X / Open-X Embodiment cross-embodiment training, OpenVLA (7B open-weight), and the 2026 generation (π0 / OpenPI flow-matching action experts).
- **The action representation.** How a VLM that outputs text comes to output a 7-DOF end-effector delta: action discretization into tokens (RT-2/OpenVLA) vs. continuous action heads / flow matching (π0); de-tokenization back to a robot action; the action-chunk + receding-horizon execution pattern (the Diffusion Policy / ACT lesson, weeks 29–30).
- **Grounding language to the scene.** Implicit grounding (the VLA does it internally, opaque) vs. explicit grounding (OWL-ViT / Grounding-DINO open-vocab detection + SAM segmentation) that you can inspect and gate on; the open-vocabulary detection pipeline; why an explicit grounding is your debugging and safety hook.
- **The VLA-as-policy integration.** Instruction + image → VLA → action chunk → behavior tree → MoveIt2 (arm) / Nav2 (base); frame conventions (camera frame vs. end-effector frame vs. base frame); the dispatch loop and re-querying the VLA as the scene changes.
- **Evaluation.** The instruction suite; per-instruction success rate; what counts as success; the eval protocol (fixed scene resets, N trials per instruction); honest reporting including partial successes and the failure taxonomy.
- **Failure modes, named.** Grounding (wrong object), spatial relation (wrong "left/right/behind"), affordance (a pose that's correct semantically but unreachable / collides), distribution shift (the fine-tune's blind spots), and the dangerous one: **confident hallucination** with no uncertainty signal.
- **The safety leash.** A verification gate: run an *independent* open-vocab grounding of the instruction, and reject the VLA action if its target disagrees; velocity/workspace clamps (week 32); the classical fallback after K rejections; logging every rejection for the failure analysis.
- **Edge-compute reality.** VLA inference latency on Orin (a 7B model is hundreds of ms per query); action chunking to amortize; async inference (predict the next chunk while executing the current); quantization's accuracy cost; why "the VLA runs at 5 Hz" is a hard design constraint, not a number to optimize away naively.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                              | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | VLM → VLA lineage; action-as-tokens; cross-embodiment |  2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | The VLA-as-policy integration; frames; action chunks |  1.5h |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Grounding: implicit vs explicit; open-vocab detection |  2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Evaluation; the failure taxonomy; the safety leash |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Edge latency; async inference; the instruction-suite run |  0h   |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                             |    0h    |    0h     |     0h     |    0h     |   0h     |     2h       |    0h      |     2h      |
| Sunday    | Quiz, review, failure-analysis polish              |    0h    |    0h     |     0h     |    1h     |   0h     |     2h       |    0h      |     3h      |
| **Total** |                                                    | **6.5h** | **6.5h**  | **4h**     | **4h**    | **5h**   | **9h**       | **2.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The VLA papers (RT-2, RT-X, OpenVLA, π0), the open-vocab detectors, the eval harnesses, and the talks worth your time |
| [lecture-notes/01-vlms-to-vlas-architecture-and-grounding.md](./02-lecture-notes/01-vlms-to-vlas-architecture-and-grounding.md) | From VLM to VLA, action-as-tokens, cross-embodiment, and how language grounds to the scene |
| [lecture-notes/02-vla-as-policy-evaluation-and-the-safety-leash.md](./02-lecture-notes/02-vla-as-policy-evaluation-and-the-safety-leash.md) | The integration loop, evaluation, the failure taxonomy, the safety leash, and edge latency |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-prompt-and-ground.md](./03-exercises/exercise-01-prompt-and-ground.md) | Run a VLM/VLA on images + instructions; observe implicit grounding and its failures by hand |
| [exercises/exercise-02-open-vocab-grounding.py](./03-exercises/exercise-02-open-vocab-grounding.py) | An open-vocab grounding node: instruction → detected target box + mask, with a confidence you can gate on |
| [exercises/exercise-03-vla-policy-loop.py](./03-exercises/exercise-03-vla-policy-loop.py) | The VLA-as-policy loop with a verification gate that rejects when grounding disagrees and falls back |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-hallucination-hunt.md](./04-challenges/challenge-01-hallucination-hunt.md) | Engineer adversarial scenes that make the VLA confidently wrong; build the gate that catches each |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the language-conditioned failure analysis |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunch_vla` language-conditioned manipulation node with grounding gate, fallback, and an instruction-suite eval |

## The "grounded, gated, and honest" promise

C24 uses a recurring marker for every exercise that ends in a language instruction actually executing safely. For this week it is the gated dispatch:

```
[vla] instruction: "bring the red cup"
[vla] action chunk proposed: grasp at (0.42, -0.11, 0.18), gripper close
[gate] open-vocab grounding of "red cup" -> box conf 0.88 at (0.41, -0.10); IoU with VLA target 0.79  -> ACCEPT
[bt] dispatching grasp to MoveIt2...
```

versus the rejection that saves you:

```
[vla] instruction: "bring the red cup"
[vla] action chunk proposed: grasp at (0.61, 0.30, 0.05)
[gate] open-vocab grounding of "red cup" -> best box at (0.41, -0.10); IoU with VLA target 0.04  -> REJECT (VLA targeting wrong object)
[gate] rejection 1/3
```

If the VLA grasps the wrong object and your stack executes it without a word, your robot is a confident liability. The point of Week 37 is to make the *accept* line ordinary and the *reject* line **loud, logged, and acted on** — and to make the third rejection hand control to the classical fallback.

## Stretch goals

If you finish the regular work early and want to push further:

- Swap your VLA backbone: run the same instruction suite on **OpenVLA** and on a **π0 / OpenPI** open checkpoint, and compare success rate and latency. The architectures differ (discrete action tokens vs. flow-matching action expert); note where each wins.
- Build a **spatial-relation probe**: a battery of "move X to the {left, right, in front of} Y" instructions and measure the VLA's accuracy on *each relation*. Spatial grounding is a known VLA weak spot — quantify yours.
- Replace your open-vocab detector (OWL-ViT) with **Grounding-DINO + SAM2** and compare grounding precision/recall on your scenes. A better gate catches more hallucinations.
- Measure the **latency Gantt** of one instruction end-to-end: image capture → VLA forward → de-tokenize → grounding gate → MoveIt2 plan → execute. This is the Week 39 latency lesson, rehearsed.

## Up next

Week 38 takes the VLA-as-policy you wired here and asks the next question: **what if the language model doesn't emit actions directly, but emits a *plan* — a sequence of skills?** Grounded planners and tool use (the C23 bridge). The instruction suite and the failure taxonomy you build this week become the evaluation substrate for a planner that calls your skills as tools. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

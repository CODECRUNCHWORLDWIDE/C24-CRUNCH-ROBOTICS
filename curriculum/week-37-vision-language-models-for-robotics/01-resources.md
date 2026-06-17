# Week 37 — Resources

Every resource here is **free**. The VLA papers are on arXiv; OpenVLA, Octo, and π0/OpenPI are open-weight with public code; the open-vocab detectors (OWL-ViT, Grounding-DINO, SAM) are open. No paywalled books are linked.

Model weights are large and the field moves fast. Pin to the checkpoint you actually downloaded and note its commit hash in your writeups — a VLA result is only reproducible against a specific checkpoint.

## Required reading (work it into your week)

- **OpenVLA: An Open-Source Vision-Language-Action Model** — the 7B open-weight VLA you fine-tuned in week 31; read the architecture and the action-tokenization sections:
  <https://arxiv.org/abs/2406.09246> · project + code: <https://openvla.github.io/>
- **RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control** — the "actions as text tokens" idea that started the VLA generation:
  <https://robotics-transformer2.github.io/>
- **Open X-Embodiment: Robotic Learning Datasets and RT-X Models** — the cross-embodiment dataset and why training across robots transfers:
  <https://robotics-transformer-x.github.io/>
- **π0 (pi-zero): A Vision-Language-Action Flow Model for General Robot Control (Physical Intelligence)** — the 2026-current flow-matching action-expert design; the open OpenPI release:
  <https://www.physicalintelligence.company/blog/pi0> · code: <https://github.com/Physical-Intelligence/openpi>
- **OWL-ViT: Simple Open-Vocabulary Object Detection with Vision Transformers** — the open-vocab detector you'll use for an explicit, gateable grounding:
  <https://arxiv.org/abs/2205.06230> · HF model card: <https://huggingface.co/docs/transformers/en/model_doc/owlvit>

## The papers (skim, don't memorize)

- **Octo: An Open-Source Generalist Robot Policy** — the transformer generalist trained on Open-X; the alternative to OpenVLA in your stretch comparison:
  <https://octo-models.github.io/>
- **CLIP: Learning Transferable Visual Models From Natural Language Supervision** — the vision-language pretraining that underlies everything; read §1–3:
  <https://arxiv.org/abs/2103.00020>
- **PaLI-X: On Scaling up a Multilingual Vision and Language Model** — a representative VLM backbone of the kind VLAs are built on:
  <https://arxiv.org/abs/2305.18565>
- **Grounding-DINO: Open-Set Object Detection** — the stronger open-vocab detector for the stretch grounding swap:
  <https://arxiv.org/abs/2303.05499>
- **Segment Anything (SAM) / SAM 2** — segmentation to turn an open-vocab box into a precise mask for grasp targeting:
  <https://segment-anything.com/> · SAM 2: <https://ai.meta.com/sam2/>

## Code and checkpoints (the ones you'll have open all week)

- **OpenVLA code + checkpoints** (load, fine-tune, infer):
  <https://github.com/openvla/openvla>
- **OpenPI (π0) code + checkpoints**:
  <https://github.com/Physical-Intelligence/openpi>
- **Hugging Face `transformers` — OWL-ViT** (zero-shot open-vocab detection in ~20 lines):
  <https://huggingface.co/docs/transformers/en/model_doc/owlvit>
- **`vision_msgs`** — the ROS2 message types for detections (`Detection2DArray`, `Detection3DArray`) your grounding node should publish:
  <https://github.com/ros-perception/vision_msgs>
- **LIBERO / SIMPLER eval suites** — standard language-conditioned manipulation benchmarks; useful templates for your own instruction suite:
  <https://libero-project.github.io/> · <https://simpler-env.github.io/>

## How-to / background

- **OpenVLA inference quickstart** — load the checkpoint, run a forward pass, de-tokenize the action:
  <https://github.com/openvla/openvla#getting-started>
- **OWL-ViT zero-shot detection example** — text queries → boxes + scores:
  <https://huggingface.co/docs/transformers/en/model_doc/owlvit#usage>
- **MoveIt2 Python (`moveit_py`)** — dispatch a grasp pose to the arm (you have this from week 23):
  <https://moveit.picknik.ai/main/doc/api/python_api/moveit_py.html>

## Talks worth your time (free, no signup)

- **CoRL / RSS VLA sessions** — the Conference on Robot Learning posts talks; search the archive for the RT-2, OpenVLA, and π0 talks, all free:
  <https://www.corl.org/>
- **Physical Intelligence blog + talks** — the π0 / π0.5 walkthroughs from the team:
  <https://www.physicalintelligence.company/blog>
- **Sergey Levine's lectures on robot learning** — the cross-embodiment and generalist-policy story from a primary source:
  <https://rail.eecs.berkeley.edu/>

## Tools you'll use this week

- **OpenVLA (or π0) checkpoint** — your VLA policy. Loaded with `transformers` / the repo's loader.
- **OWL-ViT** (`transformers`) — open-vocab detection for the explicit grounding gate.
- **SAM / SAM2** — segment the grounded box into a mask for precise grasp targeting (optional but recommended).
- **`vision_msgs`** — publish grounding results as standard detections.
- **MoveIt2 + Nav2** — the motion layer the VLA action chunk dispatches to.
- **A GPU** — local (≥ 8 GB for OpenVLA inference, more for fine-tune) or cloud (the ~USD 25/mo credit from the track hardware page).

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **VLM** | Vision-Language Model — image(s) + text in, text out (caption, answer, grounding). |
| **VLA** | Vision-Language-Action model — image + instruction in, robot **actions** out. |
| **RT-2 / RT-X** | The Google models that introduced actions-as-text-tokens and cross-embodiment. |
| **OpenVLA** | A 7B open-weight VLA; the one you fine-tuned in week 31. |
| **π0 / OpenPI** | A 2026-current open VLA using a flow-matching action expert (continuous actions). |
| **Open-X Embodiment** | The cross-robot dataset (many robots, one training set) behind RT-X. |
| **Action tokenization** | Discretizing a continuous action into tokens a VLM can emit as "text." |
| **Action chunk** | A short horizon of actions predicted at once (the DP/ACT pattern), executed receding-horizon. |
| **Grounding** | Mapping a language phrase ("the red cup") to a specific entity in the scene. |
| **Implicit grounding** | The VLA grounds internally; you can't inspect it. |
| **Explicit grounding** | A separate open-vocab detector (OWL-ViT/G-DINO) grounds the phrase to a box/mask you *can* inspect and gate on. |
| **Open-vocabulary detection** | Detect objects named by free text, not a fixed class list. |
| **Affordance error** | A grasp that's semantically right but physically unreachable / colliding. |
| **Distribution shift** | The deployed scene differs from the fine-tune data (lighting, viewpoint); the VLA degrades. |
| **Confident hallucination** | The VLA emits a wrong action with no uncertainty signal — the dangerous failure. |
| **Verification gate** | An independent check (grounding agreement) that accepts/rejects the VLA's action. |
| **Classical fallback** | The week-32 non-learned planner that takes over when the VLA is rejected K times. |

---

*If a link 404s, please open an issue so we can replace it.*

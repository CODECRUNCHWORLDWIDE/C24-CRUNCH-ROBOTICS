# Week 31 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 32. Answer key is at the bottom — don't peek.

---

**Q1.** What is Open X-Embodiment (OXE), and why does pooling data from many robots help rather than hurt?

- A) A single-robot dataset; pooling is irrelevant because all data is from one arm.
- B) A ~1M+-trajectory, 22-embodiment open dataset; training on the pool yields *positive cross-embodiment transfer* — each robot's performance improves versus training on its data alone (the RT-X result).
- C) A simulator; it has no real-robot data.
- D) A benchmark suite with no training data attached.

---

**Q2.** OXE makes heterogeneous robots trainable together with a lowest-common-denominator action space. What is it?

- A) Raw joint torques for every robot.
- B) A 6-DOF end-effector pose **delta** plus a 1-DOF gripper command — a 7-vector.
- C) Absolute joint positions in degrees.
- D) Pixel-space optical flow.

---

**Q3.** OpenVLA's backbone is a Prismatic VLM. Name its three pieces and one phrase for what each visual encoder contributes.

- A) GPT-2 + ResNet only; ResNet does everything.
- B) Llama-2-7B (language) + DINOv2 (geometric/spatial features) + SigLIP (semantic image-text features), fused.
- C) BERT + CLIP + a diffusion head.
- D) A single CLIP encoder + an MLP policy.

---

**Q4.** How does OpenVLA turn a continuous 7-D action into something a language model can emit?

- A) It regresses 7 floats with an MLP head.
- B) It runs a diffusion process over the action.
- C) It bins each dimension into 256 uniform bins over the `[q01, q99]` range and maps each bin onto one of the 256 least-used Llama vocabulary tokens, then predicts 7 tokens.
- D) It outputs the action as a JSON string of floats.

---

**Q5.** You fine-tune OpenVLA on your data but at inference leave `unnorm_key` set to the pretraining dataset's key. The bins are predicted correctly. What is the symptom?

- A) The model crashes with a shape error.
- B) The robot moves in the right *direction* but the wrong *magnitude* (e.g., 5× too far) — a silent failure, no error.
- C) The model refuses to load.
- D) The gripper inverts open/close but motion is otherwise perfect.

---

**Q6.** Octo's action head is a ______, which is why it handles multimodal actions natively (the Week 29 lesson).

- A) softmax classifier over 256 bins
- B) linear regression head
- C) diffusion (denoising) head that samples an action chunk
- D) Kalman filter

---

**Q7.** Roughly how big is OpenVLA versus Octo, and what is the practical consequence?

- A) Both ~7B; identical latency.
- B) OpenVLA ~7B, Octo ~27M/93M; OpenVLA has stronger language grounding but far higher inference latency.
- C) Octo is larger; OpenVLA is the fast one.
- D) Both under 100M; neither has a latency concern.

---

**Q8.** A bin in OpenVLA's tokenizer for `Δx` spans `q01 = -0.04 m` to `q99 = +0.04 m` over 256 bins. How wide is one bin?

- A) ~8 mm
- B) ~0.3125 mm
- C) ~3.125 cm
- D) ~80 µm

---

**Q9.** Why is fine-tuning described as *mandatory* rather than optional for a generalist VLA on your task?

- A) The license requires it.
- B) Zero-shot transfer to your specific gripper, camera framing, lighting, and objects is weak (often 30–50% at best, sometimes 0%); the pretraining gave a prior, not your setup.
- C) The model won't load without fine-tuning.
- D) Fine-tuning is only for changing the language, not the control.

---

**Q10.** What is LoRA, and why use it here instead of full fine-tuning?

- A) A data-augmentation method; it has nothing to do with weights.
- B) Low-Rank Adaptation: freeze the 7B base and learn small rank-`r` weight deltas, so it fits in ~16–24 GB and trains in minutes-to-hours on one GPU instead of needing many large GPUs.
- C) A quantization scheme that shrinks the model to 4-bit.
- D) A new optimizer that replaces Adam.

---

**Q11.** In the honest-evaluation discipline, why must the eval set be *held out* before training, with a fixed `n`?

- A) It isn't necessary; evaluating on training demos is fine for VLAs.
- B) Evaluating on training demos measures memorization, not generalization; a fixed `n` gives an honest denominator a reviewer can trust (and attack).
- C) Held-out sets make the model train faster.
- D) `n` only matters for the loss curve, not for evaluation.

---

**Q12.** A fine-tuned VLA reaches the correct red cube but misses the grasp by a centimeter on most failures. Before concluding "the policy can't grasp," what should you check first?

- A) Nothing — the policy is simply bad.
- B) Whether it's a *control*-class issue rooted in un-normalization or the EE-delta→IK/controller mapping, not the policy itself.
- C) Whether the language model needs a bigger vocabulary.
- D) Whether to switch DDS vendors.

---

**Q13.** Your task is one fixed "pick the red cube," you can collect 200 demos, and you have a tight latency budget on an Orin. What does a senior engineer most likely ship, and why?

- A) OpenVLA zero-shot — foundation models are always best.
- B) A specialist like the Week-30 ACT or a Diffusion Policy — for a single fixed task with plenty of demos, it typically beats a 7B VLA on success, latency, and cost; the VLA earns its keep mainly when you need language conditioning or broad task coverage.
- C) A hand-coded scripted policy — learning is never worth it.
- D) Octo zero-shot — it's small, so it must be best.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — OXE is the ~1M+-trajectory, 22-embodiment pool; RT-X showed positive cross-embodiment transfer. (Lecture 1 §1.1–1.3.)
2. **B** — The 6-DOF EE-pose-delta + 1-DOF gripper, a 7-vector, is the lowest-common-denominator that lets all robots' data train together. (Lecture 1 §1.2.)
3. **B** — Llama-2-7B + fused DINOv2 (geometry/where) + SigLIP (semantics/what). (Lecture 1 §3.1.)
4. **C** — 256 uniform bins per dim over `[q01, q99]`, mapped onto the rare tail of the Llama vocab; 7 tokens predicted autoregressively. (Lecture 1 §3.3.)
5. **B** — Right direction, wrong magnitude, silently — the un-normalization trap. (Lecture 2 §2.4.)
6. **C** — A diffusion head sampling an action chunk; native multimodality, like Diffusion Policy. (Lecture 1 §2.2.)
7. **B** — OpenVLA ~7B vs Octo ~27M/93M; OpenVLA = stronger grounding, much higher latency. (Lecture 1 §3.4.)
8. **B** — `(0.04 - (-0.04)) / 256 = 0.08 / 256 ≈ 0.0003125 m = 0.3125 mm`. (Lecture 1 §3.3; Exercise 1.)
9. **B** — The prior is real but it is not your setup; zero-shot is weak, so fine-tuning is the job. (Lecture 1 §1.4, Lecture 2 §2.1.)
10. **B** — Low-Rank Adaptation: train small rank-`r` deltas on a frozen base; fits one GPU, trains fast. (Lecture 2 §2.1.)
11. **B** — Training-set eval measures memorization; fixed `n` gives a defensible denominator. (Lecture 2 §3.1.)
12. **B** — Most "control" failures on a fine-tuned VLA are un-normalization or EE-delta→controller mapping bugs, not the policy. Check the pipeline first. (Lecture 2 §3.3, Challenge trap.)
13. **B** — For one fixed task with ample demos and a tight latency budget, a specialist usually wins; the generalist earns its keep on language/breadth. (Lecture 1 §3.4, Lecture 2 §3.4.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

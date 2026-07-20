# Week 37 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 38. Answer key is at the bottom — don't peek.

---

**Q1.** What is the core difference between a VLM and a VLA?

- A) A VLA is larger than a VLM.
- B) A VLM takes image(s) + text and outputs *text*; a VLA takes image + instruction and outputs robot *actions*.
- C) A VLA cannot process images.
- D) A VLM is open-weight; a VLA is always closed.

---

**Q2.** RT-2 (and OpenVLA) make a text-generating model emit motor commands by:

- A) Bolting a separate CNN onto the output.
- B) Discretizing each action dimension into bins and representing each bin as a token in the model's vocabulary, so an action is a short string of "action tokens."
- C) Training a brand-new model from scratch with no language component.
- D) Using the LLM only to caption the scene, then a hand-written rule for actions.

---

**Q3.** Why is fine-tuning an open-weight VLA (like OpenVLA) on your robot's demos described as *mandatory*, not optional?

- A) The license requires it.
- B) Cross-embodiment pretraining gives a strong prior, but your specific gripper/camera/workspace is likely out of distribution; fine-tuning pulls your embodiment into the model's distribution so zero-shot mediocrity becomes competence.
- C) Fine-tuning makes the model smaller.
- D) Without fine-tuning the model cannot load.

---

**Q4.** The 2026-generation π0 (OpenPI) differs from OpenVLA mainly in:

- A) It has no vision encoder.
- B) It replaces discrete action tokens with a continuous action expert (flow matching) that emits smooth high-frequency action chunks — better for dexterous control.
- C) It cannot follow language instructions.
- D) It runs only on CPU.

---

**Q5.** Your VLA outputs an action that the robot executes as a 50 cm move when you meant 5 cm. The most likely cause is:

- A) The DDS QoS is wrong.
- B) You failed to un-normalize the action with the same dataset statistics the model was trained on — the output is in the model's normalized action space.
- C) The camera is miscalibrated.
- D) The behavior tree ticked too fast.

---

**Q6.** Why does the VLA-as-policy loop dispatch grasps through MoveIt2 rather than commanding the motors directly from the VLA's output?

- A) MoveIt2 is faster than raw motor commands.
- B) MoveIt2 provides collision checking, joint-limit enforcement, and a planned trajectory — so an infeasible/colliding VLA pose (an affordance error) is refused at the motion layer for free.
- C) The VLA cannot output poses.
- D) ROS2 forbids direct motor commands.

---

**Q7.** What is the key difference between *implicit* and *explicit* grounding?

- A) Implicit grounding is faster.
- B) Implicit grounding happens inside the VLA and is opaque/un-auditable; explicit grounding uses a separate open-vocab detector (OWL-ViT/Grounding-DINO) that returns an inspectable box + confidence you can gate on.
- C) Explicit grounding only works in simulation.
- D) They are the same thing.

---

**Q8.** Why does the safety gate use a *second, independent* grounding instead of just trusting the VLA's confidence?

- A) The VLA's confidence is always too high.
- B) A VLA gives no calibrated action confidence (and a generative one gives none at all); an independent grounding of the same instruction is a "second opinion" — if it disagrees with the VLA's target, you've caught a likely hallucination.
- C) Two models are always twice as accurate.
- D) The detector is required by ROS2.

---

**Q9.** Which VLA failure mode is the *hardest to catch before execution* with a grounding-agreement gate, and why?

- A) Grounding error — the gate is designed for it.
- B) Spatial-relation error ("move it left" → goes right): the grounding *agrees* on the object, so the gate accepts; only the *relation* is wrong, which a target-agreement check can't see. It usually needs a post-execution verification.
- C) Affordance error — MoveIt2 catches it.
- D) Absent object — caught at the confidence threshold.

---

**Q10.** An instruction names an object that isn't in the scene ("bring the green bottle," no bottle present). In a well-built gated loop, what happens?

- A) The VLA grasps the nearest object.
- B) The explicit grounding returns no confident detection, so the loop rejects *before any action* with a "not in scene" reason.
- C) The robot crashes.
- D) The fallback grasps a random object.

---

**Q11.** Why can't you query a 7B VLA at control rate (50+ Hz) on a Jetson Orin, and what's the standard fix?

- A) You can; latency isn't an issue.
- B) A single forward pass is hundreds of ms (3–10 Hz at best); the fix is action chunking (one query buys a chunk executed over many cycles) plus async inference (compute the next chunk while executing the current).
- C) The fix is to make the model bigger.
- D) The fix is to drop the camera resolution to 1×1.

---

**Q12.** The syllabus says a language-conditioned safety case is "half-prompt, half-runtime." What's the asymmetry between the two halves?

- A) Prompts are more important than runtime checks.
- B) A prompt can reduce ambiguity but cannot *prevent* the model from hallucinating; only a runtime check (the gate, clamps, fallback) can refuse to *execute* a hallucination — so the runtime half is what actually stops a wrong action.
- C) Runtime checks are optional if the prompt is good.
- D) They are equally capable of stopping a wrong action.

---

**Q13.** In your evaluation you report 80% on "bring the red cup" but break it into "grounded right: 14/15, executed success: 12/15." Why report the split instead of just 80%?

- A) To pad the report.
- B) Grounding success and execution success have *different fixes* — a grounding failure needs better data/grounding; an execution failure (e.g., a place slip) needs better motion. The split tells the next engineer where to invest.
- C) The split is required by the license.
- D) Aggregate rates are more honest.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — VLM: text out. VLA: robot actions out, conditioned on image + instruction. (Lecture 1 §1.)
2. **B** — Discretize action dims into bins → tokens; the VLA emits action tokens like text. (Lecture 1 §1.2.)
3. **B** — Cross-embodiment gives a prior; your embodiment is OOD; fine-tuning makes it competent on your robot. (Lecture 1 §1.3, §2.)
4. **B** — π0 uses a continuous flow-matching action expert instead of discrete tokens, for smoother high-frequency control. (Lecture 1 §1.4.)
5. **B** — The action is in normalized space; un-normalize with the dataset stats or scales blow up. (Lecture 1 §3.1.)
6. **B** — MoveIt2 gives collision/limit/feasibility checking; an infeasible VLA pose is refused (affordance error caught). (Lecture 2 §1.1, §4.)
7. **B** — Implicit = opaque inside the VLA; explicit = an inspectable, gateable open-vocab detection. (Lecture 1 §5.)
8. **B** — VLAs give no reliable action confidence; an independent grounding is the second opinion that catches disagreement. (Lecture 1 §5.2, §6; Lecture 2 §5.1.)
9. **B** — Spatial-relation errors pass the agreement gate (object is right) and need a post-execution check. (Lecture 2 §4, mode 2; Challenge 1.)
10. **B** — Absent object → no confident grounding → reject before any action. (Lecture 2 §5.1; Exercise 2.)
11. **B** — Hundreds of ms per pass; action chunking + async inference bridge the control-rate gap. (Lecture 2 §6.)
12. **B** — A prompt can't prevent hallucination; only a runtime check refuses to execute it — the runtime half is load-bearing. (Lecture 2 §5.4.)
13. **B** — Grounding vs. execution failures have different fixes; the split directs the investment. (Lecture 2 §2.2–2.3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

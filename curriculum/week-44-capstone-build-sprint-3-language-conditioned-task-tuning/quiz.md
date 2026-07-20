# Week 44 — Quiz

Thirteen questions on evaluation methodology, failure modes, and VLA fine-tuning. Take it with your lecture notes closed. Aim for 11/13 before the defense ramp. Answer key at the bottom — don't peek.

---

**Q1.** Why must the twenty-instruction acceptance suite be frozen in Git *before* you fine-tune?

- A) Git is faster at reading frozen files.
- B) So every run can cite the suite's commit hash and you cannot tune the suite to flatter the model afterward.
- C) Because the trainer reads the suite as its training data.
- D) Freezing compresses the YAML and saves disk.

---

**Q2.** You run an instruction once and it succeeds. What can you honestly conclude about its success rate?

- A) It is 100%.
- B) It is at least 50%.
- C) Only that it is somewhere above 0%; one trial is essentially a coin flip you kept.
- D) Nothing at all; single successes are meaningless and should be discarded.

---

**Q3.** Which axis allocation makes for the *most* diagnostic twenty-instruction suite?

- A) Twenty rephrasings of "bring me the red cup."
- B) Twenty instructions spread across object-reference, spatial-grounding, distractor-density, phrasing, and recovery.
- C) Twenty instructions all at maximum difficulty.
- D) Twenty instructions chosen at random from a large generated set.

---

**Q4.** Why do we score each trial as binary success/failure rather than giving partial credit?

- A) Binary is easier to store in JSON.
- B) Partial credit is more accurate and we use it whenever possible.
- C) The capstone bar is "the task got done"; partial credit is un-comparable across graders and hides whether the task was actually accomplished.
- D) Because the policy can only output 0 or 1.

---

**Q5.** A "scene reset" on real hardware (Path A) is made reproducible by:

- A) Teleporting objects to fixed poses via a service call.
- B) A taped bench/floor template plus a committed reference photo per layout.
- C) Letting objects fall wherever and recording where they land.
- D) Asking the operator to "roughly" place objects from memory.

---

**Q6.** During fine-tuning, your training loss keeps dropping but suite success plateaus then *falls*. What is the most likely explanation?

- A) The GPU is overheating.
- B) The model is memorizing your demo trajectories (overfitting); lower loss does not mean better task success.
- C) The eval suite is broken.
- D) LoRA is incompatible with the base model.

---

**Q7.** You should select which fine-tuned checkpoint to ship based on:

- A) The lowest training loss.
- B) The highest success on a dev slice that is separate from the frozen acceptance suite.
- C) The largest checkpoint file.
- D) The most recent checkpoint, always.

---

**Q8.** Why LoRA instead of a full-parameter fine-tune for a capstone?

- A) LoRA always produces a more accurate policy.
- B) LoRA trains only small adapter matrices, fits on one GPU, and yields a few-hundred-MB adapter you can version and merge — defensible and cheap.
- C) Full fine-tuning is impossible on any hardware.
- D) LoRA does not require any demos.

---

**Q9.** The policy reaches the correct object every time but the gripper closes on nothing and the object is never picked up. Which failure mode is this?

- A) Grounding.
- B) Language-binding.
- C) Grasp.
- D) Placement.

---

**Q10.** You issue two different instructions and the robot performs the identical action both times, ignoring what you said. Which failure mode, and what is the first thing to check?

- A) Grasp; check the gripper TCP.
- B) Language-binding; verify the instruction string actually reaches the policy and is not being dropped.
- C) Placement; check the destination frame.
- D) Grounding; collect more color demos.

---

**Q11.** Why report a Wilson score interval instead of the naive normal approximation for your `k/N` success rate?

- A) Wilson is the only interval that exists for proportions.
- B) The naive normal approximation misbehaves near 0 and 1 and at small N — exactly the regime of a 100-trial suite.
- C) Wilson intervals are always narrower, making your numbers look better.
- D) The normal approximation requires a GPU.

---

**Q12.** Your fine-tune raised the suite from 9/20 to 16/20, but instruction 7 dropped from 2/5 to 1/5. What do you do in the report?

- A) Drop instruction 7 from the suite since the overall result is good.
- B) Quietly note it in a comment.
- C) Flag the regression explicitly and explain it; an honest report shows the instruction the fine-tune broke.
- D) Re-run only instruction 7 until it improves, then report that number.

---

**Q13.** Which of these demonstrations is safe to include in your 50-demo fine-tuning set?

- A) The exact instruction text and scene from suite instruction 1.
- B) A clean success on "get the red cup off the left bench" with the cup at a different position than any suite reset — same family, different instance.
- C) A failed teleop run where the grasp slipped, kept "for variety."
- D) An overhead-camera demo when deployment uses the wrist camera.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The frozen suite + cited commit hash is what makes the number honest. Editing the suite after a run to flatter the model is the cardinal sin of in-house eval.
2. **C** — One trial bounds the rate above 0% and nothing more. The honest unit is `k/N`; the capstone bar lives in the 20–95% range a single run cannot resolve. (D is wrong — single trials are not discarded, they are aggregated into `k/N`.)
3. **B** — Stratification across the five failure axes makes the *pattern* of which instructions fail diagnostic, so a score tells you *where* you are weak, not just *that* you are.
4. **C** — Binary scoring matches the "task got done" bar and stays comparable across graders. Partial outcomes become failures tagged with a failure mode, which is more useful than a half-point.
5. **B** — Real hardware cannot teleport, so you reproduce the scene with a physical template and a committed photo. (A is the Path B/sim answer.)
6. **B** — Training loss measures token reproduction, not task success. A falling loss with falling success is classic overfitting/memorization; you select on eval, not loss.
7. **B** — Select on a dev slice held out from the frozen suite. Selecting on the frozen suite overfits to it; selecting on loss ignores that loss lies about success.
8. **B** — LoRA's payoff is a single-GPU run and a small, versionable, mergeable adapter — exactly the defensible artifact a capstone wants. It is not magically more accurate (A) and it still needs demos (D).
9. **C** — Right object, failed pick = grasp. The first non-data check is gripper TCP calibration before adding grasp demos.
10. **B** — Identical action regardless of instruction = language-binding. First check the plumbing: is the instruction string reaching the policy at all? A dropped string masquerades as a model failure.
11. **B** — At 100 trials and rates near the extremes, the normal approximation is unreliable; Wilson behaves. (C is false — Wilson is not chosen for being narrower.)
12. **C** — Flag and explain the regression. Hiding it (B), dropping the instruction (A), or cherry-picking a re-run (D) all make the report dishonest and will not survive the panel.
13. **B** — Same family, different instance, deployment-matched observation = a good demo. A is training on the test set; C is a fumble you must filter out; D mismatches the observation space and trains a broken policy.

</details>

---

If you scored under 9, re-read the two lecture notes for the questions you missed — especially the eval-methodology ones, which are the spine of the defense. If you scored 11+, you are ready to defend a number.

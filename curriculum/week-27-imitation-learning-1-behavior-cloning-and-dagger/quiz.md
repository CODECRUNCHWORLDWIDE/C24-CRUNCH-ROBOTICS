# Week 27 — Quiz

Thirteen questions on behavior cloning, the training loop, covariate shift, DAgger, the diffusion-of-error problem, and honest evaluation. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 28. Answer key is at the bottom — don't peek.

---

**Q1.** Behavior cloning frames imitation as:

- A) Reinforcement learning with a sparse reward.
- B) Supervised learning: train a policy to predict the expert's action from the observation, using (observation, action) pairs as labeled data.
- C) Unsupervised clustering of trajectories.
- D) Inverse kinematics.

---

**Q2.** Your BC policy has a *one-step offset* between observations and actions in the dataset (action at `t` is paired with observation at `t+1`). What is the effect?

- A) None; the policy still learns fine.
- B) The policy learns to predict the action for the *wrong* state — a silent data bug that looks like a modeling problem; fix it at the recording layer by pairing on timestamps.
- C) The policy trains faster.
- D) It only matters for discrete actions.

---

**Q3.** Why must you normalize observations *and* actions, fitting the stats on the *training split only*?

- A) Normalization is optional and cosmetic.
- B) Mixed scales let the largest-dimension dominate the MSE loss; fitting on train only avoids leaking validation statistics into training; and you store the stats to un-normalize the predicted action at deployment.
- C) PyTorch requires it.
- D) It makes the loss curve prettier with no real effect.

---

**Q4.** A BC policy has *low train loss and low validation loss* but fails most of its deployment rollouts by drifting. What is going on?

- A) Underfitting — train more.
- B) Overfitting — regularize.
- C) Covariate shift — the loss is computed on the expert's states, but the policy is tested on its own drifting states; healthy loss curves cannot reveal it.
- D) A bug in the optimizer.

---

**Q5.** Why can't you fix covariate shift with more epochs or a bigger network?

- A) You can; more epochs always fix it.
- B) Both make the policy better on the *expert's* state distribution; neither gives it data about the *off-distribution* states it actually visits. You need data from the policy's own distribution, which only DAgger collects.
- C) Bigger networks overfit, which fixes covariate shift.
- D) Covariate shift is an optimizer setting.

---

**Q6.** The compounding-error result says behavior cloning's expected mistakes over a `T`-step horizon grow as:

- A) `O(εT)` — linear.
- B) `O(ε T²)` — quadratic, because a mistake puts the policy in an unfamiliar state where it is *more* likely to err again; DAgger reduces this to `O(εT)`.
- C) `O(ε)` — constant.
- D) `O(2^T)` — exponential.

---

**Q7.** In DAgger, during a data-collection rollout, who chooses the actions and who provides the labels?

- A) The expert chooses and labels both.
- B) The *policy* chooses the actions (so we visit the policy's own state distribution), but the *expert* provides the action label at each visited state.
- C) The policy chooses and labels both.
- D) A random policy chooses; the previous policy labels.

---

**Q8.** Each DAgger round, you should:

- A) Replace the dataset with the new policy-rollout data.
- B) Aggregate — *grow* the dataset by adding the policy's visited states (expert-labeled) to the existing demos; replacing throws away the expert's good behavior.
- C) Delete the original expert demos.
- D) Train from scratch with no data.

---

**Q9.** The "diffusion of error" problem refers to:

- A) Diffusion Policy's noise schedule.
- B) Per-step action errors accumulating over a multi-step trajectory (and jittery single-step predictions), which motivates action chunking (ACT) and is partly addressed by predicting a *sequence* of actions at once.
- C) A bug in the dataloader.
- D) Gaussian noise in the observations.

---

**Q10.** Your expert demos approach the block from *two* sides (some left, some right). A BC policy with MSE loss at the fork tends to:

- A) Pick the left path consistently.
- B) Average the two good actions into a bad one — heading straight into the obstacle — because MSE regression predicts the mean; this multimodal-averaging failure persists even with perfect data and no covariate shift, and motivates Diffusion Policy (Week 29).
- C) Pick the right path consistently.
- D) Refuse to act.

---

**Q11.** What makes a policy evaluation honest rather than a vibe?

- A) Running it once and watching it look good.
- B) A crisp pre-stated success predicate, a fixed set of start states (including novel ones), multiple seeds (≥ 20), a success rate reported with a confidence interval, and per-trial failure classification.
- C) Reporting the training loss.
- D) Counting how many demos you collected.

---

**Q12.** Why does a learned policy ship with a safety clamp and a classical fallback?

- A) ROS2 requires it.
- B) A learned policy can output garbage (an out-of-distribution observation can produce a wild action); the velocity/workspace clamp rejects out-of-bounds actions and the classical fallback (e.g., the Week-25 grasp planner) takes over after repeated rejections — the "ship the learned policy with a leash" principle.
- C) To make it train faster.
- D) Clamps improve the loss.

---

**Q13.** You report "BC succeeded 12/20 and BC+DAgger succeeded 15/20." A skeptic asks if the difference is real. The honest response is:

- A) "15 > 12, so DAgger clearly won."
- B) "At 20 trials those rates have wide overlapping confidence intervals (~±19%), so it may be noise; I'll run more trials to tell signal from noise — and both were scored on the same fixed protocol."
- C) "Trust me, it looked better."
- D) "The training loss was lower for DAgger."

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — BC is supervised learning: (observation, action) pairs, predict the expert's action. (Lecture 1 §1.)
2. **B** — A one-step offset teaches the policy to predict the action for the wrong state; a silent data bug fixed by timestamp-based pairing (the Week 5 stamping lesson). (Lecture 1 §2.1.)
3. **B** — Mixed scales let the largest dimension dominate MSE; fit norm on train only (no val leakage); store stats to un-normalize at deployment. (Lecture 1 §3-4.)
4. **C** — Covariate shift: the loss is on the expert's states, the policy is tested on its own drifting states; healthy curves cannot show it. (Lecture 1 §5, Lecture 2 §1.)
5. **B** — More epochs / bigger nets improve performance on `d_expert`; neither gives data about `d_policy`. Only DAgger collects the policy's own states. (Lecture 2 §1.)
6. **B** — BC's mistakes grow `O(εT²)` (a mistake raises the chance of every subsequent mistake); DAgger reduces it to `O(εT)`. (Lecture 2 §1.1.)
7. **B** — The policy chooses actions (sample its states); the expert labels (correct action at each visited state). That inversion is what makes DAgger work. (Lecture 2 §3.)
8. **B** — Aggregate, don't replace; the dataset grows, keeping the expert's good behavior and adding the recovery data. (Lecture 2 §3.)
9. **B** — Per-step errors accumulating over a trajectory (and jitter); motivates action chunking (ACT). (Lecture 2 §4.)
10. **B** — MSE averages the two good actions into a bad one (the mean of left and right is straight ahead); persists with perfect data, motivates Diffusion Policy. (Lecture 2 §4.)
11. **B** — Crisp predicate, fixed starts (incl. novel), ≥ 20 seeds, rate with an interval, per-trial classification. (Lecture 2 §5.)
12. **B** — A learned policy can output garbage; clamp rejects out-of-bounds actions, fallback takes over after repeated rejections — "ship the learned policy with a leash." (Lecture 2 §6.)
13. **B** — At 20 trials the intervals are wide and overlapping; report the interval, run more trials to tell signal from noise, and confirm the same fixed protocol. (Lecture 2 §5, Challenge 1.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed — especially Lecture 2 on covariate shift. If you scored 11 or higher, you're ready for the [homework](./homework.md).

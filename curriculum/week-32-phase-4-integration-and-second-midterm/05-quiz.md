# Week 32 — Quiz

Thirteen questions on the learned-policy-with-a-leash pattern, safety scaffolds, predictive filters, the intervention rate, the learned-policy hazards, and the second-midterm review. Take it with your lecture notes closed. Aim for 11/13 before you sit the midterm review. Answer key at the bottom — don't peek.

---

**Q1.** Why is a learned policy (Diffusion Policy, ACT, VLA) called an *unverified controller*, in contrast to PID/LQR/MPC?

- A) It is slower than a classical controller.
- B) Its output is unbounded, it does not know when it is off-distribution, and there is no tractable way in 2026 to prove it will not run away — unlike PID/LQR/MPC, each of which comes with a safety argument you can state and check before running.
- C) It cannot be trained on a GPU.
- D) It only works in simulation.

---

**Q2.** A base twist commands `vx = 2.0` m/s and `wz = 1.0` rad/s. The limits are `v_max = 1.0`, `w_max = 1.5`. What does the *correct* clamp do?

- A) Saturate `vx` to 1.0 and leave `wz` at 1.0 — per-channel saturation.
- B) Uniformly rescale both by `1/2.0` (the worst-case over-limit factor), giving `vx = 1.0`, `wz = 0.5`, preserving the curvature ratio so the path shape is unchanged.
- C) Reject the action outright.
- D) Set both to zero.

---

**Q3.** Why is per-channel saturation wrong for a coordinated arm joint-velocity vector?

- A) It is slower to compute.
- B) Saturating one joint but not the others desynchronizes the trajectory — the joints no longer reach their waypoints together, so the end-effector path warps and a grasp goes off by centimeters.
- C) It uses too much memory.
- D) It is not wrong; per-channel saturation is the standard approach.

---

**Q4.** The capstone spec fixes the fallback at "the learned policy is rejected **three times in a row**." Why three *consecutive*, and not three total?

- A) Three is an arbitrary number with no meaning.
- B) One rejection is noise (a transient bad observation); three *consecutive* rejections is the signature of a policy genuinely *stuck* off-distribution. The counter resets on any safe action, so isolated rejects don't trigger the fallback.
- C) The BT can only count to three.
- D) Three total rejections is the same as three consecutive.

---

**Q5.** Which deployment defect does a *confidence gate* (sample the policy K times, reject if the action spread is high) primarily catch?

- A) The too-loose filter.
- B) The multimodal collapse — a policy averaging two good actions into one bad one — detected as high variance / multimodality in the action samples.
- C) A frozen sim clock.
- D) A QoS mismatch.

---

**Q6.** Why can you *not* trust the policy's self-reported confidence alone as your only guard?

- A) Confidence is always exactly 0.5.
- B) The silent-confidence failure: a policy can be *wrong and report high confidence*, so a guard that only rejects low-confidence actions lets the confidently-wrong action through. Hard physical bounds must catch it by its consequences, regardless of the policy's opinion.
- C) Confidence is too expensive to compute.
- D) The policy never reports confidence.

---

**Q7.** What is the difference between a reactive *clamp* and a *predictive* safety filter?

- A) There is no difference.
- B) A clamp checks one action (or one predicted state) against a bound; a predictive filter rolls the action *forward through a model over a short horizon* and checks the predicted *trajectory*, catching constraints that are about-to-be-violated, not yet violated.
- C) A clamp is slower than a predictive filter.
- D) A predictive filter only works on the base, not the arm.

---

**Q8.** In the control-barrier-function (CBF) safety filter, the QP minimizes `‖u − u_policy‖²` subject to `ḣ(x, u) ≥ −α·h(x)` and the box constraints. What does the solution give you?

- A) The fastest possible action.
- B) The *minimally-invasive* correction — the action closest to what the policy wanted that still satisfies the barrier (the optimal projection). When the QP is infeasible, you reject.
- C) A random safe action.
- D) The policy's action unchanged.

---

**Q9.** Why must the safety filter's per-action latency be a small fraction of the policy's inference latency?

- A) It does not matter how fast the filter is.
- B) If the filter is slower than (or comparable to) the policy, it doubles the control latency, making the robot sluggish — and a late safe action is itself a hazard. The filter must never be the bottleneck.
- C) ROS2 requires it.
- D) The filter is always faster by construction.

---

**Q10.** A policy reports **92% success** with a **40% fallback rate** over the eval set. A second policy reports **85% success** with a **2% fallback rate**. Which is the better *deployment*, and why?

- A) The 92% policy, because success rate is all that matters.
- B) The 85% / 2% policy, because the learned policy is doing the work itself and only handing off when genuinely stuck; the 92% / 40% policy is being *carried* by its classical fallback.
- C) They are equivalent.
- D) Neither; both should be retrained.

---

**Q11.** Over 40 episodes your wrapper reports **zero clamps, zero rejections, zero fallbacks**. Why is this a defect, not a clean run?

- A) It is a clean run; zero interventions is the goal.
- B) It is the *too-loose-filter* defect — the bounds are so loose they never trip, so the leash is decorative and provides no protection. A filter that never fires has never been tested by the thing it exists to catch.
- C) It means the policy is perfect.
- D) It means the eval set was too small.

---

**Q12.** What is the single most convincing piece of evidence that your safety filter is load-bearing (not too-loose)?

- A) A high success rate.
- B) The *ablation*: disable the filter, re-run the episodes, and document the unsafe actions that now execute (table-strikes, over-speed twists) that the filter previously caught. This both disproves the too-loose defect and quantifies the leash's value.
- C) A long lecture about safety.
- D) The policy's self-reported confidence.

---

**Q13.** The second-midterm review requires you to defend five artifacts: training pipeline, eval protocol, safety wrapper, fallback path, and hazard log. You can defend four of the five well. What is the outcome at the gate?

- A) Pass; four of five is a strong majority.
- B) The review is a hard gate against the rubric; all five are required, and a missing or undefended artifact (e.g., a hazard log with no learned-policy rows) is a finding the panel will catch. Defend all five, with live demonstrations and numbers.
- C) Pass; the hazard log can be added later.
- D) The panel averages the five into a percentage.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — A learned policy is unbounded (nothing caps its action at your limits), confident even off-distribution (no built-in "I'm unsure"), and unverifiable at scale in 2026 — the opposite of PID/LQR/MPC, each of which carries a stability/constraint argument you check before running. (Lecture 1 §1.)

2. **B** — Uniform rescaling by the worst-case over-limit factor (`f = 2.0`) scales *both* channels, preserving the curvature ratio `vx/wz = 2.0` so the path shape is unchanged. Per-channel saturation (A) would collapse the ratio to 1.0 and warp the path. (Lecture 1 §4; Exercise 1.)

3. **B** — Saturating one joint and not the others desynchronizes the coordinated trajectory; the joints miss their shared waypoints and the end-effector path warps. The correct clamp is a single uniform time-rescale of the whole vector. (Lecture 1 §4.)

4. **B** — One rejection is a transient (a one-frame perception glitch). Three *consecutive* rejections means the policy is stuck off-distribution at this state. The counter resets on any safe action, so three *isolated* rejects separated by safe actions do not fire the fallback. (Lecture 1 §6; Exercise 3.)

5. **B** — The sample-variance confidence gate catches the multimodal collapse by detecting the multimodality (high spread in the K action samples) directly, before the policy averages two good actions into a bad one. (Lecture 1 §3.3, §2 Defect 2.)

6. **B** — The silent-confidence failure: a confidently-wrong action defeats a confidence-only gate. The hard physical bounds (clamps, CBF, state guards) must catch the unsafe action by its *consequences* — it would violate a constraint — regardless of how confident the policy is. (Lecture 1 §2 Defect 3, §3.3.)

7. **B** — A clamp is reactive (one action / one state vs. a bound); a predictive filter rolls the action forward through a model over a horizon and checks the predicted trajectory, catching the constraint that's about-to-be-violated. (Lecture 1 §5; Lecture 2 §1.)

8. **B** — The CBF QP returns the minimally-invasive correction: the closest action to `u_policy` that satisfies the barrier and box constraints. Infeasible QP → reject. This is the optimal version of the heuristic "project to nearest safe." (Lecture 2 §1.1.)

9. **B** — A filter slower than (or comparable to) the policy doubles control latency, making the robot sluggish; a late safe action is its own hazard. Measure `p50`/`p95` and report them against the policy inference time. (Lecture 2 §1.2.)

10. **B** — The 85% / 2% policy is doing the work and only falling back when genuinely stuck; the 92% / 40% policy is being carried by its classical planner. The fallback rate, not the success rate alone, is the deployment signal. (Lecture 1 §7; Lecture 2 §2.2.)

11. **B** — The too-loose-filter defect (Defect 4). Bounds that never trip make the leash decorative — no protection, no evidence it works, and the worst kind of false pass because it *looks* like success. (Lecture 1 §2 Defect 4; Lecture 2 §2.2.)

12. **B** — The ablation. Disabling the filter and documenting the unsafe actions that now execute both disproves the too-loose defect and quantifies the leash's value — the strongest possible evidence for the panel. (Lecture 2 §2.3.)

13. **B** — The review is a hard gate against the five-part rubric; all five are necessary. A hazard log missing the learned-policy rows is a finding the panel will catch. Defend all five with live demonstrations (a live rejection, a live fallback) and numbers (the intervention-rate breakdown). (Lecture 2 §4.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed — especially Lecture 1 on the leash and the four defects, and Lecture 2 on the predictive filter and the midterm defense. If you scored 11 or higher, you're ready for the [homework](./06-homework.md) and the [mini-project](./07-mini-project/00-overview.md) — and the midterm review.

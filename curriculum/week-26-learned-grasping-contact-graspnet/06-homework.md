# Week 26 Homework

Six problems that drive the learned-grasping pipeline into your fingers. The full set should take about **5 hours**. Work in your Week 26 Git repository (the same workspace as the exercises and the `crunchbot_grasp` mini-project) so every problem produces at least one commit you can point to at the Phase 4 midterm in Week 32.

The headline deliverable is **Problem 4 — the per-object success-rate report**, the artifact the midterm panel reads to judge whether your stack is real or a one-shot demo.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`) and your overlay. Have your **week-23 MoveIt2 arm** and **week-14 RGB-D camera** spawnable in Gz Sim — Problems 2, 4, and 6 run against them. If the sim is broken, the synthetic clouds from the exercises are your fallback; say so in your writeup.

---

## Problem 1 — Round-trip the pose math

**Problem statement.** Take your batched `reconstruct_grasp_poses` from Exercise 1. For 1,000 random `(contact, approach, baseline, width)` inputs, reconstruct the pose, convert `R` to a quaternion and back to a matrix, and confirm it round-trips. Then deliberately *break* it by removing the Gram–Schmidt orthogonalization and show the round-trip error explodes. Record both error distributions.

**Acceptance criteria.**

- A `notes/week-26/pose-roundtrip.md` reporting the max and mean `|R_reconstructed - R_roundtrip|` over 1,000 samples, both *with* and *without* orthogonalization.
- With orthogonalization, max error `< 1e-5`. Without it, max error is orders of magnitude larger.
- One sentence explaining why a non-orthonormal `R` does not survive the quaternion round-trip.
- Committed.

**Hint.** Reuse the week-1 quaternion routines (or `scipy.spatial.transform.Rotation`). The point of the "broken" run is to *see* the failure the Exercise 1 assertion prevents.

**Estimated time.** 40 minutes.

---

## Problem 2 — The depth-unit bug, reproduced and fixed

**Problem statement.** Run your grasp node against the week-14 camera (or sim) with the depth-to-meters conversion **disabled**. Capture the resulting cloud (the points will be ~1000× too far) and the empty/garbage grasp output. Then enable the conversion and capture the correct cloud and a real grasp shortlist. Document the before/after.

**Acceptance criteria.**

- `notes/week-26/depth-units.md` shows the cloud's z-range with the bug (e.g. hundreds of meters) and without it (~0.4–1.0 m).
- The grasp shortlist is empty/nonsense with the bug and non-empty with the fix.
- You state the rule: depth from RealSense/sim plugins is frequently `uint16` millimeters; Contact-GraspNet wants meters.
- Committed.

**Hint.** Print `cloud[:, 2].min(), cloud[:, 2].max()` right after deprojection. A z-min of 400 (meters) instead of 0.4 is the bug screaming at you.

**Estimated time.** 40 minutes.

---

## Problem 3 — Segmentation quality vs. grasp quality

**Problem statement.** Take one scene with two adjacent objects. Run grasping three ways: (a) no segmentation (whole scene), (b) a *loose* mask that leaks onto the neighbor, (c) a *tight, correct* mask. For each, count how many of the top-5 grasps would span two objects (a grasp whose two contact points fall on different object clouds). Tabulate.

**Acceptance criteria.**

- `notes/week-26/segmentation-quality.md` with a table: condition → top-5 grasps → number of object-spanning grasps.
- The unsegmented and loose-mask conditions produce object-spanning grasps; the tight mask produces none (or far fewer).
- One sentence on why "the network is rarely the bottleneck; segmentation usually is."
- Committed.

**Hint.** A grasp spans two objects if its two contact points (contact and contact + width·baseline) belong to different segmentation labels. You don't need SAM2 for this — a hand-drawn ROI mask per object is enough to make the point.

**Estimated time.** 50 minutes.

---

## Problem 4 — The per-object success-rate report (headline deliverable)

**Problem statement.** This is the midterm-grade artifact. Pick each of three objects (mug, box, tool) at least 5 times with your full `crunchbot_grasp` stack. Log every attempt: object, learned-or-fallback, success/fail, and failure bucket on failure. Produce `notes/week-26/success-rate-report.md` with: a per-object and overall success-rate table, a failure-bucket histogram, the intervention rate, and a one-paragraph reading naming *which bucket dominates and what you'd fix next*.

**Acceptance criteria.**

- `notes/week-26/success-rate-report.md` exists with all four elements (table, histogram, intervention rate, reading).
- At least 15 total attempts logged with per-attempt outcome and bucket.
- The reading names a *specific* next fix tied to the dominant bucket (e.g. "perception dominates → depth completion for thin objects"), **not** a generic "improve the network."
- Committed.

**Hint.** The reading is graded harder than the numbers. A 73% success rate with "perception dominates because the tool is thin and undersampled, so I'll add a depth-completion pass" is a strong answer; the same 73% with "needs more work" is not. The bucket histogram is what makes the reading possible — log the bucket on *every* failure.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Prove the fallback never stalls

**Problem statement.** Feed your pick stack three inputs the learned network cannot handle: (a) an empty mask, (b) a transparent object (no points), (c) a novel object the network is unconfident on. For each, show the system either falls back to the antipodal sampler *or* returns a clean "no grasp available, aborting safely" — but **never hangs or crashes**.

**Acceptance criteria.**

- `notes/week-26/fallback-stress.md` with the log output for all three inputs.
- For the non-empty-cloud case (c), the fallback fires and is logged.
- For the empty-cloud cases (a, b), the system aborts cleanly with a logged reason, not a hang or a traceback.
- One sentence: why "degrade, never stall" is the Phase 4 design rule.
- Committed.

**Hint.** The transparent case has *no points*, so even the fallback can't grasp — the correct behavior is a clean abort, not a fallback grasp on empty air. Distinguish "fall back to a worse grasp" (cloud has points) from "abort safely" (cloud is empty). Getting that distinction right is the whole problem.

**Estimated time.** 45 minutes.

---

## Problem 6 — Confidence-threshold sweep

**Problem statement.** On one opaque object, sweep the confidence threshold from 0.5 to 0.9 in steps of 0.1. For each threshold, record: number of grasps above threshold, number after NMS, and (if you run the pick) the success rate. Plot grasp-count vs. threshold and discuss the trade-off.

**Acceptance criteria.**

- `notes/week-26/threshold-sweep.md` with the table and a short discussion.
- You identify a sensible operating threshold and justify it (too low → false-positive grasps; too high → no grasps on harder objects).
- You explicitly note that this sweep does *nothing* for the transparent-object case (no points to threshold on) — connecting to Challenge 1.
- Committed.

**Hint.** This is the curve you actually tune in deployment. The interesting part is that lowering the threshold helps on marginal-but-real objects and *cannot* help when the input cloud is empty — which is why the transparent failure is a different category entirely.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Pose round-trip | 40 min |
| 2 — Depth-unit bug | 40 min |
| 3 — Segmentation vs grasp quality | 50 min |
| 4 — Success-rate report (headline) | 1 h 15 min |
| 5 — Fallback never stalls | 45 min |
| 6 — Confidence-threshold sweep | 40 min |
| **Total** | **~5 h 10 min** |

When you've finished all six, push your repo and make sure the `crunchbot_grasp` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 27's imitation policy calls it as a skill. Then take the [quiz](./05-quiz.md) with your notes closed.

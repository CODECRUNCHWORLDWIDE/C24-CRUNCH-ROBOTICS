# Week 26 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 27. Answer key is at the bottom — don't peek.

---

**Q1.** Contact-GraspNet predicts a grasp as a *contact point + approach + baseline + width* instead of a free 6-DOF pose. What is the primary advantage of this representation?

- A) It uses fewer floating-point operations at inference.
- B) Every visible point becomes a dense supervisory signal, the output is constrained to observed geometry, and the network generalizes by learning a local surface function.
- C) It avoids needing a point cloud at all.
- D) It makes the network larger and therefore more accurate.

---

**Q2.** Why is regressing a free 6-DOF gripper pose directly so data-hungry and brittle?

- A) Quaternions are slow to compute.
- B) The output space (`R^3 × SO(3)`) is enormous and mostly empty/inside the object, supervision is sparse, and nothing ties the output to visible geometry, so it can hallucinate mid-air grasps.
- C) `SO(3)` cannot be represented in PyTorch.
- D) Free-pose regression is actually the standard and works fine.

---

**Q3.** The direction head outputs six raw channels (approach + baseline). Before you can build a valid rotation matrix you must:

- A) Multiply them by the width.
- B) Normalize both to unit length and Gram–Schmidt-orthogonalize the baseline against the approach, because the gripper axes are orthonormal and the raw output is neither.
- C) Average them into a single direction.
- D) Nothing — the network guarantees orthonormal output.

---

**Q4.** You reconstruct a grasp's rotation `R` and find `det(R) = -1`. What is wrong?

- A) The width is negative.
- B) The confidence is too low.
- C) Your axis order is left-handed — you likely computed `x × z` instead of `y = z × x`, or stacked the axes in the wrong order.
- D) The point cloud is empty.

---

**Q5.** The grasp center (gripper origin) relative to the predicted contact point is:

- A) Exactly at the contact point.
- B) One full width along the approach direction.
- C) Half a width along the baseline direction (the contact is on one finger; the center is between the fingers).
- D) Half a width along the approach direction.

---

**Q6.** Why run segmentation *before* Contact-GraspNet instead of grasping the whole scene?

- A) It makes inference faster only.
- B) Locally, the gap between two adjacent objects looks like a graspable concavity, so the unsegmented network proposes confident grasps that span two objects and knock them over.
- C) Contact-GraspNet cannot process more than 256 points.
- D) Segmentation is required to load the checkpoint.

---

**Q7.** A RealSense publishes depth as `uint16` millimeters; Contact-GraspNet expects meters. You forget the conversion. What happens?

- A) The node crashes immediately.
- B) Every point is 1000× too far away, the cloud is meters off in front of the camera, and every reconstructed grasp is geometric nonsense — a silent, easy-to-miss bug.
- C) The depth is automatically converted by `cv_bridge`.
- D) Nothing; Contact-GraspNet is unit-agnostic.

---

**Q8.** Contact-GraspNet returns *zero* confident grasps on a clear glass cup. The fastest correct diagnosis is:

- A) The network is undertrained on glass; retrain it.
- B) Lower the confidence threshold to 0.3.
- C) Look at the depth image: the IR passed through the glass and there are no valid points over the object — a **perception** (sensor) failure, fixed upstream with depth completion, not a network failure.
- D) Switch DDS vendors.

---

**Q9.** In the four-bucket failure taxonomy, a confident and reachable-looking grasp for which MoveIt2 returns no plan belongs to which bucket?

- A) Perception.
- B) Prediction.
- C) Planning.
- D) Execution.

---

**Q10.** Why does the grasp node publish poses in the *camera optical frame* and let the pick node transform them at execution time, rather than transforming to `base_link` immediately?

- A) The camera frame is faster to type.
- B) So the tf2 lookup uses the *freshest* transform at execution — critical when the camera is arm-mounted and moving; transforming early bakes in a stale transform.
- C) MoveIt2 only accepts camera-frame poses.
- D) `base_link` does not exist in the tf tree.

---

**Q11.** Why does the pick pipeline check IK feasibility for the *pre-grasp* pose, not just the grasp pose?

- A) The pre-grasp is the only pose that matters.
- B) A grasp can be reachable while the straight-line approach to it passes through the table, a joint limit, or a collision — so both must be feasible.
- C) Pre-grasp IK is faster to compute.
- D) MoveIt2 requires exactly two IK checks.

---

**Q12.** What does the *intervention rate* (fraction of picks using the antipodal fallback) tell you?

- A) Nothing useful.
- B) A high rate means the learned policy rarely sees a clean cloud — your perception is failing often, so fix segmentation/depth, not the network.
- C) It only measures GPU utilization.
- D) A high rate means the network is overconfident.

---

**Q13.** Grasp NMS suppresses a candidate grasp when, relative to a higher-confidence kept grasp, it is:

- A) A different color.
- B) Within a small center distance *and* within a small approach-angle threshold (it is a near-duplicate proposal).
- C) Lower in the point cloud.
- D) Of a different width only.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The contact-point representation gives dense supervision (every point), constrains the output to observed geometry, and generalizes via a local surface function. (Lecture 1 §1.1.)
2. **B** — Huge, mostly-empty output space; sparse supervision; no tie to visible geometry, so it hallucinates. (Lecture 1 §1.)
3. **B** — Normalize and Gram–Schmidt-orthogonalize; the raw head output is neither unit nor orthogonal, and skipping it yields a non-orthonormal `R`. (Lecture 1 §2.2.)
4. **C** — `det(R) = -1` is a left-handed frame; check `y = z × x` and the column order. (Lecture 1 §3.)
5. **C** — Half a width along the *baseline* (closing axis); the contact is on one finger, the center is between them. A sign error here misses the object by a width. (Lecture 1 §3.)
6. **B** — Unsegmented, the inter-object gap looks graspable and the network proposes object-spanning grasps. (Lecture 2 §1.)
7. **B** — Meters vs millimeters; everything is 1000× off and the grasps are nonsense — a classic silent bug. (Lecture 2 §2.)
8. **C** — It is a perception/sensor failure (no points over the transparent object), fixed with depth completion; retraining and threshold-lowering are both wrong. (Lecture 2 §4.1; Challenge 1.)
9. **C** — Planning: confident, plausible grasp but no MoveIt2 plan / infeasible pre-grasp. (Lecture 2 §4.)
10. **B** — Live tf2 at execution time gives the freshest transform; early transform bakes in a stale one, fatal for an arm-mounted camera. (Lecture 2 §3.1.)
11. **B** — A reachable grasp can have an unreachable/colliding approach; you must IK-check both. (Lecture 2 §3.2.)
12. **B** — A high intervention rate signals failing perception, not a bad network — fix the cloud. (Mini-project; Lecture 2 §5.)
13. **B** — Grasp NMS suppresses near-duplicates: close center *and* aligned approach. (Lecture 1 §4.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).

# Week 25 — Quiz

Thirteen questions on grasp mechanics, the friction cone, antipodal grasps, the gripper-frame convention, scoring, and the 2026 landscape. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 26. Answer key is at the bottom — don't peek.

---

**Q1.** What is the difference between force closure and form closure?

- A) They are two names for the same thing.
- B) Force closure resists any wrench *using friction* and needs few contacts; form closure constrains the object *geometrically* with no friction needed but requires many contacts (≥ 4 in 2D, ≥ 7 in 3D).
- C) Form closure needs friction; force closure doesn't.
- D) Force closure only applies to 3-finger hands.

---

**Q2.** A two-finger parallel-jaw gripper achieves which kind of closure on a typical object?

- A) Form closure, because two fingers cage the object.
- B) Force closure — two contacts plus friction plus enough squeeze; it cannot form-close a general object (that needs ≥ 7 frictionless contacts in 3D).
- C) Neither; two fingers can never hold anything.
- D) Both simultaneously.

---

**Q3.** The friction cone at a point contact has half-angle:

- A) `mu` (the friction coefficient directly).
- B) `arctan(mu)` about the inward surface normal.
- C) `arcsin(mu)`.
- D) Always 45 degrees.

---

**Q4.** A water glass (`mu ≈ 0.2`) is harder to grasp than a rubber-coated block (`mu ≈ 0.6`). In friction-cone terms, why?

- A) Glass is heavier.
- B) The lower `mu` gives a narrower friction cone (`arctan(0.2) ≈ 11°` vs `arctan(0.6) ≈ 31°`), so fewer grasp geometries put the closing line inside both cones — fewer feasible grasps and less pose-error tolerance.
- C) Glass reflects light.
- D) `mu` does not affect graspability.

---

**Q5.** The 2D two-contact force-closure test is:

- A) The contacts are on opposite sides of the object's centroid.
- B) The line segment joining the two contact points lies inside *both* friction cones.
- C) The two contacts are exactly 90 degrees apart.
- D) The gripper applies more than 10 N.

---

**Q6.** A grasp is "antipodal" when:

- A) The two contacts are on the same face of the object.
- B) The two contact surface normals are anti-parallel and collinear with the line joining the contacts, so closing squeezes the object rather than pushing it away.
- C) The gripper approaches from directly above.
- D) The object is symmetric.

---

**Q7.** Two contacts are placed on the *same* face of a box, normals both pointing the same way, the closing line perpendicular to the normals. Is this a valid grasp?

- A) Yes, it is a strong antipodal grasp.
- B) No — the closing line is ~90° off the inward normals, far outside the friction cones; the fingers push the object away instead of squeezing it.
- C) Yes, but only for boxes.
- D) Only if `mu > 1.0`.

---

**Q8.** When you build the SE(3) grasp pose, which axis must be perpendicular to the closing (baseline) axis?

- A) None; they are parallel.
- B) The approach axis — the gripper approaches *across* the closing line, not along it; getting this wrong (or mismatching your gripper's URDF tool-frame convention) reaches a pose 90° wrong.
- C) The world z-axis only.
- D) The closing axis is perpendicular to itself.

---

**Q9.** Why does a grasp planner generate many candidates and try the top-K in order, rather than finding "the one best grasp"?

- A) To waste compute.
- B) Because the score is a heuristic not an oracle, reachability prunes the list (the top geometric grasp may be unreachable), and grasps are multimodal (a mug has rim/handle/body grasps) — a ranked list captures all three.
- C) ROS2 requires at least ten candidates.
- D) The first grasp is always wrong.

---

**Q10.** A grasp scores 0.95 antipodal quality but MoveIt2 cannot find a collision-free plan to it. How should it rank against a reachable grasp scoring 0.7?

- A) Above it — antipodal quality is all that matters.
- B) Below it — an unreachable grasp has an effective value of zero; reachability is a gate, so a reachable 0.7 beats an unreachable 0.95.
- C) Tied.
- D) It should crash the planner.

---

**Q11.** What does Contact-GraspNet's contact representation correspond to in this week's material?

- A) Nothing; it is a completely different idea.
- B) The antipodal contact geometry — a contact point on the cloud plus an approach and width — *learned*; the network predicts the same contacts you reasoned about analytically, with an added object prior.
- C) The PID controller.
- D) The TF tree.

---

**Q12.** A grasp planner confidently fails on a transparent water glass. Where is the bug most likely?

- A) In the antipodal scoring math.
- B) Upstream of the grasp planner — the depth camera returns garbage (holes, noise) on transparent/reflective surfaces, so the cloud is wrong and the planner trusts a wrong cloud; no grasp-planner sophistication fixes a sensor that can't see the object.
- C) In the gripper firmware.
- D) In the friction coefficient only.

---

**Q13.** The syllabus says "most grasp failures are pose errors, not policy errors." Which set of mitigations follows directly from that?

- A) Train a bigger network.
- B) Add gripper-width margin (open wider than the contact separation), prefer grasps centered in the friction cones (robust to a few degrees of pose error), and visualize the gripper at the grasp before executing.
- C) Increase the publish rate of `/cmd_vel`.
- D) Use a heavier gripper.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Force closure: friction, few contacts. Form closure: geometric, no friction needed, many contacts (≥ 4 in 2D, ≥ 7 in 3D). (Lecture 1 §1.)
2. **B** — A two-finger gripper does force closure (two contacts + friction + squeeze). It cannot form-close a general object — that needs ≥ 7 frictionless contacts in 3D. (Lecture 1 §1.)
3. **B** — `alpha = arctan(mu)` about the inward surface normal. (Lecture 1 §2.)
4. **B** — Lower `mu` → narrower cone → fewer grasps put the closing line inside both cones, and less tolerance for pose error. (Lecture 1 §2, Exercise 2 mu sweep.)
5. **B** — The line joining the contacts lies inside both friction cones. That *is* the antipodal condition. (Lecture 1 §3.)
6. **B** — Normals anti-parallel and collinear with the joining line; closing squeezes rather than pushes. (Lecture 1 §4.)
7. **B** — Both contacts on the same face: the closing line is ~90° off the inward normals, far outside the cones; the fingers push the object away. (Lecture 1 §3, Exercise 1 Grasp 4.)
8. **B** — The approach axis must be perpendicular to the closing axis; mismatching your gripper's tool-frame convention reaches a pose 90° wrong — the silent failure. (Lecture 2 §1.1.)
9. **B** — The score is a heuristic, reachability prunes, and grasps are multimodal; a ranked top-K captures all three. (Lecture 2 §2.2.)
10. **B** — Reachability is a gate; an unreachable grasp's effective value is zero, so a reachable 0.7 outranks an unreachable 0.95. (Lecture 2 §2.3.)
11. **B** — Contact-GraspNet learns the antipodal contact geometry (contact point + approach + width) with an object prior. It is your analytic geometry, learned — which is why this week comes first. (Lecture 2 §3.2.)
12. **B** — The failure is upstream: the depth sensor can't see transparent/reflective surfaces, so the cloud is wrong and the planner confidently trusts it. A perception failure, not a grasp-math failure. (Lecture 2 §3.4.)
13. **B** — Pose-error mitigations: width margin, grasps centered in the friction cones (robust to a few degrees), and visualize-before-execute. (Lecture 1 §6.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).

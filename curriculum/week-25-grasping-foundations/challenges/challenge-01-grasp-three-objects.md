# Challenge 1 — Grasp Three Objects, and Defend the Top Grasp

**Time estimate:** ~90 minutes.

## Problem statement

Run your antipodal grasp planner on **three different objects** — a cylinder (a can or cup), a box (a cracker-box shape), and an irregular object (a tool, a mug with a handle, or a YCB-style object) — and for each one: generate candidates, rank them with the full score (antipodal quality + width fit + approach sanity + collision-freedom), visualize the top-10 over the cloud, and **write a one-paragraph defense of why the #1 grasp is the #1 grasp** — and what geometry would make it fail.

This mirrors the real skill: you rarely just execute a grasp. You explain — to a teammate, to a reviewer, to yourself at 3 a.m. when the robot keeps dropping the mug — *why* this grasp and not another, in the geometric language of contacts, friction cones, and approach directions.

## The objects and where to get clouds

You can use real RealSense captures, Gz Sim point clouds, or synthetic clouds (the Exercise-2 generator builds a cylinder; extend it for a box and an L-shaped tool). The objects must be genuinely different in grasp character:

- **Cylinder (can/cup).** Antipodal grasps are everywhere — any diameter pass is antipodal. The interesting question is *which* height and *which* approach.
- **Box.** Antipodal grasps exist on opposing faces; the width depends on which pair of faces. A box has a small number of distinct good grasps, not a continuum.
- **Irregular (mug with handle / tool).** Multimodal: the body, the rim, the handle are all candidate grasp regions, with very different scores and reachabilities. This is where ranking earns its keep.

## Your task

For **each of the three objects**, produce:

1. **A ranked top-10** from your planner, each grasp printed as `pose, width, antipodal score, full score, REACHABLE?`.
2. **A visualization** — the cloud with the top grasps drawn (Open3D lines or rviz2 markers; bonus for a gripper mesh at the #1 grasp).
3. **A defense paragraph** answering: Why is #1 the top grasp? Which score term dominated (antipodal quality, width fit, approach, collision)? What is the failure mode that would make it fail (pose error sensitivity, narrow friction margin, approach near the table)?
4. **The runner-up contrast** — name the #2 grasp and say, in one sentence, why it ranked below #1 (it usually differs in exactly one term: a slightly worse approach, a width nearer the gripper edge, a tighter friction-cone margin).

## Acceptance criteria

- [ ] A file `challenge-01-grasp-defense.md` with a section per object, each containing the ranked top-10, the defense paragraph, and the runner-up contrast.
- [ ] A visualization per object (image or screen recording) showing the top grasps over the cloud.
- [ ] For each object, the defense names the **dominant score term** for the #1 grasp and the **specific failure mode** that would break it.
- [ ] For the irregular object, you explicitly identify the **multimodality** — at least two distinct grasp regions (e.g., body vs. handle) appearing in the top-10 — and why one region ranks above the other.
- [ ] Every grasp in the top-10 is within the gripper's width range and passes the friction-cone test (score > 0).
- [ ] Committed to your Week 25 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The subtle error is defending the #1 grasp by its **antipodal score alone**. On a cylinder, dozens of grasps have a near-perfect antipodal score (0.99) — antipodal quality does *not* distinguish them. What distinguishes them is the *other* terms: the approach direction (don't come up through the table), the width (use the gripper's middle range, not its edge), and reachability (the arm can actually get there). If your defense says "#1 is best because it's the most antipodal," and #2 through #10 are equally antipodal, you have not actually explained the ranking — you've named a tie-breaker that isn't breaking the tie. Defend the grasp by the term that *separated* it from its near-equals, not by the term they all share.

## Stretch

- Add a **gripper mesh** (a simple two-finger box model) drawn at the #1 grasp in rviz2, and visually confirm the fingers clear the object and the table. This is the single best view for the pose-is-off failure (Lecture 1 §6).
- For the irregular object, take the #1 grasp and **perturb it** by 3 mm and 5 degrees, re-run the friction-cone test, and report at what perturbation it stops force-closing. This is the "pose-error tolerance" of that grasp, and it is the most honest measure of robustness — a grasp that fails at 3 mm of error is fragile no matter how high its score.
- Run the same three objects with `mu = 0.2` (slick) and `mu = 0.6` (grippy) and report how the candidate counts and the top grasp change. The slick run is the transparent-water-glass-adjacent case: fewer feasible grasps, less pose-error tolerance.

## Why this matters

Next week you deploy Contact-GraspNet and compare its grasps against your heuristic's. That comparison is only meaningful if you can *defend* what your heuristic picked — otherwise "the network is better" is a vibe, not a finding. Every manipulation engineer eventually has to explain why a robot grasps the way it does, usually to someone asking why it just dropped something. The engineer who can point at the friction-cone margin and the approach direction and say "this grasp had 4 mm of pose tolerance and the network's had 12 mm, that's why the network's held" is the one who improves the system instead of re-rolling the dice.

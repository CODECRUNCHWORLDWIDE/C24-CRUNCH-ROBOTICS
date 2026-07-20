# Challenge 1 — Build a Reachability Map of the Arm's Workspace

**Time estimate:** ~90 minutes.

## Problem statement

You are about to promise a manipulation project that "the arm can reach the cup on the left bench." Before you make that promise, you build the evidence: a **reachability map** — a sampled model of which end-effector positions the arm can reach, scored by how *well* it can reach them (manipulability), so you can distinguish the confident interior of the workspace from the unreliable shell near the boundary and the singular zones inside it.

This mirrors the real skill. A workspace is not a sphere with a sharp edge — it has a reachable interior, a fuzzy boundary where IK starts failing, and *holes and thin zones* near singularities where the arm is technically reachable but practically unreliable. A senior engineer knows their arm's envelope cold, including those interior weak spots, because "the planner failed" three weeks into a project is a much more expensive way to learn it.

You will build the map two ways — **forward** (sample joint space, run FK, see where the hand lands) and **inverse** (sample task space, run IK, see what's reachable) — and reconcile them, because they answer subtly different questions.

## The two approaches

**Forward (joint-space sampling).** Sample random joint vectors within the arm's limits, run your FK from Exercise 1 on each, and record the tip position and the manipulability at that configuration. This gives you the *true* reachable set (everything FK produces is reachable by construction) and the manipulability *texture* across it — but it samples task space unevenly (the wrist clusters poses).

**Inverse (task-space sampling).** Lay a grid over the task space (a 3D box around the arm), and for each grid cell ask IK "can you reach a pose here?" Use your damped-least-squares solver from Exercise 2 (or MoveIt2's `/compute_ik`). This gives an even task-space map and directly answers "is *this* point reachable" — but it inherits your IK solver's failure modes (a point your seed-dependent solver missed may still be reachable).

The reconciliation is the insight: where the two disagree is exactly where IK is *unreliable*, which is near singularities and the boundary.

## Your task

Build a reachability map of your arm (UR5e, MyCobot, or the planar 3R from Exercise 2 if you want a fast 2D version to start). Produce:

1. **A forward map.** Sample at least 50,000 joint vectors within limits, run FK, and bin the tip positions into a voxel grid (or a 2D grid for the planar arm). For each occupied voxel, record the *maximum manipulability* seen there.
2. **An inverse map.** Grid the task space, run IK at each cell from a fixed seed, and record success/failure and the manipulability at the solution.
3. **The reconciliation.** Overlay the two. Identify cells that are reachable in the forward map but where IK *failed* in the inverse map — these are your unreliable zones. Explain each in terms of singularities (Lecture 1 §5) or seed-dependence (Lecture 2 §3).
4. **A validation.** For 100 task-space points your map calls reachable and 100 it calls unreachable, query MoveIt2's `/compute_ik` and report the agreement rate. Your map should agree with MoveIt2 well above 90% on the confident interior; the disagreements should cluster exactly where you predicted (boundary, singular zones).

## Acceptance criteria

- [ ] A script `reachability_map.py` that produces both maps and saves a visualization (a matplotlib 2D heatmap for the planar arm, or an RViz `MarkerArray` / Open3D voxel cloud colored by manipulability for the 6-DOF arm).
- [ ] A `challenge-01-writeup.md` containing:
  - The reachable-volume estimate (or area, for the planar arm) and the max-reach radius, compared to the arm's published reach (~0.85 m for the UR5e).
  - A figure of the manipulability texture — the high-manipulability core and the low-manipulability shell are visibly distinct.
  - At least **two** identified unreliable zones, each explained as a specific singularity (shoulder / elbow / wrist) or a seed-dependence artifact, with the joint configuration that produces it.
  - The MoveIt2 `/compute_ik` validation table: agreement rate on reachable points, agreement rate on unreachable points, and a one-paragraph account of where and why they disagree.
- [ ] You used your **own** FK (Exercise 1) and IK (Exercise 2) to build the map — not MoveIt2 — and used MoveIt2 only to *validate*. The point is that you can reason about reachability from first principles, then check yourself.
- [ ] Committed to your Week 23 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The seductive mistake is to build *only* the inverse map and call it the reachability map. But a single-seed IK solver will report "unreachable" for plenty of points that are perfectly reachable from a *different* seed (the up-to-8-solutions problem from Lecture 2 §1) — so your inverse map will have false holes that are really just "my seed didn't find the branch that reaches here." That is why you build the forward map too: everything in the forward map is reachable *by construction*, so any forward-reachable point your inverse map marks unreachable is a solver artifact, not a true hole. Confusing a solver artifact for a workspace hole is the exact mistake that makes a team redesign a perfectly capable cell. Distinguish them.

## Stretch

- **Reachability for a 6D pose, not just a 3D point.** A point being reachable says nothing about whether it's reachable *with the orientation you need*. Re-run the inverse map demanding a fixed end-effector orientation (e.g. gripper pointing down, for a top grasp) and watch the reachable set shrink dramatically. This is the map that actually matters for grasping — and it's the bridge to Week 25.
- **Manipulability-aware goal selection.** Given a target point and a tolerance, write a function that returns the *most manipulable* reachable pose within tolerance — the configuration furthest from any singularity. This is exactly the trick a production manipulation stack uses to pick robust grasp approaches.
- **Compare KDL vs TRAC-IK reachability.** Swap MoveIt2's kinematics plugin (README stretch goal) and re-run the inverse map. TRAC-IK will report more points reachable than KDL — quantify the difference and you've measured, on your own arm, why the plugin choice matters.

## Why this matters

In Week 24 your composed robot drives to a table and the arm reaches a pose — and the milestone reviewer's first question is "how did you know that pose was reachable before you sent it?" "I tried it and it worked" is a junior answer. "Here is the reachability map; the pose sits in the high-manipulability interior, 0.62 m from the base, well inside the 0.85 m envelope and far from any singular zone" is the answer of an engineer who will be trusted to size a robot cell before a single part is ordered. Every manipulation project eventually needs this map. Build it once, here, on an arm you understand from the screws up.

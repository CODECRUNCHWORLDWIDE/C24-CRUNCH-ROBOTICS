# Mini-Project — `crunch_grasp`: An Analytic Grasp Planner You Can Defend

> Build a reusable analytic grasp planner that takes a tabletop point cloud and emits a **ranked list of reachable grasps** — each a pose, a width, and a confidence in a named frame — visualizes the top-10 in rviz2 with gripper-mesh overlays, and verifies the best grasp is reachable by your Week-23 MoveIt2 arm. No learned model, no GPU: pure geometry, fully explainable, and the sanity gate your learned grasping (Week 26) will be checked against.

This is the artifact that turns this week's geometry into a tool. After this week, "where do I grasp this object?" is a question your code answers with a *ranked, defensible, reachable* list — not a guess, not a magic number from a network you can't interrogate. When Contact-GraspNet arrives next week, this planner is what you compare it to, and the only way that comparison is meaningful is if your analytic grasps are correct and you can defend them.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This planner becomes the **analytic fallback and sanity gate** in your Phase 4 manipulation stack. In Week 26 you compare its grasps against Contact-GraspNet's; in the capstone's "learned policy with a classical fallback" pattern (Week 32), an analytic grasp planner like this *is* the classical fallback. Build it well now; you'll lean on it for the rest of Phase 4.

---

## What you will build

A small ament-python package `crunch_grasp` with three deliverables:

1. **`crunch_grasp/planner.py`** — the analytic planner. Cloud in (object-segmented), ranked reachable grasps out. It samples antipodal candidates (Lecture 1), scores them with the full heuristic (Lecture 2 §2.1), builds the gripper-frame pose (Lecture 2 §1), checks reachability via MoveIt2, and emits a ranked list.
2. **`crunch_grasp/grasp_markers.py`** — a node/helper that publishes the top-K grasps as a `visualization_msgs/MarkerArray` (approach arrows, baseline lines, and a gripper-mesh overlay at the #1 grasp) for rviz2 — the view that makes the pose-is-off failure visible.
3. **A demo + a MoveIt2 bridge** — a node that takes a cloud (a synthetic cylinder/box, a Gz Sim cloud, or a RealSense capture), runs the planner, publishes the markers, and hands the top reachable grasp to MoveIt2 as a `PoseStamped` / `moveit_msgs/Grasp` for a plan-and-execute.

By the end you have a public repo of ~300–400 lines of Python that any future Phase-4 package can `from crunch_grasp.planner import GraspPlanner` and get a ranked, reachable, explainable grasp set.

---

## Why analytic first, learned second

You could skip straight to Contact-GraspNet next week. Don't — not without this. The analytic planner gives you:

- **Explainability.** Every grasp's score decomposes into antipodal quality, width fit, approach sanity, and collision-freedom. When a grasp ranks #1, you can say *why*. A network's confidence number cannot.
- **A sanity gate.** Next week, before you execute a Contact-GraspNet grasp, you can run your `antipodal_score` on its predicted contacts to *verify* it sits inside the friction cones. A learned grasp that fails your analytic check is a red flag worth catching before the fingers move.
- **A fallback.** When the learned planner has no confident proposal (a transparent object, an out-of-distribution shape), the analytic planner still produces *something* — the Week-32 classical fallback, prototyped here.

The learned planner adds the object prior and the clutter handling the heuristic lacks (Lecture 2 §3.3). The two are complementary. You build the explainable one first so the network has something to be measured against.

---

## Package layout

```
crunch_grasp/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_grasp
├── crunch_grasp/
│   ├── __init__.py
│   ├── geometry.py          # friction cone, antipodal score, gripper-frame pose
│   ├── planner.py           # sample -> score -> rank -> reachability (the core)
│   ├── grasp_markers.py     # MarkerArray publisher for rviz2
│   └── moveit_bridge.py     # hand the top grasp to MoveIt2 as a Grasp/PoseStamped
├── launch/
│   └── grasp_demo.launch.py # cloud source + planner + markers + (optional) execute
└── test/
    ├── test_geometry.py     # unit tests: friction cone, antipodal score, pose build
    └── test_planner.py      # unit tests: ranking, width filter, reachability pruning
```

---

## Deliverable 1 — `planner.py` (the core)

The heart of the project. It must:

- **Sample** antipodal candidate pairs on the object cloud (Lecture 1 §5): downsample, estimate + orient normals, pair contacts roughly along the inward normal, apply the friction-cone test and the gripper-width filter.
- **Score** each candidate with the full heuristic (Lecture 2 §2.1): antipodal quality (dominant), width fit, approach sanity (penalize approaching into the table), and a collision-freedom gate (a grasp whose gripper geometry intersects the table or another object scores 0).
- **Build the pose** for each candidate in the gripper-frame convention (Lecture 2 §1): grasp point (midpoint), closing axis (the A-B line), a sane approach axis, assembled into a rotation matrix matching *your gripper's URDF tool-frame convention*, plus a standoff pre-grasp pose.
- **Check reachability** against MoveIt2 (Lecture 2 §2.3): walk the score-sorted list, ask MoveIt2 to *plan* (not execute) to each grasp, and prune the unreachable ones — so the final ranking reflects what the arm can do.
- **Emit** a ranked list of `Grasp` objects, each carrying the pose, the width, the confidence (the score), the frame, and a `reachable` flag — the "pose, width, confidence, frame, REACHABLE" promise line.

The function signature and the promise-line print are the contract:

```python
class GraspPlanner:
    def plan(self, object_cloud, frame_id: str) -> list:
        """Cloud in (object-segmented, in frame_id), ranked reachable grasps out.
        Each result: (pose_stamped, width, confidence, reachable)."""
        ...

# Every emitted grasp prints as exactly: pose, width, confidence, frame, REACHABLE.
#   grasp #1  pose=(0.412, -0.085, 0.231) quat=(0.00, 0.71, 0.00, 0.71)
#             width=0.058 m  conf=0.91  frame=base_link  REACHABLE
```

A grasp missing any of the five fields is not a grasp; it's a wish. The planner refuses to emit an incomplete grasp.

---

## Deliverable 2 — `grasp_markers.py` (the view that catches pose errors)

A helper that publishes the top-K grasps as a `visualization_msgs/MarkerArray`:

- An **arrow** per grasp along the approach axis (so you see how the gripper comes in).
- A **line** per grasp along the closing/baseline axis between the two contacts (so you see what it squeezes).
- A **gripper-mesh overlay** at the #1 grasp — your gripper's collision geometry (even a simple two-finger box) posed at the grasp — so you can *see* whether the fingers clear the object and the table.

This is the single best debugging view for the pose-is-off failure (Lecture 1 §6). A grasp that looks wrong on screen is wrong, whatever the score says. The markers are color-coded by rank (best = green, worst of top-K = red) so the ranking is visible at a glance.

---

## Deliverable 3 — the demo + MoveIt2 bridge

A `launch/grasp_demo.launch.py` that:

1. Sources a cloud — a synthetic cylinder/box (built in), a Gz Sim depth cloud, or a RealSense capture (with the table RANSAC'd out and the object clustered, Week 15).
2. Runs the planner and publishes the markers.
3. Optionally hands the **top reachable grasp** to MoveIt2 via `moveit_bridge.py` as a `moveit_msgs/Grasp` (grasp pose + pre-grasp approach + post-grasp retreat + gripper posture) for a plan-and-execute pick — under the Week-24 composed graph and safety leash.

The bridge must use the *cloud's* timestamp when transforming the grasp into the planning frame (the Week 5 stamping lesson), and it must add the gripper-width margin (open wider than the contact separation) before approach (the Lecture 1 §6 mitigation).

---

## Rules

- **You may** read the ROS2 / Open3D / MoveIt2 docs, the GPD and Contact-GraspNet code (for the grasp representation), and your own exercise code.
- **You must** build the grasp pose in *your gripper's* URDF tool-frame convention. A grasp pose 90° off because you used the lecture's default convention instead of your gripper's fails the demo.
- **You must** make the collision-freedom check a *hard gate* — a colliding grasp scores ~0 and never reaches the top-10. A planner that ranks a table-approaching grasp #1 has not internalized Lecture 2 §2.1.
- **You must** prune unreachable grasps from the ranking via a MoveIt2 *plan* (not execute) check; the final list contains only reachable grasps (or flags reachability per grasp).
- **You must not** depend on any learned grasp model — that is Week 26. This planner is analytic, explainable, and self-contained.
- Python 3.12 (Ubuntu 24.04), `rclpy` on Jazzy, Open3D, NumPy, SciPy.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-25-crunch-grasp-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_grasp` succeeds with no warnings.
- [ ] `planner.py` emits a ranked list where every grasp prints the full promise line (pose, width, confidence, frame, REACHABLE).
- [ ] Every emitted grasp passes the friction-cone test (score > 0) and is within the gripper's width range; colliding and unreachable grasps are gated/pruned out.
- [ ] `grasp_markers.py` publishes a `MarkerArray` that renders the top-10 in rviz2 with approach arrows, baseline lines, and a gripper-mesh overlay at #1.
- [ ] `colcon test --packages-select crunch_grasp` passes, with at least:
  - `test_geometry.py`: friction-cone test, antipodal score (including the outside-cone → 0 case), and the orthonormal/right-handed grasp-pose construction.
  - `test_planner.py`: ranking order, the width filter, and that an unreachable or colliding grasp is pruned.
- [ ] The demo runs the planner on at least two objects (a cylinder and a box) and visualizes the ranked grasps.
- [ ] The top reachable grasp is handed to MoveIt2 and the arm plans to it (execute is a bonus, plan is required) — proving the grasp is reachable from the Week-23 setup.
- [ ] A `README.md` with the score breakdown, the run commands, and a paragraph defending why the top grasp on the cylinder is the top grasp (in geometric terms).
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Geometry correctness** | 25 | Friction-cone test, antipodal score, and gripper-frame pose all correct; the pose matches the gripper's URDF convention; tests green. |
| **Scoring & ranking** | 20 | Full heuristic (antipodal + width + approach + collision gate); collision is a hard gate; ranking is sensible and defensible. |
| **Reachability** | 15 | Unreachable grasps pruned via a MoveIt2 plan check; the final list reflects what the arm can do. |
| **The promise line** | 10 | Every grasp emits pose, width, confidence, frame, REACHABLE; no incomplete grasps. |
| **Visualization** | 15 | MarkerArray renders top-10 in rviz2 with approach arrows, baseline lines, and a gripper-mesh overlay at #1. |
| **MoveIt2 integration** | 10 | Top grasp handed over and plannable; correct frame transform with the cloud's stamp; width margin added. |
| **Docs & hygiene** | 5 | Clear README with the top-grasp defense; clean repo (no `build/`/`install/` checked in). |

**90+** is portfolio-grade and ready to be the Week-26 comparison baseline and the Week-32 classical fallback. **70–89** works but has a soft collision gate, a missing reachability prune, or an incomplete promise line. **Below 70** means the geometry or the ranking isn't trustworthy — fix that first, because next week's comparison against the learned planner is only meaningful if your analytic grasps are correct.

---

## Stretch goals

- **Pose-error robustness ranking.** For each top grasp, compute its friction-cone tolerance (the max pose perturbation it survives, from homework P1) and add it as a ranking term — prefer grasps robust to a few millimeters and degrees of error, not just high-scoring ones. This is the single best predictor of real-world success.
- **Clutter handling.** Run on a two-object scene and add a collision check against the *other* object, not just the table. Watch the heuristic struggle where Contact-GraspNet (trained on clutter) would do better — and note exactly where, for next week.
- **The analytic verify-gate.** Write the function you'll use in Week 26: given a grasp pose from *any* source (your planner or Contact-GraspNet), find the nearest cloud contacts and run `antipodal_score` to verify it sits inside the friction cones. This is your learned-grasp sanity gate.
- **CI job.** Add a GitHub Actions workflow that builds the package and runs `colcon test` (the geometry and ranking tests need no GPU or robot) in a headless container.

---

## Common pitfalls (read before you start, re-read when stuck)

These are the failures that eat the most hours on this planner. Knowing them in advance is half the cure.

- **The gripper reaches a pose 90° wrong.** You built the orientation in the lecture's default convention, not *your gripper's* URDF tool-frame convention. The fingers sweep sideways through the object. Check the URDF tool frame and align your column assignment to it.
- **Every candidate scores 0.** Your normals are flipped (pointing into the object instead of out), so the antipodal test compares against the wrong cone. Run `orient_normals_consistent_tangent_plane` and verify the normals point away from the interior.
- **The top grasp approaches up through the table.** Your scorer lacks the approach-sanity term or the collision gate. A high antipodal score with a table-approaching pose ranks #1 only if you forgot the gate. Add it; it is a *hard* gate, not a soft weight.
- **The top grasp is unreachable.** You ranked by geometry alone and never checked reachability. MoveIt2 can't plan to it. Prune unreachable grasps via a plan (not execute) check, so the ranking reflects what the arm can do.
- **The grasp lands 5 cm from the object.** A frame or stamp bug — you transformed the grasp with `now()` instead of the cloud's timestamp while the arm was moving, or the grasp is in the camera frame and you handed it over as if it were in the planning frame.
- **The fingers knock the object over before closing.** No width margin — you opened to exactly the contact separation, so the fingers brushed the object on approach. Open wider than the contact width.
- **A "high-confidence" grasp fails anyway.** The score is a heuristic, not an oracle; the term it didn't capture (pose-error tolerance, a bad cloud on a reflective object) is the one that bit you. Fall through to the next ranked grasp.
- **The cloud has the table in it.** You skipped the RANSAC table-removal and clustering, so the planner grasps the table. Segment the object first (Week 15).

Each pitfall maps to a lecture section. When a grasp fails, *visualize the gripper at the grasp* first — most of these are visible on screen before you read a line of code.

## How this connects to the rest of C24

- **Week 26 (Contact-GraspNet)** deploys a learned planner and compares its grasps against *this* planner's on the same objects — the comparison only works because your analytic grasps are correct and defensible.
- **Week 32 (learned policy + classical fallback)** uses an analytic grasp planner like this as the classical fallback when the learned policy is rejected — your `crunch_grasp` is that fallback, built seven weeks early.
- **The capstone** grasps a perceived object under a language instruction; the VLA selects *which* object, and a grasp planner (learned, with this as the gate/fallback) selects *how* to grasp it.

## Definition of done (the one-line self-check)

Before you call the planner finished, confirm each in one line:

- **Every emitted grasp** prints the full promise line: pose, width, confidence, frame, REACHABLE.
- **Every emitted grasp** passes the friction-cone test (score > 0) and fits the gripper width.
- **Colliding grasps** score ~0 (the hard gate works); a table-approaching grasp is never #1.
- **Unreachable grasps** are pruned via a MoveIt2 plan check; the final list reflects what the arm can do.
- **The pose** matches your gripper's URDF tool-frame convention (verified in MoveIt2, not just on paper).
- **The markers** render the top-10 in rviz2 with approach arrows, baseline lines, and a gripper mesh at #1.
- **The top grasp** transforms into the planning frame with the cloud's stamp and is plannable by MoveIt2.
- **The tests** (`test_geometry.py`, `test_planner.py`) are green.

If any line is "no," that part isn't done. The README's top-grasp defense is the proof you understand *why* #1 is #1 — write it in geometric terms, not "it scored highest."

When you've finished, push the repo and take the [quiz](../05-quiz.md).

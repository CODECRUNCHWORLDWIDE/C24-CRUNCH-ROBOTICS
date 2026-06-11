# Lecture 2 — The Gripper-Frame Convention, Scoring, and the 2026 Landscape

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can turn an antipodal contact pair into an SE(3) grasp pose in a gripper-frame convention, transform it into the arm's planning frame, score and rank candidates by more than antipodal quality, check reachability, and situate your heuristic against the grasp datasets and learned planners that dominate 2026.

Lecture 1 found *where to grasp* — the antipodal contact pairs. This lecture turns that into *a pose the arm can execute*, ranks the candidates, and tells you where the heuristic stops and the learned planners begin. The through-line:

> **A grasp the arm can't reach is not a grasp, and a grasp you can't rank is not a plan. The gripper-frame convention turns contacts into a reachable pose; the score turns a pile of candidates into an ordered list you try top-down.**

---

## Part 1 — The gripper-frame convention: contacts to a pose

An antipodal pair is two points and a width. MoveIt2 wants a `geometry_msgs/PoseStamped` — a position and an orientation in a named frame. The bridge is the **gripper-frame convention**: a coordinate frame attached to the grasp, from which the full SE(3) pose is built.

### 1.1 The three things a grasp pose encodes

A parallel-jaw grasp pose encodes three geometric facts, and you build the orientation from three axes:

- **The grasp point** — the origin of the grasp frame, the point the gripper closes *around*. The natural choice is the midpoint of the antipodal pair: `p = (p_A + p_B) / 2`.
- **The closing (baseline) axis** — the direction the two fingers close along. For an antipodal grasp this is the line joining the contacts: `b = (p_B - p_A) / ||p_B - p_A||`. The fingers sit on either side of `p`, separated by the width, along `b`.
- **The approach axis** — the direction the gripper moves in to reach the grasp. It must be (a) perpendicular to the closing axis (the gripper approaches *across* the closing line, not along it) and (b) not pointing up through the table or into the object's bulk. A sane default: the component of the object-surface-average-inward direction (or the camera ray, or world-down for a top-down grasp) that is orthogonal to `b`.

From `b` (closing) and `a` (approach), the third axis is the cross product, and the three orthonormal axes are the columns of the rotation matrix:

```python
import numpy as np

def grasp_orientation(closing_axis, approach_axis) -> np.ndarray:
    """Build a 3x3 rotation matrix (gripper frame) from the closing and approach
    axes. Convention here: x = approach, y = closing (baseline), z = x cross y.
    Adjust the column assignment to YOUR gripper's URDF tool-frame convention."""
    a = np.asarray(approach_axis, float)
    a = a / (np.linalg.norm(a) + 1e-12)
    b = np.asarray(closing_axis, float)
    # Make the closing axis orthogonal to the approach axis (Gram-Schmidt).
    b = b - np.dot(b, a) * a
    b = b / (np.linalg.norm(b) + 1e-12)
    c = np.cross(a, b)                      # third axis, right-handed
    R = np.column_stack([a, b, c])          # columns are the gripper-frame axes
    return R
```

> **The convention is gripper-specific, and getting it wrong is the silent failure.** Which axis is "approach" depends on *your* gripper's tool frame in its URDF — some grippers approach along +z (top-down classic), some along +x. The orientation you build must match the frame MoveIt2 plans the tool to. If you build a pose with the approach along +z but your gripper's tool frame approaches along +x, the arm will dutifully plan to an orientation 90° wrong and the fingers will sweep sideways through the object. Check your gripper's URDF tool frame *first*, and align the column assignment in `grasp_orientation` to it. REP 103's x-forward/y-left/z-up convention is the reference, but your URDF is the ground truth.

### 1.2 Assembling the pose and the standoff

The grasp pose is the position `p` plus the orientation `R`, as a quaternion. But you almost never command the gripper straight to the contact pose — you command a **pre-grasp / standoff pose** first, offset back along the approach axis, then approach the final pose, then close. The standoff gives the planner room and gives the approach a clean straight-line final segment.

```python
from scipy.spatial.transform import Rotation

def build_grasp_pose(pA, pB, approach_axis, standoff=0.10):
    """Return (grasp_pose, pregrasp_pose) as (position, quaternion_xyzw) tuples.
    standoff: meters back along the approach axis for the pre-grasp pose."""
    p = (np.asarray(pA) + np.asarray(pB)) / 2.0
    b = np.asarray(pB) - np.asarray(pA)
    R = grasp_orientation(closing_axis=b, approach_axis=approach_axis)
    quat = Rotation.from_matrix(R).as_quat()        # (x, y, z, w)
    approach = R[:, 0]                              # column 0 is the approach axis here
    pregrasp = p - approach * standoff              # back off along approach
    return (p, quat), (pregrasp, quat)
```

### 1.3 Transforming into the planning frame

The grasp you computed lives in the frame the *cloud* was captured in — typically the camera frame, or a sensor frame. MoveIt2 plans in the arm's planning frame (often `base_link` or `world`). You must transform the grasp pose through the TF tree before you hand it over, and you must do it *honestly* — using the transform at the cloud's timestamp, not `now()`, exactly the Week 5 stamping lesson:

```python
# Transform the grasp PoseStamped from the camera frame into the planning frame.
# (rclpy + tf2_ros; the lookup uses the cloud's stamp, not now().)
import tf2_geometry_msgs   # registers PoseStamped with the tf2 buffer
from geometry_msgs.msg import PoseStamped

def to_planning_frame(tf_buffer, grasp_pose_cam: PoseStamped,
                      planning_frame="base_link") -> PoseStamped:
    # grasp_pose_cam.header.frame_id is the camera frame; .stamp is the cloud's stamp.
    return tf_buffer.transform(grasp_pose_cam, planning_frame,
                               timeout=rclpy.duration.Duration(seconds=0.5))
```

A grasp pose in the wrong frame, or transformed with the wrong timestamp while the arm is moving, is a pose error — and pose errors are where grasps fail (Lecture 1 §6). The frame and the stamp are not bookkeeping; they are the difference between the fingers landing on the object and landing 5 cm away.

---

## Part 2 — Scoring, ranking, and reachability

Lecture 1's `antipodal_score` is the *first* term. A deployable planner combines several terms into one rank, because antipodal quality alone will happily rank a grasp that approaches up through the table as #1.

### 2.1 The full heuristic score

A practical grasp score is a weighted combination of terms, each in `[0, 1]`:

```python
def grasp_score(cand, approach_axis, gripper_max_width, table_normal,
                collision_fn) -> float:
    """Combine antipodal quality, width fit, approach sanity, and collision-freedom.
    cand = (pA, pB, antipodal, width); collision_fn returns True if the gripper at
    this grasp collides with the table/scene."""
    pA, pB, antipodal, width = cand

    # 1. Antipodal quality (Lecture 1): how centered in the friction cones.
    s_anti = antipodal

    # 2. Width fit: prefer grasps that use the gripper's middle range, not its edges.
    #    A grasp at the very max width has no closing margin; one at min is fiddly.
    frac = width / gripper_max_width
    s_width = 1.0 - abs(frac - 0.6) / 0.6          # peaks around 60% of max opening
    s_width = max(0.0, s_width)

    # 3. Approach sanity: penalize approaching INTO the table (approach aligned with
    #    the table's up-normal means coming from below; we want from above/side).
    a = np.asarray(approach_axis) / (np.linalg.norm(approach_axis) + 1e-12)
    up = np.asarray(table_normal) / (np.linalg.norm(table_normal) + 1e-12)
    # approach should oppose 'up' (come down) or be horizontal; reward -dot.
    s_approach = float(np.clip(0.5 - 0.5 * np.dot(a, up), 0.0, 1.0))

    # 4. Collision-freedom: the gripper geometry at this grasp must not hit the scene.
    s_collision = 0.0 if collision_fn(pA, pB, approach_axis) else 1.0

    # Weighted sum. Collision is a hard gate (a colliding grasp scores ~0).
    return s_collision * (0.5 * s_anti + 0.2 * s_width + 0.3 * s_approach)
```

The weights are a starting point, not gospel — tune them on your gripper and objects. The *structure* is the lesson: antipodal quality dominates (it is the force-closure guarantee), width and approach shape the ranking, and collision is a hard gate that zeroes any grasp the gripper can't physically execute.

### 2.2 Why you rank and try top-K, not "the one"

A beginner finds "the best grasp" and executes it. A senior engineer generates *hundreds* of candidates, ranks them, and tries the **top-K** in order, falling through to the next when one fails. Three reasons:

- **The score is a heuristic, not an oracle.** The #1 grasp by score is not guaranteed to succeed; it is the most likely. If it fails (the object shifts, the cloud was slightly wrong), #2 is right there.
- **Reachability prunes the list.** The #1 grasp by geometry may be unreachable by the arm (outside the workspace, or MoveIt2 can't find a collision-free plan to it). You don't discover that until you check — so you keep a ranked list and try down it.
- **Grasps are multimodal.** A mug can be grasped by the rim, the handle, or the body — several distinct, all-valid grasps. A ranked list captures this; "the one grasp" throws away the alternatives that save you when the first is blocked.

### 2.3 Reachability: the grasp the arm can't reach is no grasp

A grasp's geometric score says nothing about whether the arm can get there. Before you commit a grasp, check reachability — and prune the unreachable ones from the ranking:

```python
# Reachability check: can MoveIt2 plan to the grasp pose? (sketch)
def is_reachable(move_group, grasp_pose_stamped) -> bool:
    """Ask MoveIt2 for a plan to the grasp pose WITHOUT executing. A grasp the
    planner can't reach (workspace limit, no collision-free path) is pruned."""
    move_group.set_pose_target(grasp_pose_stamped)
    plan_result = move_group.plan()                # plan only, do not execute
    return plan_result.success
```

In the mini-project you fold this into the ranking: compute the geometric score for all candidates, sort, then walk the sorted list checking reachability, and emit the ranked *reachable* grasps. A grasp that scores 0.95 but is unreachable ranks below a reachable 0.7 — because an unreachable grasp has an effective value of zero. This is the `REACHABLE` flag in the week's "pose, width, confidence, frame, REACHABLE" promise line.

---

## Part 3 — The 2026 landscape: datasets and learned planners

Your analytic heuristic is correct, explainable, and needs no model. So why does the field train networks? Because a heuristic has no *prior*. It knows the friction-cone geometry but nothing about *which* grasps tend to succeed for *this kind of object*. The learned planners add exactly that prior, trained on enormous grasp datasets. Knowing the landscape tells you what the data buys and where your heuristic still wins.

### 3.1 The datasets

- **ACRONYM** (Eppner et al., 2021) — 17.7 million parallel-jaw grasps on ~8.8k ShapeNet objects, each grasp *physically simulated* and labeled success/failure. It is the training data for Contact-GraspNet. The key idea: simulate grasps at scale, label them by whether the object stayed in the gripper through a shaking test, and learn from millions of labeled attempts. Simulation lets you label far more grasps than you could ever execute physically.
- **GraspNet-1Billion** (Fang et al., CVPR 2020) — a *billion* grasp poses across ~97k images of real cluttered scenes, with a standardized evaluation API and a dense per-scene grasp annotation. It is the benchmark the field reports on, and it captures *clutter* — grasps in scenes with multiple objects touching, which a single-object heuristic doesn't model.
- **YCB** — not a grasp dataset but the standard physical *objects* (the red mug, the cracker box, the power drill) that grasp papers benchmark on, so results are comparable across labs. When you sanity-check your heuristic, grasp a YCB-style mug.

### 3.2 The learned planners

- **Contact-GraspNet** (Sundermeyer et al., ICRA 2021) — the planner you deploy next week. Its insight is to represent a 6-DoF grasp by its *contact point* on the observed cloud plus an orientation and width — which is *exactly the antipodal contact representation of this week, learned*. The network takes a segmented point cloud and predicts, per point, a grasp contact, an approach, and a confidence. It is "segmentation + geometry + a small network," and the geometry it predicts is the geometry you built by hand. That is precisely why this week comes first: Contact-GraspNet is not magic, it is your antipodal sampler with a learned prior about good contacts.
- **GPD** (ten Pas et al.) — the influential *pre*-deep-learning sampler: generate antipodal-style candidates on the cloud (like your mini-project), then score each with a small CNN trained on grasp success. It is the missing link between your heuristic and Contact-GraspNet — same candidate generation, learned scoring.
- **Dex-Net** (Mahler et al.) — the grasp-quality-CNN lineage; it frames grasp robustness as a learned metric over a synthetic dataset of grasps with analytically computed quality. Read it for the "analytic quality vs. learned quality" contrast.

### 3.3 What the data buys, and where the heuristic wins

| Dimension | Analytic heuristic (this week) | Learned planner (Week 26) |
|---|---|---|
| Object prior | None — pure geometry | Strong — learned which grasps succeed per object class |
| Clutter | Poorly modeled (single-object) | Modeled (trained on cluttered scenes) |
| Transparent/reflective objects | Fails — the cloud is wrong, the heuristic trusts it | Also struggles, but some models learn to compensate |
| Multimodality | Captures it via ranked candidates | Captures it natively (predicts a distribution) |
| Explainability | Total — every score term is legible | Low — a confidence number, not a reason |
| Compute | CPU, milliseconds, no model | GPU, a trained checkpoint |
| Failure diagnosis | "the pose is off by X, here's why" | "the confidence was high but it missed" — harder to debug |

The honest summary a senior engineer gives in 2026: **"Use the learned planner for the prior and the clutter; keep the analytic check as a sanity gate and a fallback."** Contact-GraspNet proposes a grasp; your antipodal check can *verify* it sits inside the friction cones before you execute, and your heuristic can *fall back* when the network has no confident proposal. The two are complementary, not competitors — which is exactly why you learn the geometry first and the network second.

### 3.3.1 The analytic planner as a verification gate for the learned one

The most useful thing your analytic planner does next week is not *propose* grasps — it is *verify* the learned planner's grasps. When Contact-GraspNet emits a grasp pose with confidence 0.9, that confidence is a learned number with no geometric guarantee behind it. Your analytic check can add the guarantee cheaply:

- Take the network's predicted grasp pose and width.
- Find the cloud points the closed gripper's fingers would contact (the points nearest each finger's contact patch).
- Estimate the normals at those points and run `antipodal_score` on the implied contact pair.
- If the score is 0 (the contacts fall outside the friction cones), the network's "0.9 confidence" grasp is geometrically *infeasible* — a red flag worth catching before the fingers move.

This verify-gate is the single most valuable composition of analytic and learned grasping: the network brings the object prior and the clutter handling; your analytic check brings the geometric guarantee the network lacks. A learned grasp that passes the analytic check is one you can execute with confidence; one that fails it is one to skip in favor of the next-ranked candidate. This is why the mini-project's stretch goal is exactly this gate — it is what you wire into Week 26, and it is the embodiment of "use the learned planner for the prior, keep the analytic check as a sanity gate."

### 3.3.2 Multimodality, and why a distribution beats a single best grasp

A subtle advantage of learned planners worth understanding now: they natively represent grasp *multimodality*. A mug affords several genuinely different grasps — the rim, the handle, the body — and they are not points on a continuum; they are distinct modes. A planner that predicts a single "best" grasp must collapse this multimodality to one choice, and if that choice is blocked (the handle faces a wall), it has nothing. A planner that predicts a *distribution* over grasps keeps all the modes, so when one is blocked, another is available.

Your analytic heuristic captures multimodality *implicitly* through the ranked candidate list — the rim grasps and handle grasps both appear in the top-K, at different scores. The learned planners (and especially the Diffusion-Policy-style action models you meet in Week 29) capture it *explicitly* as a learned distribution. Either way, the lesson is the same one from §2.2: you want a ranked list or a distribution, not a single grasp, because real objects afford many grasps and the value of the alternatives is exactly that they survive when the top choice is blocked. A grasp planner that returns one pose is brittle; one that returns a ranked, multimodal set is robust.

### 3.4 The failure mode the data can't fully fix

One failure deserves its own mention because it bites learned planners hardest and it is *not* a geometry problem: **transparent and reflective objects.** A depth camera returns garbage (holes, wild noise) on glass, clear plastic, and shiny metal, because the IR pattern passes through or scatters. Your analytic heuristic trusts the cloud, so a wrong cloud yields a wrong grasp — confidently. A learned planner trained on opaque objects has the same problem. The lesson: a grasp is only as good as the cloud it is computed from, and the cloud is only as good as the object's optical properties allow. When a grasp fails on a clear water glass, the bug is upstream of the grasp planner — it is in the depth sensor — and no amount of grasp-network sophistication fixes a sensor that can't see the object. This is the kind of failure the homework postmortem asks you to diagnose: *pose failure, policy failure, or perception failure?*

---

## Part 4 — Handing the grasp to MoveIt2

The week ends where it began: at the MoveIt2 interface from Week 23. Your planner emits a ranked list of reachable grasps; you take the top one and execute a pick:

1. **Move to the pre-grasp / standoff pose** (offset back along the approach axis).
2. **Open the gripper** to the grasp width plus a margin (the margin is the Lecture 1 §6 mitigation — open wider than the contact separation so approach is forgiving).
3. **Approach** along the approach axis to the grasp pose (a Cartesian straight-line move).
4. **Close the gripper** to the contact width.
5. **Lift** (retreat along the approach axis or straight up) and confirm the object came with it.

MoveIt2's `moveit_msgs/Grasp` message encodes exactly this: the `grasp_pose`, the `pre_grasp_approach`, the `post_grasp_retreat`, and the `pre_grasp_posture` / `grasp_posture` (the gripper open/close). Your planner's job is to fill that message for the top-ranked reachable grasp; MoveIt2's pick pipeline executes it. The composed graph from Week 24 runs it under the safety leash — and "arm strikes during a grasp" is the hazard-log row that guards this exact motion.

---

## Part 4.5 — The pre-grasp, the grasp, and the retreat: a grasp is a small trajectory

It is tempting to think of "the grasp" as a single pose. It is not — it is a *small trajectory* with at least three distinct waypoints, and conflating them is a common cause of knock-the-object-over failures.

- **The pre-grasp (standoff).** Offset back along the approach axis (§1.2). The gripper arrives here *open*, with the fingers clear of the object. The standoff distance must be large enough that the open fingers don't already collide with the object or neighbors — for a parallel-jaw gripper, a few centimeters past the finger length.
- **The grasp pose.** The gripper has approached along a straight Cartesian line from the pre-grasp to here, fingers still open, now straddling the object along the closing axis. The approach segment is *straight* on purpose: a curved approach can clip the object, and a straight line is the easiest motion to reason about and the easiest for MoveIt2 to execute as a Cartesian path.
- **The close.** At the grasp pose, the fingers close to the contact width. Crucially, you opened *wider* than the contact separation at the pre-grasp (the Lecture-1 §6 margin), so the close has room — the fingers do not brush the object on the way in and knock it before they grip.
- **The retreat.** After closing, lift along the approach axis (or straight up) to a post-grasp pose, confirming the object came with the gripper.

MoveIt2's `moveit_msgs/Grasp` encodes exactly this trajectory: `pre_grasp_approach` (the direction and distance of the straight approach), `post_grasp_retreat` (the lift), and the `pre_grasp_posture` / `grasp_posture` (gripper open, then closed). When your planner emits a grasp, it is emitting this whole little trajectory, not a single pose — and a planner that emits only the grasp pose, leaving the approach and retreat to chance, produces grasps that collide on the way in. The pre-grasp/grasp/retreat decomposition is *why* the message has those fields, and filling them correctly is the difference between a grasp that works and one that knocks the cup over a half-centimeter before it closes.

There is one more reason the decomposition matters: it is where the *approach direction* earns its place in the score (§2.1). A grasp whose approach segment passes through the table, or through a neighboring object, is infeasible no matter how good its antipodal score — and you cannot see that from the grasp pose alone; you see it from the *approach segment*. The collision gate in the scorer checks the swept volume of the gripper along the approach, not just at the final pose. A grasp is feasible only if its entire little trajectory — pre-grasp, approach, grasp, retreat — is collision-free, which is a stronger condition than "the final pose is collision-free."

## Part 4.8 — Quick reference: pose, scoring, and the landscape

**Q: What three things does a grasp pose encode?**
Grasp point (origin), closing/baseline axis (finger-close direction), approach axis (how the gripper comes in).

**Q: What must the approach axis be relative to the closing axis?**
Perpendicular. The gripper approaches across the closing line, not along it.

**Q: What decides the orientation convention?**
Your gripper's URDF tool frame — not REP 103, not the lecture default. Mismatch it and the arm reaches 90° wrong.

**Q: What is the standoff / pre-grasp?**
A pose offset back along the approach axis where the gripper pauses, open, before the final straight approach.

**Q: Which frame and stamp do you transform the grasp with?**
Into the arm's planning frame, using the cloud's timestamp (not `now()`).

**Q: What are the four score terms?**
Antipodal quality (dominant), width fit, approach sanity, collision-freedom (a hard gate).

**Q: Why rank and try top-K instead of "the one"?**
Score is a heuristic, reachability prunes, grasps are multimodal — a ranked list survives a blocked top choice.

**Q: How does an unreachable high-score grasp rank?**
Below a reachable lower-score grasp; reachability is a gate, unreachable value is zero.

**Q: What does Contact-GraspNet's contact representation correspond to here?**
This week's antipodal contact geometry, learned, with an object prior.

**Q: What does the data buy that the heuristic can't?**
Object priors and clutter handling. The heuristic wins on explainability and as a sanity gate / fallback.

**Q: The failure no grasp planner fixes?**
Transparent/reflective objects — the depth cloud is wrong, so every planner trusts wrong data. A perception failure.

**Q: What does the analytic planner do for the learned one next week?**
Verify it — run `antipodal_score` on the network's predicted contacts as a friction-cone sanity gate before executing.

## Part 5 — Recap

You should now be able to:

- Build an SE(3) grasp pose from an antipodal pair: grasp point (midpoint), closing axis (the A-B line), and a sane approach axis, assembled into a rotation matrix in *your gripper's* tool-frame convention.
- Add a standoff / pre-grasp pose offset back along the approach axis, and transform the grasp from the cloud's frame into the arm's planning frame honestly (the right stamp).
- Score candidates by more than antipodal quality — width fit, approach sanity, and collision-freedom as a hard gate — and explain why you rank and try top-K rather than "the one."
- Check reachability and prune unreachable grasps, so the ranking reflects what the arm can actually do.
- Situate your heuristic against ACRONYM, GraspNet-1Billion, Contact-GraspNet, GPD, and Dex-Net — what the data buys (object priors, clutter), where the heuristic wins (explainable, no model, a sanity gate), and the perception failure (transparent objects) that no grasp planner fixes.
- Hand a ranked, reachable grasp to MoveIt2 as a `Grasp` / `PoseStamped` and execute a pick under the Week-24 safety leash.

## Part 4.6 — Tuning the score weights: a small, principled process

The score weights (`0.5` antipodal, `0.2` width, `0.3` approach, collision as a gate) are a starting point, and "tune them" is not a satisfying instruction. Here is a principled process that beats guessing:

1. **Fix the gate first.** Collision-freedom is not a weight, it is a hard gate — a colliding grasp scores 0 regardless of the other terms. Get this right before tuning anything, because a mis-gated scorer ranks executable-but-bad grasps below clear-but-good ones, and no weight tuning fixes a missing gate.
2. **Anchor on antipodal quality.** It is the force-closure term, so it should dominate among the *feasible* grasps — give it the largest weight. A grasp that barely passes the friction-cone test should rank below one comfortably centered in the cones, all else equal.
3. **Use approach to break ties the way the task wants.** On a tabletop, approaching from above is usually safest (clear of the table, clear of neighbors), so the approach term should meaningfully penalize side-and-up approaches. If your task wants side grasps (a shelf), invert the sign — the approach term encodes a *task preference*, not a universal truth.
4. **Use width to avoid the gripper's edges.** A grasp at the very maximum opening has no closing margin (one wrong millimeter and the fingers don't reach); one at the minimum is fiddly. The width term should peak in the gripper's comfortable middle range.
5. **Validate against a held-out set, not your intuition.** Collect a small set of grasps you *know* are good (they succeeded in execution) and bad (they failed), and check that your weighted score ranks the good ones above the bad ones. If it doesn't, the weights — or a missing term — are wrong. This turns weight-tuning from taste into a tiny supervised problem.

The deeper point: the weights encode *your task's* preferences (top-down vs. side, robustness vs. reach), and there is no universal best setting. What is universal is the *structure*: feasibility is a gate, force closure dominates the feasible set, and the remaining terms encode task preferences and gripper limits. A scorer with the right structure and roughly-tuned weights beats a scorer with perfect weights and the wrong structure (a missing collision gate) every time.

## Part 4.7 — The grasp planner in the larger manipulation loop

Zoom out: the grasp planner is one stage in a pipeline that Phase 4 assembles, and knowing its neighbors clarifies its job. Upstream: perception (Weeks 13–16) produces the segmented object cloud the planner consumes — and the planner is only as good as that segmentation (a cloud with the table not removed yields grasps on the table). Downstream: MoveIt2 (Week 23) executes the chosen grasp under the safety leash (Week 24) — and the planner must hand over a *reachable* grasp (§2.3) or the executor fails. Lateral: in the capstone, a VLA (Week 37) selects *which* object to grasp from a language instruction, and the grasp planner selects *how* — the VLA picks the red cup, the planner finds the grasp on it.

This framing tells you what the planner owes its neighbors: a *reachable* grasp (so MoveIt2 can execute it), in the *right frame* with the *right stamp* (so the transform is correct), with a *width and approach* (so the gripper knows how to open and come in), as part of a *ranked list* (so the next stage can fall through on failure). A planner that emits a bare pose with none of this is a planner that breaks its neighbors. The "pose, width, confidence, frame, REACHABLE" promise line (the week's marker) is exactly the contract the planner owes the rest of the pipeline — every field is there because a downstream stage needs it.

Next: the exercises put the geometry on a real cloud, and the mini-project builds the `crunch_grasp` planner end to end. Continue to [the exercises](../exercises/README.md).

---

## Part 6 — A worked end-to-end: cloud to executed pick

To close the loop, trace one grasp from cloud to execution, the path the mini-project automates:

1. **Segment.** RANSAC-remove the table, cluster, isolate the object cloud (Week 15).
2. **Sample.** Antipodal candidates on the cloud (Lecture 1 §5): hundreds of feasible pairs.
3. **Score.** Antipodal quality + width + approach + collision gate (§2.1): a ranked list.
4. **Pose.** Build each grasp's SE(3) pose in the gripper's tool-frame convention (§1), with a standoff.
5. **Reachability.** Walk the sorted list, ask MoveIt2 to plan to each; prune the unreachable (§2.3).
6. **Transform.** Move the top reachable grasp into the planning frame with the cloud's stamp (§1.3).
7. **Fill the `Grasp`.** Grasp pose, pre-grasp approach, post-grasp retreat, gripper open/close (§4).
8. **Execute.** MoveIt2's pick pipeline runs the pre-grasp → approach → close → lift, under the Week-24 safety leash.
9. **Confirm.** The object came with the gripper; if not, fall through to the next ranked grasp.
10. **Log.** Record which ranked grasp succeeded and why, so the next run's ranking can learn from the outcome.

Each step is a stage you can inspect and debug independently — and when a pick fails, the stage where it failed tells you the kind of failure: a bad segment (the cloud had the table), a bad pose (wrong convention), an unreachable grasp (skipped step 5), a knock-over (no width margin), or a perception failure (transparent object). The pipeline is not one black box; it is nine inspectable stages, which is exactly what makes an analytic planner debuggable in a way a single learned forward-pass is not.

## References

- *`moveit_msgs/Grasp` message*: <https://github.com/moveit/moveit_msgs/blob/master/msg/Grasp.msg>
- *MoveIt2 — pick and place tutorial*: <https://moveit.picknik.ai/main/doc/examples/pick_place/pick_place_tutorial.html>
- *REP 103 — Standard units and coordinate conventions*: <https://www.ros.org/reps/rep-0103.html>
- *ACRONYM grasp dataset*: <https://sites.google.com/view/graspdataset>
- *GraspNet-1Billion benchmark*: <https://graspnet.net/>
- *Contact-GraspNet*: <https://research.nvidia.com/publication/2021-03_contact-graspnet-efficient-6-dof-grasp-generation-cluttered-scenes>
- *GPD — Grasp Pose Detection*: <https://github.com/atenpas/gpd>
- *Dex-Net*: <https://berkeleyautomation.github.io/dex-net/>

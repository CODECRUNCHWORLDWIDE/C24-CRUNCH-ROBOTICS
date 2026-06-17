# Mini-Project — `crunchbot_grasp`: The First Perception → Policy → Motion Loop

> Build a ROS2 package that takes a synchronized RGB-D frame of a tabletop, segments a target object, runs Contact-GraspNet to propose ranked 6-DOF grasps, transforms the best *reachable* one into the planning frame, and drives a MoveIt2 pick — with a classical antipodal fallback when the network is unconfident. Then quantify the pick success rate over three objects and partition every failure into a named bucket.

This is the artifact the whole week builds toward, and it is the **first fully integrated learned loop** of the entire track: a sensor goes in one end and the robot *does something it was not explicitly told to do* out the other. Every prior week was a piece of this — week 14's RGB-D, week 15's point clouds, week 23's MoveIt2, week 25's antipodal grasps, week 5's QoS — and this is where they compose.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This `crunchbot_grasp` package becomes the **grasp skill** that next week's imitation policy and the capstone's language-conditioned stack call. The Phase 4 midterm (Week 32) explicitly grades whether your learned policy ships with a fallback and a documented failure envelope — both of which you build here. Build it well now; you defend it in six weeks.

---

## What you will build

A small ament-python package `crunchbot_grasp` with four deliverables:

1. **`crunchbot_grasp/grasp_node.py`** — the inference node. Synchronized RGB-D in (sensor QoS, week 5), segmentation → deproject → preprocess → Contact-GraspNet → reconstruct → NMS, ranked grasps out as a `PoseArray` with per-grasp confidence and width (command QoS).
2. **`crunchbot_grasp/pick_node.py`** — the pick executor. Subscribes to the ranked grasps, transforms to the planning frame with tf2, IK-filters (grasp *and* pre-grasp), builds the pre-grasp → approach → close → lift sequence, executes via MoveIt2, and reports SUCCESS/FAIL with a **failure bucket**.
3. **`crunchbot_grasp/fallback.py`** — the week-25 antipodal sampler, wrapped so the pick node calls it when the network returns no grasp above threshold. The system must *degrade*, never stall.
4. **An evaluation harness** (`eval/run_eval.py` + `eval/report.md`) — picks each of three objects (mug, box, tool) N times, logs every attempt with its outcome and failure bucket, and produces a success-rate table and a failure-bucket histogram.

By the end you have a public repo of ~400–550 lines that any future crunchbot package can launch as a self-contained grasp skill.

---

## Why a fallback, and why measure the intervention rate

The syllabus pattern for all of Phase 4 is **ship the learned policy with a leash.** Contact-GraspNet will, honestly, return nothing on objects it has no clean points for. A pick stack that *stalls* when that happens is unshippable. The antipodal fallback (week 25) always produces *some* grasp given any non-empty cloud — lower quality, but never a stall.

You must measure the **intervention rate**: the fraction of picks that used the fallback instead of the learned grasp. This number is diagnostic. A *low* intervention rate means the learned policy is carrying the load (good). A *high* rate means your perception is failing often enough that the network rarely sees a clean cloud — which sends you to fix segmentation or depth, not the network. The intervention rate is the single most informative number in the whole stack.

---

## Package layout

```
crunchbot_grasp/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunchbot_grasp
├── crunchbot_grasp/
│   ├── __init__.py
│   ├── grasp_node.py        # RGB-D -> ranked grasps
│   ├── pick_node.py         # ranked grasps -> MoveIt2 pick + buckets
│   ├── fallback.py          # week-25 antipodal sampler, wrapped
│   ├── geometry.py          # reconstruct_grasp_poses, grasp_nms, mat_to_pose
│   └── model.py             # Contact-GraspNet loader (checkpoint or tiny stub)
├── launch/
│   └── pick.launch.py       # camera (or sim) + grasp_node + pick_node
├── eval/
│   ├── run_eval.py          # picks each object N times, logs outcomes
│   └── report.md            # the success-rate table + bucket histogram
└── test/
    ├── test_geometry.py     # pose reconstruction orthonormality + offset
    └── test_nms.py          # NMS reduces count, keeps diversity
```

---

## Deliverable 1 — `grasp_node.py` (perception → grasps)

The node from Lecture 2 §2, made real. It must:

- Subscribe to color, depth, and `camera_info` with **`message_filters.ApproximateTimeSynchronizer`** and the **sensor QoS profile** (week 5). A `RELIABLE` subscriber on a `BEST_EFFORT` camera publisher receives nothing — verify with `ros2 topic info -v` if no frames arrive.
- Handle the **depth-unit gotcha**: convert millimeters to meters before building the cloud.
- Segment the target object (SAM2 if you have it; for the demo, a simple color-threshold or a hard-coded ROI mask is acceptable as long as the *interface* is "mask in, object cloud out").
- Deproject the masked depth to a cloud, voxel-downsample and outlier-remove (week 15), reconstruct poses, NMS, and publish a ranked `PoseArray` **in the camera optical frame** with a parallel array (or a custom message) of confidences and widths.
- Guard every stage with an explicit early return that publishes an empty result and logs *why* (empty mask, sparse cloud, no confident grasp).

The node must import the pose math from `geometry.py` (which you tested in Exercise 1), not re-implement it inline.

---

## Deliverable 2 — `pick_node.py` (grasps → motion → bucket)

The pick executor from Lecture 2 §3. It must:

- Subscribe to `/grasp_poses`, transform each grasp to `base_link` with live tf2 (**not** a cached transform — for an arm-mounted camera the transform changes).
- Walk the ranked list and select the first grasp whose **grasp and pre-grasp** are both IK-feasible (the Exercise 3 logic).
- Build and execute the four-stage sequence: planned pre-grasp, Cartesian approach, gripper close (slight over-close), Cartesian lift.
- On any failure, classify it into one of the four buckets — **perception / prediction / planning / execution** (Lecture 2 §4) — and log the bucket. This is what the eval harness aggregates.
- If no grasp is reachable *and* the grasp list is empty, invoke the fallback.

---

## Deliverable 3 — `fallback.py` (the leash)

Wrap your week-25 antipodal sampler behind a single function:

```python
def antipodal_fallback(cloud, gripper_max_width=0.085):
    """Heuristic grasp from week 25. Given any non-empty cloud, returns the
    best antipodal grasp pose + width. Never returns None for a non-empty cloud."""
    ...
```

The pick node's grasp-selection becomes:

```python
def select_grasp(self, cloud, ranked_grasps):
    if ranked_grasps and ranked_grasps[0].confidence > 0.75:
        return ranked_grasps[0], "learned"
    self.get_logger().warn("CGN unconfident -> antipodal fallback")
    return self.antipodal_fallback(cloud), "fallback"
```

The eval harness counts the `"fallback"` returns to compute the intervention rate.

---

## Deliverable 4 — the evaluation harness

`eval/run_eval.py` spawns each of three objects (mug, box, tool) in Gz Sim, runs the full pick stack N times per object (N ≥ 5), and logs every attempt: object, learned-or-fallback, outcome (success/fail), and failure bucket on failure. It writes `eval/report.md` with:

- A **success-rate table**: per object and overall, `successes / attempts`.
- A **failure-bucket histogram**: counts of perception / prediction / planning / execution failures across all attempts.
- The **intervention rate**: fraction of attempts that used the fallback.
- A one-paragraph reading of the histogram: *which bucket dominates, and therefore what you'd fix next.*

Example `report.md` shape:

```
## Pick success rate (N=5 per object)

| Object | Attempts | Successes | Rate  | Fallback used |
|--------|---------:|----------:|------:|--------------:|
| mug    |        5 |         4 | 80%   |             1 |
| box    |        5 |         5 | 100%  |             0 |
| tool   |        5 |         2 | 40%   |             3 |
| TOTAL  |       15 |        11 | 73%   |             4 |

## Failure buckets (across 4 failures)
perception: 2   prediction: 0   planning: 1   execution: 1

## Reading: perception dominates. The 'tool' is thin and the depth camera
## undersamples it, so the cloud is sparse -> fallback fires -> lower-quality
## grasps -> slips. Next fix: a denser depth capture or a depth-completion pass
## for thin objects, NOT network retraining.
```

The *reading* is the point. A success rate without a bucket histogram tells you nothing actionable. The histogram tells you exactly where the next hour goes.

---

## Rules

- **You may** read the Contact-GraspNet paper and code, the MoveIt2 docs, `rclpy` source, and your own weeks 14/15/23/25 code.
- **You must not** re-implement the pose reconstruction or NMS inline — they live in `geometry.py` and are imported. (`grep -rn "def reconstruct_grasp" --include=*.py` should find it once.)
- **You must** set sensor QoS on the RGB-D inputs and command QoS on the grasp output (week 5). An `ros2 topic info -v` that shows a mismatch fails the bring-up.
- **You must** ship the fallback. A stack that stalls on an unconfident grasp does not pass.
- Python 3.12 (Ubuntu 24.04), `rclpy` on Jazzy, PyTorch 2.x. The real Contact-GraspNet checkpoint if you have a GPU; the tiny stub from Exercise 2 if you are CPU-only (the *integration* is graded, not the grasp quality of a stub).

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-26-crunchbot-grasp-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_grasp` succeeds with no warnings.
- [ ] `ros2 launch crunchbot_grasp pick.launch.py` brings up the camera (or sim), the grasp node, and the pick node; `ros2 topic info /grasp_poses -v` shows compatible QoS on both ends.
- [ ] The grasp node publishes a ranked `PoseArray` in the camera frame; the pick node logs the four-stage sequence and a SUCCESS/FAIL-with-bucket line per attempt.
- [ ] The fallback fires (and is logged) when the learned grasp is unconfident; the stack never stalls.
- [ ] `colcon test` passes `test_geometry.py` (orthonormal `R`, correct contact-to-center offset) and `test_nms.py` (count strictly reduced, kept grasps diverse).
- [ ] `eval/report.md` contains the success-rate table, the failure-bucket histogram, the intervention rate, and the one-paragraph reading.
- [ ] A repo `README.md` with the architecture diagram (Mermaid), the run commands, and the success-rate result.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Integrated loop works** | 25 | RGB-D → grasp → pick executes end to end; at least one object is picked in sim with the "it picked it up" log line. |
| **Pose & frame correctness** | 20 | `geometry.py` produces orthonormal rotations and the correct offset; grasps are transformed to the planning frame with *live* tf2; no stale-transform bug. |
| **QoS & node hygiene** | 15 | Sensor QoS on inputs, command QoS on outputs (week 5); every pipeline stage guarded; depth-unit handling present. |
| **Fallback & intervention rate** | 15 | The leash is real and logged; the eval harness reports a meaningful intervention rate. |
| **Failure-bucket analysis** | 15 | Every failure is classified; the bucket histogram is correct and the *reading* names the right next fix (not "retrain the network"). |
| **Tests & docs** | 10 | `test_geometry.py` + `test_nms.py` green; clear README with the architecture diagram; no `build/`/`install/` checked in. |

**90+** is portfolio-grade and ready to become the grasp skill in Week 27 and the capstone. **70–89** works but has a frame bug, a missing fallback, or a hand-waved bucket analysis. **Below 70** means the loop isn't actually integrated — get one object picked end to end first.

---

## Stretch goals

- **Collision filtering.** Before committing to a grasp, render the gripper mesh at the pose and reject grasps whose finger volume intersects the non-target cloud. Report how many "confident but colliding" grasps this removes.
- **Multi-view fusion.** Capture the scene from two arm poses, fuse with ICP (week 15), and re-grasp. Quantify the success-rate improvement on a concave object.
- **The real checkpoint.** Swap the tiny stub for the real ACRONYM-trained Contact-GraspNet checkpoint on a cloud GPU and re-run the eval. Report the success-rate delta — this is the difference the weights make.
- **A `pick` action server.** Wrap the pick node as a ROS2 action (`Pick.action`) with feedback per stage and a cancellable goal — exactly the interface next week's imitation policy and the capstone's behavior tree will call.

---

## How this connects to the rest of C24

- **Week 27 (imitation)** treats this grasp stack as one *skill* the imitation policy invokes; a "reach for the red block" demo ends in a grasp call.
- **Week 32 (Phase 4 midterm)** grades the learned-policy + fallback pattern and the documented failure envelope — both of which are this mini-project.
- **The capstone (weeks 41–48)** uses this exact pick stack, driven by the language-conditioned policy, as the manipulation half of the mobile manipulator.

When you've finished, push the repo and take the [quiz](../05-quiz.md).

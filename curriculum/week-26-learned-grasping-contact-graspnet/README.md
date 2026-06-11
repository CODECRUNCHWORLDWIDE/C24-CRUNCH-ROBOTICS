# Week 26 — Learned Grasping: Contact-GraspNet

Last week you generated antipodal grasps by hand: sample a point cloud, score candidates with a heuristic, pick the best. It works on a clean tabletop and falls apart the moment the scene gets cluttered, the object is novel, or the geometry is concave. This week you replace the heuristic with a **learned** grasp predictor — Contact-GraspNet — and wire it into the first fully integrated **perception → policy → motion** loop of the entire track. By Friday a single RGB-D frame goes in, a ranked list of 6-DOF gripper poses comes out, the top reachable one gets handed to MoveIt2, and your week-23 arm picks up a mug in Gz Sim.

This is the week the robot stops being told *exactly* what to do and starts proposing what to do. It is also the week you confront the central truth of learned grasping: **the network is the easy part.** Contact-GraspNet is a PointNet++ backbone with three small heads. It is maybe 12 million parameters. What makes it work is the *representation* — predicting a contact point and a gripper baseline direction instead of a free-floating SE(3) pose — and the *data*, six million simulated grasps from the ACRONYM dataset that taught it what a graspable surface looks like. We teach the architecture, but we spend more time on the contact-point trick and on the segmentation step that decides *which object* you are grasping, because that is where real deployments live or die.

We assume your **week-23 MoveIt2 setup** still plans and executes to a `geometry_msgs/PoseStamped` goal, your **week-14 RGB-D camera** still publishes synchronized color + depth + `camera_info`, and you finished **week-25** with a working notion of the gripper-frame convention and antipodal scoring. If any of those are broken, fix them first — every exercise this week composes them.

The one idea to internalize before you read another line: **a learned grasp is a distribution over contact geometry, not a lookup.** Contact-GraspNet does not memorize "mugs are grasped by the handle." It learns that a pair of nearly-parallel surfaces about a gripper-width apart, with the approach direction clear of collision, is graspable — and it generalizes that to objects it has never seen. When it fails, it fails on objects that *violate the depth assumption it was trained on*: transparent glass that the depth camera renders as a hole, mirror-finish metal that returns garbage depth, thin wires below the depth resolution. You will reproduce those failures on purpose, because knowing the failure envelope is the difference between a demo and a deployment.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** the Contact-GraspNet architecture end to end — the PointNet++ set-abstraction backbone, the contact-point representation, and the three prediction heads (grasp confidence, approach/baseline directions, grasp width) — and state why predicting a *contact point* is more sample-efficient than regressing a free 6-DOF pose.
- **Reconstruct** a full 6-DOF grasp pose from the network's raw outputs (contact point, approach vector, baseline vector, width) using the published gripper-frame convention, and verify it against the gripper mesh in rviz2.
- **Run** segmentation-aware grasping: take an RGB-D frame, segment the target object (SAM2 or a class mask), restrict grasp prediction to that object's points, and rank the resulting grasps.
- **Deploy** a pretrained Contact-GraspNet checkpoint as a ROS2 node that consumes a synchronized RGB-D frame and publishes ranked grasp poses as a `vision_msgs`-style message with per-grasp confidence.
- **Integrate** the grasp node with MoveIt2: transform the top grasp into the planning frame, generate a pre-grasp/approach/lift trajectory, filter unreachable grasps by IK feasibility, and execute the pick.
- **Quantify** grasp success rate over a set of objects, partition failures into perception / prediction / planning / execution buckets, and read the buckets to know *where* to spend the next hour of debugging.
- **Predict and reproduce** Contact-GraspNet's documented failure modes on transparent and reflective objects, and describe the depth-completion and multi-view mitigations a 2026 shop reaches for.
- **Wrap** the learned grasp in a classical fallback (the week-25 antipodal sampler) so that when the network returns no confident grasp, the system degrades instead of stalling.

## Prerequisites

This week assumes you have completed **C24 weeks 1–25**, or have equivalent fluency. Specifically:

- A working **MoveIt2 + Gz Sim** bring-up of a 6-DOF arm with a parallel-jaw gripper (week 23), able to plan-and-execute to a pose goal sent on a topic.
- A **synchronized RGB-D source** (week 14): `sensor_msgs/Image` color, `sensor_msgs/Image` depth, and a `sensor_msgs/CameraInfo` with valid intrinsics, all on a known TF frame.
- The **point-cloud tooling** from week 15 (Open3D, voxel downsample, statistical outlier removal) and the **gripper-frame convention** and antipodal scoring from week 25.
- **PyTorch ≥ 2.3** with CUDA (a cloud GPU is fine; CPU works for inference but is slow). You can write a `Dataset`, a forward pass, and load a checkpoint from C5.
- The **QoS literacy** from week 5 — the RGB-D topics are `BEST_EFFORT` sensor streams; the grasp-pose output is a low-rate command-class topic. You will set both correctly.

You do **not** need to *train* Contact-GraspNet from scratch — that is a multi-GPU, multi-day job on six million grasps and is out of scope. You will deploy and fine-tune a pretrained checkpoint, which is exactly what a robotics shop does in 2026. We read the training loss so you understand the checkpoint you load; we do not reproduce the training run.

## Topics covered

- **The grasp-representation problem.** Why regressing a free 6-DOF `SE(3)` pose per object is data-hungry and unstable, and how Contact-GraspNet's contact-point parameterization (a point on the object surface + a baseline direction + an approach direction + a width) collapses the output space onto the observed geometry and makes every training point a dense supervisory signal.
- **The architecture.** PointNet++ set-abstraction and feature-propagation layers as the backbone; the three heads — a per-point grasp-confidence score, a (approach, baseline) direction pair, and a grasp-width regressor; how the network turns N input points into up to N grasp proposals.
- **Pose reconstruction.** The exact math to assemble a `4x4` gripper transform from the contact point, the predicted approach and baseline unit vectors (orthonormalized via Gram–Schmidt), and the half-width offset to the gripper center — plus the published gripper-frame convention so your poses line up with MoveIt2's end-effector frame.
- **Segmentation-aware grasping.** Why "grasp the scene" is rarely what you want; running SAM2 or a class segmentation to produce an object mask, lifting the 2D mask to the 3D point set, and predicting grasps only on the target object so the ranked list is grasps *for the thing you asked for*.
- **Training data vs. runtime data.** ACRONYM (six million simulated grasps on ShapeNet meshes) as the training distribution; the sim-to-real depth gap; why the checkpoint generalizes to novel objects but not to materials that break the depth sensor.
- **The ROS2 deployment pattern.** A grasp-inference node: synchronized RGB-D subscription (`message_filters`), preprocessing (deproject to cloud, crop, downsample), batched GPU inference, NMS over grasps, and a ranked `vision_msgs`-style output with confidence and width per grasp.
- **The pick pipeline.** Transforming grasps into the planning frame with tf2; IK-feasibility filtering; constructing the pre-grasp → approach → grasp → lift sequence with MoveIt2's Cartesian path / pick interface; the gripper-actuation handshake.
- **Failure analysis.** The four failure buckets (perception, prediction, planning, execution); the transparent/reflective failure mode and why it is a *sensor* failure dressed up as a *network* failure; depth completion (e.g. learned depth inpainting) and multi-view fusion as the standard mitigations.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Grasp representation; PointNet++ backbone; the 3 heads |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Pose reconstruction; gripper frame; exercises 1 & 2    |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Segmentation-aware grasping; ROS2 inference node        |   2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | MoveIt2 pick integration; failure buckets              |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Transparent/reflective failures; the fallback          |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work (the pick stack)                |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, success-rate writeup, review                     |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The Contact-GraspNet paper + code, ACRONYM/GraspNet-1B datasets, MoveIt2 pick docs, SAM2, depth-completion reading |
| [lecture-notes/01-contact-graspnet-architecture.md](./lecture-notes/01-contact-graspnet-architecture.md) | The representation, the PointNet++ backbone, the three heads, and pose reconstruction with real PyTorch |
| [lecture-notes/02-deployment-segmentation-and-the-pick-loop.md](./lecture-notes/02-deployment-segmentation-and-the-pick-loop.md) | Segmentation-aware grasping, the ROS2 inference node, the MoveIt2 pick pipeline, and the failure buckets |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-pose-reconstruction.md](./exercises/exercise-01-pose-reconstruction.md) | Reconstruct a 6-DOF grasp from raw network outputs and verify it against the gripper mesh |
| [exercises/exercise-02-grasp-inference.py](./exercises/exercise-02-grasp-inference.py) | Load a Contact-GraspNet checkpoint, run inference on a point cloud, NMS and rank the grasps |
| [exercises/exercise-03-pick-pipeline.py](./exercises/exercise-03-pick-pipeline.py) | Filter grasps by IK feasibility and build the pre-grasp/approach/lift sequence for MoveIt2 |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-transparent-object-failure.md](./challenges/challenge-01-transparent-object-failure.md) | Reproduce, diagnose, and mitigate the transparent-object failure mode with depth completion |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the per-object success-rate report |
| [mini-project/README.md](./mini-project/README.md) | The `crunchbot_grasp` pick stack: perception → Contact-GraspNet → MoveIt2 → fallback |

## The "it picked it up" promise

C24 uses a recurring marker for every exercise that ends in the robot actually doing the thing. For this week it is the pick:

```
[grasp_node] RGB-D frame @ t=12.40: 8732 points -> 214 grasps -> 19 above conf 0.75
[grasp_node] top grasp: conf=0.91 width=0.058m frame=camera_color_optical_frame
[pick] transformed to base_link; IK feasible; planning approach...
[pick] approach OK, grasp OK, lift OK
[pick] gripper closed at width 0.061m; object lifted 0.12m -> SUCCESS
```

If the top grasp is high-confidence but the pick fails, the failure is almost never the network — it is the transform, the IK reachability, or the gripper actuation. The whole point of the week is to make that line ordinary, and to make a failure land in a *named bucket* instead of a shrug.

## Stretch goals

If you finish the regular work early and want to push further:

- Run Contact-GraspNet on a **cluttered** scene (five objects touching) and study how segmentation quality drives grasp quality. Turn segmentation off (grasp the whole scene) and watch the ranked list fill with grasps that span two objects.
- Implement **collision filtering** in the gripper frame: for each proposed grasp, render the gripper mesh at the pose and reject grasps whose finger volume intersects the (non-target) point cloud. Measure how many "confident but colliding" grasps this removes.
- Add **multi-view fusion**: capture the scene from two camera poses (move the arm-mounted camera), fuse the two clouds with ICP from week 15, and re-run grasping. Quantify the improvement on a concave object.
- Read the **GraspNet-1Billion** paper and contrast its dense per-point grasp annotation and its grasp-confidence metric with Contact-GraspNet's contact-point approach. Write a half-page on when you'd pick one over the other.

## Up next

Week 27 takes the integrated pick loop you built here and asks a harder question: what if you *can't* write the policy at all — what if the task is "reach for the red block" and the only specification you have is human demonstrations? That is imitation learning: Behavior Cloning and DAgger. The grasp node you wrote this week becomes one skill the imitation policy can call. Push your `crunchbot_grasp` stack before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

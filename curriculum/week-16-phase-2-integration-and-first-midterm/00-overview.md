# Week 16 — Phase 2 Integration: The Fused Perception Node and the First Midterm

Welcome to **C24 · Crunch Robotics**, Week 16 — the last week of Phase 2 and the first hard gate in the track. For seven weeks you built perception parts. An IMU got calibrated and bias-corrected. An EKF fused it with wheel odometry into a bounded-drift estimate. AMCL localized against a map and a GTSAM factor graph stopped lying about nonlinearity. OpenCV calibrated a camera and ran optical flow. A YOLO detector hit its latency budget on the edge. A RealSense came up and projected a metric, confidence-gated point cloud. Open3D voxel-filtered, ground-segmented, clustered, and registered that cloud, and you measured the drift. This week you take **all of it** and compose it into **one fused perception node** — IMU + wheel odometry into the EKF; LiDAR into the 3D clustering; the RGB-D camera into a YOLO detector — that publishes a single unified `/perception/objects` topic, with detected objects in the `map` frame, inside a **30 ms end-to-end cycle** on an Orin Nano (or with a documented reason why not on Path B).

That fused node is the deliverable. It is also the **Phase 2 milestone and the first midterm**, and the midterm is a *hard gate*: you defend your perception stack to a panel against a written rubric, and a failure here sends you back to the offending week. This is the first time the track tells you, formally, that a beautiful component that doesn't *compose* is not good enough. Two of the three flagship portfolio projects (the SYLLABUS calls this "the 30-ms perception cycle") are born this week.

The first thing to internalize is that **integration is not "wire the parts together." Integration is where the parts disagree, and your job this week is to find every disagreement before the panel does.** Each perception component was correct in isolation against its own test. Composed, they fight: the EKF publishes `/odometry/filtered` at 30 Hz but the clustering node stamps its detections in the camera optical frame, not `map`; the YOLO detector's 2D box and the LiDAR cluster's 3D box are the *same physical object* but nothing associates them; the RGB-D detection is 80 ms stale by the time it lands in the unified topic; the point-cloud node's ICP hit a degenerate corridor and fed the EKF a wrong-local-minimum transform that corrupted the estimate. None of these is a bug in any single component. All of them are integration defects, and they only appear when the whole perception graph is live. A senior robotics engineer expects this and budgets for it.

The second thing to internalize is that **a perception pipeline is a *latency budget*, and you defend yours with a number, not a feeling.** When the syllabus says "hit a 30 ms end-to-end cycle," that is a measurement: from the sensor timestamp to the moment `/perception/objects` is published, at the 95th percentile, with the whole graph live. Lecture 1 teaches you to draw the latency block diagram — every hop from sensor to fused output, with a measured cost — so the 30 ms is a *sum of hops you can each profile*, not a wish. Half of midterm failures are not engineering failures; they are *measurement* failures, where the student says "it's fast" and the panel asks "p95, under load, sensor-stamp to publish?" and the room goes quiet.

The third thing to internalize is that **the midterm is an architecture review, and you prepare for it like a contract.** The panel will not ask you to recite the EKF update equations. They will point at your running graph and ask: "why that QoS on `/perception/objects`?" "where does a stale detection get rejected?" "how does your fused estimate bound drift?" "what happens when the LiDAR drops out?" Lecture 2 teaches the architecture-review format and the senior habit that survives it: a one-page **perception architecture brief** — a block diagram, a latency budget, the frame/timing contract between every component, and the failure-mode table — that you write *before* the review and that answers most of the panel's questions before they're asked. The midterm is a conversation you can rehearse, and this week is the rehearsal.

The fourth thing to internalize is that **this midterm is a rehearsal for the capstone.** The fused perception node you build this week is the *exact* perception layer of the Week 40 capstone milestone and the Week 48 defense. The 30 ms budget here becomes the ≤ 50 ms end-to-end perception requirement of the capstone spec. The drift you bound here becomes the < 0.5 m / 20 m capstone acceptance number. The "defend your stack to a panel" format here is the same format you face at Weeks 32, 40, and 48. Pass this gate well and you have a portfolio piece and a rehearsed defense; pass it sloppily and the same weaknesses resurface at the capstone, where they cost weeks instead of a resubmission.

## Learning objectives

By the end of this week, you will be able to:

- **Compose** Weeks 9–15 into one fused perception node: IMU + wheel odometry into the EKF (`robot_localization`), LiDAR into the 3D clustering (Week 15), and the RGB-D camera into a YOLO detector (Week 13), publishing a unified `/perception/objects` (`vision_msgs/Detection3DArray`) with detections in the `map` frame.
- **Design** an end-to-end perception graph with an explicit *interface contract* — topic, message type, frame, rate, and QoS — for every seam between components, and verify those contracts at bring-up.
- **Draw** a perception latency block diagram: every hop from sensor stamp to `/perception/objects` publish, each with a measured cost, summing to the end-to-end budget.
- **Measure** the end-to-end perception latency honestly — sensor stamp to publish, p95, with the whole graph live — and report it as a number with a script, not an adjective.
- **Associate** a 2D camera detection with a 3D LiDAR/RGB-D cluster into a single fused object (the detection-to-cluster data association), and explain the failure modes (no match, double match, frame disagreement).
- **Guard** against the stale-perception race with a stamp-age check at the point of use, and against a bad registration with the health-gating from Week 15, so the fused estimate doesn't corrupt on one bad input.
- **Diagnose** the four canonical perception-integration defects: the frame/timing mismatch, the stale-perception race, the data-association failure, and the latency-budget blowout under load.
- **Defend** the perception stack to a panel: a block diagram, a latency budget, the frame/timing contract, the failure-mode table, and honest measured numbers (latency p95 and drift) — the architecture-review format that gates Phase 2.

## Prerequisites

This week assumes you have completed **Weeks 1–15** of C24, or have the equivalent components already built and tested. Specifically:

- **A bias-corrected IMU (Week 9) and an EKF (Week 10).** `robot_localization`'s `ekf_node` fusing wheel odometry + IMU into `/odometry/filtered`, with covariances stated honestly. This week it's the motion backbone of the fused node.
- **3D clustering and scan-to-scan odometry (Week 15).** Your `crunchbot_perception3d` node: ground-removed Euclidean clusters as `vision_msgs/Detection3DArray`, plus ICP odometry with a published health signal. This week it's the 3D-detection branch.
- **A YOLO ROS2 inference node (Week 13).** YOLOv8/v10 exported to TensorRT, consuming `/camera/image_raw`, publishing `vision_msgs/Detection2DArray` at ~30 FPS. This week it's the 2D-detection branch.
- **A trustworthy RGB-D cloud (Week 14).** Your `crunchbot_rgbd` bring-up: synchronized, filtered, confidence-gated `/crunchbot/points`. This week it feeds both the clustering and (via alignment) the detection-to-cluster association.
- **Week 5 QoS literacy and Week 2 tf2.** The fused node lives or dies on correct QoS on every seam and a clean `map → odom → base_link → camera/lidar` frame tree. If either is fuzzy, the integration *will* surface it.
- **A working ROS2 Jazzy on Ubuntu 24.04**, your sim or hardware that runs the robot and the camera, and (Path A) a Jetson Orin Nano for the latency target, or (Path B) a documented CPU/GPU substitution.

You do **not** need any new library this week. Week 16 introduces almost no new API. It introduces a new *discipline*: composition, latency budgeting, data association, and an honest architecture-review defense. The hard part is not writing code — it is making seven weeks of perception agree, inside 30 ms, in front of a panel.

## Topics covered

- **End-to-end perception graph design.** The data flow from sensors to `/perception/objects`: IMU + wheel odom → EKF → the `map → odom` and `odom → base_link` transforms; LiDAR/RGB-D → clustering → 3D detections; camera → YOLO → 2D detections; the fusion node that associates and publishes. The interface contract (topic/type/frame/rate/QoS) for every seam.
- **The perception latency budget.** Drawing the latency block diagram; the hops (sensor acquisition, transport, inference, clustering, association, transform, publish); measuring each; the difference between one model's inference time and the path's end-to-end latency; p95 under load vs. mean idle.
- **Topic timing diagrams.** How fast each producer publishes, how fast each consumer ticks, where a slow producer feeds a fast consumer (the stale-perception race), and the stamp-age guard at the point of use.
- **Detection-to-cluster data association.** Matching a 2D camera detection to a 3D cluster: project the cluster into the image and IoU-match the box, or back-project the 2D box's ray and nearest-cluster-match; the failure modes (no match, double match, frame/time disagreement); producing a fused 3D object with a class label.
- **Frame discipline at scale.** Everything must agree on `map → odom → base_link → sensor` (REP 105). The detections publish in `map`; the camera detects in the optical frame; the transform chain and the *stamp at which you look it up* are where the frame/timing mismatch hides.
- **Robustness gates.** The stamp-age check (reject a detection older than tolerance), the ICP health gate (de-weight a bad registration), and the EKF covariance discipline (an honest covariance lets the filter ignore a bad input) — so one bad component doesn't corrupt the fused output.
- **The four perception-integration defects.** The frame/timing mismatch (detections in the wrong frame or looked up at the wrong stamp), the stale-perception race (a fast consumer using a slow producer's stale data), the data-association failure (the 2D and 3D detections of one object never get fused, or two objects get merged), and the latency-budget blowout (the pipeline hits 30 ms idle but 70 ms when the YOLO and the clustering contend for the GPU/CPU).
- **The architecture-review / midterm format.** The perception architecture brief (block diagram, latency budget, interface contract, failure-mode table, measured numbers); how a panel reads a perception stack; the questions they ask; defending a number; the hard-gate consequences and how to prepare.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract — though this is a gate week, so "budget" and "measurement" are the operative words. Integration is best done in long, uninterrupted blocks: you need the full perception graph, the sim or robot, the camera, and the profiling tools all live at once, and context-switching out of a half-composed graph is the most expensive thing you can do this week.

| Day       | Focus                                                            | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Perception graph design; the interface contract; latency budget   |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Compose the stack; data association; fight the integration bugs   |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | Measure the latency; robustness gates; the architecture brief     |    1.5h  |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | The midterm-defense rehearsal; the challenge                     |    0.5h  |    0h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Mini-project — the fused node + the measured budget               |    0h    |    0h     |     0h     |    0.5h   |   1h     |     3h       |    0.5h    |     5h      |
| Saturday  | Mini-project deep work; measure latency + drift; brief polish     |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, midterm sign-off prep                              |    0h    |    0h     |     0h     |    1h     |   0h     |     3h       |    0h      |     4h      |
| **Total** |                                                                  | **6h**   | **5.5h**  | **2h**     | **3.5h**  | **5h**   | **14h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The integration, latency-profiling, data-association, and architecture-review references that matter in 2026 — ROS2 Jazzy docs, `vision_msgs`, REP 105, profiling tools, and the systems-integration talks |
| [lecture-notes/01-perception-pipeline-design-and-the-latency-budget.md](./02-lecture-notes/01-perception-pipeline-design-and-the-latency-budget.md) | The end-to-end perception graph, the interface contract, drawing the latency block diagram, measuring end-to-end latency, and the four integration defects |
| [lecture-notes/02-the-midterm-defense-and-the-architecture-review.md](./02-lecture-notes/02-the-midterm-defense-and-the-architecture-review.md) | The architecture-review format, the perception architecture brief, data association, the robustness gates, defending a number, and the hard-gate consequences |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-draw-the-latency-budget.md](./03-exercises/exercise-01-draw-the-latency-budget.md) | Guided: turn your perception graph into an interface-contract table and a latency block diagram with a measured budget per hop |
| [exercises/exercise-02-perception-latency-probe.py](./03-exercises/exercise-02-perception-latency-probe.py) | Runnable: a probe node that measures sensor-stamp-to-publish latency end-to-end, reports the p50/p95/p99 distribution, and flags budget blowouts |
| [exercises/exercise-03-detection-cluster-association.py](./03-exercises/exercise-03-detection-cluster-association.py) | Runnable: associate 2D detections with 3D clusters into fused objects, with the no-match / double-match failure modes handled |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-defend-the-perception-stack.md](./04-challenges/challenge-01-defend-the-perception-stack.md) | A full midterm-defense rehearsal: present the architecture brief and answer a panel's questions against the rubric |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the perception architecture brief, with a rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for the **Phase 2 milestone** — the fused perception node publishing `/perception/objects` inside a measured latency budget, defended at the first midterm |

## The "inside the budget, in the map frame" promise

C24 uses a recurring marker for every integration that meets its contract. The Week 16 milestone is not "the node publishes objects." It is "the node publishes *fused* objects, *in the map frame*, *inside the latency budget*, *with every component's confidence honored*, all measured." A passing run's self-report looks like this:

```
[perception_node] /perception/objects published @ 31.2 Hz
[perception_node]   fused objects: 3 (2 with 2D+3D association, 1 LiDAR-only)
[perception_node]   red_cup: class=cup conf=0.91 @ map(1.82, -0.41, 0.74)  [2D+3D fused]
[perception_node]   latency: sensor-stamp -> publish p50=21 ms p95=28 ms p99=34 ms
[perception_node]   drift: /odometry/filtered vs ground truth = 0.18 m / 12 m path
[perception_node]   health: lidar_odom fitness=0.94, 0 stale detections rejected this window
```

If the latency p95 is 70 ms, or the detections are in the camera optical frame instead of `map`, or the 2D and 3D detections of the cup never fused, **the milestone is not met** — fix the integration defect, do not paper over it. The point of Week 16 is to make that report ordinary, and to make every number on it a measurement you can defend to a panel.

## A note on what's not here

Week 16 composes the perception stack and defends it. It does **not** cover:

- **Planning, control, or manipulation.** Nav2, MoveIt2, the behavior tree, and the controllers are **Phase 3 (Weeks 17–24)**. This week's output (`/perception/objects`) is the *input* to that work; you build the perception, not what acts on it.
- **The learned policy or the VLA.** The grasp-selecting policy is **Phase 4 (Weeks 25–32)**. This week localizes and classifies objects; it does not decide what to do with them.
- **The full capstone integration.** Standing up the *whole* robot (perception + planning + control + policy + safety) is **Week 40**. This week is the perception slice of that, built and defended early — exactly so Week 40 inherits a validated perception layer instead of building one under capstone pressure.
- **The second midterm and the capstone defense.** Weeks 32 and 48 are the later gates. The architecture-review *format* you learn this week is the same one you face there; this is the rehearsal.

The point of Week 16 is a sharp, load-bearing skill: compose seven weeks of perception into one node, make every seam's contract explicit, measure the latency and drift honestly, and defend the stack to a panel against a rubric. Everything in Phase 3 consumes the `/perception/objects` you publish this week — and the capstone's perception layer *is* this node, hardened.

## Stretch goals

If you finish the regular work early and want to push further:

- Read the **ROS2 Jazzy intra-process composition** docs and convert your perception graph to a single composable-node container, eliminating the inter-process serialization that eats your latency budget: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html>.
- Profile the composed graph with **`ros2 topic delay`** and a tracing tool (`ros2_tracing` / LTTng) to find the single hop that dominates your latency, then optimize it (intra-process, zero-copy, or moving a transform out of the hot path).
- Add a **third detection source** (the OAK-D's on-camera detector, which arrives already associated with depth) and fold it into the association, then re-measure the budget — does the pre-associated detection save you the association hop?
- Record the perception run as a **`ros2 bag`** so the panel can replay your `/perception/objects` and your latency, not just watch a live demo — a bag is the artifact a reviewer can re-open.
- Read a **published perception post-incident report** (an AV or AMR company engineering blog) and map its failure to one of this week's four integration-defect categories.

## Up next

Continue to **Week 17 — Nav2 Architecture and Lifecycle** once your milestone is signed and your perception stack has passed the midterm. Phase 3 takes the `/perception/objects` you publish this week and *acts* on it: Nav2 plans the base around the obstacles you detected, behavior trees orchestrate the task, and the controllers (PID → LQR → MPC) execute it. The latency discipline you build this week becomes the control-loop timing budget; the frame contract becomes the costmap's sensor inputs; the architecture-review format becomes the Phase 3 milestone defense. You have passed the first hard gate. The robot can now *see*. Next, it learns to *move*.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*

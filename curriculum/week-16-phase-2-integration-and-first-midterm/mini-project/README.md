# Mini-Project — The Fused Perception Node (Phase 2 Milestone + First Midterm)

> Compose Weeks 9–15 into **one fused perception node** — IMU + wheel odometry into the EKF, LiDAR/RGB-D into 3D clustering, the camera into a YOLO detector — that publishes a single unified `/perception/objects` (`vision_msgs/Detection3DArray`), with detected objects in the **`map` frame**, inside a measured **end-to-end latency budget** (target 30 ms on Orin Nano; documented otherwise on Path B), with every component's confidence honored. Then **defend it to a panel** at the first midterm. When the panel signs the rubric, Phase 2 is complete.

**Estimated time:** ~14 hours (split across Thursday through Sunday in the suggested schedule).

This is the most important mini-project of Phase 2. It is not a new build — it is the **integration** of seven weeks of perception into one node that turns raw sensors into fused objects. You are not adding a feature this week. You are proving that the parts you built, composed, agree — inside a latency budget, in front of a panel. The deliverable is graded as the **Phase 2 milestone and the first midterm** (10% of the track for the architecture-review writeup, per the assessment matrix, plus the milestone sign-off), and the midterm is a **hard gate**: a failure sends you back to the offending week.

This mini-project **compounds — it is the compounding.** Every prior perception mini-project fed this one: the Week 10 EKF is the motion backbone, the Week 13 YOLO node is the 2D-detection branch, the Week 14 `crunchbot_rgbd` cloud feeds the clustering and the association, the Week 15 `crunchbot_perception3d` clusters-and-odometry are the 3D branch. The syllabus calls this node "the 30-ms perception cycle" and names it one of the three flagship portfolio projects. This week you assemble it for the first time and defend it.

---

## What you will build

A single composed system, brought up under one launch graph, that runs this:

```bash
# Bring up the whole perception stack in one command.
ros2 launch crunch_perception perception.launch.py

# Watch the fused output and the live numbers.
ros2 topic echo /perception/objects
ros2 run crunch_perception latency_probe          # the milestone latency number
```

The node then, continuously and observably:

1. **Estimates state** — the EKF fuses IMU + wheel odometry into `/odometry/filtered` and the `map → odom → base_link` transforms, with honest covariances.
2. **Detects in 3D** — the LiDAR/RGB-D cloud is voxel-filtered, ground-segmented, and clustered into `vision_msgs/Detection3DArray` (Week 15), in the `map` frame.
3. **Detects in 2D** — the camera image runs through the YOLO TensorRT node into `vision_msgs/Detection2DArray` (Week 13).
4. **Fuses** — the data-association node (Exercise 3) matches 2D detections to 3D clusters into single objects (class + position), publishing `/perception/objects` in `map`, with no-match clusters published as `unknown`.
5. **Guards** — the stamp-age gate rejects stale inputs; the ICP health gate inflates the odom covariance on a bad registration; the confidence gate drops low-confidence detections.
6. **Reports** — the latency probe measures sensor-stamp-to-publish p95; a health topic reports the per-component status (EKF drift, ICP fitness, stale-rejection count).

By the end you have a public repo, a launch graph that stands the whole perception stack up, a measured latency budget and drift number, a one-page architecture brief, and a signed midterm.

---

## Why this is a milestone, not a feature

The previous mini-projects each built a component. This one *composes* them, and the composition is the test. The acceptance criteria are the syllabus's: a unified `/perception/objects` in `map`, inside the 30 ms cycle, defended to a panel. The midterm grades the *defense* — the architecture brief, the latency budget, the failure-mode answers — not just the code, because a beautiful node you can't defend is not good enough at a hard gate. A weak milestone here is a weak capstone perception layer in twenty-four weeks; the composition does not heal a broken component, and the panel's job is to find which component is weak by composing everything and seeing what breaks.

---

## Package layout

One umbrella package that composes the rest, plus the artifacts you built this week:

```
crunch_ws/src/
└── crunch_perception/                       # ament_python (the integrator)
    ├── crunch_perception/
    │   ├── __init__.py
    │   ├── fusion_node.py                    # data association -> /perception/objects
    │   ├── association.py                    # Exercise 3 logic, ROS-free + testable
    │   ├── gates.py                          # stamp-age, ICP-health, confidence gates
    │   ├── latency_probe.py                  # Exercise 2, productionized
    │   └── perception_health.py              # per-component health -> /perception/health
    ├── launch/
    │   └── perception.launch.py              # stands the WHOLE perception stack up
    ├── config/
    │   ├── ekf_params.yaml                    # from Week 10
    │   ├── clustering_params.yaml             # from Week 15
    │   └── yolo_params.yaml                    # from Week 13
    ├── perception-brief.md                    # the architecture brief (Lecture 2 §2.4)
    ├── measure_drift.py                        # the drift acceptance measurement
    └── test/
        ├── test_association.py                # no-match, double-match, frame cases
        └── test_gates.py                      # stamp-age, covariance-inflation logic
```

The `crunch_perception` package does not re-implement the EKF, the clustering, the YOLO node, or the RGB-D bring-up — it **depends on** the packages you built in Weeks 9–15 and composes them. Its own code is the integrator: the fusion node, the gates, the latency probe, the health reporter, and the brief.

---

## Functional requirements

### R1 — One launch graph stands the whole perception stack up

`perception.launch.py` brings up: the sensors/sim, the EKF, the `crunchbot_perception3d` clustering + odometry, the YOLO detector, the fusion node, the latency probe, and the health reporter. A single command. No second terminal of manual `ros2 run` calls.

### R2 — Unified `/perception/objects` in the `map` frame

The fusion node publishes `vision_msgs/Detection3DArray` on `/perception/objects`, in the `map` frame, stamped with the originating sensor's acquisition time. Each object carries its 3D position (from the cluster), and — where associated — its class and confidence (from YOLO). No-match clusters are published as `unknown` (an obstacle without a class is still an obstacle); no-match detections are logged, not invented in 3D.

### R3 — Inside the latency budget, measured

`latency_probe.py` measures sensor-stamp-to-publish latency end-to-end, with the whole graph live, and reports p50/p95/p99. Target: p95 ≤ 30 ms on Orin Nano (Path A) or a documented Path-B number. **Report the number you get, not the number you want.** If p95 is 38 ms, the milestone notes it, the latency block diagram says which hop to cut, and the fix is an action item.

### R4 — Correct frames and timing

Detections are transformed into `map` at the *detection's acquisition stamp* via tf2 time-travel (Lecture 1 §1.5), not at `now()`. The frame chain (`map → odom → base_link → sensor`) is valid (REP 105). A reviewer can verify the detections land in the right `map`-frame positions, not shifted by robot motion.

### R5 — The robustness gates are live

`gates.py`: the stamp-age gate rejects detections older than tolerance (and counts the rejections); the ICP-health gate inflates the odom covariance when fitness is low (so the EKF de-weights it); the confidence gate drops low-confidence detections. Feeding a degraded input (kill the LiDAR, force a low-fitness scan) demonstrably triggers the right gate and the fused estimate stays bounded.

### R6 — Data association fuses the streams

The 2D and 3D detections of the same object fuse into one `/perception/objects` entry (class + position), via the Hungarian assignment from Exercise 3. The association rate (% of objects with 2D+3D fusion) is reported.

### R7 — The acceptance numbers, measured honestly

- `latency_probe` reports the end-to-end p95 (target ≤ 30 ms).
- `measure_drift.py` reports the `/odometry/filtered` drift over a measured path vs. ground truth (the early read on the capstone's < 0.5 m / 20 m number).

### R8 — The architecture brief exists and is defended

`perception-brief.md` (Lecture 2 §2.4): the block diagram, the interface-contract table, the latency budget, the failure-mode table, and the measured numbers. It is presented at the midterm and answers the panel's questions.

---

## Rules

- **You may** reuse every package you built in Weeks 9–15, the ROS2 Jazzy docs, and your own exercise and challenge code.
- **You must** target ROS2 **Jazzy** on **Ubuntu 24.04**; `rclpy` for the integrator nodes. The latency target is the Orin Nano (Path A) or a documented Path-B substitution.
- **You must** bring the whole perception stack up with **one launch command**. A bring-up that needs a sequence of manual `ros2 run` calls is an automatic fail — the latency budget is a real number and a manual sequence can't meet it consistently.
- **You must** transform detections at the detection's acquisition stamp (tf2 time-travel), not at `now()`. Transforming at `now()` is a frame/timing defect (R4) and a near-certain panel question.
- **You must** publish no-match clusters as `unknown`, not drop them. An unclassified obstacle is still an obstacle.
- **You must** measure the latency p95 honestly, under load, sensor-stamp to publish, and report the number you get.
- **You must not** hide a bad input — the gates must honestly weight or reject it, and the health topic must report it. A node that silently trusts a bad input fails R5.

---

## Acceptance criteria

- [ ] A public repo named `c24-week-16-crunch-perception-<yourhandle>`.
- [ ] `colcon build` of `crunch_perception` and its dependencies succeeds with no errors.
- [ ] `ros2 launch crunch_perception perception.launch.py` brings up the whole stack in one command.
- [ ] `/perception/objects` publishes `Detection3DArray` in the `map` frame, fused (class + position) where associated, `unknown` for LiDAR-only clusters.
- [ ] `latency_probe` reports the end-to-end p95; the number is recorded in the repo README (target ≤ 30 ms, but report the actual).
- [ ] Detections land in the correct `map`-frame positions (transformed at the detection stamp, not `now()`), verifiable in rviz2.
- [ ] Killing the LiDAR or forcing a low-fitness scan triggers the right gate and the fused estimate stays bounded (demonstrated, with the health topic showing it).
- [ ] `measure_drift.py` reports the drift over a measured path.
- [ ] `colcon test` passes, with at least: `test_association.py` (no-match, double-match, frame cases) and `test_gates.py` (stamp-age, covariance inflation).
- [ ] `perception-brief.md` exists with all five sections and is presented at the midterm.
- [ ] **The midterm is passed:** a panel signs the architecture-review rubric.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What earns them |
|------|-------:|-----------------|
| **One-command bring-up + composition** | 15 | Whole stack up in one launch; all four input branches composing into one node. |
| **Unified `/perception/objects` in `map`** | 20 | Fused objects (class + position) in the `map` frame, correct frame/timing, no-match clusters published as `unknown`. |
| **Latency budget, measured** | 20 | End-to-end p95 measured under load, sensor-stamp to publish; the budget block diagram; honest reporting. |
| **Robustness gates** | 15 | Stamp-age, ICP-health-covariance, and confidence gates live and demonstrated; one bad input doesn't corrupt the output. |
| **Data association** | 10 | 2D+3D fusion via Hungarian assignment; no-match/double-match handled; association rate reported. |
| **The architecture-review defense** | 15 | The brief (5 sections); the panel's questions answered; numbers defended with scripts; the rubric signed. |
| **Tests + docs** | 5 | Association and gate unit tests; clear README with the measured numbers and the brief. |

A submission that publishes objects but transforms them at `now()` (frame/timing defect), or whose latency is asserted not measured, or whose gates are absent, **caps at 50 points** regardless of polish. Correct frames/timing, a measured budget, and honest robustness gates are the milestone's load-bearing properties — the rubric weights them accordingly. And the midterm is a *hard gate*: an unsigned rubric is not a passing milestone, full stop.

---

## How this compounds into the capstone

| Week | What it does with the fused perception node |
|------|---------------------------------------------|
| **17–24 (Phase 3)** | Nav2 plans the base around the obstacles in `/perception/objects`; the behavior tree and controllers act on it. Your output is their input. |
| **32 (second midterm)** | The same architecture-review format, harder — the brief you wrote here is the template. |
| **40 (capstone milestone)** | This node *is* the capstone's perception layer; the 30 ms budget becomes the ≤ 50 ms requirement; the drift number becomes the < 0.5 m / 20 m acceptance gate. |
| **48 (defense)** | The panel reads your perception stack with the same five-layer lens you defended here. |

Build it once, compose it cleanly, measure it honestly, defend it calmly — and it carries you to the capstone. That is why this is a milestone and a hard gate, not a feature.

---

## Implementation guidance — compose in dependency order

This is an *integration* project, and the order you compose in is the difference between a clean bring-up and a tangle. Bring the stack up in dependency order — the same logic as a lifecycle bring-up — verifying each layer before adding the next:

1. **State estimation first.** Bring up the EKF and confirm `/odometry/filtered` and the `map → odom → base_link` transforms are live and correct (`tf2_echo`). Everything downstream needs these transforms; if the frame tree is broken here, every detection lands in the wrong place later and you won't know which layer did it.
2. **The two detection branches, independently.** Bring up the clustering (Week 15) and confirm `/perception/clusters` in `map`; bring up the YOLO node (Week 13) and confirm `/perception/detections_2d`. Verify each *alone* against the EKF transforms before fusing them — a bug in one branch is easy to find now, hard to find after fusion.
3. **The fusion node, with association.** Add `fusion_node` consuming both branches. Confirm `/perception/objects` fuses 2D+3D where the object is in both, and publishes `unknown` for LiDAR-only clusters. Verify the detections land in the right `map`-frame positions (transformed at the detection stamp).
4. **The gates.** Add the stamp-age, ICP-health, and confidence gates. Verify each by forcing its trigger condition (a stale input, a low-fitness scan, a low-confidence detection) and watching the right gate respond.
5. **The probe and the brief last.** Run the latency probe to get the milestone number, run the drift measurement, and assemble the architecture brief. These are the *evidence*, produced once the stack is composed and working.

Composing all at once and then debugging a silent failure across four branches is the slow, painful path. Layer by layer, verified, is how you have a defensible node by Saturday and a calm midterm on Sunday.

## A note on the "30 ms" — and what to do if you miss it

The 30 ms budget is a target, and the milestone asks you to *measure and report* — not to fake. If your honest p95 is 38 ms, here is the senior response, and it is *not* "fudge the number":

- **Report the real number** in the README and the brief. An honest 38 ms with a plan beats a fictional 28 ms that collapses under the panel's "run the probe for me."
- **Diagnose it with the latency block diagram** (Lecture 1 §1.8). Which hop on the critical path dominates? Almost always the detector or the inter-process transport.
- **Apply the highest-value lever** (Lecture 1 §1.11): compose the graph intra-process (often reclaims 5–15 ms for free), then quantize the detector to INT8 if it's still over.
- **If you're on Path B without an Orin Nano**, the syllabus explicitly allows documenting *why* — measure on your hardware, state the target hardware, and note the expected delta. "47 ms on my laptop CPU; the budget is for an Orin Nano with TensorRT, where the YOLO hop drops from 30 ms to 12 ms, bringing the critical path under 30 ms" is a defensible, honest account.

The milestone grades *honest measurement and a credible plan*, not a magic number. A learner who reports 38 ms, shows the budget, names the hop, and states the fix demonstrates more understanding than one who reports a suspiciously round 30 ms with no decomposition. Measure honestly; the panel respects the number you can defend, not the number you wish you had.

## The midterm logistics

Because this is a hard gate, treat the midterm itself as a deliverable with its own preparation, not an afterthought to the build:

- **Schedule it after the build is done**, not during. You want the stack composed, measured, and the brief written *before* you defend. A midterm defended over a half-working graph fails on the live demo.
- **Bring the brief and the scripts.** The brief (block diagram, contract, budget, failure table, numbers) answers most questions before they're asked; the scripts (latency probe, drift) let you answer "run it for me" on the spot.
- **Rehearse the question bank** (Challenge 1) with a peer first. The question you can't answer in rehearsal is the one that fails you live; find it Thursday, not on review day.
- **Expect to be sent back if a component is weak** — and treat that as the system working. The composition is diagnostic; a failed defense that pinpoints "your EKF covariances are dishonest, fix Week 10" is cheaper now than discovering it at the capstone. The gate exists to find the weak component while fixing it is still a resubmission, not a crisis.

## Submission

Push to your public repo, tag it `week-16-midterm`, and open the README with: the launch command, the measured latency p95 and drift, a screenshot of `/perception/objects` in rviz2, and a link to `perception-brief.md`. In your cohort channel, post the repo link. Schedule the midterm with a panel: they read your brief, watch the live fused output, ask the question bank (Challenge 1), and sign — or send you back to the layer that broke. The signed rubric completes Phase 2 and is the gate into Phase 3.

When you've finished, push the repo and take the [quiz](../quiz.md).

# Week 16 Homework

Six problems that turn this week's lectures into the artifacts and measurements your midterm needs. The full set should take about **5 hours**. Work in your Week 16 perception repository so each problem produces a committed artifact you point at during the midterm defense.

The headline deliverable is **Problem 4 — the perception architecture brief**, the one-page artifact you present to the panel. Treat it as a document a reviewer reads and grades, not a journal entry.

Each problem includes a short **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`). Have your composed perception stack (Weeks 9–15) runnable — Problems 1, 2, 3, and 6 run against it.

---

## Problem 1 — The interface-contract audit

**Problem statement.** Bring up your composed perception graph. For **every** seam (producer→consumer edge), record the real topic, type, frame, rate, and QoS from `ros2 topic info -v`, `ros2 topic hz`, and `ros2 topic echo --field header.frame_id`. Build the interface-contract table in `notes/week-16/interface-contract.md` and flag every mismatch.

**Acceptance criteria.**

- `notes/week-16/interface-contract.md` has one row per seam (at least eight), every cell from real introspection.
- A "findings" subsection lists every frame/QoS/rate mismatch (or argues there are none, with evidence).
- At least the `/perception/objects`, `/perception/clusters`, and `/perception/detections_2d` seams are documented with their frames.
- Committed.

**Hint.** `for t in $(ros2 topic list | grep perception); do echo "=== $t ==="; ros2 topic info "$t" -v; done`. The classic finding: a detection topic in the camera optical frame that needs transforming to `map` before fusion.

**Estimated time.** 40 minutes.

---

## Problem 2 — Measure the end-to-end latency under load

**Problem statement.** Run your Exercise-2 latency probe against your *live composed stack* (not `--demo`), with the whole graph working. Record the p50/p95/p99. Then run it again with an artificial extra load (a second YOLO instance, or a stress process on the GPU/CPU) and record how the p95 changes. Document the budget verdict.

**Acceptance criteria.**

- `notes/week-16/latency.md` shows the p50/p95/p99 idle and under load.
- You state the measurement endpoints (sensor stamp → `/perception/objects` publish) and confirm the sensor stamp is carried through the pipeline (not re-stamped with `now()`).
- A budget verdict: inside / over the 30 ms target (or your documented Path-B target), and by how much.
- If over: you name the dominant hop on the critical path (from your latency block diagram) and the lever to cut it.
- Committed.

**Hint.** If the probe reports ~0 ms or "no samples," a stage is re-stamping with `now()` — fix the stamp discipline (Week 5 §3.1) before trusting any number. The under-load p95 is usually the honest one; idle numbers flatter you.

**Estimated time.** 45 minutes.

---

## Problem 3 — Fix a frame/timing defect on purpose

**Problem statement.** In a copy of your fusion node, deliberately transform detections at `now()` instead of the detection's acquisition stamp. Drive the robot (or move the camera) and show the detections land in the *wrong* `map`-frame position, shifted in the direction of motion. Then fix it (transform at the detection stamp via tf2 time-travel) and show they land correctly. Document both.

**Acceptance criteria.**

- `notes/week-16/frame-timing.md` shows the wrong result (detections shifted by robot motion) and the correct result (detections in the right place), ideally with rviz2 screenshots.
- You quantify the error: at your robot's speed, how far off was the `now()` version? (motion × staleness).
- You state the rule in one sentence: transform a detection at its acquisition stamp, not `now()`.
- Committed.

**Hint.** The error is `velocity × (now − detection_stamp)`. At 1 m/s and 50 ms of pipeline latency, that's 5 cm — visible in rviz2, fatal for grasping. The fix is `lookup_transform("map", frame, det.header.stamp, timeout=...)`.

**Estimated time.** 50 minutes.

---

## Problem 4 — The perception architecture brief (headline deliverable)

**Problem statement.** This is the artifact you present at the midterm. Assemble the one-page perception architecture brief (Lecture 2 §2.4) at `notes/week-16/perception-brief.md` with all five sections:

1. **Block diagram** — inputs, stages, output, topic names on the edges (Mermaid or a clean drawing).
2. **Interface-contract table** — from Problem 1.
3. **Latency budget** — the block diagram with measured per-hop costs, the critical path, and the p50/p95/p99 from Problem 2.
4. **Failure-mode table** — one row per failure (LiDAR dropout, ICP degenerate, ambiguous association, stale detection, budget blowout): symptom, gate, degraded behavior.
5. **Measured numbers** — latency p95, drift, association rate, each with the script that produces it.

**Acceptance criteria.**

- `notes/week-16/perception-brief.md` exists with all five sections.
- The latency budget computes the critical path as `max(branches) + tail`, not the sum.
- The failure-mode table names the *specific gate* (stamp-age, ICP-health-covariance, confidence) for each failure, not "it would break."
- Every number is a *measured* number with a named script, not an adjective.
- A peer reviewed it against your running graph and signed off.
- Committed.

**Hint.** This brief is the union of Problems 1 and 2 plus the failure-mode table and the drift number. The failure-mode table is the section that most distinguishes a passing brief — rehearse answering "what happens when X fails" for each row out loud (Challenge 1).

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Implement and test the data association

**Problem statement.** Take your Exercise-3 association logic (or write it). Make `association.py` ROS-free and unit-test it: a known set of clusters and detections with a known correct pairing, plus the no-match cluster (→ `unknown`), the no-match detection (→ logged), and a double-match case (two clusters projecting onto one detection — confirm the Hungarian solver assigns at most one). Document the tests.

**Acceptance criteria.**

- `association.py` is ROS-free (pure functions on cluster/detection data) and importable.
- `test_association.py` covers: the correct pairing, the no-match cluster becomes `unknown` (not dropped), the no-match detection is logged, and the double-match is resolved to a single assignment.
- `notes/week-16/association.md` records the test cases and what each proves.
- Committed.

**Hint.** The double-match test is the important one: build two clusters whose projected boxes both overlap one detection, run the Hungarian assignment, and assert exactly one cluster matches — the solver prevents the assignment double-match (the underlying segmentation error is a separate, upstream bug).

**Estimated time.** 45 minutes.

---

## Problem 6 — Demonstrate a robustness gate

**Problem statement.** Take one robustness gate (the ICP-health-covariance gate is the most illustrative). Wire it so a low ICP fitness inflates the odometry covariance the EKF receives. Then force a low-fitness condition (a degenerate scan, or feed a synthetic low-fitness value) and show the covariance inflate and the EKF de-weight that input — the fused estimate staying bounded instead of corrupting.

**Acceptance criteria.**

- `notes/week-16/robustness-gate.md` shows the odometry covariance at normal fitness and at low fitness (the inflation).
- You demonstrate the EKF de-weighting the bad input (the filtered estimate doesn't jump when a bad scan arrives).
- You state in one sentence why an honest covariance lets the filter ignore a bad input without a hard reject.
- Committed.

**Hint.** `cov_scale = 1.0 if fitness >= min_fitness else 100.0`, applied to the odometry message's covariance diagonal before it reaches the EKF. The EKF reads that covariance and trusts the measurement proportionally less. Echo the `/odometry/filtered` and confirm it stays smooth across a low-fitness scan.

**Estimated time.** 35 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Interface-contract audit | 40 min |
| 2 — Latency under load | 45 min |
| 3 — Fix a frame/timing defect | 50 min |
| 4 — Perception architecture brief (headline) | 1 h 15 min |
| 5 — Data association + tests | 45 min |
| 6 — Robustness gate | 35 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_perception` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — and that `perception-brief.md` is ready to present. Then take the [quiz](./05-quiz.md) with your notes closed, and schedule your midterm defense.

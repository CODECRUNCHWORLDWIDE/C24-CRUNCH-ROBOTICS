# Week 39 Homework

Six problems that drive the measure-first, price-the-tradeoff discipline into your fingers. The full set should take about **6 hours**. Work in a `week-39/` directory in your capstone repo so each problem is a commit you can point a Week 40/48 reviewer to.

The headline deliverable is **Problem 4 — the version-controlled latency budget**, the artifact called out in the syllabus. Treat it as the contract a reviewer reads, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

At the top of your `week-39/README.md`, write the marker line once you've optimized the graph:

```
End-to-end perception→policy cycle on Orin Nano (15 W mode):
  baseline:  148 ms p95   (FAIL — budget is 50 ms)
  optimized:  44 ms p95   (PASS — INT8 detector, FP16 policy, composable container)
  accuracy cost: detector mAP@0.5 0.512 → 0.498  (-1.4 pts, within the 3-pt floor)
```

If you can't fill in those numbers honestly, the homework isn't done.

---

## Problem 1 — The honest baseline

**Problem statement.** Pin your device (`nvpmodel -m 0 && jetson_clocks`, or your Path B cap), warm up, and measure the per-stage p95 of your integrated graph over 500+ cycles. Record the `tegrastats` health summary alongside it.

**Acceptance criteria.**
- `week-39/baseline.md` with a per-stage p95 table and the end-to-end p95, all from 500+ warmed cycles.
- The pinned power mode and `tegrastats` health (GPU clock, `tj@`, power, RAM) are recorded.
- The sum is computed and compared to the 50 ms target.
- Committed.

**Hint.** If the first and second runs disagree by more than a couple ms, you didn't warm up or the device throttled. Re-baseline under pinned, warm conditions (Lecture 1 §5). A baseline you can't reproduce is not a baseline.

**Estimated time.** 45 minutes.

---

## Problem 2 — Diagnose every over-budget stage

**Problem statement.** For each stage over its budget, write a one-line diagnosis: compute-bound or memory-bound, with the *evidence* (the `GR3D_FREQ` reading during that stage and/or the `nsys` memcpy bar). Then name the lever you will apply, from the ladder (Lecture 2 §1).

**Acceptance criteria.**
- `week-39/diagnosis.md` with one row per over-budget stage: stage | p95 | bound type | evidence | planned lever.
- Each diagnosis cites a real profiler observation, not a guess.
- The planned lever matches the diagnosis (no INT8 for a memory-bound stage).
- Committed.

**Hint.** GPU pinned at 99% during the stage → compute-bound → precision lever. GPU idle with a fat memcpy → memory-bound → copy-elimination lever. Getting this wrong wastes the whole next problem (Lecture 1 §4).

**Estimated time.** 45 minutes.

---

## Problem 3 — Quantize the detector and measure both columns

**Problem statement.** Take your detector to INT8 with a representative calibration set (300–1000 frames from your robot's domain), build the engine, and measure the mAP delta on a *held-out* eval set. Decide accept/reject against a floor you declare first.

**Acceptance criteria.**
- `week-39/int8.md` records: calibration set size + source, the floor (declared before measuring), FP16 baseline mAP, INT8 mAP, the delta, and the accept/reject decision.
- The eval set is *distinct* from the calibration set.
- The latency before/after (whole-graph p95) is recorded too — both columns.
- Committed.

**Hint.** Model `verify`/calibration on `exercise-02`. If INT8 drops below the floor, try a better calibration set first (most common fix), then mixed `--int8 --fp16` (keep the head FP16). Don't reach for QAT unless those fail (Lecture 2 §3.4, §4.2).

**Estimated time.** 75 minutes.

---

## Problem 4 — The version-controlled latency budget (headline)

**Problem statement.** Write `week-39/latency-budget.yaml` (or `.md`): the per-stage allocation summing to ≤ 50 ms with headroom, plus the measured p95 per stage and the sum gate. Wire Exercise 3's `check_budget` as a test that fails when the sum regresses. Show it failing on a regressed input and passing on the real one.

**Acceptance criteria.**
- `week-39/latency-budget.{yaml,md}` with budget + measured columns and a sum gate against 50 ms.
- A runnable check (adapted from `exercise-03`) that exits non-zero on a deliberately-regressed measured set and zero on the real one — both outputs pasted into the writeup.
- The worst-offender stage is named by the gate.
- Committed.

**Hint.** The gate's verdict is the *sum* vs the target, not any single stage (Lecture 1 §2). This is the artifact a reviewer reads first; make it the cleanest file in the directory.

**Estimated time.** 60 minutes.

---

## Problem 5 — Eliminate one copy

**Problem statement.** Find one host↔device copy or one ROS2 process-boundary serialization on your critical path and eliminate it (zero-copy allocation, or a composable-node container). Measure the whole-graph p95 before and after. The accuracy cost must be *zero* (outputs bit-identical or within tolerance) — verify that too.

**Acceptance criteria.**
- `week-39/copy-elimination.md` documents the copy (with the `nsys` bar that proved it), the fix, and the before/after whole-graph p95.
- The fix is verified to be accuracy-neutral (outputs match within tolerance).
- The `nsys` bar is gone (or shrunk) in the after-capture.
- Committed.

**Hint.** The most common win is a pointcloud crossing a process boundary — a composable container fix (Lecture 2 §7.2). On Jetson, also check for a needless `cudaMemcpy` of the camera image (Lecture 2 §7.1). This is the rung that often beats INT8 and costs no accuracy.

**Estimated time.** 75 minutes.

---

## Problem 6 — One rejected optimization

**Problem statement.** Apply one optimization that you *expect* might break the accuracy floor — aggressive pruning, INT8 on a precision-sensitive policy, or a resolution drop — measure both columns honestly, and *reject* it with a written rationale. The deliverable is the rejection, not a win.

**Acceptance criteria.**
- `week-39/rejected.md` records the optimization, the latency win it offered, the accuracy cost it incurred, the floor it broke, and the decision to roll back.
- The measurement is real (you actually applied and measured it, not predicted).
- One sentence on what this taught you about your model's sensitivity.
- Committed.

**Hint.** Diffusion policies are more quantization-sensitive than detectors (Lecture 2 §4.2) — INT8 on the policy is a good candidate to find a real floor break. A report that contains a *rejected* optimization is stronger than one with only wins, because it proves you measured instead of hoped.

**Estimated time.** 45 minutes.

---

## Grading rubric (100 points)

| Problem | Points | Full marks |
|---------|-------:|-----------|
| P1 — Honest baseline | 14 | 500+ warmed cycles, pinned mode, `tegrastats` health recorded, reproducible |
| P2 — Diagnose stages | 16 | Each over-budget stage correctly labeled with profiler evidence; lever matches diagnosis |
| P3 — INT8 + both columns | 20 | Representative calib, held-out eval, floor declared first, accept/reject decision |
| P4 — Latency budget artifact | 20 | Budget+measured table, working sum gate (fails on regression), worst-offender named |
| P5 — Eliminate a copy | 18 | Real copy identified with `nsys`, fixed, before/after p95, verified accuracy-neutral |
| P6 — A rejected optimization | 12 | A real measurement of a floor-breaking optimization, rejected with rationale |

**Pass threshold: 75/100.** Note the weighting: P3 and P4 carry the most, because pricing a quantization honestly and enforcing a budget are the two skills Week 40's integration depends on directly. A homework set with a speedup but no accuracy number, or a budget with no working gate, fails those problems regardless of the rest — they're the load-bearing ones.

---

## Why this homework matters

Every problem here is a rehearsal for the capstone. The baseline and diagnosis are how you'll start Week 40's integration. The INT8 measurement is the accuracy-cost answer the Week 48 panel will demand. The budget artifact is the contract that keeps your graph fitting the robot as you add features in Weeks 41–47. The copy elimination is usually the biggest free win on the whole robot. And the rejected optimization is the proof — to a skeptical reviewer — that you measure instead of hope. Nothing here is busywork; it's the difference between a robot that fits its hardware and a demo that only runs when the lab is cold.

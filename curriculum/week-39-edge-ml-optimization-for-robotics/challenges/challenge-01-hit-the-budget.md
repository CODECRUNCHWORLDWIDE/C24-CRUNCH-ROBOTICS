# Challenge 1 — Hit the Budget

**Type:** Hands-on, open-ended, on the target hardware.
**Estimated time:** ~3 hours (profile 45 min, optimize 90 min, report 45 min).
**Difficulty:** Hard — this is the capstone-grade version of the entire week.

---

## The setup

You have a profiled integrated graph (from Exercise 1) that is roughly **3x over** the 50 ms cycle target — two or three stages are red, the sum is ~150 ms p95. Your job is to bring the whole graph under 50 ms p95 on the Orin Nano (or your Path B stand-in), and to produce a report that proves you did it *and* states exactly what accuracy you paid.

This is not "make it fast by any means." It is "make the right cut, prove it with a measurement, and price it honestly." A graph that hits 44 ms p95 by silently dropping the detector to a resolution that misses small objects is a *failure* even though the number looks good — because the accuracy cost was hidden, not measured. The discipline is the grade.

---

## What you must do

1. **Start from a real profile.** Use your Exercise 1 `latency-profile.md` — the per-stage p95s and the compute-vs-memory diagnosis for each over-budget stage. If you skipped Exercise 1, you cannot do this challenge honestly; go back.

2. **Set the accuracy floors first.** Before you optimize anything, write down the floor for each accuracy-bearing stage: e.g. "detector mAP@0.5 ≥ 0.48," "depth RMSE ≤ 0.06 m." These are task decisions, made *before* you know what the optimization will cost, so you cannot rationalize a bad trade after the fact.

3. **Optimize per-stage, by the diagnosis.** Climb the ladder (Lecture 2 §1) for each over-budget stage:
   - A **compute-bound** stage (GPU pinned at 99%) → FP16, then clean re-export, then INT8 PTQ (measure the mAP delta!), then escalate only if the floor breaks.
   - A **memory-bound** stage (GPU idle, fat memcpy bar) → composable container / zero-copy *first*; a model trick will not help a stage that was waiting on memory.
   - You may not apply a fix whose diagnosis does not match the stage. Quantizing a projection stage that has no weights is an automatic finding against you.

4. **Re-measure the whole graph after every change.** The sum of individually-fixed stages is not the graph's number — copies and queue interactions shift. Take the end-to-end Foxglove p95 over 500+ cycles after each change.

5. **Stop when green, with margin.** You want the sum under 50 ms with a few ms of headroom (thermal drift will eat tight margins). Do not over-optimize a stage that is already comfortably under budget.

---

## Acceptance criteria

You pass the challenge if:

- [ ] The optimized graph measures **≤ 50 ms p95** end-to-end (Foxglove cycle latency, 500+ cycles, pinned power mode), with stated margin.
- [ ] **Every** optimization is recorded with both columns: the latency win *and* the measured accuracy cost on a held-out set (or "0 accuracy cost" for the copy-elimination fixes, which is itself a measured claim — the outputs must be bit-identical or within tolerance).
- [ ] Every accuracy-bearing optimization stays **above its pre-declared floor**, or you rolled it back and recorded why.
- [ ] Each fix's diagnosis (compute- vs memory-bound) is stated and *matches* the optimization you applied to it.
- [ ] The report shows the **whole-graph re-measurement** after each change, not just the per-stage estimate.

## Deliverable

A `hit-the-budget.md` report containing:

1. **The starting profile** — per-stage p95, the sum, and the diagnosis for each over-budget stage (lift from Exercise 1).
2. **The accuracy floors**, declared up front.
3. **The optimization log** — one entry per change: stage, diagnosis, lever applied, latency before/after (whole-graph p95), accuracy before/after, accept/reject decision.
4. **The final budget table** — the green version, with margin (the Lecture 1 §2 artifact).
5. **The headline marker line** (the "it fits on the robot" promise from the README):

   ```
   End-to-end perception→policy cycle on Orin Nano (15 W mode):
     baseline:  148 ms p95   (FAIL — budget is 50 ms)
     optimized:  44 ms p95   (PASS — INT8 detector, FP16 policy, composable container)
     accuracy cost: detector mAP@0.5 0.512 → 0.498  (-1.4 pts, within the 3-pt floor)
   ```

Commit it next to your capstone. This report *is* a capstone artifact — it is the evidence, in the Week 48 defense, that your robot's autonomy fits the hardware it runs on.

---

## Stretch

- **Pareto sweep:** redo the optimized graph at three `nvpmodel` power modes and plot latency vs power. Report the cheapest mode that still clears 50 ms — that is the mode that ships, and "we run at 10 W with 6 ms margin" is a strong defense-panel answer.
- **The honest rollback:** find one optimization that *looked* good (big speedup) but broke an accuracy floor, and document the rollback. A report that contains a rejected optimization is *stronger* than one that contains only wins — it proves you measured.
- **Thermal soak:** run the optimized graph for 20 minutes and watch whether the p95 drifts up as the chassis warms (`tj@` in `tegrastats`). If it blows the budget when hot, your margin was a lie told by a cold device. Report the steady-state p95.

# Week 45 Homework

Six deliverables that build your interview muscle and complete the Sprint-4 capstone polish. The full set should take about **6 hours**. Work in a `week-45/` directory in your capstone repo so each deliverable is a commit you can point a Week 47 reviewer to.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

At the top of your `week-45/README.md`, write the marker line from the week overview once you've done the mocks:

```
Mock 1 (system design): 31/40 · weakest: latency budgeting, failure-mode coverage
Mock 2 (technical):     27/40 · weakest: EKF update Jacobian, MPC stability argument
Study plan: 4 topics, 6.5 hours, scheduled before Week 47.
```

If you can't fill those numbers in honestly, the homework isn't done.

---

## Problem 1 — The 90-second elevator stack

**Problem statement.** Write, then *record yourself saying*, a 90-second spoken description of your capstone's full autonomy stack — the "elevator version" from Lecture 1 §9. It must name your sensors, compute target, localization approach, planner, controllers (base and arm), the safety layer, and your single biggest risk. Time it. If it runs over 110 seconds, cut it down.

**Acceptance criteria.**
- `week-45/elevator-stack.md` with the written version (≤ 200 words).
- An audio or video recording (`elevator-stack.m4a`/`.mp4`) of you saying it in ≤ 110 seconds.
- It names every layer: sensors → state estimation → planning → control → policy → safety → biggest risk.
- Committed.

**Hint.** This is your capstone, compressed. Steal the structure from Lecture 1's worked micro-example and swap in *your* components. The biggest-risk sentence is mandatory and the part most people forget.

**Estimated time.** 45 minutes.

---

## Problem 2 — Write the EKF predict step from memory

**Problem statement.** On a blank sheet (or whiteboard), with `exercise-02` closed, write the EKF predict step for your capstone's *own* state vector and motion model — not the textbook unicycle, *yours*. Write `x̂⁻ = f(x̂, u)`, derive your `F = ∂f/∂x`, and write `P⁻ = F P Fᵀ + Q`. Then photograph it and verify it against a small NumPy script.

**Acceptance criteria.**
- `week-45/ekf-predict.md` with a photo/scan of your hand-written predict step and `F` derivation for your robot's state.
- A `week-45/verify_ekf.py` that implements your predict and checks `F` against a finite-difference Jacobian (model the structure on `exercise-02`). It prints `F MATCHES` on success.
- The mean is propagated through your *nonlinear* `f`, not `F x̂`.
- Committed.

**Hint.** If your capstone uses `robot_localization`, your state is the 15-dimensional pose/twist/accel vector — you don't have to derive all of it by hand; derive the 2D pose sub-block `[x, y, θ]` and state that the full filter extends it. The finite-difference check from `exercise-02` is the template for `verify_ekf.py`.

**Estimated time.** 75 minutes.

---

## Problem 3 — Five STAR stories

**Problem statement.** Pick your five flagship projects (Lecture 2 §6.1 suggests a set). Write a two-minute STAR story for each: Situation, Task, Action (the technical meat), Result (a number). Then, under each, list the **three deepest follow-up questions** an interviewer could ask and a one-line answer to each — proving you can defend the story.

**Acceptance criteria.**
- `week-45/star-stories.md` with five stories, each ≤ 250 words, each ending in a quantified Result.
- Each story has three anticipated follow-ups with real answers (not "I'd look it up").
- At least one Result cites a real number from your Week 43 telemetry or Week 44 eval suite.
- No overclaiming: every Action you describe, you can defend with the follow-ups you wrote.
- Committed.

**Hint.** The follow-ups are the real work. For the perception story, the follow-up is "what's the INT8 accuracy cost and how did you calibrate?" For the policy story, it's "why a VLA and not a scripted grasp?" If you can't answer your own follow-up, that's a study-plan item.

**Estimated time.** 75 minutes.

---

## Problem 4 — Run and self-grade both mocks

**Problem statement.** Run the two graded mocks (system-design from `exercise-01`, technical from the mini-project script) with a peer. Fill both rubrics — yours and the interviewer's. Feed the scores into `exercise-03-self-grade-mocks.py` and capture the output.

**Acceptance criteria.**
- `week-45/mock-scorecards.md` with both 40-point scorecards from both graders, for both mocks.
- The self-vs-interviewer **gap** recorded for each mock.
- `week-45/self-grade.txt` — the verbatim output of `exercise-03` with your real numbers.
- The marker line at the top of `week-45/README.md` filled in.
- Committed.

**Hint.** A gap > 4 in your favor isn't a failure of the homework — it's a finding. Note it explicitly: "I rated myself 4 above my interviewer on communication; I'll record my next mock and watch it back." Self-awareness is graded.

**Estimated time.** Covered by the mini-project's mock time; budget 30 minutes here for the write-up and tool run.

---

## Problem 5 — The targeted study plan

**Problem statement.** From the self-grade tool's ranked weakest topics, write a study plan: one row per weak topic, with a *specific* resource, an hour budget, and a *calendar slot* before Week 47.

**Acceptance criteria.**
- `week-45/study-plan.md` with a table: Topic | Why weak | Specific resource | Hours | Scheduled (day + time).
- Total hours ≥ what the self-grade tool budgeted.
- Every resource is specific (a named chapter, notebook, or lecture — not "review controls").
- One closing paragraph naming the single biggest gap and your fix.
- Committed.

**Hint.** "Tedrake Underactuated, LQR chapter, Sat 14–16" is specific. "Get better at controls" is not. The calendar slot is what makes a plan a plan; without it you'll arrive at Week 47 having read nothing.

**Estimated time.** 30 minutes.

---

## Problem 6 — Sprint-4 capstone polish

**Problem statement.** This is the last quiet build sprint. Do three concrete polish tasks: (a) drive your launch graph to **zero warnings** on a clean cold-boot (`ros2 launch ...` with no red text); (b) profile one latency hotspot and tighten it, recording the before/after p95 from your Week 43 dashboard; (c) write the one-paragraph architecture summary you'll read aloud in the Week 48 defense.

**Acceptance criteria.**
- `week-45/polish.md` documenting: the warnings you killed (before/after launch log excerpt), the hotspot you tightened (before/after p95 number), and the architecture-summary paragraph (≤ 150 words).
- The launch graph cold-boots with zero warnings (paste the clean log tail).
- The latency improvement is a real measured number, not an estimate.
- Committed.

**Hint.** Common launch-graph warnings: deprecated QoS overrides, missing `use_sim_time` consistency, lifecycle nodes left unconfigured, TF frame typos. The latency hotspot is often a pointcloud copy crossing a process boundary — a composable container fix (Lecture 2 §6.2) frequently buys the most. Don't add features this week; harden what exists.

**Estimated time.** 90 minutes.

---

## Grading rubric (100 points)

| Problem | Points | Full marks |
|---------|-------:|-----------|
| P1 — Elevator stack | 12 | ≤ 110s recording, all layers + biggest risk named |
| P2 — EKF predict from memory | 20 | Correct hand-derived `F` for your robot; `verify_ekf.py` prints `F MATCHES` |
| P3 — Five STAR stories | 18 | Five quantified stories, each with three defensible follow-ups |
| P4 — Run + self-grade mocks | 20 | Both mocks run with a human; both scorecards; honest gap recorded |
| P5 — Study plan | 15 | Specific resources, hours, calendar slots; total ≥ budget |
| P6 — Sprint-4 polish | 15 | Zero-warning cold-boot; real before/after latency; architecture paragraph |

**Pass threshold: 75/100.** Note the weighting: P2 and P4 carry the most, because writing the EKF from memory and running honest mocks are the two things Week 47 will test directly. A homework set with inflated mock scores or a hand-waved EKF derivation fails those problems regardless of the rest — they're the load-bearing ones.

---

## Why this homework matters

Every problem here is a rehearsal for something three weeks out. The elevator stack is your Week 48 opening line. The EKF derivation is the Week 47 technical centerpiece. The STAR stories are the résumé round. The mocks are the dress rehearsal. The study plan is your prep schedule. The polish is the robot the panel actually watches. Nothing here is busywork — it's the difference between walking into the Week 47 loop prepared and walking in hoping. Do it honestly, find the holes now, and close them while they're cheap.

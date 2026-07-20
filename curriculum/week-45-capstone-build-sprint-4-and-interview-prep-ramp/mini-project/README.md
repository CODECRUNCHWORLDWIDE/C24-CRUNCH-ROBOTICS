# Mini-Project — Two Graded Mock Interviews + a Targeted Study Plan

> **Phase 6 / Week 45 deliverable.** This mini-project is the graded artifact for the interview-prep ramp. It compounds directly into **Week 47**, where you run a full-loop mock with an instructor or senior reviewer. The weakest-topics study plan you produce here is the input to your Week 47 prep — do it honestly or arrive at Week 47 unprepared.

## What you're building

Not code. A **rehearsal record.** By the end of this mini-project you will have:

1. Run **two graded mock interviews** with a peer — one system-design, one technical — each scored against a rubric by *both* you and your interviewer.
2. Produced a **scored self-grade** (via `exercises/exercise-03-self-grade-mocks.py`) that ranks your weakest topics across both mocks.
3. Written a **targeted study plan** — specific topics, specific resources, specific hours, scheduled on specific days before Week 47.
4. Defended **one** capstone decision through three "why" layers (the week's challenge, folded in here as evidence).

The deliverable is a folder, `interview-prep-w45/`, committed alongside your capstone, that a Week 47 reviewer could pick up and immediately understand where you are.

## Why this is the mini-project (and not more robot code)

You have forty-four weeks of robot code. What you *don't* have yet is evidence that you can defend it across a table. The Week 47 full-loop mock and the Week 48 capstone defense are both verbal, adversarial, and timed. A reviewer signs off on your readiness based on whether you can *talk*. This mini-project is the dress rehearsal, and like every dress rehearsal its value is entirely in how seriously you take it. A mock you sandbagged is a lie you tell yourself that the Week 47 reviewer will uncover for free.

## Honoring the compounding chain

Your capstone has been building since Week 41:

- **Week 41** gave you the safety case — your failure-mode answers and the "safety doesn't depend on the smart parts" thesis come from here.
- **Week 42** gave you the hardware/sim-hardening integration day — your "real-sensor noise vs sim" answers come from here.
- **Week 43** gave you the telemetry dashboard — your *numbers* (latency p95, solve time, CPU/GPU load) come from here. When the prober says "how do you know?", you point at a Foxglove panel.
- **Week 44** gave you the twenty-instruction eval suite and the fine-tune — your policy-quality answers and per-instruction success rates come from here.

Every mock answer in this project should reach back into that chain. That's the difference between "I think it's fast" and "p95 is 28 ms, here's the panel."

---

## Part 1 — The system-design mock (graded)

Run `exercises/exercise-01-system-design-mock.md` for real, with a peer, on the clock.

**Setup**
- 45 minutes, timed. A whiteboard. The warehouse-AMR prompt.
- Your peer interviews using the interviewer script in exercise 1; they probe one decision three layers deep and throw the 200-robot curveball.
- You run the seven-phase method out loud.

**Capture**
- The interviewer fills the 10-dimension, 40-point rubric live.
- You fill the *same* rubric immediately after, before seeing theirs.
- Photograph or export your box diagram. It goes in the deliverable folder.

**Grade**
- Compute both totals. Record the **gap** between your self-score and the interviewer's. A gap > 4 in your favor is a self-awareness flag — you're overrating yourself, which is exactly what gets you blindsided in a real loop.

**Deliverable:** `interview-prep-w45/mock1-system-design.md` containing both rubric scorecards, the gap, the box-diagram export, and three sentences on where you froze.

---

## Part 2 — The technical mock (graded)

Now swap energy: this one is math and sensors, not architecture.

**Setup**
- 45 minutes, timed. The prober runs the technical script below.
- Required centerpiece: **"Explain how an EKF works and write the predict step on the board."** You write `x̂⁻ = f(x̂, u)` and `P⁻ = F P Fᵀ + Q` from memory, narrate every symbol, and survive the three standard follow-ups (linearization breakdown, tuning Q/R, EKF-vs-factor-graph). You wrote and verified this in `exercise-02-ekf-predict-on-the-board.py`; now do it on a board with a human watching.

**The technical script (for the prober)**
Ask one from each bucket, in order, ~9 minutes each:
1. **Kinematics:** "Forward kinematics and the Jacobian of a planar 2-link arm — what's the Jacobian *for*?" Probe singularities.
2. **Controls:** "PID vs LQR vs MPC — when each? Is your base controller stable, and how do you argue it?"
3. **Estimation (centerpiece):** "Explain an EKF and write the predict step." Then the three follow-ups.
4. **Coding:** one timed problem — IoU of two AABBs, or voxel-downsample a point cloud, or a sensor-timestamp ring buffer. 10 minutes, narrated.
5. **Résumé deep-dive:** "Walk me through your perception pipeline." Then dig two levels past the STAR story.

**Capture & grade**
- Interviewer and you each fill the 10-dimension technical rubric (below).
- Record the gap, same as Part 1.

**Deliverable:** `interview-prep-w45/mock2-technical.md` with both scorecards, the gap, a photo of your whiteboard EKF predict step, and three sentences on where you froze.

### Technical mock rubric (40 points; 0–4 per dimension)

| # | Dimension | 0 | 2 | 4 |
|---|-----------|---|---|---|
| 1 | Kinematics (FK + Jacobian) | Wrong/blank | FK right, Jacobian shaky | FK + Jacobian + singularity/DLS |
| 2 | Controls trade-offs | Couldn't compare | Named differences | Compared + stability argument |
| 3 | EKF predict (written) | Couldn't write it | Wrote it with errors | Correct, mean via nonlinear f |
| 4 | EKF update / Jacobians | Blank | Partial | Update + H + gain intuition |
| 5 | Sensor-fusion trade-offs | None | Vague | EKF-vs-UKF-vs-factor-graph, when each |
| 6 | Coding correctness | Didn't work | Worked w/ bugs | Correct, edge cases handled |
| 7 | Complexity + clarity | Silent/unclear | Some narration | Stated complexity, clean narration |
| 8 | Résumé STAR story | Rambling | Structured | Tight, specific, with numbers |
| 9 | Deep-dive / no overclaim | Bluffed, caught | Minor overclaim | Defended all; "I'd measure that" at edge |
| 10 | Communication | Designed in silence | Narrated some | Clear, structured throughout |

---

## Part 3 — Self-grade and rank weakest topics

Feed both rubrics into the tool.

```bash
# edit the two SCORES dicts with your real numbers, then:
python3 exercises/exercise-03-self-grade-mocks.py
```

It prints your weighted totals, your band (PASS / BORDERLINE / FAIL at 75% / 60%), and a ranked list of your weakest dimensions with study-hour budgets. Save the output verbatim.

**Deliverable:** `interview-prep-w45/self-grade.txt` — the tool's output, unedited.

---

## Part 4 — The targeted study plan

This is the part that compounds into Week 47. Take the ranked weakest topics and turn each into a concrete, scheduled study block. Vague plans ("get better at controls") are worthless. Specific plans close gaps.

For each weak topic, write a row:

| Topic | Why it's weak (from the mock) | Resource (specific) | Hours | Scheduled |
|-------|-------------------------------|---------------------|------:|-----------|
| EKF update Jacobian | Couldn't derive H for range-bearing on the board | Re-do exercise-02; Labbe EKF notebook §11 | 2.0 | Sat 10–12 |
| MPC stability argument | Said "it's stable" with no terminal-cost reasoning | Tedrake Underactuated, LQR+MPC chapters | 2.0 | Sun 14–16 |
| Latency budgeting | Never tied latency to stopping distance | Re-read Lecture 1 §3.3; instrument my own loop | 1.5 | Sat 16–17.5 |

The plan must total at least the hours the self-grade tool budgeted, every row must name a *specific* resource (not "the internet"), and every row must have a *calendar slot* before Week 47.

**Deliverable:** `interview-prep-w45/study-plan.md` — the table above, filled with your real topics, plus one paragraph: "the single biggest gap the mocks revealed, and what I'm doing about it."

---

## Part 5 — Fold in the challenge

Drop your `defend-<decision>.md` from this week's challenge into the folder as evidence you can hold up under recursive probing. The Week 47 reviewer reads it as a sample of your defense under pressure.

---

## Final deliverable structure

```
interview-prep-w45/
├── README.md                  ← one paragraph: where you are, biggest gap, plan summary
├── mock1-system-design.md     ← both scorecards, gap, box-diagram export, froze-on notes
├── mock2-technical.md         ← both scorecards, gap, whiteboard-EKF photo, froze-on notes
├── self-grade.txt             ← verbatim output of exercise-03
├── study-plan.md              ← scheduled, specific, hours-budgeted study blocks
└── defend-<decision>.md       ← the three-layer "why" transcript from the challenge
```

Commit it alongside your capstone repo.

---

## Grading rubric (100 points)

| Criterion | Points | What full marks looks like |
|-----------|-------:|----------------------------|
| Both mocks actually run, timed, with a human | 20 | Real 45-min mocks, both rubrics filled by two people |
| EKF predict written from memory, correct | 15 | Mean via nonlinear f, covariance via F, narrated |
| Self-grade honest (small self-vs-interviewer gap) | 15 | Gap ≤ 4 on both, or you flag and explain a larger gap |
| Weakest topics correctly identified | 10 | Ranking matches what the transcripts show |
| Study plan specific, scheduled, resourced | 20 | Every row: real resource, real hours, real calendar slot |
| Challenge defense folded in | 10 | Three-layer transcript with a measured/artifact-backed answer |
| Folder complete and committed | 10 | All six files present, README orients a Week-47 reviewer |

**Pass threshold: 75/100.** A mock you didn't actually run, or a study plan with no calendar slots, fails regardless of the other sections — because both are exactly the corners you'd cut under real pressure, and Week 47 will expose them.

---

## A closing note

The temptation is to treat this as paperwork and inflate every score so the folder looks good. Resist it completely. The folder is not for a grader's approval — it's a map of where you'll get hurt in three weeks. An honest 25/40 that you study against beats a fake 38/40 that ambushes you in the Week 47 loop. The whole value of a dress rehearsal is finding the gaps while they're cheap to fix.

# Week 37 Homework

Six problems that drive the VLA-integration and safety discipline into your fingers. The full set should take about **5 hours**. Work in your Week 37 Git repository (the same workspace as the exercises and the `crunch_vla` mini-project) so every problem produces at least one commit you can point to at the Phase 5 milestone in Week 40.

The headline deliverable is **Problem 4 — the language-conditioned failure analysis**, the syllabus's "honest failure documentation." Treat it as a section of your future capstone safety case, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Have a VLA you can run (your week-31 OpenVLA, or an open checkpoint) and an open-vocab detector (OWL-ViT). If you lack GPU access this week, the substitution — run against the Exercise-2/3 stubs extended with your own scenarios — is noted per problem; the *methodology* is the graded part either way.

---

## Problem 1 — De-tokenize and frame-check a real action

**Problem statement.** Load your VLA and run one forward pass on (a real image, "pick up the cup"). Capture the raw model output, de-tokenize/un-normalize it to a 7-vector action using the checkpoint's dataset stats, and identify the **frame** the delta is expressed in. Then do the frame sanity-check from Lecture 2 §3: command a pure +x delta (gate off) and confirm the gripper moves the direction you expect. Write it up in `notes/week-37/action-decode.md`.

**Acceptance criteria.**
- The raw output, the de-normalized 7-vector, and the dataset stats used are recorded.
- You state which frame the delta is in (end-effector / camera / base) and cite where you confirmed it (model card / dataset config).
- The +x sanity-check result is recorded: did the gripper move as expected? If not, what was wrong, and how you fixed the transform.
- Committed.

**Hint.** The OpenVLA repo ships `unnorm_key` / dataset stats with the checkpoint — use them, don't guess. If you have no VLA access, document the de-tokenization *procedure* against the OpenVLA README and explain the frame issue conceptually, labeled as a substitution.

**Estimated time.** 50 minutes.

---

## Problem 2 — Tune the grounding threshold

**Problem statement.** Take your open-vocab grounder (OWL-ViT, or the Exercise-2 stub extended with real-ish scores). Run it on ~10 scenes, some containing the queried object and some not. Sweep the confidence threshold `GROUND_CONF_MIN` and find the value that best separates "object present" from "object absent" (maximizes correct present/absent calls). Write it up in `notes/week-37/threshold-sweep.md` with a small table.

**Acceptance criteria.**
- A table: threshold → (true-present accepted, false-absent accepted) across your scenes.
- A chosen `GROUND_CONF_MIN` with a one-sentence justification (the value below which absent objects start getting confidently boxed).
- One sentence on the cost of setting it too high (rejecting valid instructions) vs. too low (accepting phantom objects).
- Committed.

**Hint.** This threshold is a precision/recall trade-off, exactly like a detector operating point. A too-low threshold is dangerous — it's the absent-object hallucination (mode 5) getting past the gate. Err slightly conservative.

**Estimated time.** 40 minutes.

---

## Problem 3 — Wire the gate to the VLA loop

**Problem statement.** Connect your Exercise-3 gate to a real (or stubbed) VLA proposal on at least one instruction, and produce a logged trace of a full accept and a full reject→fallback, with the actual agreement scores. Write it up in `notes/week-37/gated-loop-trace.md`.

**Acceptance criteria.**
- A trace of one ACCEPT (agreement above threshold, action dispatched) and one REJECT→FALLBACK (three rejections, then classical grasp at the grounded location), with the real agreement numbers.
- The trace shows the *independent* grounding's box and the VLA's target separately, so the disagreement is visible.
- One sentence: which failure mode the reject corresponds to.
- Committed.

**Hint.** If you can't make the real VLA reliably hallucinate on demand, force a reject by feeding the gate a VLA target you've manually offset to the wrong object — the point is to exercise the *gate*, and a forced-wrong target is a legitimate test, clearly labeled.

**Estimated time.** 45 minutes.

---

## Problem 4 — The language-conditioned failure analysis (headline deliverable)

**Problem statement.** This is the syllabus deliverable ("document failure modes" / "honest failure documentation"). Run the three syllabus instructions ("bring the red cup," "move the blue block to the left," "pick up the tool") through your gated loop, N ≥ 8 trials each, and write a failure analysis at `notes/week-37/failure-analysis.md` against this template:

1. **Setup** — the VLA/checkpoint (with hash), the scenes, the success criteria, N per instruction.
2. **Results table** — per instruction: trials, grounded-right, executed-success, success rate, dominant failure mode, intervention (fallback) rate.
3. **The failure taxonomy applied** — for each instruction's dominant failure, classify it (modes 1–5) and explain the mechanism (why did it fail *that* way).
4. **What the gate caught vs. missed** — count of wrong actions the gate rejected (good) vs. wrong outcomes that still happened (e.g., a spatial-relation error that passed the gate).
5. **The one number that matters** — the rate of wrong actions that *reached the actuators* with the gate on (ideally low/zero), the number a safety case quotes.
6. **Next investment** — given the table, the single highest-value fix (more data for a grounding failure? a post-place check for a spatial failure?).

**Acceptance criteria.**
- `notes/week-37/failure-analysis.md` exists, hits all six headings, ~500–700 words.
- The results table has **per-instruction** rates with the grounded/executed split (not aggregate-only).
- Failures are classified by mode with a mechanism, not "it didn't work."
- The "reached the actuators" number is stated explicitly.
- The next-investment item is specific and justified by the data.
- Committed.

**Hint.** If running real trials isn't feasible, run the stub loop with deliberately-injected failures of each mode and report the methodology and the gate's catch/miss — clearly labeled as a stub run. The graded skill is the *honesty and structure* of the analysis.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Spatial relations: measure the weak spot

**Problem statement.** Build a small battery of spatial-relation instructions: "move the block to the {left, right, in front of, behind} the cup," ≥ 3 trials each. Measure the VLA's accuracy *per relation*. Write it up in `notes/week-37/spatial-relations.md`.

**Acceptance criteria.**
- A table: relation → trials → correct → accuracy.
- A statement of which relation is worst, and a hypothesis why (image-frame vs. robot-frame "left"? training-data scarcity?).
- One sentence on why the grounding-agreement gate does *not* catch a spatial-relation error pre-execution.
- Committed.

**Hint.** Be precise about whose "left" you mean — image-left, object-left, or robot-left — and define success accordingly *before* you run, or your accuracy numbers are meaningless. This ambiguity is itself part of why VLAs struggle here.

**Estimated time.** 45 minutes.

---

## Problem 6 — Latency budget for one instruction

**Problem statement.** Time one instruction end-to-end through your loop and break the latency into stages: image capture → VLA forward → de-tokenize → grounding (gate) → MoveIt2 plan → execute-start. Produce a simple per-stage breakdown in `notes/week-37/latency-budget.md` and identify the dominant stage.

**Acceptance criteria.**
- A per-stage latency table (milliseconds) for one instruction, summing to the end-to-end time.
- The dominant stage identified (almost certainly the VLA forward pass).
- One concrete latency-reduction idea (action chunking to amortize? running grounding in parallel with the VLA? quantizing the VLA?) and its expected effect and risk.
- Committed.

**Hint.** Use `time.perf_counter()` around each stage. If you ran the grounding *serially after* the VLA, your idea-for-improvement is obvious: parallelize them (Lecture 2 §6). This is the Week 39 latency-Gantt lesson, rehearsed on one instruction.

**Estimated time.** 45 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — De-tokenize + frame-check | 50 min |
| 2 — Tune the grounding threshold | 40 min |
| 3 — Wire the gate to the loop | 45 min |
| 4 — Failure analysis (headline) | 1 h 15 min |
| 5 — Spatial relations | 45 min |
| 6 — Latency budget | 45 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_vla` [mini-project](./mini-project/README.md) is in the same workspace — the capstone reuses its gate and instruction suite. Then take the [quiz](./quiz.md) with your notes closed.

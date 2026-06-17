# Week 46 Homework

Six deliverables that build the chaos machinery and the postmortems. The full set should take about **6 hours**. Work in a `week-46/` directory in your capstone repo so each deliverable is a commit you can point a Week 48 reviewer to.

The headline deliverables are **Problems 4 and 5 — the two postmortems**, the artifacts the Week 48 panel reads and the Week 47 interviewer probes. Treat them as portfolio pieces, not lab notes.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

At the top of `week-46/README.md`, write the marker lines once you've run the drills:

```
Drill 1 (LiDAR dropout @ T+0):  detected T+1.2s · degraded-mode T+1.4s ·
                                operator alert T+2.1s · safe-abort T+18s  → PASS (< 60s)
Drill 2 (doorway deadlock @ T+0): detected T+8s (3rd replan cycle) · operator-assist
                                  requested T+9s · replanned-around T+41s → PASS (< 60s)
```

If you can't fill in those timestamps honestly from a bag, the homework isn't done.

---

## Problem 1 — The drill design + E-stop proof

**Problem statement.** Write the five-part design (Exercise 1) for both drills, and *prove* the software E-stop path is outside each blast radius by tracing your launch graph.

**Acceptance criteria.**
- `week-46/drill-design.md` with both drills' five parts, measurable hypotheses.
- For each, a written proof the E-stop node is in its own process/executor and subscribes to nothing the fault poisons.
- The reversal command for each injection is given.
- Committed.

**Hint.** The E-stop proof is the part that matters and the part people skip. Actually open the launch file and trace it (Lecture 2 §1). If the E-stop shares a process with anything the LiDAR feeds, you found a single point of failure — fix it before gameday.

**Estimated time.** 50 minutes.

---

## Problem 2 — Wire in the watchdog + health aggregator

**Problem statement.** Productionize Exercise 2 into a ROS2 node in your capstone: per-sensor watchdogs (QoS deadline + staleness), a health aggregator publishing one robot-health topic, DEGRADED vs FAULT logic that the BT and dashboard consume.

**Acceptance criteria.**
- The watchdog detects a `/scan` dropout within 500 ms (deadline event) and the aggregator flips to DEGRADED (camera+imu alive) or FAULT (no exteroceptive sensing).
- `/robot_health` is published and shown on the Foxglove dashboard.
- A test (adapt `exercise-02`) shows the OK/DEGRADED/FAULT logic across the scenarios.
- Committed.

**Hint.** Use the QoS deadline callback for speed *and* the staleness timer as a portable backstop (Lecture 1 §3). The `can_degrade()` encoding is part of your safety case — write it down explicitly.

**Estimated time.** 75 minutes.

---

## Problem 3 — Wire in the deadlock detector + recovery ladder

**Problem statement.** Productionize Exercise 3: a detector that trips on the replan-without-progress conjunction, driving a recovery-ladder BT branch (relax → clear → operator-assist → controlled stop).

**Acceptance criteria.**
- The detector subscribes to your planner's replan count and `/odom`, trips only on the conjunction (not on normal avoidance or waiting).
- The recovery ladder escalates correctly and each rung is operator-detectable on the dashboard.
- A test (adapt `exercise-03`) shows detection and ladder behavior.
- Committed.

**Hint.** The false-positive guard is the whole subtlety: replanning while moving is normal, stationary without replanning is waiting (Lecture 2 §3). Tune the window and thresholds against a *normal* run first so you don't trip on legitimate avoidance.

**Estimated time.** 75 minutes.

---

## Problem 4 — Postmortem: sensor dropout (headline)

**Problem statement.** Run Drill 1 live (or via the harness), bagged, and write the blameless postmortem against the Lecture 2 §7 template.

**Acceptance criteria.**
- `week-46/postmortem-drill-1.md` with: summary + marker line, bag-cited timeline, root cause distinct from contributing factors, what worked, an honest what-didn't, action items (owned, dated, safety-case impact).
- The timeline times come from the rosbag, not memory.
- At least one action item closes a Week 41 hazard-log gap.
- Committed.

**Hint.** The "what didn't" section is the most valuable and the one people leave empty. If nothing surprised you, you either didn't push hard enough or you're not being honest (Lecture 2 §7). A real gap found and turned into an action item is worth more than a clean story.

**Estimated time.** 50 minutes.

---

## Problem 5 — Postmortem: planner deadlock (headline)

**Problem statement.** Run Drill 2 live (or via the harness), bagged, and write the blameless postmortem.

**Acceptance criteria.**
- `week-46/postmortem-drill-2.md` with the full template, marker line, bag-cited timeline.
- Which recovery-ladder rung recovered (and why the earlier rungs did or didn't fire) is explained.
- Root cause (the moved obstacle made the first plan infeasible) distinct from contributing factors (e.g. a too-conservative inflation radius that made the doorway look blocked).
- At least one action item feeding the safety case.
- Committed.

**Hint.** If your robot recovered at rung 1 (relaxed replan), say *why* the conservative plan failed and the relaxed one worked — that's the engineering insight (often an over-tuned inflation radius). If it escalated to operator-assist, that's a pass; explain why autonomy couldn't solve it (Lecture 2 §3, §5).

**Estimated time.** 50 minutes.

---

## Problem 6 — The safety-case feedback loop

**Problem statement.** Take the action items from both postmortems and the surprises from your "what didn't" sections, and update your Week 41 hazard log: new hazard rows, new mitigations, or revised residual-risk ratings.

**Acceptance criteria.**
- `week-46/safety-case-update.md` listing each new/changed hazard-log row with a pointer to the postmortem finding that drove it.
- Every gameday surprise is either now a mitigated hazard or an accepted-and-documented residual risk.
- One paragraph: how this drill changed your confidence in the safety case.
- Committed.

**Hint.** This is the loop that makes the safety case *alive* instead of a document you wrote once (Lecture 2 §7). The unannounced-third-failure stretch goal, if you tried it, is a rich source of new hazard rows.

**Estimated time.** 40 minutes.

---

## Grading rubric (100 points)

| Problem | Points | Full marks |
|---------|-------:|-----------|
| P1 — Drill design + E-stop proof | 14 | Both five-part designs; E-stop proven outside each blast radius |
| P2 — Watchdog + aggregator | 16 | < 500 ms detection; one robot-health signal; DEGRADED/FAULT logic on the dashboard |
| P3 — Deadlock detector + ladder | 16 | Conjunction detection (no false positives); ladder escalates; operator-detectable |
| P4 — Sensor-dropout postmortem | 20 | Blameless, bag-cited, root cause vs factors, honest what-didn't, owned/dated action items |
| P5 — Deadlock postmortem | 20 | Same bar; the recovery-rung analysis explained |
| P6 — Safety-case feedback loop | 14 | Every surprise becomes a mitigated hazard or documented residual risk |

**Pass threshold: 75/100.** Note the weighting: the two postmortems (20 each) carry the most, because explaining a failure blamelessly and feeding it back into the safety case is the skill that separates a robot operator from a robot demoer. A postmortem with a sanitized "what didn't" section, or one whose timeline came from memory instead of a bag, fails those problems regardless of the rest — they're the load-bearing ones.

---

## Why this homework matters

Every problem here is a rehearsal for operating a real robot. The drill design is how an on-call engineer plans a controlled experiment. The watchdog and deadlock detector are the difference between a robot that notices a failure and one that gets lucky. The two postmortems are the artifacts that win the second-round interview — "tell me about a time your robot failed" is *the* question, and you'll have two written, honest, bag-backed answers. And the safety-case loop is how the document you wrote in Week 41 stays true as the robot changes. Nothing here is busywork; it's the difference between a robot you can put in a room with a person and a demo you can only run when nothing goes wrong.
